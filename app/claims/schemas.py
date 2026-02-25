from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


class ClaimStatusEnum(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class ClaimCreateSchema(BaseModel):
    subscription_id: UUID
    claim_amount: Decimal = Field(..., max_digits=12, decimal_places=2)
    reason: str = Field(..., min_length=5)
    incident_date: Optional[datetime] = None


class ClaimStatusUpdateSchema(BaseModel):
    status: ClaimStatusEnum
    reviewer_note: Optional[str] = None


class ClaimResponseSchema(BaseModel):
    id: UUID
    user_id: str
    subscription_id: UUID
    claim_amount: str
    reason: str
    incident_date: Optional[datetime] = None
    status: ClaimStatusEnum
    reviewer_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ClaimListResponseSchema(BaseModel):
    claims: List[ClaimResponseSchema]
    total: int
    page: int
    limit: int
