from typing import Optional
from enum import Enum
from app.core.schema import BaseSchema


class UserRoleEnum(str, Enum):
    USER = "user"
    ADMIN = "admin"


class BaseUserSchema(BaseSchema):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: bool | None = None
    role: Optional[UserRoleEnum] = None
    code: Optional[str] = None
    profile_picture: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    occupation: Optional[str] = None
    ghana_card_number: Optional[str] = None

    class Config:
        from_attributes = True


class UserSchema(BaseUserSchema):
    password: str | None = None


class UserResponseSchema(BaseUserSchema):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: bool | None = None
    role: Optional[UserRoleEnum]
    profile_picture: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    occupation: Optional[str] = None
    ghana_card_number: Optional[str] = None


class UserProfileUpdateSchema(BaseUserSchema):
    pass
