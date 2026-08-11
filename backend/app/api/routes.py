from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DbDep, get_membership, require_roles
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Brand, BrandGuidelines, ContentItem, ContentStatus, Lead, Organization, OrganizationMember, Role, ScheduledPost, SocialAccount, SocialInteraction, User
from app.schemas import (
    BrandCreate,
    BrandOut,
    BrandUpdate,
    DashboardOverview,
    HealthResponse,
    LoginRequest,
    MembershipOut,
    OrganizationCreate,
    OrganizationOut,
    TokenResponse,
    UserOut,
)

router = APIRouter()
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
def health(db: DbDep) -> HealthResponse:
    db_status = "ok"
    redis_status = "not_configured"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
    try:
        import redis

        client = redis.from_url(settings.redis_url, socket_connect_timeout=0.5)
        client.ping()
        redis_status = "ok"
    except Exception:
        redis_status = "unavailable"

    overall = "ok" if db_status == "ok" else "degraded"
    ai_provider = settings.llm_provider
    return HealthResponse(
        status=overall,
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        database=db_status,
        redis=redis_status,
        ai_provider=ai_provider,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/version")
def version() -> dict:
    return {"app": settings.app_name, "version": settings.app_version, "environment": settings.environment}


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbDep) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")
    token = create_access_token(str(user.id), {"email": user.email})
    return TokenResponse(access_token=token)


@router.get("/auth/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user


@router.post("/auth/logout")
def logout(user: CurrentUser) -> dict:
    return {"ok": True, "user_id": str(user.id)}


@router.get("/users/me/memberships", response_model=list[MembershipOut])
def my_memberships(user: CurrentUser, db: DbDep) -> list[OrganizationMember]:
    from sqlalchemy.orm import joinedload

    return (
        db.query(OrganizationMember)
        .options(joinedload(OrganizationMember.organization))
        .filter(OrganizationMember.user_id == user.id)
        .all()
    )


@router.post("/organizations", response_model=OrganizationOut)
def create_organization(payload: OrganizationCreate, user: CurrentUser, db: DbDep) -> Organization:
    existing = db.query(Organization).filter(Organization.slug == payload.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail="Organization slug already exists")
    org = Organization(name=payload.name, slug=payload.slug)
    db.add(org)
    db.flush()
    db.add(
        OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            role=Role.admin,
        )
    )
    db.commit()
    db.refresh(org)
    return org


@router.get("/organizations", response_model=list[OrganizationOut])
def list_organizations(user: CurrentUser, db: DbDep) -> list[Organization]:
    return (
        db.query(Organization)
        .join(OrganizationMember)
        .filter(OrganizationMember.user_id == user.id)
        .all()
    )


@router.get("/organizations/{organization_id}", response_model=OrganizationOut)
def get_organization(organization_id: UUID, user: CurrentUser, db: DbDep) -> Organization:
    get_membership(db, user, organization_id)
    org = db.get(Organization, organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.get("/brands", response_model=list[BrandOut])
def list_brands(
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> list[Brand]:
    return (
        db.query(Brand)
        .filter(Brand.organization_id == membership.organization_id)
        .order_by(Brand.created_at.asc())
        .all()
    )


@router.post("/brands", response_model=BrandOut)
def create_brand(
    payload: BrandCreate,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator)),
) -> Brand:
    exists = (
        db.query(Brand)
        .filter(Brand.organization_id == membership.organization_id, Brand.slug == payload.slug)
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="Brand slug already exists in organization")
    brand = Brand(organization_id=membership.organization_id, **payload.model_dump())
    db.add(brand)
    db.flush()
    db.add(BrandGuidelines(brand_id=brand.id))
    db.commit()
    db.refresh(brand)
    return brand


@router.get("/brands/{brand_id}", response_model=BrandOut)
def get_brand(
    brand_id: UUID,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> Brand:
    brand = db.get(Brand, brand_id)
    if not brand or brand.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand


@router.patch("/brands/{brand_id}", response_model=BrandOut)
def update_brand(
    brand_id: UUID,
    payload: BrandUpdate,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator)),
) -> Brand:
    brand = db.get(Brand, brand_id)
    if not brand or brand.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Brand not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(brand, key, value)
    db.commit()
    db.refresh(brand)
    return brand


@router.get("/analytics/overview", response_model=DashboardOverview)
def analytics_overview(
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> DashboardOverview:
    brands_count = db.query(Brand).filter(Brand.organization_id == membership.organization_id).count()
    draft_count = (
        db.query(ContentItem)
        .filter(
            ContentItem.organization_id == membership.organization_id,
            ContentItem.status == ContentStatus.draft.value,
        )
        .count()
    )
    review_count = (
        db.query(ContentItem)
        .filter(
            ContentItem.organization_id == membership.organization_id,
            ContentItem.status == ContentStatus.review.value,
        )
        .count()
    )
    connected_accounts = (
        db.query(SocialAccount)
        .filter(
            SocialAccount.organization_id == membership.organization_id,
            SocialAccount.status == "connected",
        )
        .count()
    )
    scheduled_posts = (
        db.query(ScheduledPost)
        .filter(
            ScheduledPost.organization_id == membership.organization_id,
            ScheduledPost.status == "scheduled",
        )
        .count()
    )
    failed_posts = (
        db.query(ScheduledPost)
        .filter(
            ScheduledPost.organization_id == membership.organization_id,
            ScheduledPost.status == "failed",
        )
        .count()
    )
    published_posts = (
        db.query(ScheduledPost)
        .filter(
            ScheduledPost.organization_id == membership.organization_id,
            ScheduledPost.status == "published",
        )
        .count()
    )
    response_backlog = (
        db.query(SocialInteraction)
        .filter(
            SocialInteraction.organization_id == membership.organization_id,
            SocialInteraction.status.in_(["new", "assigned", "draft_reply"]),
        )
        .count()
    )
    accounts = (
        db.query(SocialAccount)
        .filter(
            SocialAccount.organization_id == membership.organization_id,
            SocialAccount.status == "connected",
        )
        .all()
    )
    health_map = {p: "not_connected" for p in ["instagram", "facebook", "linkedin"]}
    for account in accounts:
        health_map[account.platform] = f"{account.connection_mode}:{account.status}"

    from app.services import analytics as analytics_service

    kpi = analytics_service.summarize_overview(db, membership.organization_id)
    leads_count = db.query(Lead).filter(Lead.organization_id == membership.organization_id).count()

    return DashboardOverview(
        followers=kpi["followers"],
        reach=kpi["reach"],
        impressions=kpi["impressions"],
        engagement_rate=kpi["engagement_rate"],
        clicks=kpi["clicks"],
        leads=max(kpi["leads"], leads_count),
        published_posts=published_posts,
        response_backlog=response_backlog,
        brands_count=brands_count,
        connected_accounts=connected_accounts,
        failed_posts=failed_posts,
        scheduled_posts=scheduled_posts,
        approval_items=review_count,
        draft_count=draft_count,
        integration_health=[{"platform": k, "status": v} for k, v in health_map.items()],
        action_queue=[
            {
                "id": "failed",
                "type": "publishing",
                "title": f"{failed_posts} failed publish job(s)",
                "priority": "high" if failed_posts else "low",
            },
            {
                "id": "inbox",
                "type": "engagement",
                "title": f"{response_backlog} inbox item(s) awaiting reply",
                "priority": "high" if response_backlog else "low",
            },
            {
                "id": "scheduled",
                "type": "publishing",
                "title": f"{scheduled_posts} post(s) scheduled",
                "priority": "medium" if scheduled_posts else "low",
            },
            {
                "id": "drafts",
                "type": "content",
                "title": f"{draft_count} draft(s) in AI Studio",
                "priority": "medium" if draft_count else "low",
            },
        ],
        recommendations=[
            {
                "id": "rec-analytics",
                "title": "Review Analytics trends",
                "detail": "Sync metrics and compare platform/post performance under Analytics.",
            }
        ],
    )


@router.get("/integration-health")
def integration_health(
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> dict:
    accounts = (
        db.query(SocialAccount)
        .filter(
            SocialAccount.organization_id == membership.organization_id,
            SocialAccount.status == "connected",
        )
        .all()
    )
    by_platform = {p: "not_connected" for p in ["instagram", "facebook", "linkedin", "youtube", "x"]}
    for account in accounts:
        by_platform[account.platform] = f"{account.connection_mode}:{account.status}"
    for planned in ("youtube", "x"):
        if by_platform[planned] == "not_connected":
            by_platform[planned] = "planned"
    from app.core.config import get_settings

    settings = get_settings()
    return {
        "organization_id": str(membership.organization_id),
        "platforms": [{"platform": k, "status": v} for k, v in by_platform.items()],
        "connected_accounts": len(accounts),
        "ai_provider": settings.llm_provider,
        "meta_configured": settings.meta_configured,
        "linkedin_configured": settings.linkedin_configured,
        "phase": "6",
    }


@router.get("/audit")
def audit_placeholder(
    user: CurrentUser,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.analyst)),
) -> dict:
    return {"items": [], "organization_id": str(membership.organization_id)}
