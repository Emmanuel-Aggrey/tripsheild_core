from fastapi import APIRouter, Query, Depends, HTTPException, status
from fastapi_utils.cbv import cbv
from app.core.dependency_injection import service_locator
from .schemas import (
    FeatureCreateSchema,
    FeatureUpdateSchema,
    FeatureResponseSchema,
)
from .models import Feature
from app.dependencies import get_db
from app.accounts.schemas import UserSchema
from sqlalchemy.orm import Session
from app.authentication.utils import get_current_active_user
from typing import List

router = APIRouter(dependencies=[Depends(get_current_active_user)])


@cbv(router)
class FeatureView:
    current_user: UserSchema = Depends(get_current_active_user)
    db: Session = Depends(get_db)
    
    def _check_admin(self):
        if self.current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
    
    @router.post("/", response_model=FeatureResponseSchema,
                 status_code=status.HTTP_201_CREATED)
    def create_feature(self, data: FeatureCreateSchema):

        self._check_admin()
        
        
        existing = service_locator.general_service.filter_data(
        db=self.db,
        model=Feature,
        filter_values={"name": data.name},
        single_record=True
    )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Feature with name '{data.name}' already exists"
            )
            
        
        feature = service_locator.general_service.create_data(
            db=self.db, 
            model=Feature, 
            data=data.model_dump()
        )
        return feature
    
    @router.get("/", response_model=List[FeatureResponseSchema])
    def list_features(
        self,
        active_only: bool = Query(True),
    ):
        result = service_locator.general_service.filter_data(
            db=self.db, 
            filter_values={"is_active": active_only},
            model=Feature,
            single_record=False
        )
        return result
        
    @router.get("/{id}/", response_model=FeatureResponseSchema)
    def get_feature(self, id: str):
        feature = service_locator.general_service.get_data_by_id(
            db=self.db, 
            model=Feature, 
            key=id
        )
        
        return feature
    
    @router.patch("/{id}/", response_model=FeatureResponseSchema)
    def update_feature(self, id: str, data: FeatureUpdateSchema):
        self._check_admin()
        
        feature = service_locator.general_service.update_data(
            db=self.db,
            model=Feature,
            key=id,
            data=data.model_dump(exclude_unset=True)
        )
       
        return feature
    
    @router.delete("/{id}/", status_code=status.HTTP_200_OK)
    def delete_feature(self, id: str):
        self._check_admin()
        
        service_locator.general_service.delete_data(
            db=self.db,
            model=Feature,
            key=id
        )
       
            
        return {"message": "Feature deleted successfully"}