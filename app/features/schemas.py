from pydantic import Field
from typing import Optional
from uuid import UUID
from app.core.schema import BaseSchema


class FeatureBaseSchema(BaseSchema):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    is_active: bool = True


class FeatureCreateSchema(FeatureBaseSchema):
    pass


class FeatureUpdateSchema(BaseSchema):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class FeatureResponseSchema(FeatureBaseSchema):
    id: UUID

    class Config:
        from_attributes = True
