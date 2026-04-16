from app.test.base import BaseTest
from fastapi import status
import uuid
from app.accounts.models import User
import pytest
from app.core.dependency_injection import service_locator


class TestAuthentication(BaseTest):
    @pytest.fixture(autouse=True)
    def mock_notification_services(self, monkeypatch):
        async def fake_send_template_email(*args, **kwargs):
            return None

        def fake_send_text_message(*args, **kwargs):
            return {"ok": True}

        monkeypatch.setattr(
            service_locator.core_service,
            "send_template_email",
            fake_send_template_email,
        )
        monkeypatch.setattr(
            service_locator.core_service,
            "send_text_message",
            fake_send_text_message,
        )

    def test_create_user(self):
        email = f"deadpool-{uuid.uuid4().hex[:8]}@example.com"
        response = self.client.post(
            "/register/",
            json={
                "first_name": "deadpool",
                "last_name": "wilson",
                "phone_number": f"23324{uuid.uuid4().hex[:7]}",
                "email": email,
                "password": "chimichangas4life",
            },
        )
        assert response.status_code == status.HTTP_200_OK, response.text
        data = response.json()
        assert data["email"] == email
        assert "id" in data

    def test_gimme_jwt(self):
        email = f"deadpool-{uuid.uuid4().hex[:8]}@example.com"
        phone_number = f"23324{uuid.uuid4().hex[:7]}"
        password = "chimichangas4life"
        register_response = self.client.post(
            "/register/",
            json={
                "first_name": "deadpool",
                "last_name": "wilson",
                "phone_number": phone_number,
                "email": email,
                "password": password,
            },
        )
        assert register_response.status_code == status.HTTP_200_OK, register_response.text

        db = self.get_db()
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        assert user.code is not None

        verify_response = self.client.post(
            "/verify/",
            json={"email": email, "code": user.code},
        )
        assert verify_response.status_code == status.HTTP_200_OK, verify_response.text

        response = self.client.post(
            "/gimme-jwt/",
            json={"email": email, "password": password},
        )
        assert response.status_code == status.HTTP_200_OK, response.text

        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        mobile_login_response = self.client.post(
            "/gimme-jwt/",
            json={"phone_number": phone_number, "password": password},
        )
        assert mobile_login_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, mobile_login_response.text

    def test_email_login_otp_flow(self):
        email = f"otp-email-{uuid.uuid4().hex[:8]}@example.com"
        phone_number = f"23324{uuid.uuid4().hex[:7]}"
        password = "chimichangas4life"

        register_response = self.client.post(
            "/register/",
            json={
                "first_name": "deadpool",
                "last_name": "wilson",
                "phone_number": phone_number,
                "email": email,
                "password": password,
            },
        )
        assert register_response.status_code == status.HTTP_200_OK, register_response.text

        db = self.get_db()
        user = db.query(User).filter(User.email == email).first()
        assert user is not None

        verify_response = self.client.post(
            "/verify/",
            json={"email": email, "code": user.code},
        )
        assert verify_response.status_code == status.HTTP_200_OK, verify_response.text

        request_otp_response = self.client.post(
            "/login/email/",
            json={"email": email},
        )
        assert request_otp_response.status_code == status.HTTP_200_OK, request_otp_response.text
        assert request_otp_response.json(
        )["detail"] == "OTP sent to email"

        db.refresh(user)
        assert user.code is not None

        login_response = self.client.post(
            "/login/verify-otp/",
            json={"email": email, "code": user.code},
        )
        assert login_response.status_code == status.HTTP_200_OK, login_response.text
        assert "access_token" in login_response.json()

    def test_phone_login_otp_flow(self):
        email = f"otp-phone-{uuid.uuid4().hex[:8]}@example.com"
        phone_number = f"23324{uuid.uuid4().hex[:7]}"
        password = "chimichangas4life"

        register_response = self.client.post(
            "/register/",
            json={
                "first_name": "deadpool",
                "last_name": "wilson",
                "phone_number": phone_number,
                "email": email,
                "password": password,
            },
        )
        assert register_response.status_code == status.HTTP_200_OK, register_response.text

        db = self.get_db()
        user = db.query(User).filter(User.phone_number == phone_number).first()
        assert user is not None

        verify_response = self.client.post(
            "/verify/",
            json={"phone_number": phone_number, "code": user.code},
        )
        assert verify_response.status_code == status.HTTP_200_OK, verify_response.text

        request_otp_response = self.client.post(
            "/login/phone/",
            json={"phone_number": phone_number},
        )
        assert request_otp_response.status_code == status.HTTP_200_OK, request_otp_response.text
        assert request_otp_response.json(
        )["detail"] == "OTP sent to phone number"

        db.refresh(user)
        assert user.code is not None

        login_response = self.client.post(
            "/login/verify-otp/",
            json={"phone_number": phone_number, "code": user.code},
        )
        assert login_response.status_code == status.HTTP_200_OK, login_response.text
        assert "access_token" in login_response.json()

    def test_testing_user_otp_is_not_modified(self):
        email = f"testing-user-{uuid.uuid4().hex[:8]}@example.com"
        phone_number = f"23324{uuid.uuid4().hex[:7]}"
        password = "chimichangas4life"

        register_response = self.client.post(
            "/register/",
            json={
                "first_name": "deadpool",
                "last_name": "wilson",
                "phone_number": phone_number,
                "email": email,
                "password": password,
            },
        )
        assert register_response.status_code == status.HTTP_200_OK, register_response.text

        db = self.get_db()
        user = db.query(User).filter(User.email == email).first()
        assert user is not None

        user.is_testing_user = True
        user.code = "123456"
        db.commit()
        db.refresh(user)

        request_otp_response = self.client.post(
            "/login/email/",
            json={"email": email},
        )
        assert request_otp_response.status_code == status.HTTP_200_OK, request_otp_response.text
        db.refresh(user)
        assert user.code == "123456"

        login_response = self.client.post(
            "/login/verify-otp/",
            json={"email": email, "code": "123456"},
        )
        assert login_response.status_code == status.HTTP_200_OK, login_response.text

        db.refresh(user)
        assert user.code == "123456"
