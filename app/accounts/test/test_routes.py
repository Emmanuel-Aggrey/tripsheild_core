from app.test.base import BaseTest
from fastapi import status
import uuid

from ..factories import UserFactory


class TestAccount(BaseTest):
    def test_get_user(self):
        user = UserFactory()

        self.force_authenticate(user)
        response = self.client.get("/accounts/me/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == user.email

    def test_update_profile(self):
        user = UserFactory(email=f"user-{uuid.uuid4().hex[:8]}@example.com")
        self.force_authenticate(user)

        response = self.client.patch(
            "/accounts/me/",
            json={"first_name": "updated_user"},
        )

        assert response.status_code == status.HTTP_200_OK, response.text
        data = response.json()
        assert data["first_name"] == "updated_user"
