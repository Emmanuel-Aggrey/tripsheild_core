from pydantic import Field
from typing import Optional
from app.core.schema import BaseSchema
from pydantic import BaseModel


class LiteralBaseSchema(BaseSchema):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    is_active: bool = True


class TransportTypeSchema(LiteralBaseSchema):
    pass


class TypeOfIncidentSchema(LiteralBaseSchema):
    pass


class AllLiteralsResponseSchema(BaseModel):
    transport_types: Optional[list[TransportTypeSchema]] = None
    type_of_incidents: Optional[list[TypeOfIncidentSchema]] = None
