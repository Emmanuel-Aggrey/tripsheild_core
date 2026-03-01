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

    @router.get("/", response_model=list[UserResponseSchema])
    async def get_users(self, request: Request):
        return service_locator.account_service.get_users(self.db)

    @router.get("/me/", response_model=UserResponseSchema)
    async def get_account(self, request: Request):
        return self.current_user

    @router.patch("/{id}/", response_model=UserResponseSchema)
    async def update_profile(self, id: str, payload: UserProfileUpdateSchema):
        if not service_locator.account_service.is_admin(self.current_user) and str(self.current_user.id) != id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required or you are not allowed to update this user"
            )

        update_data = payload.model_dump(exclude_unset=True)

        updated_user = service_locator.general_service.update_data(
            db=self.db,
            key=id,
            data=update_data,
            model=User
        )
        return updated_user
