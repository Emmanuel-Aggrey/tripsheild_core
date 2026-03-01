from fastapi import APIRouter, Query, Depends, HTTPException, status
from fastapi_utils.cbv import cbv
from typing import Optional
from fastapi_pagination import Page, Params
from fastapi_pagination.ext.sqlalchemy import paginate as sa_paginate
from app.core.dependency_injection import service_locator
from .schemas import (
    PackageCreateSchema,
    PackageUpdateSchema,
    PackageResponseSchema,
    SubscriptionCreateSchema,
    SubscriptionUpdateSchema,
    SubscriptionResponseSchema,
)
from .models import Package, Subscription
from app.dependencies import get_db
from app.accounts.schemas import UserSchema
from sqlalchemy.orm import Session
from app.authentication.utils import get_current_active_user


packages_router = APIRouter(dependencies=[Depends(get_current_active_user)])
subscriptions_router = APIRouter(
    dependencies=[Depends(get_current_active_user)])


@cbv(packages_router)
class PackageView:
    current_user: UserSchema = Depends(get_current_active_user)
    db: Session = Depends(get_db)

    def _check_admin(self):
        if self.current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

    @packages_router.post("/", response_model=PackageResponseSchema, status_code=status.HTTP_201_CREATED)
    def create_package(self, data: PackageCreateSchema):
        self._check_admin()

        if service_locator.general_service.filter_data(
            db=self.db, model=Package,
            filter_values={"name": data.name}, single_record=True
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Package with name '{data.name}' already exists"
            )

        package_data = data.model_dump()
        package_data["price"] = str(data.price)
        if data.coverage_amount is not None:
            package_data["coverage_amount"] = str(data.coverage_amount)
        package_data.setdefault("status", Package.STATUS.ACTIVE)
        feature_ids = [fid for fid in package_data.pop(
            "feature_ids", []) if fid]

        package = service_locator.general_service.create_data(
            db=self.db, model=Package, data=package_data
        )

        if feature_ids:
            from app.features.models import Feature
            features = self.db.query(Feature).filter(
                Feature.id.in_(feature_ids)).all()
            if features:
                package.features = features
                self.db.commit()
                self.db.refresh(package)

        return package

    @packages_router.get("/", response_model=Page[PackageResponseSchema])
    def list_packages(self, active_only: bool = Query(True), params: Params = Depends()):
        queryset = self.db.query(Package)
        if active_only:
            queryset = queryset.filter(
                Package.is_active.is_(True),
                Package.status == Package.STATUS.ACTIVE
            )
        return sa_paginate(self.db, queryset, params)

    @packages_router.get("/{id:uuid}/", response_model=PackageResponseSchema)
    def get_package(self, id: str):
        package = service_locator.general_service.get_data_by_id(
            db=self.db, key=id, model=Package,
        )
        if not package:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
        return package

    @packages_router.patch("/{id:uuid}/", response_model=PackageResponseSchema)
    def update_package(self, id: str, data: PackageUpdateSchema):
        self._check_admin()

        update_data = data.model_dump(exclude_unset=True)
        if "price" in update_data:
            update_data["price"] = str(update_data["price"])
        if update_data.get("coverage_amount"):
            update_data["coverage_amount"] = str(
                update_data["coverage_amount"])
        if "status" in update_data:
            update_data["status"] = update_data["status"].value

        feature_ids = update_data.pop("feature_ids", None)

        package = service_locator.general_service.update_data(
            db=self.db, model=Package, key=id, data=update_data
        )
        if not package:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")

        if feature_ids is not None:
            from app.features.models import Feature
            feature_ids = [fid for fid in feature_ids if fid]
            package.features = self.db.query(Feature).filter(
                Feature.id.in_(feature_ids)).all() if feature_ids else []
            self.db.commit()
            self.db.refresh(package)

        return package

    @packages_router.delete("/{id:uuid}/", status_code=status.HTTP_200_OK)
    def delete_package(self, id: str):
        self._check_admin()
        if not service_locator.general_service.delete_data(db=self.db, key=id, model=Package):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
        return {"message": "Package deleted successfully"}


@cbv(subscriptions_router)
class SubscriptionView:
    current_user: UserSchema = Depends(get_current_active_user)
    db: Session = Depends(get_db)

    @subscriptions_router.get("/", response_model=Page[SubscriptionResponseSchema])
    def list_subscriptions(
        self,
        status_filter: str | None = Query(default=None, alias="status"),
        params: Params = Depends(),
    ):
        queryset = self.db.query(Subscription).filter(
            Subscription.user_id == str(self.current_user.id)
        )
        if status_filter:
            queryset = queryset.filter(Subscription.status == status_filter)
        return sa_paginate(self.db, queryset, params)

    @subscriptions_router.get("/{id}/", response_model=SubscriptionResponseSchema)
    def get_subscription(self, id: str) -> Optional[Subscription]:
        subscription = service_locator.package_service.get_subscriptions(
            subscription_id=id, user_id=str(self.current_user.id)
        )
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
        return subscription

    @subscriptions_router.patch("/{id}/", response_model=SubscriptionResponseSchema)
    def update_subscription(self, id: str, data: SubscriptionUpdateSchema):
        try:
            return service_locator.package_service.cancel_subscription(
                subscription_id=id, user_id=str(self.current_user.id)
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @subscriptions_router.post("/{package_id}/", response_model=SubscriptionResponseSchema, status_code=status.HTTP_201_CREATED)
    def subscribe_to_package(self, package_id: str, payload: SubscriptionCreateSchema):
        if service_locator.general_service.filter_data(
            db=self.db, model=Subscription,
            filter_values={
                "user_id": str(self.current_user.id),
                "package_id": package_id,
                "status": Subscription.STATUS.ACTIVE,
            },
            single_record=True,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Active subscription already exists for this package",
            )

        try:
            return service_locator.package_service.subscribe_to_package(
                user_id=str(self.current_user.id),
                package_id=package_id,
                auto_renew=payload.auto_renew,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
