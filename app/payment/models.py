from app.core.models import BaseModel
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM, UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship


class Payment(BaseModel):

    class CURRENCY:
        GHS = "GHS"
        USD = "USD"
        EUR = "EUR"
        ALL = (GHS, USD, EUR)
        CHOICES = (
            (GHS, "Ghanaian Cedi"),
            (USD, "US Dollar"),
            (EUR, "Euro"),
        )

    class PROVIDER:
        MTN = "mtn"
        AirtelTigo = "atl"
        Vodafone = "vod"

        ALL = (
            MTN,
            AirtelTigo,
            Vodafone,
        )
        CHOICES = (
            (MTN, ("MTN")),
            (AirtelTigo, ("AirtelTigo")),
            (Vodafone, ("Vodafone")),
        )

    class STATUS:
        SUCCESS = "success"
        FAILED = "failed"
        ONGOING = "ongoing"

        CHOICES = (
            (SUCCESS, "Success"),
            (FAILED, "Failed"),
            (ONGOING, "Ongoing"),
        )
        ALL = (SUCCESS, FAILED, ONGOING)

    class PAYMENT_METHOD:
        MOMO = "momo"
        CASH = "cash"
        BANK = "bank"

        CHOICES = (
            (MOMO, "Momo"),
            (CASH, "Cash"),
            (BANK, "Bank"),
        )
        ALL = (MOMO, CASH, BANK)

    __tablename__ = "payments"

    provider = Column(
        PG_ENUM(*PROVIDER.ALL, name='payment_provider'),
        nullable=True
    )
    user_id = Column(String, nullable=False, index=True)
    subscription_id = Column(PG_UUID(as_uuid=True), ForeignKey(
        "subscriptions.id"), nullable=False)
    amount = Column(String(20), nullable=False)
    currency = Column(String(3), default=CURRENCY.GHS, nullable=False)
    payment_method = Column(
        PG_ENUM(*PAYMENT_METHOD.ALL, name='payment_method'),
        nullable=False
    )
    transaction_id = Column(String(100), nullable=True, unique=True)
    ussd_reference = Column(String(100), nullable=True)
    web_page_reference = Column(String(100), nullable=True)
    status = Column(
        PG_ENUM(*STATUS.ALL, name='payment_transaction_status'),
        nullable=False,
        default=STATUS.ONGOING
    )
    failure_reason = Column(Text, nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    payment_metadata = Column(JSONB, nullable=True, default=dict)
    initiate_payment_prompt = Column(Boolean, default=False, nullable=False)
    payment_link = Column(String, nullable=True)

    subscription = relationship("Subscription", back_populates="payments")
