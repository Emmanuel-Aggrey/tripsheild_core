from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Annotated, Optional
import jwt
import re

from app.accounts.schemas import UserSchema
from app.dependencies import get_db
from app.settings import ACCESS_TOKEN_EXPIRE_MINUTES
from app.settings import ALGORITHM
from app.settings import SECRET_KEY
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.core.dependency_injection import service_locator

from .schemas import TokenData

router = APIRouter()
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def normalize_phone_number(phone_number: str) -> str:
    if not phone_number:
        return phone_number

    phone = re.sub(r"[\s\-\(\)\+]", "", phone_number)

    if phone.startswith("0"):
        phone = "233" + phone[1:]

    if not phone.startswith("233"):
        return None

    return "+" + phone


def verify_password(plain_password, hashed_password):
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(identifier: str, db: Session):
    user = service_locator.account_service.get_user_by_identifier(
        db, identifier)
    if user:
        return user


def authenticate_user(db: Session, identifier: str, password: str):
    user = service_locator.account_service.get_user_by_identifier(
        db, identifier)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
    expire_time: int = ACCESS_TOKEN_EXPIRE_MINUTES,
    unit: str = "minutes",
) -> dict:
    if expires_delta is None:
        expires_delta = calculate_expiration_time(expire_time, unit)

    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})

    # Encode the JWT token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def calculate_expiration_time(expire_time: int, unit: str) -> timedelta:
    if unit == "minutes":
        return timedelta(minutes=expire_time)
    elif unit == "hours":
        return timedelta(hours=expire_time)
    elif unit == "days":
        return timedelta(days=expire_time)
    else:
        raise ValueError(
            "Invalid unit for expiration time. Use 'minutes', 'hours', or 'days'."
        )


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="gimme-jwt")

auth_scheme = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(auth_scheme)],
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid token or token expired",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        subject: str = payload.get("sub")
        if subject is None:
            raise credentials_exception
        token_data = TokenData(sub=subject)
    except InvalidTokenError:
        raise credentials_exception

    user = service_locator.account_service.get_user_by_identifier(
        db, token_data.sub)

    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[UserSchema, Depends(get_current_user)], request: Request
):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    request.state.user = current_user
    return current_user


def decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except (InvalidTokenError, Exception):
        return None


def validate_token(db: Session, token: str) -> dict:
    subject = decode_token(token)

    if not subject:
        return {"valid": False, "user_id": None}

    user = service_locator.account_service.get_user_by_identifier(db, subject)
    return {
        "valid": bool(user and user.is_active),
        "user_id": str(user.id) if user else None
    }


async def validate_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(auth_scheme)],
    db: Session = Depends(get_db),
) -> UserSchema:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid token or token expired",
        headers={"WWW-Authenticate": "Bearer"},
    )

    subject = decode_token(credentials.credentials)
    if not subject:
        raise credentials_exception

    user = service_locator.account_service.get_user_by_identifier(db, subject)

    if not user or not user.is_active:
        raise credentials_exception

    return user
