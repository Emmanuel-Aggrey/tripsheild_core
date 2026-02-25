from app.core.models import BaseModel
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM


class User(BaseModel):
    class Role:
        USER = "user"
        ADMIN = "admin"
        ALL = (USER, ADMIN)
        CHOICES = ((USER, "User"), (ADMIN, "Admin"))
        ALL = (USER, ADMIN)
    __tablename__ = "users"
    email = Column(String, unique=True, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=False)
    role = Column(
        PG_ENUM(*Role.ALL, name='role'),
        nullable=True,
        default=Role.USER
    )
    code = Column(String, nullable=True)
    profile_picture = Column(String, nullable=True)
    address = Column(String, nullable=True)
    date_of_birth = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    occupation = Column(String, nullable=True)
    ghana_card_number = Column(String, nullable=True)
