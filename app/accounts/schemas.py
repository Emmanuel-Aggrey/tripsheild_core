from typing import Optional
from enum import Enum
from app.core.schema import BaseSchema
from pydantic import BaseModel
from pydantic import model_validator


class UserRoleEnum(str, Enum):
    USER = "user"
    ADMIN = "admin"


class BaseUserSchema(BaseSchema):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[UserRoleEnum] = None
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
    role: Optional[UserRoleEnum]
    profile_picture: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    occupation: Optional[str] = None
    ghana_card_number: Optional[str] = None
    is_registration_complete: bool = False

    @model_validator(mode="after")
    def set_registration_complete(self):
        self.is_registration_complete = bool(
            self.email
            and self.first_name
            and self.last_name
        )
        return self


class UserProfileUpdateSchema(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    role: Optional[UserRoleEnum] = None
    profile_picture: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    occupation: Optional[str] = None
    ghana_card_number: Optional[str] = None

    class Config:
        from_attributes = True
