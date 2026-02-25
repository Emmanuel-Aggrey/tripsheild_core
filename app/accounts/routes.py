from app.authentication.utils import get_current_active_user
from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request, HTTPException, status
from app.core.dependency_injection import service_locator
from .schemas import UserResponseSchema
from .schemas import UserSchema
from .schemas import UserProfileUpdateSchema
from .models import User
from app.dependencies import get_db
from fastapi_utils.cbv import cbv
from sqlalchemy.orm import Session

router = APIRouter(dependencies=[Depends(get_current_active_user)])


@cbv(router)
class AccountView:
    db: Session = Depends(get_db)
    current_user: UserSchema = Depends(get_current_active_user)

    @router.get("/me/", response_model=UserResponseSchema)
    @router.get("/", response_model=UserResponseSchema)
    async def get_account(self, request: Request):
        return self.current_user

    @router.patch("/me/", response_model=UserResponseSchema)
    @router.patch("/", response_model=UserResponseSchema)
    async def update_profile(self, payload: UserProfileUpdateSchema):
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            return self.current_user

        if "email" in update_data:
            existing = service_locator.account_service.get_user_by_email(
                self.db, update_data["email"]
            )
            if existing and str(existing.id) != str(self.current_user.id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already in use",
                )

        updated_user = service_locator.general_service.update_data(
            db=self.db,
            key=self.current_user.id,
            data=update_data,
            model=User
        )
        return updated_user
