from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from enum import Enum
from app.core.schema import BaseSchema
from app.literal.schemas import TransportTypeSchema


class PackageStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"


# Feature schema for nested response
class FeatureInPackageSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str] = None
    is_active: bool


class PackageBaseSchema(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    price: Decimal = Field(..., max_digits=10, decimal_places=2)
    duration: int = Field(..., gt=0, description="Duration in days")
    coverage_amount: Optional[Decimal] = Field(
        None, max_digits=12, decimal_places=2)
    is_active: bool = True
    status: PackageStatusEnum = PackageStatusEnum.ACTIVE


class PackageCreateSchema(PackageBaseSchema):
    feature_ids: Optional[List[UUID]] = Field(
        default_factory=list, description="List of feature IDs to assign")

    @field_validator('feature_ids')
    @classmethod
    def validate_feature_ids(cls, v):
        if v:
            return [fid for fid in v if fid is not None]
        return []


class PackageUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2)
    duration: Optional[int] = Field(None, gt=0)
    coverage_amount: Optional[Decimal] = Field(
        None, max_digits=12, decimal_places=2)
    is_active: Optional[bool] = None
    status: Optional[PackageStatusEnum] = None
    feature_ids: Optional[List[UUID]] = Field(
        None, description="List of feature IDs (replaces existing)")

    @field_validator('feature_ids')
    @classmethod
    def validate_feature_ids(cls, v):
        if v is not None:
            return [fid for fid in v if fid is not None]
        return v


class PackageResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str] = None
    price: str  # Stored as string in DB
    duration: int
    coverage_amount: Optional[str] = None
    is_active: bool
    status: str
    features: List[FeatureInPackageSchema] = []
    created_at: datetime
    updated_at: datetime


class PackageListResponseSchema(BaseModel):
    packages: List[PackageResponseSchema]
    total: int
    page: int
    limit: int


class SubscriptionStatusEnum(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PaymentStatusEnum(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class SubscriptionCreateSchema(BaseModel):
    package_id: UUID
    auto_renew: bool = False
    location_from: Optional[str] = None
    location_to: Optional[str] = None
    data: Optional[dict] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    transport_type_id: UUID
    beneficiary_name: str


class SubscriptionResponseSchema(BaseSchema):
    beneficiary_name: Optional[str] = None
    auto_renew: bool = False
    location_from: Optional[str] = None
    location_to: Optional[str] = None
    data: Optional[dict] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: SubscriptionStatusEnum
    payment_status: PaymentStatusEnum
    user_id: UUID
    package: Optional[PackageResponseSchema] = None
    transport_type: Optional[TransportTypeSchema] = None


class SubscriptionListResponseSchema(BaseModel):
    subscriptions: List[SubscriptionResponseSchema]
    total: int
    page: int
    limit: int


class SubscriptionUpdateSchema(BaseModel):
    status: SubscriptionStatusEnum

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v != SubscriptionStatusEnum.CANCELLED:
            raise ValueError("Only cancellation is allowed")
        return v
