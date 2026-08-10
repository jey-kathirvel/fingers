from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Brand, User
from app.schemas import DashboardOverviewOut

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=DashboardOverviewOut)
def overview(
    organization_id: str | None = None,
    brand_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardOverviewOut:
    # Phase 1: live endpoint with seed/zero values and brand-aware placeholders.
    brand_count = db.query(Brand).count()
    brand_name = None
    if brand_id:
        brand = db.get(Brand, brand_id)
        brand_name = brand.name if brand else None

    return DashboardOverviewOut(
        followers=1240 if brand_count else 0,
        reach=8420 if brand_count else 0,
        impressions=15320 if brand_count else 0,
        engagement_rate=3.4 if brand_count else 0.0,
        clicks=286 if brand_count else 0,
        leads=12 if brand_count else 0,
        published_posts=18 if brand_count else 0,
        response_backlog=5 if brand_count else 0,
        failed_posts=1 if brand_count else 0,
        scheduled_posts=4 if brand_count else 0,
        approval_items=2 if brand_count else 0,
        integration_health=[
            {"platform": "Instagram", "status": "not_connected"},
            {"platform": "Facebook", "status": "not_connected"},
            {"platform": "LinkedIn", "status": "not_connected"},
        ],
        ai_recommendations=[
            f"Connect Meta and LinkedIn for {brand_name or 'your active brand'} to unlock publishing.",
            "Create your first multi-platform draft in AI Studio (Phase 2).",
            "Review brand voice guidelines before scheduling campaigns.",
        ],
    )
