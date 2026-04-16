from .models import Package, Subscription
from typing import Optional
from uuid import UUID
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)


class PackageService:
    def __init__(self):
        from app.core.dependency_injection import service_locator
        self.service_locator = service_locator

    def _load_subscription(self, db, **filters) -> Optional[Subscription]:
        query = db.query(Subscription).options(
            joinedload(Subscription.package).joinedload(Package.features)
        )
        for key, value in filters.items():
            query = query.filter(getattr(Subscription, key) == value)
        return query.first()

    def _get_subscription(self, db, subscription_id: str, user_id) -> Subscription:
        subscription = self._load_subscription(
            db, id=UUID(subscription_id), user_id=user_id
        )
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")
        return subscription

    def subscribe_to_package(self, db, data: dict) -> Subscription:

        if not self.service_locator.general_service.filter_data(
            db=db,
            model=Package,
            filter_values={"id": data["package_id"], "is_active": True},
            single_record=True
        ):
            raise ValueError("Package not found or inactive")

        # Check if user has an unpaid subscription for this package (regardless of status)
        unpaid_subscription = db.query(Subscription).filter(
            Subscription.user_id == data["user_id"],
            Subscription.package_id == data["package_id"],
            Subscription.payment_status != Subscription.PAYMENT_STATUS.PAID,
            Subscription.status != Subscription.STATUS.CANCELLED
        ).first()

        if unpaid_subscription:
            raise ValueError(
                "You have an unpaid subscription for this package. Please complete payment first.")

        return self.service_locator.general_service.create_data(
            db=db, model=Subscription, data=data
        )

    def get_subscriptions(self, db, subscription_id: str, user_id) -> Optional[Subscription]:

        try:
            return self._load_subscription(
                db, id=UUID(subscription_id), user_id=user_id
            )
        except ValueError:
            return None

    def cancel_subscription(self, db, subscription_id: str, user_id) -> Subscription:
        try:
            subscription = self._get_subscription(db, subscription_id, user_id)
            if subscription.status == Subscription.STATUS.CANCELLED:
                raise ValueError("Subscription already cancelled")

            self.service_locator.general_service.update_data(
                db=db, key=UUID(subscription_id),
                data={"status": Subscription.STATUS.CANCELLED},
                model=Subscription,
            )
            logger.info(f"Cancelled subscription {subscription_id}")
            return self._load_subscription(db, id=UUID(subscription_id))
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to cancel subscription: {e}")
            raise

    def activate_subscription(self, db, subscription_id: str) -> Subscription:

        try:
            up_uuid = UUID(subscription_id)
            subscription = self._load_subscription(db, id=up_uuid)
            if not subscription:
                raise ValueError(f"Subscription {subscription_id} not found")

            package = self.service_locator.general_service.filter_data(
                db=db, filter_values={"id": subscription.package_id},
                model=Package, single_record=True
            )
            if not package:
                raise ValueError("Package not found")

            now = datetime.now(timezone.utc)
            self.service_locator.general_service.update_data(
                db=db, key=up_uuid, model=Subscription, data={
                    "status": Subscription.STATUS.ACTIVE,
                    "payment_status": Subscription.PAYMENT_STATUS.PAID,
                    "start_date": now,
                    "end_date": now + timedelta(days=package.duration),
                }
            )
            logger.info(f"Activated subscription {subscription_id}")
            return self._load_subscription(db, id=up_uuid)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to activate subscription: {e}")
            raise

    def change_package(self, db, user_id, current_subscription_id: str, new_package_id: str) -> Subscription:
        try:
            subscription = self._get_subscription(
                db, current_subscription_id, user_id)
            if subscription.status == Subscription.STATUS.CANCELLED:
                raise ValueError("Subscription already cancelled")

            new_subscription = self.subscribe_to_package(db, data={
                "user_id": user_id,
                "package_id": UUID(new_package_id),
                "status": Subscription.STATUS.PENDING,
                "payment_status": Subscription.PAYMENT_STATUS.PENDING,
                "auto_renew": False,
                "start_date": None,
                "end_date": None,
            })
            self.service_locator.general_service.update_data(
                db=db, key=UUID(current_subscription_id),
                data={"status": Subscription.STATUS.CANCELLED},
                model=Subscription,
            )
            db.commit()
            logger.info(
                f"Changed package for user {user_id}: {current_subscription_id} -> {new_package_id}")
            return new_subscription
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to change package: {e}")
            raise
