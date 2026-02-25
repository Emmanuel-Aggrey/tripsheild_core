from app.payment.models import Payment
from app.packages.models import Package, Subscription
from app.database import SessionLocal
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

    def initiate_payment(self, user_id: str, subscription_id: str, payment_method: str,
                         phone_number: str = None, provider: str = None, email: str = None,
                         skip_ussd: bool = False) -> Payment:
        db = SessionLocal()
        try:
            subscription = self.service_locator.general_service.filter_data(
                db=db, filter_values={
                    "id": subscription_id, "user_id": user_id},
                model=Subscription, single_record=True
            )
            if not subscription:
                raise ValueError(f"Subscription {subscription_id} not found")

            if subscription.payment_status == Subscription.PAYMENT_STATUS.PAID:
                raise ValueError("Package already paid for")

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
                    "email": email,
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
                    self.service_locator.general_service.update_data(
                        db=db, key=payment.id,
                        data={"status": Payment.STATUS.FAILED,
                              "failure_reason": str(e)},
                        model=Payment
                    )
                    db.commit()
                    raise

            db.commit()
            db.refresh(payment)
            logger.info(
                f"Created payment {payment.id} for subscription {subscription_id}")
            return payment

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to initiate payment: {e}")
            raise
        finally:
            db.close()

    def verify_payment(self, payment: Payment) -> Payment:
        db = SessionLocal()
        try:
            response = self._make_request(
                "GET", f"transaction/verify/{payment.web_page_reference}")

            if response.get("status") is True:
                data = response.get("data", {})
                payment_status = Payment.STATUS.SUCCESS if data.get(
                    "status") == "success" else Payment.STATUS.FAILED

                update_data = {
                    "status": payment_status,
                    "payment_metadata": {
                        **(payment.payment_metadata or {}),
                        "paystack_verification_response": data
                    }
                }

                if payment_status == Payment.STATUS.SUCCESS:
                    update_data["paid_at"] = datetime.now(timezone.utc)
                    if payment.initiate_payment_prompt:
                        update_data["initiate_payment_prompt"] = False
                    self.service_locator.package_service.activate_subscription(
                        str(payment.subscription_id))

                updated = self.service_locator.general_service.update_data(
                    db=db, key=payment.id, data=update_data, model=Payment
                )
                logger.info(
                    f"Verified payment {payment.id}: {data.get('status')}")
                return updated
            else:
                raise ValueError(
                    f"Verification failed: {response.get('message')}")

        except Exception as e:
            logger.error(f"Failed to verify payment: {e}")
            raise
        finally:
            db.close()

    def submit_otp(self, payment_id: str, otp: str, user_id: str) -> Payment:
        db = SessionLocal()
        try:
            payment = self._get_payment(
                db, id=UUID(payment_id), user_id=user_id)
            if not payment:
                raise ValueError(f"Payment {payment_id} not found")
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
                    "status": Payment.STATUS.SUCCESS if is_success else Payment.STATUS.FAILED,
                    "initiate_payment_prompt": False,
                    "payment_metadata": {
                        **(payment.payment_metadata or {}),
                        "otp_submitted": True,
                        "paystack_final_response": paystack_response.get("data")
                    }
                }

                if is_success:
                    update_data["paid_at"] = datetime.now(timezone.utc)
                else:
                    update_data["failure_reason"] = paystack_response.get(
                        "message", "OTP verification failed")

                updated = self.service_locator.general_service.update_data(
                    db=db, key=UUID(payment_id), data=update_data, model=Payment
                )

                if is_success:
                    self.service_locator.package_service.activate_subscription(
                        str(payment.subscription_id))

                logger.info(
                    f"OTP submission for payment {payment_id}: {'success' if is_success else 'failed'}")
                return updated

            except Exception as e:
                logger.error(f"OTP submission failed: {e}")
                self.service_locator.general_service.update_data(
                    db=db, key=UUID(payment_id),
                    data={"status": Payment.STATUS.FAILED, "failure_reason": str(
                        e), "initiate_payment_prompt": False},
                    model=Payment
                )
                db.commit()
                raise

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to submit OTP: {e}")
            raise
        finally:
            db.close()

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

    def create_payment_link(self, payment_id: str, user_id: UUID,
                            description: str = None, customer_email: str = None,
                            customer_name: str = None) -> dict:
        db = SessionLocal()
        try:
            payment = self._get_payment(db, id=UUID(payment_id))
            if not payment:
                raise ValueError(f"Payment {payment_id} not found")

            redirect_url = f"{settings.CORE_CONSUMER_API_URL}/payment/redirect/{payment_id}"
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
            if customer_email:
                payload["customer_email"] = customer_email
            if customer_name:
                payload["customer_name"] = customer_name

            response = self._make_request("POST", "page", payload)

            if response.get("status") is True:
                payment_link = self.get_paystack_payment_url(
                    str(payment.id), str(user_id))
                self.service_locator.general_service.update_data(
                    db=db, key=payment.id,
                    data={"payment_link": payment_link, "ussd_reference": ""},
                    model=Payment
                )
                return {
                    "payment_link": payment_link,
                    "page_slug": str(payment.id),
                    "payment_id": payment_id,
                    "ussd_reference": "",
                    "status": "created",
                }
            else:
                raise ValueError(
                    f"Failed to create payment link: {response.get('message')}")

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create payment link: {e}")
            raise
        finally:
            db.close()

    def get_paystack_payment_url(self, slug: str, user_id: str) -> str:
        db = SessionLocal()
        try:
            user = self.service_locator.general_service.filter_data(
                db=db, filter_values={"id": user_id}, model=User, single_record=True
            )
            name_parts = (user.username or "").split(maxsplit=1)
            params = {
                "email": user.email,
                "first_name": name_parts[0] if name_parts else "",
                "last_name": name_parts[1] if len(name_parts) > 1 else "",
            }
            base_url = f"https://paystack.shop/pay/{slug}"
            return f"{base_url}?{urlencode(params)}" if params.get("email") else base_url
        finally:
            db.close()

    def get_payment(self, payment_id: str, user_id: str) -> Optional[Payment]:
        db = SessionLocal()
        try:
            return self._get_payment(db, id=UUID(payment_id), user_id=user_id)
        except ValueError:
            return None
        finally:
            db.close()

    def list_user_payments(self, user_id: str, status: str = None, page: int = 1, limit: int = 10) -> Dict:
        db = SessionLocal()
        try:
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
        finally:
            db.close()

    def update_payment_page(self, slug: str, active: bool = None, redirect_url: str = None) -> dict:
        payload = {}
        if active is not None:
            payload["active"] = active
        if redirect_url:
            payload["redirect_url"] = redirect_url
        return self._make_request("PUT", f"page/{slug}", payload)

    def disable_payment_page(self, slug: str) -> dict:
        return self._make_request("PUT", f"page/{slug}", {"active": False})
