from datetime import datetime
from typing import Optional, List
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, ConfigDict, EmailStr


class PaymentMethodEnum(str, Enum):
    MOMO = "momo"
    CASH = "cash"
    BANK = "bank"


class PaymentProviderEnum(str, Enum):
    MTN = "mtn"
    AIRTELTIGO = "atl"
    VODAFONE = "vod"


class PaymentStatusEnum(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    ONGOING = "ongoing"


class BuySubscriptionRequestSchema(BaseModel):
    package_id: Optional[UUID] = None
    payment_method: PaymentMethodEnum = PaymentMethodEnum.MOMO
    phone_number: Optional[str] = None
    provider: Optional[PaymentProviderEnum] = None
    email: Optional[EmailStr] = "info@kayaktechgroup.com"
    create_web_link: bool = True


class InitiatePaymentRequestSchema(BaseModel):
    subscription_id: UUID
    payment_method: PaymentMethodEnum = PaymentMethodEnum.MOMO
    phone_number: Optional[str] = None
    provider: Optional[PaymentProviderEnum] = None
    email: Optional[EmailStr] = None
    skip_ussd: bool = False


class SubmitOtpRequestSchema(BaseModel):
    otp: str


class PaymentResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str
    subscription_id: UUID
    amount: str
    currency: str
    payment_method: str
    provider: Optional[str] = None
    transaction_id: Optional[str] = None
    ussd_reference: Optional[str] = None
    web_page_reference: Optional[str] = None
    status: PaymentStatusEnum
    failure_reason: Optional[str] = None
    initiate_payment_prompt: bool
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    payment_link: Optional[str] = None


class PaymentListResponseSchema(BaseModel):
    payments: List[PaymentResponseSchema]
    total: int
    page: int
    limit: int
