from fastapi import APIRouter,  Depends

from fastapi_utils.cbv import cbv
from .schemas import AllLiteralsResponseSchema, LiteralBaseSchema
from .models import TransportType
from app.dependencies import get_db
from app.accounts.schemas import UserSchema
from sqlalchemy.orm import Session
from app.authentication.utils import get_current_active_user
from app.literal.categories import LiteralCategory


literal_router = APIRouter(dependencies=[Depends(get_current_active_user)])
subscriptions_router = APIRouter(
    dependencies=[Depends(get_current_active_user)])


@cbv(literal_router)
class LiteralView:

    current_user: UserSchema = Depends(get_current_active_user)
    db: Session = Depends(get_db)

    @literal_router.get("/all/", response_model=AllLiteralsResponseSchema)
    def get_all_literals(self):
        return AllLiteralsResponseSchema(
            transport_types=self.db.query(TransportType).all()
        )

    @literal_router.get("/{category}/", response_model=list[LiteralBaseSchema])
    def get_literal_by_category(self, category: LiteralCategory):
        model = self.category_to_model(category)
        return self.db.query(model).all()

    def category_to_model(self, category: LiteralCategory):
        mapping = {
            LiteralCategory.TRANSPORT_TYPES: TransportType,
        }
        return mapping.get(category)
