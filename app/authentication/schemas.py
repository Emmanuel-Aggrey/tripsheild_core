from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field
from pydantic import model_validator
from typing import Optional


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    sub: str | None = None


class UserRegistrationForm(BaseModel):
    email: Optional[EmailStr] = Field(
        default=None, description="Email address")
    phone_number: Optional[str] = Field(
        default=None, min_length=10, max_length=20)
    first_name: Optional[str] = Field(
        default=None, min_length=2, max_length=64)
    last_name: Optional[str] = Field(default=None, min_length=2, max_length=64)
    password: str = Field(min_length=8, max_length=64)
    profile_picture: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    occupation: Optional[str] = None
    ghana_card_number: Optional[str] = None
    role: str = "user"

    @model_validator(mode="after")
    def validate_contact(self):
        if not self.email and not self.phone_number:
            raise ValueError("Either email or phone_number is required")
        return self


class LoginForm(BaseModel):
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(
        default=None, min_length=10, max_length=20)
    password: str = Field(min_length=8, max_length=64)

    @model_validator(mode="after")
    def validate_identifier(self):
        if not self.email and not self.phone_number:
            raise ValueError("Either email or phone_number is required")
        return self


class EmailPasswordLoginForm(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)


class EmailLoginRequest(BaseModel):
    email: EmailStr


class PhoneLoginRequest(BaseModel):
    phone_number: str = Field(min_length=10, max_length=20)


class VerifyLoginOtpSchema(BaseModel):
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(
        default=None, min_length=10, max_length=20)
    code: str = Field(min_length=4, max_length=10)

    @model_validator(mode="after")
    def validate_identifier(self):
        if not self.email and not self.phone_number:
            raise ValueError("Either email or phone_number is required")
        if self.email and self.phone_number:
            raise ValueError(
                "Only one of email or phone_number can be provided")
        return self


class TokenValidationRequest(BaseModel):
    token: str


class VerifyEmailSchema(BaseModel):
    email: Optional[str] = None
    phone_number: Optional[str] = None
    code: str

    @model_validator(mode="after")
    def validate_identifier(self):
        if not self.email and not self.phone_number:
            raise ValueError("Either email or phone_number is required")
        return self
