import uuid
from fastapi import status

from app.packages.models import Package, Subscription
from app.literal.models import TransportType
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

    def _create_transport_type(self) -> TransportType:
        db = self.get_db()
        transport_type = TransportType(
            name=f"Air-{uuid.uuid4().hex[:8]}",
            description="Air transport",
            is_active=True,
        )
        db.add(transport_type)
        db.commit()
        db.refresh(transport_type)
        return transport_type

    def test_subscribe_list_get_cancel(self):
        user = UserFactory(email=f"user-{uuid.uuid4().hex[:8]}@example.com")
        package = self._create_package()
        transport_type = self._create_transport_type()
        self.force_authenticate(user)

        subscribe_response = self.client.post(
            "/subscriptions/",
            json={
                "package_id": str(package.id),
                "auto_renew": True,
                "transport_type_id": str(transport_type.id),
                "beneficiary_name": "Test User",
            },
        )
        assert subscribe_response.status_code == status.HTTP_201_CREATED, subscribe_response.text
        subscription = subscribe_response.json()
        assert str(subscription["user_id"]) == str(user.id)
        assert subscription["status"] == Subscription.STATUS.PENDING

        list_response = self.client.get("/subscriptions/")
        assert list_response.status_code == status.HTTP_200_OK, list_response.text
        listed = list_response.json()
        assert listed["total"] >= 1
        assert len(listed["items"]) >= 1

        get_response = self.client.get(f"/subscriptions/{subscription['id']}/")
        assert get_response.status_code == status.HTTP_200_OK, get_response.text
        assert get_response.json()["id"] == subscription["id"]

        cancel_response = self.client.patch(
            f"/subscriptions/{subscription['id']}/",
            json={"status": "cancelled"},
        )
        assert cancel_response.status_code == status.HTTP_200_OK, cancel_response.text
        assert cancel_response.json(
        )["status"] == Subscription.STATUS.CANCELLED

    def test_subscribe_multiple_times_same_package(self):
        """Test that a user can purchase the same package multiple times if first is paid"""
        user = UserFactory(email=f"user-{uuid.uuid4().hex[:8]}@example.com")
        package = self._create_package()
        transport_type = self._create_transport_type()
        db = self.get_db()

        # Create first subscription for this package with PAID status
        existing = Subscription(
            user_id=str(user.id),
            package_id=package.id,
            status=Subscription.STATUS.ACTIVE,
            payment_status=Subscription.PAYMENT_STATUS.PAID,
            auto_renew=False,
            transport_type_id=transport_type.id,
            beneficiary_name="Test User",
        )
        db.add(existing)
        db.commit()

        # Should be able to create a second subscription for the same package since first is paid
        self.force_authenticate(user)
        response = self.client.post(
            "/subscriptions/",
            json={
                "package_id": str(package.id),
                "auto_renew": False,
                "transport_type_id": str(transport_type.id),
                "beneficiary_name": "Test User 2",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["package"]["id"] == str(package.id)
        assert data["status"] == Subscription.STATUS.PENDING
        assert data["payment_status"] == Subscription.PAYMENT_STATUS.PENDING

    def test_subscribe_blocked_when_unpaid_exists(self):
        """Test that a user cannot purchase same package if unpaid subscription exists"""
        user = UserFactory(email=f"user-{uuid.uuid4().hex[:8]}@example.com")
        package = self._create_package()
        transport_type = self._create_transport_type()
        db = self.get_db()

        # Create first subscription with UNPAID (PENDING) status
        existing = Subscription(
            user_id=str(user.id),
            package_id=package.id,
            status=Subscription.STATUS.ACTIVE,
            payment_status=Subscription.PAYMENT_STATUS.PENDING,
            auto_renew=False,
            transport_type_id=transport_type.id,
            beneficiary_name="Test User",
        )
        db.add(existing)
        db.commit()

        # Should NOT be able to create another subscription while unpaid one exists
        self.force_authenticate(user)
        response = self.client.post(
            "/subscriptions/",
            json={
                "package_id": str(package.id),
                "auto_renew": False,
                "transport_type_id": str(transport_type.id),
                "beneficiary_name": "Test User 2",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "unpaid" in response.json()["detail"].lower()
