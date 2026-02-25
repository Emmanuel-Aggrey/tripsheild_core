
from decimal import Decimal
from app.core.schema import BaseSchema
from pydantic import Field


class InsurancRecordSchema(BaseSchema):
    user_id: str = Field(..., description="The id of the user")
    status: str = Field(..., description="The status of the record")
    amount: Decimal = Field(..., description="The amount of the record",
                            max_digits=10, decimal_places=2)
    duration: int = Field(..., description="The duration of the record")

    class Config:
        from_attributes = True
