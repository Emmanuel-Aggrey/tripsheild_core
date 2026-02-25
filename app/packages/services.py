from .models import Package, Subscription
from app.database import SessionLocal
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

    def subscribe_to_package(self, user_id, package_id: str, auto_renew: bool = False) -> Subscription:
        db = SessionLocal()
        try:
            package = self.service_locator.general_service.filter_data(
                db=db, filter_values={"id": package_id, "is_active": True},
                model=Package, single_record=True
            )
            if not package:
                raise ValueError(f"Package {package_id} not found or inactive")

            subscription = self.service_locator.general_service.create_data(
                db=db, model=Subscription, data={
                    "user_id": user_id,
                    "package_id": package_id,
                    "status": Subscription.STATUS.PENDING,
                    "payment_status": Subscription.PAYMENT_STATUS.PENDING,
                    "auto_renew": auto_renew,
                }
            )
            return self._load_subscription(db, id=subscription.id)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to subscribe to package: {e}")
            raise
        finally:
            db.close()

    def get_subscriptions(self, subscription_id: str, user_id) -> Optional[Subscription]:
        db = SessionLocal()
        try:
            return self._load_subscription(
                db, id=UUID(subscription_id), user_id=user_id
            )
        except ValueError:
            return None
        finally:
            db.close()

    def cancel_subscription(self, subscription_id: str, user_id) -> Subscription:
        db = SessionLocal()
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
        finally:
            db.close()

    def activate_subscription(self, subscription_id: str) -> Subscription:
        db = SessionLocal()
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
        finally:
            db.close()

    def change_package(self, user_id, current_subscription_id: str, new_package_id: str) -> Subscription:
        self.cancel_subscription(current_subscription_id, user_id)
        return self.subscribe_to_package(user_id, new_package_id)
