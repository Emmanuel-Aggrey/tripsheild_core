from fastapi import APIRouter, HTTPException, Request, Depends, Query, status
from fastapi.responses import RedirectResponse
from fastapi_pagination import Page, Params
from fastapi_pagination.ext.sqlalchemy import paginate as sa_paginate
import requests
from app import settings
import logging
import hashlib
import hmac
import json
from datetime import datetime, timezone
from fastapi_utils.cbv import cbv
from app.dependencies import get_db
from app.accounts.schemas import UserSchema
from sqlalchemy.orm import Session
from app.payment.models import Payment
from app.authentication.utils import get_current_active_user
from app.core.dependency_injection import service_locator
from app.payment.schemas import (
    BuySubscriptionRequestSchema,
    InitiatePaymentRequestSchema,
    SubmitOtpRequestSchema,
    PaymentResponseSchema,
)
from app.packages.models import Subscription

logger = logging.getLogger(__name__)

router = APIRouter()


@cbv(router)
class PaymentView:
    db: Session = Depends(get_db)
    current_user: UserSchema = Depends(get_current_active_user)

    @router.post("/buy/", status_code=status.HTTP_201_CREATED)
    def buy_subscription(self, payload: BuySubscriptionRequestSchema):
        user_id = str(self.current_user.id)

        if service_locator.general_service.filter_data(
            db=self.db, model=Subscription,
            filter_values={
                "user_id": user_id,
                "package_id": payload.package_id,
                "status": Subscription.STATUS.ACTIVE,
            },
            single_record=True,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Active subscription already exists for this package",
            )

        try:
            subscription = service_locator.package_service.subscribe_to_package(
                user_id=user_id,
                package_id=str(payload.package_id),
                auto_renew=payload.auto_renew,
            )

            payment = service_locator.payment_service.initiate_payment(
                user_id=user_id,
                subscription_id=str(subscription.id),
                payment_method=payload.payment_method.value,
                phone_number=payload.phone_number,
                provider=payload.provider.value if payload.provider else None,
                email=str(payload.email or self.current_user.email),
                skip_ussd=payload.create_web_link,
            )

            response = {"subscription": subscription, "payment": payment}

            if payload.create_web_link:
                response["payment_page"] = service_locator.payment_service.create_payment_link(
                    payment_id=str(payment.id),
                    user_id=self.current_user.id,
                    customer_email=str(
                        payload.email or self.current_user.email),
                    customer_name=self.current_user.username,
                )

            return response
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.post("/", response_model=PaymentResponseSchema, status_code=status.HTTP_201_CREATED)
    def initiate_payment(self, payload: InitiatePaymentRequestSchema):
        try:
            return service_locator.payment_service.initiate_payment(
                user_id=str(self.current_user.id),
                subscription_id=str(payload.subscription_id),
                payment_method=payload.payment_method.value,
                phone_number=payload.phone_number,
                provider=payload.provider.value if payload.provider else None,
                email=str(payload.email or self.current_user.email),
                skip_ussd=payload.skip_ussd,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.post("/{payment_id}/otp/", response_model=PaymentResponseSchema)
    def submit_otp(self, payment_id: str, payload: SubmitOtpRequestSchema):
        try:
            return service_locator.payment_service.submit_otp(
                payment_id=payment_id,
                otp=payload.otp,
                user_id=str(self.current_user.id),
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.get("/my-payments/", response_model=Page[PaymentResponseSchema])
    def list_my_payments(
        self,
        payment_status: str | None = Query(default=None, alias="status"),
        params: Params = Depends(),
    ):
        queryset = self.db.query(Payment).filter(
            Payment.user_id == str(self.current_user.id))
        if payment_status:
            queryset = queryset.filter(Payment.status == payment_status)
        return sa_paginate(self.db, queryset, params)

    @router.post("/{payment_id}/verify/", response_model=PaymentResponseSchema)
    def verify_payment(self, payment_id: str):
        payment = service_locator.general_service.get_data_by_id(
            db=self.db, key=payment_id, model=Payment
        )
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        if str(payment.user_id) != str(self.current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        if not payment.ussd_reference and not payment.web_page_reference:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No reference found")

        try:
            return service_locator.payment_service.verify_payment(payment)
        except Exception as e:
            logger.error(f"Error verifying payment: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Internal server error")

    @router.get("/{payment_id}/", response_model=PaymentResponseSchema)
    def get_payment(self, payment_id: str):
        payment = service_locator.payment_service.get_payment(
            payment_id=payment_id, user_id=str(self.current_user.id)
        )
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        return payment


@router.get("/redirect/{payment_id}/")
async def payment_redirect(request: Request, payment_id: str, db: Session = Depends(get_db)):
    try:
        reference = request.query_params.get("reference")
        payment = service_locator.general_service.get_data_by_id(
            db=db, key=payment_id, model=Payment
        )
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        result_status = "pending"

        if reference:
            service_locator.general_service.update_data(
                db=db, key=payment.id,
                data={"web_page_reference": reference}, model=Payment
            )
            try:
                response = requests.get(
                    f"{settings.PAYSTACK_BASE_URL}/transaction/verify/{reference}",
                    headers={
                        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"},
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()

                if data.get("data", {}).get("status") == "success":
                    service_locator.general_service.update_data(
                        db=db, key=payment.id,
                        data={"status": Payment.STATUS.SUCCESS,
                              "paid_at": datetime.now(timezone.utc)},
                        model=Payment
                    )
                    service_locator.package_service.activate_subscription(
                        str(payment.subscription_id))
                    service_locator.payment_service.disable_payment_page(
                        str(payment.id))
                    result_status = "success"
                else:
                    service_locator.general_service.update_data(
                        db=db, key=payment.id,
                        data={"status": Payment.STATUS.FAILED}, model=Payment
                    )
                    result_status = "failed"
            except Exception as e:
                logger.error(f"Payment verification error: {str(e)}")
                result_status = "error"

        frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
        return RedirectResponse(
            url=f"{frontend_url}/payment/result?status={result_status}&payment_id={payment_id}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in payment redirect: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/callback/")
async def paystack_callback(request: Request, db: Session = Depends(get_db)):
    try:
        paystack_signature = request.headers.get("x-paystack-signature")
        if not paystack_signature:
            raise HTTPException(status_code=400, detail="No signature")

        request_body = await request.body()
        if not request_body:
            raise HTTPException(status_code=400, detail="Empty body")

        computed_signature = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
            request_body, hashlib.sha512
        ).hexdigest()

        if not hmac.compare_digest(computed_signature, paystack_signature):
            raise HTTPException(status_code=400, detail="Invalid signature")

        ip_address = request.headers.get(
            "x-forwarded-for", "").split(",")[0].strip()
        if ip_address not in settings.PAYSTACK_VALID_IP_ADDRESSES:
            raise HTTPException(status_code=403, detail="Unauthorized")

        payload = json.loads(request_body.decode("utf-8"))
        data = payload.get("data", {})
        payment_status = data.get("status")
        reference = data.get("reference")

        if not all([payment_status, reference]):
            raise HTTPException(status_code=400, detail="Missing fields")

        payment = (
            service_locator.general_service.get_data_by_field(
                db=db, field="web_page_reference", value=reference, model=Payment
            ) or service_locator.general_service.get_data_by_field(
                db=db, field="ussd_reference", value=reference, model=Payment
            )
        )

        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        if payment.status == Payment.STATUS.SUCCESS:
            return {"message": "Already processed"}

        if payment_status == "success":
            service_locator.general_service.update_data(
                db=db, key=payment.id,
                data={"status": Payment.STATUS.SUCCESS,
                      "paid_at": datetime.now(timezone.utc)},
                model=Payment
            )
            service_locator.package_service.activate_subscription(
                str(payment.subscription_id))
            service_locator.payment_service.disable_payment_page(
                str(payment.id))
        else:
            service_locator.general_service.update_data(
                db=db, key=payment.id,
                data={"status": Payment.STATUS.FAILED}, model=Payment
            )

        return {"message": "Processed", "payment_id": str(payment.id)}

    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Callback error: {str(e)}")
        raise HTTPException(status_code=500, detail="Server error")
