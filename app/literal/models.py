from app.core.models import BaseModel
from sqlalchemy import Column, Boolean
from sqlalchemy import String
from sqlalchemy.orm import relationship


class Literal(BaseModel):

    __abstract__ = True

    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)


class TransportType(Literal):

    __tablename__ = "transport_types"

    subscriptions = relationship(
        "Subscription", back_populates="transport_type")
    packages = relationship(
        "Package", back_populates="transport_type")
