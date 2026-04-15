from .shemas import InsurancRecordSchema
from .models import InsurancRecord
from app.database import SessionLocal
from typing import Optional, Dict
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


class InsuranceRecordService:
    def __init__(self):
        from app.core.dependency_injection import service_locator
        self.service_locator = service_locator

    # Valid status transitions
    VALID_STATUS_TRANSITIONS = {
        "pending": ["approved", "rejected"],
        "approved": [],  # Cannot change once approved
        "rejected": [],  # Cannot change once rejected
    }

    def _validate_status_transition(self, current_status: str, new_status: str,
                                    admin_action: bool = False) -> bool:
        """Validate if status transition is allowed."""
        if admin_action:
            # Admins can change from pending to approved/rejected
            if current_status == "pending" and new_status in ["approved", "rejected"]:
                return True
            return False

        # Non-admin status transitions
        allowed = self.VALID_STATUS_TRANSITIONS.get(current_status, [])
        return new_status in allowed

    def _serialize_record(self, record: InsurancRecord) -> dict:
        """Serialize a record to a dictionary."""
        return {
            "id": str(record.id),
            "user_id": record.user_id,
            "amount": str(record.amount),
            "duration": record.duration,
            "status": record.status,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }

    def create_insurance_record(self, payload: dict) -> InsurancRecordSchema:
        """Create a new insurance record from API payload data."""
        # Accept both nested and flat payloads for compatibility.
        data = payload.get("data", payload)

        insurance_data = {
            "user_id": data.get("user_id"),
            "amount": str(data.get("amount")),
            "duration": data.get("duration"),
            "status": data.get("status", "pending")
        }

        db = SessionLocal()
        try:
            record = self.service_locator.general_service.create_data(
                db=db,
                model=InsurancRecord,
                data=insurance_data
            )
            logger.info(f"✓ Created insurance record {record.id}")
            return InsurancRecordSchema(**insurance_data)
        except Exception as e:
            db.rollback()
            logger.error(f"✗ Failed to create insurance record: {e}")
            raise
        finally:
            db.close()

    def get_insurance_record(self, record_id: str, user_id: str) -> Optional[dict]:
        """Get a specific insurance record by ID."""
        db = SessionLocal()
        try:
            # Validate UUID format
            try:
                record_uuid = UUID(record_id)
            except ValueError:
                logger.error(f"Invalid record_id format: {record_id}")
                return None

            record = self.service_locator.general_service.filter_data(
                db=db,
                filter_values={"id": record_uuid, "user_id": user_id},
                model=InsurancRecord,
                single_record=True
            )

            if not record:
                logger.warning(
                    f"Record {record_id} not found for user {user_id}")
                return None

            return self._serialize_record(record)
        except Exception as e:
            logger.error(f"✗ Failed to get insurance record: {e}")
            raise
        finally:
            db.close()

    def update_insurance_record(self, record_id: str, user_id: str,
                                update_data: dict, admin_action: bool = False) -> Optional[dict]:
        """Update an existing insurance record."""
        db = SessionLocal()
        try:

            # Get the existing record
            filter_values = {"id": record_id}
            if not admin_action:
                filter_values["user_id"] = user_id

            record = self.service_locator.general_service.filter_data(
                db=db,
                filter_values=filter_values,
                model=InsurancRecord,
                single_record=True
            )

            if not record:
                raise ValueError(f"Record {record_id} not found")

            # Remove admin_action from update_data if present
            update_data.pop("admin_action", None)

            # Convert amount to string if present
            if "amount" in update_data:
                update_data["amount"] = str(update_data["amount"])

            # Update the record
            update_data.pop("status", None)

            updated_record = self.service_locator.general_service.update_data(
                db=db,
                key=record_id,
                data=update_data,
                model=InsurancRecord
            )

            logger.info(f"✓ Updated insurance record {record_id}")
            return self._serialize_record(updated_record)
        except Exception as e:
            db.rollback()
            logger.error(
                f"✗ Failed to update insurance record: {e}, {update_data}")
            raise
        finally:
            db.close()

    def delete_insurance_record(self, record_id: str, user_id: str) -> bool:
        """Delete (soft or hard) an insurance record."""
        db = SessionLocal()
        try:
            # Validate UUID format
            try:
                record_uuid = UUID(record_id)
            except ValueError:
                logger.error(f"Invalid record_id format: {record_id}")
                raise ValueError(f"Invalid record_id: {record_id}")

            # Verify the record belongs to the user
            record = self.service_locator.general_service.filter_data(
                db=db,
                filter_values={"id": record_uuid, "user_id": user_id},
                model=InsurancRecord,
                single_record=True
            )

            if not record:
                raise ValueError(
                    f"Record {record_id} not found for user {user_id}")

            # Hard delete for now (can be changed to soft delete)
            self.service_locator.general_service.delete_data(
                db=db,
                key=record_uuid,
                model=InsurancRecord
            )

            logger.info(f"✓ Deleted insurance record {record_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"✗ Failed to delete insurance record: {e}")
            raise
        finally:
            db.close()

    def list_insurance_records(self, user_id: str, status: str = None,
                               page: int = 1, limit: int = 10) -> Dict:
        """List insurance records with filtering and pagination."""
        db = SessionLocal()
        try:
            # Build filter
            filter_values = {"user_id": user_id}
            if status:
                filter_values["status"] = status

            # Get all records matching filter
            records = self.service_locator.general_service.filter_data(
                db=db,
                filter_values=filter_values,
                model=InsurancRecord,
                single_record=False
            )

            # Calculate pagination
            total = len(records)
            start = (page - 1) * limit
            end = start + limit
            paginated_records = records[start:end]

            # Serialize records
            serialized_records = [
                self._serialize_record(record) for record in paginated_records
            ]

            return {
                "records": serialized_records,
                "total": total,
                "page": page,
                "limit": limit
            }
        except Exception as e:
            logger.error(f"✗ Failed to list insurance records: {e}")
            raise
        finally:
            db.close()
