import random
from pydantic import EmailStr
from sqlalchemy.orm import Session
from app.accounts.models import User
from app.authentication.schemas import UserRegistrationForm


class AccountService:
    def __init__(self):
        from app.core.dependency_injection import service_locator
        self.service_locator = service_locator

    def get_user(self, db: Session, user_id: int):
        return self.service_locator.general_service.get_data_by_id(db, User, user_id)

    def get_user_by_email(self, db: Session, email: EmailStr):
        return self.service_locator.general_service.filter_data(
            db, {"email": email},
            User, single_record=True)

    def is_admin(self, user: User):
        return user.role == User.Role.ADMIN

    def get_user_by_phone(self, db: Session, phone_number: str):
        from app.authentication.utils import normalize_phone_number

        normalized_input = normalize_phone_number(phone_number)

        if not normalized_input:
            return None

        users = db.query(User).all()
        for user in users:
            if user.phone_number:
                normalized_stored = normalize_phone_number(user.phone_number)
                if normalized_stored == normalized_input:
                    return user

        return None

    def get_user_by_identifier(self, db: Session, identifier: str):
        user = self.get_user_by_email(db, identifier)
        if user:
            return user
        return self.get_user_by_phone(db, identifier)

    def get_users(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(User).offset(skip).limit(limit).all()

    def create_user(self, db: Session, user: "UserRegistrationForm"):
        from app.authentication.utils import get_password_hash, normalize_phone_number

        # Check email (case-insensitive)
        if user.email:
            existing_user = db.query(User).filter(
                User.email.ilike(user.email.strip())
            ).first()
            if existing_user:
                raise ValueError("User with this email already exists")

        # Check phone number (normalized)
        if user.phone_number:
            normalized_input = normalize_phone_number(
                user.phone_number.strip())
            if not normalized_input:
                raise ValueError("Invalid phone number format")

            # Check against all users with normalized phone
            all_users = db.query(User).all()
            for existing_user in all_users:
                if existing_user.phone_number:
                    normalized_existing = normalize_phone_number(
                        existing_user.phone_number)
                    if normalized_existing == normalized_input:
                        raise ValueError(
                            "User with this phone number already exists")

            phone_number = normalized_input
        else:
            phone_number = user.phone_number

        code = self.generate_code(db)

        data = {
            "email": user.email.strip() if user.email else None,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone_number": phone_number,
            "hashed_password": get_password_hash(user.password),
            "is_active": False,
            "role": user.role or User.Role.USER,
            "code": code,
            "profile_picture": user.profile_picture,
            "address": user.address,
            "date_of_birth": user.date_of_birth,
            "gender": user.gender,
            "occupation": user.occupation,
            "ghana_card_number": user.ghana_card_number,
        }

        user = self.service_locator.general_service.create_data(db, User, data)

        return user, code

    def generate_code(self, db: Session) -> str:
        while True:
            code = str(random.randint(100000, 999999))
            if not db.query(User).filter(User.code == code).first():
                return code
