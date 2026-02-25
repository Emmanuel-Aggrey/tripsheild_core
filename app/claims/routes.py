from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi_utils.cbv import cbv
from sqlalchemy.orm import Session
from app.accounts.schemas import UserSchema
from app.authentication.utils import get_current_active_user
from app.dependencies import get_db
from app.core.dependency_injection import service_locator
from app.claims.schemas import (
    ClaimCreateSchema,
    ClaimListResponseSchema,
    ClaimResponseSchema,
    ClaimStatusUpdateSchema,
)

router = APIRouter(dependencies=[Depends(get_current_active_user)])


@cbv(router)
class ClaimView:
    current_user: UserSchema = Depends(get_current_active_user)
    db: Session = Depends(get_db)

    def _is_admin(self) -> bool:
        return self.current_user.role == "admin"

    @router.post("/", response_model=ClaimResponseSchema, status_code=status.HTTP_201_CREATED)
    def create_claim(self, payload: ClaimCreateSchema):
        try:
            return service_locator.claim_service.create_claim(
                user_id=str(self.current_user.id),
                payload=payload.model_dump(),
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.get("/", response_model=ClaimListResponseSchema)
    def list_claims(
        self,
        claim_status: str | None = Query(default=None, alias="status"),
        page: int = Query(1, ge=1),
        limit: int = Query(10, ge=1, le=100),
    ):
        return service_locator.claim_service.list_claims(
            user_id=str(self.current_user.id),
            is_admin=self._is_admin(),
            status=claim_status,
            page=page,
            limit=limit,
        )

    @router.get("/{claim_id}/", response_model=ClaimResponseSchema)
    def get_claim(self, claim_id: str):
        claim = service_locator.claim_service.get_claim(
            claim_id=claim_id,
            user_id=str(self.current_user.id),
            is_admin=self._is_admin(),
        )
        if not claim:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
        return claim

    @router.patch("/{claim_id}/status/", response_model=ClaimResponseSchema)
    def update_claim_status(self, claim_id: str, payload: ClaimStatusUpdateSchema):
        if not self._is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )

        claim = service_locator.claim_service.update_claim_status(
            claim_id=claim_id,
            status=payload.status.value,
            reviewer_note=payload.reviewer_note,
        )
        if not claim:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
        return claim
