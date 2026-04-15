import secrets
from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from app import settings
from app.database import engine
from app.accounts.models import User
from app.features.models import Feature
from app.packages.models import Package, Subscription
from app.payment.models import Payment
from app.insuranc_records.models import InsurancRecord
from app.claims.models import Claim
from app.literal.models import TransportType


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        username_ok = secrets.compare_digest(
            str(username or ""), settings.ADMIN_LOGIN_USERNAME
        )
        password_ok = secrets.compare_digest(
            str(password or ""), settings.ADMIN_LOGIN_PASSWORD
        )
        if username_ok and password_ok:
            request.session.update({"admin_logged_in": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return bool(request.session.get("admin_logged_in"))


class UserAdmin(ModelView, model=User):
    column_exclude_list = [User.hashed_password, User.code]
    name = "User"
    name_plural = "Users"


class FeatureAdmin(ModelView, model=Feature):
    name = "Feature"
    name_plural = "Features"


class PackageAdmin(ModelView, model=Package):
    name = "Package"
    name_plural = "Packages"
    column_list = [
        Package.id,
        Package.name,
        Package.description,
        Package.price,
        Package.duration,
        Package.is_active,
        Package.status,
        Package.created_at,
        Package.updated_at,
    ]


class SubscriptionAdmin(ModelView, model=Subscription):
    name = "Subscription"
    name_plural = "Subscriptions"


class PaymentAdmin(ModelView, model=Payment):
    name = "Payment"
    name_plural = "Payments"


class InsuranceRecordAdmin(ModelView, model=InsurancRecord):
    name = "Insurance Record"
    name_plural = "Insurance Records"


class ClaimAdmin(ModelView, model=Claim):
    name = "Claim"
    name_plural = "Claims"


class TransportTypeAdmin(ModelView, model=TransportType):
    name = "Transport Type"
    name_plural = "Transport Types"
    column_list = [
        TransportType.id,
        TransportType.name,
        TransportType.description,
        TransportType.is_active,

    ]


def setup_admin(app: FastAPI) -> None:
    authentication_backend = AdminAuth(
        secret_key=settings.SECRET_KEY or "change-me-in-env"
    )
    admin = Admin(
        app=app,
        engine=engine,
        authentication_backend=authentication_backend,
        title=f"{settings.APP_NAME} Admin",
        base_url="/admin",
    )
    admin.add_view(UserAdmin)
    admin.add_view(FeatureAdmin)
    admin.add_view(PackageAdmin)
    admin.add_view(SubscriptionAdmin)
    admin.add_view(PaymentAdmin)
    admin.add_view(InsuranceRecordAdmin)
    admin.add_view(ClaimAdmin)
    admin.add_view(TransportTypeAdmin)
