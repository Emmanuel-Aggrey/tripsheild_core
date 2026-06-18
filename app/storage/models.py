
from sqlalchemy import (
    Column, Integer, String, ForeignKey, Date)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.models import BaseModel


class Storage(BaseModel):
    __tablename__ = "storages"

    url = Column(String, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    filename = Column(String)
    file_size = Column(Integer)
    mime_type = Column(String)
    s3_key = Column(String)
    thumbnail = Column(String)
    upload_finished_at = Column(Date)

    user = relationship("User", back_populates="storages")

    claims = relationship(
        "Claim", secondary="claim_storages", back_populates="storages")
