from app.core.models import BaseModel
from sqlalchemy import Column, String, Text, Boolean, Table, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from datetime import datetime, timezone



package_features = Table(
    'package_features',
    BaseModel.metadata,
    Column('package_id', PG_UUID(as_uuid=True), ForeignKey('packages.id', ondelete='CASCADE'), primary_key=True),
    Column('feature_id', PG_UUID(as_uuid=True), ForeignKey('features.id', ondelete='CASCADE'), primary_key=True),
    Column('created_at', DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
)


class Feature(BaseModel):
    
 

    __tablename__ = "features"

    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
  
    packages = relationship("Package", secondary=package_features, back_populates="features")