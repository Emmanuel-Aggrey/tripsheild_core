from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import APIRouter, HTTPException, Request, Depends, status
import requests
from app import settings
import logging
import hashlib
import hmac
import json
from fastapi_utils.cbv import cbv
from app.dependencies import get_db
from app.accounts.schemas import UserSchema
from sqlalchemy.orm import Session
from app.payment.models import Payment
from app.packages.models import Subscription
from app.authentication.utils import get_current_active_user
from app.core.dependency_injection import service_locator
from app.payment.schemas import (
    BuySubscriptionRequestSchema,
    SubmitOtpRequestSchema,
    PaymentResponseSchema,
)
from uuid import UUID

logger = logging.getLogger(__name__)

router = APIRouter()


@cbv(router)
class PaymentView:
    db: Session = Depends(get_db)
    current_user: UserSchema = Depends(get_current_active_user)

    @router.post("/{subscription_id}/", status_code=status.HTTP_201_CREATED,
                 response_model=PaymentResponseSchema)
    def create(self, subscription_id: UUID, payload: BuySubscriptionRequestSchema):
        user_id = str(self.current_user.id)

        if service_locator.general_service.filter_data(
            db=self.db,
            model=Payment,
            filter_values={
                "subscription_id": subscription_id,
                "status": Payment.STATUS.SUCCESS,
            },
            single_record=True
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Subscription already paid"
            )

        try:

            payment = service_locator.payment_service.create(
                db=self.db,
                user_id=user_id,
                subscription_id=subscription_id,
                payment_method=payload.payment_method.value,
                phone_number=payload.phone_number,
                provider=payload.provider.value if payload.provider else None,
                email=str(payload.email or self.current_user.email),
                skip_ussd=payload.create_web_link,
            )

            if payload.create_web_link:
                service_locator.payment_service.create_payment_link(
                    db=self.db,
                    payment_id=str(payment.id),
                    user_id=self.current_user.id,
                    customer_email=str(
                        payload.email or self.current_user.email),
                    customer_name=self.current_user.first_name + " " + self.current_user.last_name,
                )

            return payment
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.post("/{subscription_id}/verify/", response_model=PaymentResponseSchema)
    def verify_payment(self, subscription_id: UUID):
        subscription: Subscription = service_locator.general_service.get_data_by_id(
            db=self.db, key=subscription_id, model=Subscription
        )

        if subscription.payment_status == Subscription.PAYMENT_STATUS.PAID:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Subscription already paid")

        payment = (
            self.db.query(Payment)
            .filter(
                Payment.subscription_id == subscription_id,
                Payment.user_id == str(self.current_user.id),
                Payment.status == Payment.STATUS.ONGOING,
            )
            .order_by(Payment.created_at.desc())
            .first()
        )
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        if not payment.ussd_reference and not payment.web_page_reference:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No payment reference found")

        try:
            return service_locator.payment_service.verify_payment(db=self.db, payment=payment)
        except Exception as e:
            logger.error(f"Error verifying payment: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Internal server error")

    @router.post("/{subscription_id}/otp/", response_model=PaymentResponseSchema,
                 status_code=status.HTTP_201_CREATED)
    def submit_otp(self, subscription_id: UUID, payload: SubmitOtpRequestSchema):
        try:
            return service_locator.payment_service.submit_otp(
                db=self.db,
                subscription_id=subscription_id,
                otp=payload.otp,
                user_id=str(self.current_user.id),
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.get("/{subscription_id}/", response_model=PaymentResponseSchema)
    def get_payment(self, subscription_id: UUID):
        payment = (
            self.db.query(Payment)
            .filter(
                Payment.subscription_id == subscription_id,
                Payment.user_id == str(self.current_user.id),
            )
            .order_by(Payment.created_at.desc())
            .first()
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
                db=db,
                key=payment.id,
                data={"web_page_reference": reference},
                model=Payment
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
                    service_locator.payment_service._finalize_successful_payment(
                        db, payment)
                    db.commit()
                    result_status = "success"
                else:
                    service_locator.general_service.update_data(
                        db=db,
                        key=payment.id,
                        data={"status": Payment.STATUS.FAILED},
                        model=Payment
                    )
                    db.commit()
                    result_status = "failed"

            except Exception as e:
                logger.error(f"Payment verification error: {str(e)}")
                result_status = "error"

        return RedirectResponse(
            url=f"/payments/success?status={result_status}&payment_id={payment_id}",
            status_code=status.HTTP_302_FOUND
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
            service_locator.payment_service._finalize_successful_payment(
                db, payment)
        else:
            service_locator.general_service.update_data(
                db=db, key=payment.id, data={"status": Payment.STATUS.FAILED}, model=Payment
            )

        db.commit()
        return {"message": "Processed", "payment_id": str(payment.id)}

    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Callback error: {str(e)}")
        raise HTTPException(status_code=500, detail="Server error")


templates = Jinja2Templates(directory="app/templates")


@router.get("/success", response_class=HTMLResponse)
def payment_success(request: Request):
    result_status = request.query_params.get("status")
    payment_id = request.query_params.get("payment_id")

    return templates.TemplateResponse(
        "payment_status.html",
        {
            "request": request,
            "status": result_status,
            "payment_id": payment_id,
            "deep_link": f"{settings.DEEP_LINK}?status={result_status}&payment_id={payment_id}"
        }
    )
