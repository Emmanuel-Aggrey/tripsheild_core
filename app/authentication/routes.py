from app.accounts.schemas import UserResponseSchema
from app.authentication import schemas
from app.accounts.models import User
from app.core.dependency_injection import service_locator
from app.authentication.utils import authenticate_user
from app.authentication.utils import create_access_token
from app.dependencies import get_db
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi_utils.cbv import cbv
from sqlalchemy.orm import Session


router = APIRouter()


@cbv(router)
class AuthenticationView:
    db: Session = Depends(get_db)

    async def _send_login_otp_email(self, user: User, otp_code: str):
        if not user.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User does not have an email address",
            )

        await service_locator.core_service.send_template_email(
            recipients=[user.email],
            subject="Login verification code",
            template_name="email_verification.html",
            context={
                "name": user.first_name or "User",
                "code": otp_code,
                "expiry_minutes": 10,
            },
        )

    def _send_login_otp_sms(self, user: User, otp_code: str):
        if not user.phone_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User does not have a phone number",
            )

        service_locator.core_service.send_text_message(
            user.phone_number,
            f"Your login verification code is {otp_code}.",
        )

    @router.post("/register/", response_model=UserResponseSchema)
    async def register(self, registration_form: schemas.UserRegistrationForm):
        try:
            user, code = service_locator.account_service.create_user(
                self.db, registration_form
            )

            if registration_form.email and not user.is_testing_user:
                await service_locator.core_service.send_template_email(
                    recipients=[str(registration_form.email)],
                    subject="Verify your account",
                    template_name="email_verification.html",
                    context={
                        "name": registration_form.first_name or "User",
                        "code": code,
                        "expiry_minutes": 10,
                    },
                )

            if registration_form.phone_number and not user.is_testing_user:
                service_locator.core_service.send_text_message(
                    registration_form.phone_number,
                    f"Your verification code is {code}.",
                )

            return user

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.post("/verify/")
    async def verify_email(self, payload: schemas.VerifyEmailSchema):
        try:
            from app.authentication.utils import normalize_phone_number

            if payload.email:
                user = self.db.query(User).filter(
                    User.email == payload.email).first()
            else:
                # Normalize phone number for comparison
                normalized_input = normalize_phone_number(payload.phone_number)
                if not normalized_input:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone number format")

                # Find user with matching normalized phone
                all_users = self.db.query(User).all()
                user = None
                for u in all_users:
                    if u.phone_number and normalize_phone_number(u.phone_number) == normalized_input:
                        user = u
                        break

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

            if user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Account already verified")

            if user.code != payload.code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")

            user.is_active = True
            if not user.is_testing_user:
                user.code = None
            self.db.commit()

            return {"detail": "Account verified successfully"}

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(


                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @router.post("/login/email-password/", response_model=schemas.Token)
    async def email_password_login(self, form_data: schemas.EmailPasswordLoginForm) -> schemas.Token:
        user = authenticate_user(self.db, str(
            form_data.email), form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account not verified",
            )

        token_subject = user.email or user.phone_number
        access_token = create_access_token(data={"sub": token_subject})
        return schemas.Token(access_token=access_token, token_type="bearer")

    @router.post("/login/email/")
    async def email_login_request(self, payload: schemas.EmailLoginRequest):
        user = service_locator.account_service.get_user_by_email(
            self.db, payload.email.strip())
        if not user:
            user = service_locator.general_service.create_data(
                self.db,
                User,
                {
                    "email": payload.email,
                    "is_active": False,
                    "role": User.Role.USER,
                },
            )

        if not user.is_testing_user:
            user.code = service_locator.account_service.generate_code(self.db)
        self.db.commit()
        await self._send_login_otp_email(user, user.code)

        return {"detail": "OTP sent to email"}

    @router.post("/login/phone/")
    async def phone_login_request(self, payload: schemas.PhoneLoginRequest):
        from app.authentication.utils import normalize_phone_number

        user = service_locator.account_service.get_user_by_phone(
            self.db, payload.phone_number.strip())
        if not user:
            # Normalize phone number before storing
            normalized_phone = normalize_phone_number(
                payload.phone_number.strip())
            if not normalized_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid phone number format"
                )

            user = service_locator.general_service.create_data(
                self.db,
                User,
                {
                    "phone_number": normalized_phone,
                    "is_active": False,
                    "role": User.Role.USER,
                },
            )

        if not user.is_testing_user:
            user.code = service_locator.account_service.generate_code(self.db)
        self.db.commit()
        self._send_login_otp_sms(user, user.code)

        return {"detail": "OTP sent to phone number"}

    @router.post("/login/verify-otp/", response_model=schemas.Token)
    async def verify_login_otp(self, payload: schemas.VerifyLoginOtpSchema) -> schemas.Token:
        user = None
        if payload.email:
            user = service_locator.account_service.get_user_by_email(
                self.db, payload.email.strip())
        if payload.phone_number:
            user = service_locator.account_service.get_user_by_phone(
                self.db, payload.phone_number.strip())

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if user and str(user.code).strip() != str(payload.code).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP code or code has expired",
            )

        user.is_active = True
        if not user.is_testing_user:
            user.code = None
        self.db.commit()

        token_subject = user.email or user.phone_number
        access_token = create_access_token(data={"sub": token_subject})
        return schemas.Token(access_token=access_token, token_type="bearer")

    @router.post("/gimme-jwt/", response_model=schemas.Token)
    async def gimme_jwt(self, form_data: schemas.EmailPasswordLoginForm) -> schemas.Token:
        return await self.email_password_login(form_data)
