from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from app.literal.schemas import TypeOfIncidentSchema
from app.storage.schemas import StorageResponse


class ClaimStatusEnum(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class ClaimCreateSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    subscription_id: UUID
    reason: str = Field(..., min_length=5)
    incident_date: Optional[datetime] = None
    type_of_incident_id: Optional[UUID] = None
    location_of_incidence: Optional[str] = None
    storages: Optional[List[UUID]] = None


class ClaimStatusUpdateSchema(BaseModel):
    status: ClaimStatusEnum
    reviewer_note: Optional[str] = None


class ClaimResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
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
    type_of_incident: Optional[TypeOfIncidentSchema] = None
    location_of_incidence: Optional[str] = None
    storages: Optional[List[StorageResponse]] = None


class ClaimListResponseSchema(BaseModel):
    claims: List[ClaimResponseSchema]
    total: int
    page: int
    limit: int
