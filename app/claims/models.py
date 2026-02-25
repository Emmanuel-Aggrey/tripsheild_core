from app.core.models import BaseModel
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM, UUID as PG_UUID
from sqlalchemy.orm import relationship


class Claim(BaseModel):
    class STATUS:
        PENDING = "pending"
        APPROVED = "approved"
        REJECTED = "rejected"
        PAID = "paid"
        ALL = (PENDING, APPROVED, REJECTED, PAID)

    __tablename__ = "claims"

    user_id = Column(String, nullable=False, index=True)
    subscription_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False, index=True
    )
    claim_amount = Column(String(20), nullable=False)
    reason = Column(Text, nullable=False)
    incident_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        PG_ENUM(*STATUS.ALL, name="claim_status"),
        nullable=False,
        default=STATUS.PENDING,
    )
    reviewer_note = Column(Text, nullable=True)

    subscription = relationship("Subscription")
