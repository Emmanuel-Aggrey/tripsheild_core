import uuid
from fastapi import status

from app.test.base import BaseTest
from app.accounts.factories import UserFactory
from app.packages.models import Package, Subscription
from app.payment.models import Payment
from app.literal.models import TransportType


class TestPaymentFlow(BaseTest):
    def _create_package(self) -> Package:
        db = self.get_db()
        package = Package(
            name=f"Pro-{uuid.uuid4().hex[:8]}",
            description="Pro package",
            price="200.00",
            duration=60,
            coverage_amount="5000.00",
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

    def _create_subscription(self, user_id: str, package_id) -> Subscription:
        db = self.get_db()
        transport_type = self._create_transport_type()
        subscription = Subscription(
            user_id=user_id,
            package_id=package_id,
            status=Subscription.STATUS.PENDING,
            payment_status=Subscription.PAYMENT_STATUS.PENDING,
            auto_renew=False,
            transport_type_id=transport_type.id,
            beneficiary_name="Test User",
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        return subscription

    def test_buy_subscription_and_list_payments(self):
        user = UserFactory(email=f"user-{uuid.uuid4().hex[:8]}@example.com")
        package = self._create_package()
        transport_type = self._create_transport_type()
        self.force_authenticate(user)

        # Create subscription first
        sub_response = self.client.post(
            "/subscriptions/",
            json={
                "package_id": str(package.id),
                "transport_type_id": str(transport_type.id),
                "beneficiary_name": "Test User",
            },
        )
        assert sub_response.status_code == status.HTTP_201_CREATED, sub_response.text
        subscription = sub_response.json()

        # Create payment for subscription
        payment_response = self.client.post(
            f"/payments/{subscription['id']}/",
            json={"payment_method": "bank", "create_web_link": False},
        )
        assert payment_response.status_code == status.HTTP_201_CREATED, payment_response.text
        payment = payment_response.json()
        payment_id = payment["id"]

        list_response = self.client.get("/payments/")
        assert list_response.status_code == status.HTTP_200_OK, list_response.text
        data = list_response.json()
        assert data["total"] >= 1
        assert any(p["id"] == payment_id for p in data["items"])

        get_response = self.client.get(f"/payments/{payment_id}/")
        assert get_response.status_code == status.HTTP_200_OK, get_response.text
        assert get_response.json()["id"] == payment_id

    def test_initiate_payment_for_existing_subscription(self):
        user = UserFactory(email=f"user-{uuid.uuid4().hex[:8]}@example.com")
        package = self._create_package()
        subscription = self._create_subscription(str(user.id), package.id)
        self.force_authenticate(user)

        response = self.client.post(
            f"/payments/{subscription.id}/",
            json={"payment_method": "bank"},
        )
        assert response.status_code == status.HTTP_201_CREATED, response.text
        assert response.json()["status"] == Payment.STATUS.ONGOING

    def test_verify_payment_forbidden_for_different_user(self):
        owner = UserFactory(email=f"owner-{uuid.uuid4().hex[:8]}@example.com")
        other = UserFactory(email=f"other-{uuid.uuid4().hex[:8]}@example.com")
        package = self._create_package()
        subscription = self._create_subscription(str(owner.id), package.id)

        db = self.get_db()
        payment = Payment(
            user_id=str(owner.id),
            subscription_id=subscription.id,
            amount="200.00",
            currency=Payment.CURRENCY.GHS,
            payment_method=Payment.PAYMENT_METHOD.BANK,
            status=Payment.STATUS.ONGOING,
            transaction_id=f"TXN-{uuid.uuid4().hex[:12]}",
            web_page_reference="ref-test",
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        self.force_authenticate(other)
        response = self.client.post(
            f"/payments/{subscription.id}/verify/",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN, response.text
