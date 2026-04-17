from app.payment.models import Payment
from app.packages.models import Package, Subscription
from typing import Optional, Dict
from uuid import UUID
from decimal import Decimal
from datetime import datetime, timezone
import requests
from app import settings
from fastapi import HTTPException, status
import logging
from urllib.parse import urlencode
from app.accounts.models import User
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class PaymentService:

    def __init__(self):
        from app.core.dependency_injection import service_locator
        self.service_locator = service_locator

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }

    def _make_request(self, method: str, endpoint: str, payload: Optional[Dict] = None) -> Dict:
        url = f"{settings.PAYSTACK_BASE_URL}/{endpoint}"
        try:
            response = requests.request(
                method, url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(
                f"Paystack API request failed: {str(e)} - Endpoint: {endpoint}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Payment gateway request failed: {str(e)}"
            )

    def _get_payment(self, db, **filters) -> Optional[Payment]:
        return self.service_locator.general_service.filter_data(
            db=db, filter_values=filters, model=Payment, single_record=True
        )

    def _mark_payment_failed(self, db, payment: Payment, reason: str = None) -> None:
        update = {"status": Payment.STATUS.FAILED}
        if reason:
            update["failure_reason"] = reason
        self.service_locator.general_service.update_data(
            db=db, key=payment.id, data=update, model=Payment
        )
        self.service_locator.general_service.update_data(
            db=db, key=payment.subscription_id, model=Subscription,
            data={"payment_status": Subscription.PAYMENT_STATUS.FAILED}
        )

    def _finalize_successful_payment(self, db, payment: Payment) -> None:
        self.service_locator.general_service.update_data(
            db=db, key=payment.id,
            data={"status": Payment.STATUS.SUCCESS,
                  "paid_at": datetime.now(timezone.utc)},
            model=Payment
        )
        self.service_locator.package_service.activate_subscription(
            db, str(payment.subscription_id)
        )
        self.disable_payment_page(str(payment.id))

    def create(self, db: Session, user_id: str, subscription_id: str, payment_method: str,
               phone_number: str = None, provider: str = None, email: str = None,
               skip_ussd: bool = False) -> Payment:

        try:
            subscription = self.service_locator.general_service.filter_data(
                db=db, filter_values={
                    "id": subscription_id, "user_id": user_id},
                model=Subscription, single_record=True
            )
            if not subscription:
                raise ValueError(f"Subscription {subscription_id} not found")

            if subscription.payment_status == Subscription.PAYMENT_STATUS.PAID:
                raise ValueError("Subscription already paid for")

            package = self.service_locator.general_service.filter_data(
                db=db, filter_values={"id": subscription.package_id},
                model=Package, single_record=True
            )
            if not package:
                raise ValueError("Package not found")

            import uuid as uuid_module
            transaction_id = f"TXN-{uuid_module.uuid4().hex[:12].upper()}"

            payment_data = {
                "user_id": user_id,
                "subscription_id": subscription_id,
                "amount": package.price,
                "currency": Payment.CURRENCY.GHS,
                "payment_method": payment_method,
                "provider": provider,
                "status": Payment.STATUS.ONGOING,
                "transaction_id": transaction_id,
                "payment_metadata": {
                    "phone_number": phone_number,
                    "package_name": package.name,
                }
            }

            payment = self.service_locator.general_service.create_data(
                db=db, model=Payment, data=payment_data
            )

            if payment_method == Payment.PAYMENT_METHOD.MOMO and phone_number and provider and email and not skip_ussd:
                try:
                    paystack_response = self.request_payment(
                        amount=Decimal(package.price),
                        email=email,
                        phone=phone_number,
                        provider=provider
                    )
                    update = {
                        "ussd_reference": paystack_response.get("data", {}).get("reference"),
                        "payment_metadata": {
                            **payment_data["payment_metadata"],
                            "paystack_response": paystack_response.get("data")
                        }
                    }
                    if paystack_response.get("data", {}).get("status") == "send_otp":
                        update["initiate_payment_prompt"] = True

                    self.service_locator.general_service.update_data(
                        db=db, key=payment.id, data=update, model=Payment
                    )
                    db.refresh(payment)
                except Exception as e:
                    logger.error(f"Paystack initiation failed: {e}")
                    self._mark_payment_failed(db, payment, str(e))
                    db.commit()
                    raise

            db.commit()
            db.refresh(payment)
            logger.info(
                f"Created payment {payment.id} for subscription {subscription_id}")
            return payment

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create payment: {e}")
            raise

    def verify_payment(self, db: Session, payment: Payment) -> Payment:

        try:
            response = self._make_request(
                "GET", f"transaction/verify/{payment.web_page_reference}")

            if response.get("status") is True:
                data = response.get("data", {})
                is_success = data.get("status") == "success"

                if is_success:
                    self._finalize_successful_payment(db, payment)
                    if payment.initiate_payment_prompt:
                        self.service_locator.general_service.update_data(
                            db=db, key=payment.id,
                            data={"initiate_payment_prompt": False},
                            model=Payment
                        )
                else:
                    self._mark_payment_failed(db, payment)

                self.service_locator.general_service.update_data(
                    db=db, key=payment.id,
                    data={"payment_metadata": {
                        **(payment.payment_metadata or {}),
                        "paystack_verification_response": data
                    }},
                    model=Payment
                )

                db.commit()
                logger.info(
                    f"Verified payment {payment.id}: {data.get('status')}")
                return self._get_payment(db, id=payment.id)
            else:
                raise ValueError(
                    f"Verification failed: {response.get('message')}")

        except Exception as e:
            logger.error(f"Failed to verify payment: {e}")
            raise

    def submit_otp(self, db: Session, subscription_id: str, otp: str, user_id: str) -> Payment:
        payment = (
            db.query(Payment)
            .filter(
                Payment.subscription_id == UUID(subscription_id),
                Payment.user_id == user_id,
                Payment.status == Payment.STATUS.ONGOING,
            )
            .order_by(Payment.created_at.desc())
            .first()
        )
        if not payment:
            raise ValueError(
                f"Payment for subscription {subscription_id} not found")
        if not payment.initiate_payment_prompt:
            raise ValueError("This payment does not require OTP")
        if not payment.ussd_reference:
            raise ValueError("Payment reference not found")

        try:
            paystack_response = self.initiate_otp(
                otp=otp, reference=payment.ussd_reference)
            is_success = paystack_response.get(
                "data", {}).get("status") == "success"

            update_data = {
                "initiate_payment_prompt": False,
                "payment_metadata": {
                    **(payment.payment_metadata or {}),
                    "otp_submitted": True,
                    "paystack_final_response": paystack_response.get("data")
                }
            }

            if is_success:
                self._finalize_successful_payment(db, payment)
            else:
                update_data["status"] = Payment.STATUS.FAILED
                update_data["failure_reason"] = paystack_response.get(
                    "message", "OTP verification failed")
                self._mark_payment_failed(
                    db, payment,
                    paystack_response.get("message", "OTP verification failed")
                )
                self.service_locator.general_service.update_data(
                    db=db, key=payment.id, data={"payment_metadata": update_data["payment_metadata"]}, model=Payment
                )

            db.commit()
            logger.info(
                f"OTP submission for subscription {subscription_id}: {'success' if is_success else 'failed'}")
            return self._get_payment(db, subscription_id=UUID(subscription_id))

        except Exception as e:
            db.rollback()
            logger.error(f"OTP submission failed: {e}")
            self.service_locator.general_service.update_data(
                db=db, key=payment.id,
                data={"status": Payment.STATUS.FAILED, "failure_reason": str(
                    e), "initiate_payment_prompt": False},
                model=Payment
            )
            db.commit()
            raise

    def request_payment(self, amount: Decimal, email: str, phone: str, provider: str) -> Dict:
        return self._make_request("POST", "charge", {
            "amount": int(amount * 100),
            "email": email,
            "currency": Payment.CURRENCY.GHS,
            "mobile_money": {
                "phone": phone if settings.PAYSTACK_LIVE_MODE else settings.PAYSTACK_TEST_MOBILE_NUMBER,
                "provider": provider,
            },
        })

    def initiate_otp(self, otp: str, reference: str) -> Dict:
        return self._make_request("POST", "charge/submit_otp", {"otp": otp, "reference": reference})

    def create_payment_link(self, db: Session, payment_id: str, user_id: UUID,
                            description: str = None, customer_name: str = None) -> dict:

        try:
            payment = self._get_payment(db, id=UUID(payment_id))
            if not payment:
                raise ValueError(f"Payment {payment_id} not found")

            redirect_url = f"{settings.API_BASE_URL}/payments/redirect/{payment_id}"
            package_name = payment.subscription.package.name

            payload = {
                "name": f"Payment for {package_name}",
                "amount": int(Decimal(payment.amount) * 100),
                "description": description or f"Payment for {package_name} subscription",
                "fixed_amount": True,
                "slug": str(payment.id),
                "type": "payment",
                "redirect_url": redirect_url,
                "success_message": "Payment successful",
                "metadata": {
                    "payment_id": str(payment_id),
                    "subscription_id": str(payment.subscription_id),
                    "user_id": str(user_id),
                }
            }
            if customer_name:
                payload["customer_name"] = customer_name

            response = self._make_request("POST", "page", payload)

            if response.get("status") is True:
                page_data = response.get("data", {})
                payment_link = page_data.get("url") or self.get_paystack_payment_url(
                    db, str(payment.id), str(user_id))
                self.service_locator.general_service.update_data(
                    db=db, key=payment.id,
                    data={"payment_link": payment_link, "ussd_reference": ""},
                    model=Payment
                )
                db.commit()
                return {
                    "payment_link": payment_link,
                    "page_slug": str(payment.id),
                    "payment_id": payment_id,
                    "status": "created",
                }
            else:
                raise ValueError(
                    f"Failed to create payment link: {response.get('message')}")

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create payment link: {e}")
            raise

    def get_paystack_payment_url(self, db: Session, slug: str, user_id: str) -> str:
        user: User = self.service_locator.general_service.filter_data(
            db=db, filter_values={"id": user_id}, model=User, single_record=True
        )
        params = {
            k: v for k, v in {
                "email": user.email or "info@kayaktechgroup.com",
                "first_name": user.first_name,
                "last_name": user.last_name,
            }.items() if v
        }
        base_url = f"https://paystack.shop/pay/{slug}"
        return f"{base_url}?{urlencode(params)}" if params else base_url

    def get_payment(self, db: Session, payment_id: str, user_id: str) -> Optional[Payment]:

        try:
            return self._get_payment(db, id=UUID(payment_id), user_id=user_id)
        except ValueError:
            return None

    def list_user_payments(self, db: Session, user_id: str, status: str = None, page: int = 1, limit: int = 10) -> Dict:

        filter_values = {"user_id": user_id}
        if status:
            filter_values["status"] = status
        payments = self.service_locator.general_service.filter_data(
            db=db, filter_values=filter_values, model=Payment, single_record=False
        )
        total = len(payments)
        start = (page - 1) * limit
        return {
            "payments": payments[start:start + limit],
            "total": total,
            "page": page,
            "limit": limit
        }

    def disable_payment_page(self, slug: str) -> dict:
        return self._make_request("PUT", f"page/{slug}", {"active": False})
