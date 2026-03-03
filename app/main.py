import sentry_sdk
from app import settings
from app.accounts.routes import router as accounts_router
from app.authentication.routes import router as auth_router
from app.core.routes import router as core_router
from app.insuranc_records.routes import router as insurance_router
from app.features.routes import router as features_router
from app.packages.routes import packages_router, subscriptions_router
from app.payment.routes import router as payment_router
from app.claims.routes import router as claims_router

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi_pagination import add_pagination
import logging
from app.admin import setup_admin
from .ping_render import lifespan


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

origins = [
    "http://localhost:8000",
    "http://localhost:5173",
    "http://localhost:3000",
    *settings.FRONTEND_ORIGINS,

]


app = FastAPI(
    title="Insurance   Core API Gateway",
    description="""API Gateway handling insurance Core """,
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex="http://localhost:*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

add_pagination(app)
setup_admin(app)


app.include_router(core_router, tags=["core"])
app.include_router(auth_router, tags=["auhentication"])
app.include_router(accounts_router, tags=["users"], prefix="/accounts",)
app.include_router(insurance_router, tags=["insurance"], prefix="/insurance",)
app.include_router(features_router, tags=["features"], prefix="/features",)
app.include_router(packages_router, tags=["packages"], prefix="/packages")
app.include_router(subscriptions_router, tags=[
                   "subscriptions"], prefix="/subscriptions")

app.include_router(payment_router, tags=["payments"], prefix="/payments",)
app.include_router(claims_router, tags=["claims"], prefix="/claims",)


@app.get("/")
async def root():
    return {"message": "Hello World"}


if not settings.IS_TESTING and not settings.DEBUG:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.APP_NAME,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        server_name=settings.APP_NAME,
        enable_tracing=True,
    )
