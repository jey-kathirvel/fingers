from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DbDep, require_roles
from app.models import OrganizationMember, Role
from app.schemas import (
    AccountMetricTrendOut,
    AnalyticsSyncOut,
    PlatformBreakdownOut,
    PostMetricOut,
)
from app.services import analytics as analytics_service

router = APIRouter(tags=["phase5"])


@router.post("/analytics/sync", response_model=AnalyticsSyncOut)
def sync_analytics(
    user: CurrentUser,
    db: DbDep,
    days: int = 30,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.analyst)),
) -> AnalyticsSyncOut:
    result = analytics_service.sync_analytics(
        db,
        organization_id=membership.organization_id,
        days=max(7, min(days, 90)),
    )
    return AnalyticsSyncOut(**result)


@router.get("/analytics/trends", response_model=list[AccountMetricTrendOut])
def analytics_trends(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID | None = None,
    days: int = 30,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> list[AccountMetricTrendOut]:
    series = analytics_service.trend_series(
        db,
        organization_id=membership.organization_id,
        brand_id=brand_id,
        days=max(7, min(days, 90)),
    )
    return [AccountMetricTrendOut(**row) for row in series]


@router.get("/analytics/platforms", response_model=list[PlatformBreakdownOut])
def analytics_platforms(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID | None = None,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> list[PlatformBreakdownOut]:
    rows = analytics_service.platform_breakdown(
        db,
        organization_id=membership.organization_id,
        brand_id=brand_id,
    )
    return [PlatformBreakdownOut(**row) for row in rows]


@router.get("/analytics/posts", response_model=list[PostMetricOut])
def analytics_posts(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID | None = None,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> list[PostMetricOut]:
    rows = analytics_service.list_post_metrics(
        db,
        organization_id=membership.organization_id,
        brand_id=brand_id,
    )
    return [PostMetricOut(**row) for row in rows]
