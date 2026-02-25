from app.core.models import BaseModel
from sqlalchemy import Column
from sqlalchemy import String, Integer
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM


class InsurancRecord(BaseModel):

    class Status:
        PENDING = "pending"
        APPROVED = "approved"
        REJECTED = "rejected"

        CHOICES = (
            (PENDING, ("Pending")),
            (APPROVED, ("approved")),
            (REJECTED, ("rejected")),

        )

        ALL = (PENDING, APPROVED, REJECTED)
    __tablename__ = "insurance_records"
    user_id = Column(String, index=True)
    amount = Column(String)
    duration = Column(Integer)
    status = Column(
        PG_ENUM(*Status.ALL, name='status'),
        nullable=False,
        default=Status.PENDING
    )
