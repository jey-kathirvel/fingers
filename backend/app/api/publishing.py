from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentUser, DbDep, require_roles
from app.models import (
    ContentItem,
    ContentVersion,
    OrganizationMember,
    PublishingLog,
    Role,
    ScheduledPost,
    SocialAccount,
)
from app.schemas import (
    CalendarItemOut,
    PublishNowRequest,
    PublishingLogOut,
    SchedulePostRequest,
    ScheduledPostOut,
    SocialAccountCreate,
    SocialAccountOut,
)
from app.social import publisher

router = APIRouter(tags=["phase3"])


def _account(db, membership: OrganizationMember, account_id: UUID) -> SocialAccount:
    account = db.get(SocialAccount, account_id)
    if not account or account.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Social account not found")
    return account


def _content_item(db, membership: OrganizationMember, content_item_id: UUID) -> ContentItem:
    item = (
        db.query(ContentItem)
        .options(joinedload(ContentItem.versions))
        .filter(ContentItem.id == content_item_id, ContentItem.organization_id == membership.organization_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    return item


def _resolve_version(item: ContentItem, account: SocialAccount, version_id: UUID | None) -> ContentVersion:
    if version_id:
        version = next((v for v in item.versions if v.id == version_id), None)
        if not version:
            raise HTTPException(status_code=404, detail="Content version not found")
    else:
        version = next((v for v in item.versions if v.platform == account.platform), None)
        if not version:
            raise HTTPException(status_code=400, detail="No content version matches account platform")
    if account.platform != version.platform:
        raise HTTPException(status_code=400, detail="Account platform mismatch")
    return version


@router.get("/social-accounts", response_model=list[SocialAccountOut])
def list_social_accounts(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID | None = None,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> list[SocialAccount]:
    q = db.query(SocialAccount).filter(SocialAccount.organization_id == membership.organization_id)
    if brand_id:
        q = q.filter(SocialAccount.brand_id == brand_id)
    return q.order_by(SocialAccount.created_at.desc()).all()


@router.post("/social-accounts", response_model=SocialAccountOut)
def connect_social_account(
    payload: SocialAccountCreate,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator)),
) -> SocialAccount:
    from app.models import Brand
    from app.social.linkedin import fetch_profile, normalize_author_urn

    brand = db.get(Brand, payload.brand_id)
    if not brand or brand.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Brand not found")

    mode = payload.connection_mode if payload.connection_mode in {"simulation", "live"} else "simulation"
    if mode == "live" and payload.platform in {"instagram", "facebook"}:
        raise HTTPException(
            status_code=400,
            detail="Live Meta publishing is deferred. Use simulation for Instagram/Facebook, or connect LinkedIn live.",
        )
    if mode == "live" and payload.platform == "linkedin" and not payload.access_token:
        raise HTTPException(status_code=400, detail="LinkedIn live connect requires an access token")

    account_name = payload.account_name
    external_id = payload.external_account_id
    token_expires_at = None

    if mode == "live" and payload.platform == "linkedin" and payload.access_token:
        try:
            profile = fetch_profile(payload.access_token)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        external_id = normalize_author_urn(external_id) or profile.person_urn
        if not account_name or account_name.strip().lower() in {"linkedin", "live linkedin"}:
            account_name = profile.name or account_name
    else:
        external_id = external_id or f"{payload.platform}-{payload.account_name}"

    account = SocialAccount(
        organization_id=membership.organization_id,
        brand_id=payload.brand_id,
        platform=payload.platform,
        account_name=account_name,
        external_account_id=external_id,
        status="connected",
        connection_mode=mode,
        access_token=payload.access_token,
        token_expires_at=token_expires_at,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/social-accounts/{account_id}")
def disconnect_social_account(
    account_id: UUID,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin)),
) -> dict:
    account = _account(db, membership, account_id)
    account.status = "disconnected"
    db.commit()
    return {"ok": True, "id": str(account_id)}


@router.post("/scheduled-posts", response_model=ScheduledPostOut)
def schedule_post(
    payload: SchedulePostRequest,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.approver)),
) -> ScheduledPost:
    item = _content_item(db, membership, payload.content_item_id)
    account = _account(db, membership, payload.social_account_id)
    if account.brand_id != item.brand_id:
        raise HTTPException(status_code=400, detail="Account brand mismatch")
    if account.status != "connected":
        raise HTTPException(status_code=400, detail="Social account is not connected")
    version = _resolve_version(item, account, payload.content_version_id)
    if item.status not in {"approved", "scheduled", "draft", "review"}:
        raise HTTPException(status_code=400, detail=f"Cannot schedule content in status={item.status}")

    scheduled_for = payload.scheduled_for
    if scheduled_for.tzinfo is None:
        scheduled_for = scheduled_for.replace(tzinfo=timezone.utc)

    post = publisher.schedule_version(
        db,
        organization_id=membership.organization_id,
        brand_id=item.brand_id,
        content_item=item,
        version=version,
        account=account,
        scheduled_for=scheduled_for,
        created_by=user.id,
    )
    db.commit()
    db.refresh(post)
    return post


@router.get("/scheduled-posts", response_model=list[ScheduledPostOut])
def list_scheduled_posts(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID | None = None,
    status: str | None = None,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> list[ScheduledPost]:
    q = db.query(ScheduledPost).filter(ScheduledPost.organization_id == membership.organization_id)
    if brand_id:
        q = q.filter(ScheduledPost.brand_id == brand_id)
    if status:
        q = q.filter(ScheduledPost.status == status)
    return q.order_by(ScheduledPost.scheduled_for.asc()).all()


@router.delete("/scheduled-posts/{post_id}")
def cancel_scheduled_post(
    post_id: UUID,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.approver)),
) -> dict:
    post = db.get(ScheduledPost, post_id)
    if not post or post.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Scheduled post not found")
    if post.status not in {"scheduled", "failed"}:
        raise HTTPException(status_code=400, detail="Only scheduled/failed posts can be cancelled")
    post.status = "cancelled"
    publisher.add_log(
        db,
        organization_id=membership.organization_id,
        scheduled_post_id=post.id,
        content_item_id=post.content_item_id,
        platform=post.platform,
        action="cancel",
        status="ok",
        message="Cancelled by user",
    )
    db.commit()
    return {"ok": True, "id": str(post_id)}


@router.post("/publishing/publish-now", response_model=ScheduledPostOut)
def publish_now_from_content(
    payload: PublishNowRequest,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.approver)),
) -> ScheduledPost:
    item = _content_item(db, membership, payload.content_item_id)
    account = _account(db, membership, payload.social_account_id)
    if account.brand_id != item.brand_id:
        raise HTTPException(status_code=400, detail="Account brand mismatch")
    if account.status != "connected":
        raise HTTPException(status_code=400, detail="Social account is not connected")
    version = _resolve_version(item, account, payload.content_version_id)
    if item.status not in {"approved", "scheduled", "draft", "review", "published"}:
        raise HTTPException(status_code=400, detail=f"Cannot publish content in status={item.status}")

    now = datetime.now(timezone.utc)
    post = publisher.schedule_version(
        db,
        organization_id=membership.organization_id,
        brand_id=item.brand_id,
        content_item=item,
        version=version,
        account=account,
        scheduled_for=now,
        created_by=user.id,
    )
    publisher.process_scheduled_post(db, post)
    db.commit()
    db.refresh(post)
    return post


@router.post("/scheduled-posts/{post_id}/publish-now", response_model=ScheduledPostOut)
def publish_now(
    post_id: UUID,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.approver)),
) -> ScheduledPost:
    post = db.get(ScheduledPost, post_id)
    if not post or post.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Scheduled post not found")
    post.scheduled_for = datetime.now(timezone.utc)
    if post.status in {"failed", "cancelled"}:
        post.status = "scheduled"
    publisher.process_scheduled_post(db, post)
    db.commit()
    db.refresh(post)
    return post


@router.post("/scheduled-posts/{post_id}/retry", response_model=ScheduledPostOut)
def retry_post(
    post_id: UUID,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.approver)),
) -> ScheduledPost:
    post = db.get(ScheduledPost, post_id)
    if not post or post.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Scheduled post not found")
    if post.status not in {"failed", "scheduled", "cancelled"}:
        raise HTTPException(status_code=400, detail="Only failed/scheduled/cancelled posts can be retried")
    post.status = "scheduled"
    post.scheduled_for = datetime.now(timezone.utc)
    publisher.process_scheduled_post(db, post)
    db.commit()
    db.refresh(post)
    return post


@router.get("/calendar", response_model=list[CalendarItemOut])
def calendar(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID | None = None,
    days: int = 30,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> list[CalendarItemOut]:
    start = datetime.now(timezone.utc) - timedelta(days=7)
    end = datetime.now(timezone.utc) + timedelta(days=max(1, min(days, 90)))
    q = (
        db.query(ScheduledPost, ContentItem, SocialAccount)
        .join(ContentItem, ContentItem.id == ScheduledPost.content_item_id)
        .join(SocialAccount, SocialAccount.id == ScheduledPost.social_account_id)
        .filter(
            ScheduledPost.organization_id == membership.organization_id,
            ScheduledPost.scheduled_for >= start,
            ScheduledPost.scheduled_for <= end,
        )
    )
    if brand_id:
        q = q.filter(ScheduledPost.brand_id == brand_id)
    rows = q.order_by(ScheduledPost.scheduled_for.asc()).all()
    return [
        CalendarItemOut(
            id=post.id,
            title=item.title,
            platform=post.platform,
            status=post.status,
            scheduled_for=post.scheduled_for,
            content_item_id=post.content_item_id,
            brand_id=post.brand_id,
            account_name=account.account_name,
        )
        for post, item, account in rows
    ]


@router.get("/publishing-logs", response_model=list[PublishingLogOut])
def publishing_logs(
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> list[PublishingLog]:
    return (
        db.query(PublishingLog)
        .filter(PublishingLog.organization_id == membership.organization_id)
        .order_by(PublishingLog.created_at.desc())
        .limit(100)
        .all()
    )


@router.get("/integrations/linkedin/oauth-url")
def linkedin_oauth_url(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator)),
) -> dict:
    from app.core.config import get_settings
    from app.models import Brand
    from app.social.linkedin import build_authorize_url

    brand = db.get(Brand, brand_id)
    if not brand or brand.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Brand not found")
    settings = get_settings()
    if not settings.linkedin_configured:
        raise HTTPException(status_code=400, detail="LinkedIn app credentials are not configured")
    try:
        return build_authorize_url(
            organization_id=str(membership.organization_id),
            brand_id=str(brand_id),
            user_id=str(user.id),
            settings=settings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/integrations/linkedin/callback")
def linkedin_oauth_callback(
    db: DbDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = Query(default=None),
) -> RedirectResponse:
    from app.core.config import get_settings
    from app.models import Brand
    from app.social.linkedin import exchange_code_for_token, fetch_profile, parse_oauth_state

    frontend = "https://fingers.ads-ai.in/integrations"
    if error:
        detail = error_description or error
        return RedirectResponse(f"{frontend}?linkedin=error&detail={detail}", status_code=302)
    if not code or not state:
        return RedirectResponse(f"{frontend}?linkedin=error&detail=missing_code", status_code=302)

    settings = get_settings()
    try:
        parsed = parse_oauth_state(state, settings=settings)
        tokens = exchange_code_for_token(code, settings=settings)
        profile = fetch_profile(tokens.access_token)
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(f"{frontend}?linkedin=error&detail={str(exc)[:180]}", status_code=302)

    brand = db.get(Brand, UUID(parsed["brand_id"]))
    if not brand or str(brand.organization_id) != parsed["organization_id"]:
        return RedirectResponse(f"{frontend}?linkedin=error&detail=brand_mismatch", status_code=302)

    expires_at = None
    if tokens.expires_in:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(tokens.expires_in))

    account = SocialAccount(
        organization_id=brand.organization_id,
        brand_id=brand.id,
        platform="linkedin",
        account_name=profile.name or "LinkedIn",
        external_account_id=profile.person_urn,
        status="connected",
        connection_mode="live",
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_expires_at=expires_at,
        metadata_json=None,
    )
    db.add(account)
    db.commit()
    return RedirectResponse(f"{frontend}?linkedin=connected", status_code=302)
