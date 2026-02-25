import uuid
from fastapi import status

from app.test.base import BaseTest
from app.accounts.models import User
from app.accounts.factories import UserFactory
from app.packages.models import Package, Subscription


class TestClaimFlow(BaseTest):
    def _create_package(self, coverage: str = "3000.00") -> Package:
        db = self.get_db()
        package = Package(
            name=f"ClaimPack-{uuid.uuid4().hex[:8]}",
            description="Package for claim tests",
            price="150.00",
            duration=30,
            coverage_amount=coverage,
            is_active=True,
            status=Package.STATUS.ACTIVE,
        )
        db.add(package)
        db.commit()
        db.refresh(package)
        return package

    def _create_subscription(self, user_id: str, package_id, active: bool = True) -> Subscription:
        db = self.get_db()
        subscription = Subscription(
            user_id=user_id,
            package_id=package_id,
            status=Subscription.STATUS.ACTIVE if active else Subscription.STATUS.PENDING,
            payment_status=Subscription.PAYMENT_STATUS.PAID if active else Subscription.PAYMENT_STATUS.PENDING,
            auto_renew=False,
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        return subscription

    def test_create_list_get_claim(self):
        user = UserFactory(email=f"user-{uuid.uuid4().hex[:8]}@example.com")
        package = self._create_package()
        subscription = self._create_subscription(str(user.id), package.id, active=True)
        self.force_authenticate(user)

        create_response = self.client.post(
            "/claims/",
            json={
                "subscription_id": str(subscription.id),
                "claim_amount": "450.00",
                "reason": "Minor accident damages",
            },
        )
        assert create_response.status_code == status.HTTP_201_CREATED, create_response.text
        claim = create_response.json()
        assert claim["status"] == "pending"

        list_response = self.client.get("/claims/")
        assert list_response.status_code == status.HTTP_200_OK, list_response.text
        assert list_response.json()["total"] >= 1

        get_response = self.client.get(f"/claims/{claim['id']}/")
        assert get_response.status_code == status.HTTP_200_OK, get_response.text
        assert get_response.json()["id"] == claim["id"]

    def test_create_claim_rejects_inactive_subscription(self):
        user = UserFactory(email=f"user-{uuid.uuid4().hex[:8]}@example.com")
        package = self._create_package()
        subscription = self._create_subscription(str(user.id), package.id, active=False)
        self.force_authenticate(user)

        response = self.client.post(
            "/claims/",
            json={
                "subscription_id": str(subscription.id),
                "claim_amount": "200.00",
                "reason": "Need support",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_admin_can_update_claim_status(self):
        user = UserFactory(email=f"user-{uuid.uuid4().hex[:8]}@example.com")
        admin = UserFactory(
            email=f"admin-{uuid.uuid4().hex[:8]}@example.com",
            role=User.Role.ADMIN,
        )
        package = self._create_package()
        subscription = self._create_subscription(str(user.id), package.id, active=True)

        self.force_authenticate(user)
        create_response = self.client.post(
            "/claims/",
            json={
                "subscription_id": str(subscription.id),
                "claim_amount": "300.00",
                "reason": "Hospital expenses",
            },
        )
        assert create_response.status_code == status.HTTP_201_CREATED, create_response.text
        claim_id = create_response.json()["id"]

        self.force_authenticate(admin)
        update_response = self.client.patch(
            f"/claims/{claim_id}/status/",
            json={"status": "approved", "reviewer_note": "Approved by admin"},
        )
        assert update_response.status_code == status.HTTP_200_OK, update_response.text
        assert update_response.json()["status"] == "approved"
