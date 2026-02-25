import sentry_sdk
from app import settings
from app.accounts.routes import router as accounts_router
from app.authentication.routes import router as auth_router
from app.core.routes import router as core_router
from app.insuranc_records.routes import router as insurance_router
from app.features.routes import router as features_router
from app.packages.routes import router as packages_router
from app.payment.routes import router as payment_router
from app.claims.routes import router as claims_router

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

origins = [
    "http://localhost:8000",
    "http://localhost:5173",
]


app = FastAPI(
    title="Insurance   Core API Gateway",
    description="""API Gateway handling insurance Core """,
    version="1.0.0",
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


app.include_router(core_router, tags=["core"])
app.include_router(auth_router, tags=["auhentication"])
app.include_router(accounts_router, tags=["users"], prefix="/accounts",)
app.include_router(insurance_router, tags=["insurance"], prefix="/insurance",)
app.include_router(features_router, tags=["features"], prefix="/features",)
app.include_router(packages_router, tags=["packages"], prefix="/packages",)
app.include_router(payment_router, tags=["payment"], prefix="/payment",)
app.include_router(claims_router, tags=["claims"], prefix="/claims",)


@app.get("/")
async def root():
    return {"message": "Hello World"}


if not settings.IS_TESTING and not settings.DEBUG:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.CHAT_API_BASE_URL,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        server_name=settings.CHAT_API_BASE_URL,
        enable_tracing=True,
    )
