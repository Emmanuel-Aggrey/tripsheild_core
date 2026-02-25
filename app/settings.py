import os

from dotenv import dotenv_values

# Load environment variables from .env file

config = {
    **dotenv_values(".env"),
    **os.environ,  # override loaded values with environment variables
}


APP_NAME = config.get("APP_NAME", "Insurance Consumer")

FRONTEND_URL = config.get("FRONTEND_URL")
CORE_CONSUMER_API_URL = config.get("CORE_CONSUMER_API_URL")
SECRET_KEY = config.get("SECRET_KEY")
ALGORITHM = config.get("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(config.get("ACCESS_TOKEN_EXPIRE_MINUTES"))
ORGANISATION_TOKEN_EXPIRE_DAYS = int(
    config.get("ORGANISATION_TOKEN_EXPIRE_DAYS"))


DATABASE_HOST = config.get("DATABASE_HOST")
DATABASE_USER = config.get("DATABASE_USER")
DATABASE_PASSWORD = config.get("DATABASE_PASSWORD")
DATABASE_NAME = config.get("DATABASE_NAME")
DATABASE_PORT = config.get("DATABASE_PORT")
SENTRY_DSN = config.get("SENTRY_DSN")
CHAT_API_BASE_URL = config.get("CHAT_API_BASE_URL")

IS_TESTING = config.get("IS_TESTING") == "True"
DEBUG = config.get("DEBUG", "False") == "True"


SQLALCHEMY_DATABASE_URL = (
    "postgresql://{user}:{password}@{host}:{port}/{dbname}".format(
        user=DATABASE_USER,
        password=DATABASE_PASSWORD,
        host=DATABASE_HOST,
        port=DATABASE_PORT,
        dbname=DATABASE_NAME,
    )
)


AWS_S3_REGION_NAME = config.get("AWS_S3_REGION_NAME")
AWS_SECRET_ACCESS_KEY = config.get("AWS_SECRET_ACCESS_KEY")
AWS_ACCESS_KEY_ID = config.get("AWS_ACCESS_KEY_ID")
BUCKET_NAME = config.get("AWS_STORAGE_BUCKET_NAME")
AWS_PRESIGNED_EXPIRY = int(config.get("AWS_PRESIGNED_EXPIRY"))
FILE_MAX_SIZE = int(config.get("FILE_MAX_SIZE"))
AWS_DEFAULT_ACL = "public-read"


APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT: int = int(os.getenv("APP_PORT", "8003"))


# PAYSTACK
PAYSTACK_LIVE_MODE = config.get("PAYSTACK_LIVE_MODE", "False") == "True"

PAYSTACK_BASE_URL = config.get("PAYSTACK_BASE_URL", "https://api.paystack.co")

PAYSTACK_TEST_MOBILE_NUMBER = config.get(
    "PAYSTACK_TEST_MOBILE_NUMBER", "0541111111")
PAYSTACK_VALID_IP_ADDRESSES = config.get(
    "PAYSTACK_VALID_IP_ADDRESSES", "127.0.0.1").split(",")

PAYSTACK_SECRET_KEY = (
    config.get("PAYSTACK_TEST_SECRET_KEY", "WFWS")
    if not PAYSTACK_LIVE_MODE
    else config.get("PAYSTACK_LIVE_SECRET_KEY", "WFWS")
)


REDIS_URL = config.get("REDIS_URL", "redis://localhost:6379/0")


# SMTP
MAIL_USERNAME = config.get("MAIL_USERNAME")
MAIL_PASSWORD = config.get("MAIL_PASSWORD")
MAIL_PORT = config.get("MAIL_PORT")
MAIL_FROM = config.get("MAIL_FROM")
MAIL_SERVER = config.get("MAIL_SERVER")
MAIL_STARTTLS = config.get("MAIL_STARTTLS", "True") == "True"
MAIL_SSL_TLS = config.get("MAIL_SSL_TLS", "False") == "True"
USE_CREDENTIALS = config.get("USE_CREDENTIALS", "True") == "True"
VALIDATE_CERTS = config.get("VALIDATE_CERTS", "True") == "True"


HUBTEL_SMS_CONFIGURATION = {
    "clientsecret": config.get("HUBTEL_SMS_CLIENTSECRET"),
    "clientid": config.get("HUBTEL_SMS_CLIENTID"),
    "from": config.get("HUBTEL_SMS_FROM"),
    "url": config.get("HUBTEL_SMS_URL"),
}

# Admin panel credentials
ADMIN_LOGIN_USERNAME = config.get("ADMIN_LOGIN_USERNAME", "admin")
ADMIN_LOGIN_PASSWORD = config.get("ADMIN_LOGIN_PASSWORD", "admin123")
