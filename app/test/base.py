from app.accounts.models import User
from app.authentication.utils import create_access_token
from app.database import Base
from app.dependencies import get_db
from app.main import app
from app.settings import SQLALCHEMY_DATABASE_URL
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # connect_args={"check_same_thread": False},
    # poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


class BaseTest:
    client = TestClient(app)
    db = None

    @classmethod
    def get_db(cls):
        if cls.db is None:
            cls.db = TestingSessionLocal()
        return cls.db

    def force_authenticate(self, user: User = None):
        if user is None:
            self.client.headers = {"Authorization": ""}
            return

        token = create_access_token(data={"sub": user.email})
        self.client.headers = {"Authorization": f"Bearer {token}"}
        self.client.headers = {"authorization": f"Bearer {token}"}
        return token
