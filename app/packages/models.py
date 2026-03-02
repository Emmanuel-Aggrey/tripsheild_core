from app.core.models import BaseModel
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM, UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from app.features.models import package_features


class Package(BaseModel):

    class STATUS:
        ACTIVE = "active"
        INACTIVE = "inactive"
        DEPRECATED = "deprecated"

        CHOICES = (
            (ACTIVE, "Active"),
            (INACTIVE, "Inactive"),
            (DEPRECATED, "Deprecated"),
        )
        ALL = (ACTIVE, INACTIVE, DEPRECATED)

    __tablename__ = "packages"

    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    # Stored as string for precision
    price = Column(String(20), nullable=False)
    duration = Column(Integer, nullable=False)  # Duration in days
    features = relationship(
        "Feature", secondary=package_features, back_populates="packages")

    coverage_amount = Column(String(20), nullable=True)  # Max coverage amount
    is_active = Column(Boolean, default=True, nullable=False)
    status = Column(
        PG_ENUM(*STATUS.ALL, name='package_status'),
        nullable=False,
        default=STATUS.ACTIVE
    )

    # Relationships
    subscriptions = relationship("Subscription", back_populates="package")
    features = relationship(
        "Feature", secondary=package_features, back_populates="packages")


class Subscription(BaseModel):

    class STATUS:
        PENDING = "pending"
        ACTIVE = "active"
        EXPIRED = "expired"
        CANCELLED = "cancelled"

        CHOICES = (
            (PENDING, "Pending"),
            (ACTIVE, "Active"),
            (EXPIRED, "Expired"),
            (CANCELLED, "Cancelled"),
        )
        ALL = (PENDING, ACTIVE, EXPIRED, CANCELLED)

    class PAYMENT_STATUS:
        PENDING = "pending"
        PAID = "paid"
        FAILED = "failed"
        REFUNDED = "refunded"

        CHOICES = (
            (PENDING, "Pending"),
            (PAID, "Paid"),
            (FAILED, "Failed"),
            (REFUNDED, "Refunded"),
        )
        ALL = (PENDING, PAID, FAILED, REFUNDED)

    __tablename__ = "subscriptions"

    user_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    package_id = Column(PG_UUID(as_uuid=True), ForeignKey(
        "packages.id"), nullable=False)
    status = Column(
        PG_ENUM(*STATUS.ALL, name='subscriptions_status'),
        nullable=False,
        default=STATUS.PENDING
    )
    payment_status = Column(
        PG_ENUM(*PAYMENT_STATUS.ALL, name='payment_status'),
        nullable=False,
        default=PAYMENT_STATUS.PENDING
    )
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    auto_renew = Column(Boolean, default=False, nullable=False)
    location_from = Column(String, nullable=True)
    location_to = Column(String, nullable=True)
    data = Column(JSONB, nullable=True, default=dict)

    # Relationships
    package = relationship("Package", back_populates="subscriptions")
    payments = relationship("Payment", back_populates="subscription")
