from typing import Dict, Optional
from uuid import UUID
import logging
from decimal import Decimal, InvalidOperation
from app.database import SessionLocal
from app.claims.models import Claim
from app.packages.models import Subscription, Package

logger = logging.getLogger(__name__)


class ClaimService:
    def __init__(self):
        from app.core.dependency_injection import service_locator
        self.service_locator = service_locator

    def _serialize_claim(self, claim: Claim) -> dict:
        return {
            "id": str(claim.id),
            "user_id": claim.user_id,
            "subscription_id": str(claim.subscription_id),
            "claim_amount": claim.claim_amount,
            "reason": claim.reason,
            "incident_date": claim.incident_date.isoformat() if claim.incident_date else None,
            "status": claim.status,
            "reviewer_note": claim.reviewer_note,
            "created_at": claim.created_at.isoformat() if claim.created_at else None,
            "updated_at": claim.updated_at.isoformat() if claim.updated_at else None,
        }

    def create_claim(self, user_id: str, payload: dict) -> dict:
        db = SessionLocal()
        try:
            subscription_id = payload.get("subscription_id")
            claim_amount = payload.get("claim_amount")

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
            if package and package.coverage_amount:
                try:
                    if Decimal(str(claim_amount)) > Decimal(str(package.coverage_amount)):
                        raise ValueError("Claim amount exceeds package coverage")
                except InvalidOperation:
                    raise ValueError("Invalid claim amount")

            data = {
                "user_id": user_id,
                "subscription_id": subscription_id,
                "claim_amount": str(claim_amount),
                "reason": payload.get("reason"),
                "incident_date": payload.get("incident_date"),
                "status": Claim.STATUS.PENDING,
            }
            claim = self.service_locator.general_service.create_data(
                db=db, model=Claim, data=data
            )
            return self._serialize_claim(claim)
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
            return self._serialize_claim(claim)
        except ValueError:
            return None
        finally:
            db.close()

    def list_claims(
        self, user_id: str, is_admin: bool = False, status: str = None, page: int = 1, limit: int = 10
    ) -> Dict:
        db = SessionLocal()
        try:
            filter_values = {}
            if not is_admin:
                filter_values["user_id"] = user_id
            if status:
                filter_values["status"] = status

            claims = self.service_locator.general_service.filter_data(
                db=db, filter_values=filter_values, model=Claim, single_record=False
            )

            total = len(claims)
            start = (page - 1) * limit
            end = start + limit
            paginated = claims[start:end]
            return {
                "claims": [self._serialize_claim(c) for c in paginated],
                "total": total,
                "page": page,
                "limit": limit,
            }
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
            return self._serialize_claim(updated)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update claim status: {e}")
            raise
        finally:
            db.close()
