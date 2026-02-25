import uuid
from fastapi import status

from app.packages.models import Package, Subscription
from app.test.base import BaseTest
from app.accounts.factories import UserFactory


class TestPackageSubscriptions(BaseTest):
    def _create_package(self) -> Package:
        db = self.get_db()
        package = Package(
            name=f"Starter-{uuid.uuid4().hex[:8]}",
            description="Starter package",
            price="120.00",
            duration=30,
            coverage_amount="1000.00",
            is_active=True,
            status=Package.STATUS.ACTIVE,
        )
        db.add(package)
        db.commit()
        db.refresh(package)
        return package

    def test_subscribe_list_get_cancel(self):
        user = UserFactory(email=f"user-{uuid.uuid4().hex[:8]}@example.com")
        package = self._create_package()
        self.force_authenticate(user)

        subscribe_response = self.client.post(
            f"/packages/{package.id}/subscribe/",
            json={"package_id": str(package.id), "auto_renew": True},
        )
        assert subscribe_response.status_code == status.HTTP_201_CREATED, subscribe_response.text
        subscription = subscribe_response.json()
        assert str(subscription["user_id"]) == str(user.id)
        assert subscription["status"] == Subscription.STATUS.PENDING

        list_response = self.client.get("/packages/subscriptions/")
        assert list_response.status_code == status.HTTP_200_OK, list_response.text
        listed = list_response.json()
        assert listed["total"] >= 1
        assert len(listed["items"]) >= 1

        get_response = self.client.get(f"/packages/subscriptions/{subscription['id']}/")
        assert get_response.status_code == status.HTTP_200_OK, get_response.text
        assert get_response.json()["id"] == subscription["id"]

        cancel_response = self.client.patch(
            f"/packages/subscriptions/{subscription['id']}/",
            json={"status": "cancelled"},
        )
        assert cancel_response.status_code == status.HTTP_200_OK, cancel_response.text
        assert cancel_response.json()["status"] == Subscription.STATUS.CANCELLED

    def test_subscribe_conflict_when_active_exists(self):
        user = UserFactory(email=f"user-{uuid.uuid4().hex[:8]}@example.com")
        package = self._create_package()
        db = self.get_db()
        existing = Subscription(
            user_id=str(user.id),
            package_id=package.id,
            status=Subscription.STATUS.ACTIVE,
            payment_status=Subscription.PAYMENT_STATUS.PAID,
            auto_renew=False,
        )
        db.add(existing)
        db.commit()

        self.force_authenticate(user)
        response = self.client.post(
            f"/packages/{package.id}/subscribe/",
            json={"package_id": str(package.id), "auto_renew": False},
        )
        assert response.status_code == status.HTTP_409_CONFLICT
