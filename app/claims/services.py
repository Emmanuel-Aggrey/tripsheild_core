from typing import Optional
from uuid import UUID
import logging
from app.database import SessionLocal
from app.claims.models import Claim
from app.packages.models import Subscription, Package
from app.claims.schemas import ClaimResponseSchema, ClaimListResponseSchema
from app.storage.models import Storage
logger = logging.getLogger(__name__)


class ClaimService:
    def __init__(self):
        from app.core.dependency_injection import service_locator
        self.service_locator = service_locator

    def _to_schema(self, claim: Claim) -> dict:
        return ClaimResponseSchema.model_validate(claim).model_dump()

    def create_claim(self, user_id: str, payload: dict) -> dict:
        db = SessionLocal()
        try:
            subscription_id = payload.get("subscription_id")

            subscription: Subscription = self.service_locator.general_service.filter_data(
                db=db,
                filter_values={"id": subscription_id, "user_id": user_id},
                model=Subscription,
                single_record=True,
            )
            if not subscription:
                raise ValueError("Subscription not found")
            if subscription.status != Subscription.STATUS.ACTIVE:
                raise ValueError("Only active subscriptions can submit claims")

            package: Package = self.service_locator.general_service.filter_data(
                db=db,
                filter_values={"id": subscription.package_id},
                model=Package,
                single_record=True,
            )
            if not package or not package.price:
                raise ValueError("Package has no price set")

            claim_amount = package.price

            storage_ids = payload.get("storages") or []
            storages = [
                self.service_locator.general_service.get_data_by_id(
                    db=db, key=sid, model=Storage)
                for sid in storage_ids
            ]

            claim = self.service_locator.general_service.create_data(
                db=db,
                model=Claim,
                data={
                    **payload,
                    "user_id": user_id,
                    "claim_amount": str(claim_amount),
                    "status": Claim.STATUS.PENDING,
                    "storages": storages,
                },
            )

            return self._to_schema(claim)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create claim: {e}")
            raise
        finally:
            db.close()

    def get_claim(self, claim_id: str, user_id: str, is_admin: bool = False) -> Optional[dict]:
        db = SessionLocal()
        try:
            filter_values = {"id": UUID(claim_id)}
            if not is_admin:
                filter_values["user_id"] = user_id
            claim: Claim = self.service_locator.general_service.filter_data(
                db=db, filter_values=filter_values, model=Claim, single_record=True
            )
            if not claim:
                return None
            return self._to_schema(claim)
        except ValueError:
            return None
        finally:
            db.close()

    def list_claims(
        self, user_id: str, is_admin: bool = False, status: str = None, page: int = 1, limit: int = 10
    ) -> dict:
        db = SessionLocal()
        try:
            filter_values = {}
            if not is_admin:
                filter_values["user_id"] = user_id
            if status:
                filter_values["status"] = status

            claims = self.service_locator.general_service.filter_data(
                db=db, filter_values=filter_values, model=Claim, single_record=False,
                order_by=Claim.created_at.desc()
            )

            total = len(claims)
            start = (page - 1) * limit
            paginated = claims[start: start + limit]

            return ClaimListResponseSchema(
                claims=[ClaimResponseSchema.model_validate(
                    c) for c in paginated],
                total=total,
                page=page,
                limit=limit,
            ).model_dump()
        finally:
            db.close()

    def update_claim_status(self, claim_id: str, status: str, reviewer_note: str = None) -> Optional[dict]:
        db = SessionLocal()
        try:
            claim_uuid = UUID(claim_id)
            claim = self.service_locator.general_service.filter_data(
                db=db, filter_values={"id": claim_uuid}, model=Claim, single_record=True
            )
            if not claim:
                return None

            updated = self.service_locator.general_service.update_data(
                db=db,
                key=claim_uuid,
                data={"status": status, "reviewer_note": reviewer_note},
                model=Claim,
            )
            return self._to_schema(updated)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update claim status: {e}")
            raise
        finally:
            db.close()
