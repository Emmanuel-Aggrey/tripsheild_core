from fastapi_utils.cbv import cbv
from app.core.dependency_injection import service_locator
from app.authentication.utils import get_current_active_user
from fastapi import Depends
from sqlalchemy.orm import Session
from fastapi_pagination import Page
from fastapi_pagination import paginate
from app.dependencies import get_db
from app.insuranc_records.shemas import InsurancRecordSchema
from app.insuranc_records.models import InsurancRecord
from fastapi import APIRouter

router = APIRouter(dependencies=[Depends(get_current_active_user)])


@cbv(router)
class InsurancRecordsView:
    db: Session = Depends(get_db)

    @router.get("/insuranc_records/", response_model=Page[InsurancRecordSchema])
    async def get_insuranc_records(self,):
        insuranc_records_service = service_locator.general_service.list_data(
            self.db, InsurancRecord)

        return paginate(insuranc_records_service)
