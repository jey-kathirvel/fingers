from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
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

    brand = db.get(Brand, payload.brand_id)
    if not brand or brand.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Brand not found")

    mode = payload.connection_mode if payload.connection_mode in {"simulation", "live"} else "simulation"
    account = SocialAccount(
        organization_id=membership.organization_id,
        brand_id=payload.brand_id,
        platform=payload.platform,
        account_name=payload.account_name,
        external_account_id=payload.external_account_id or f"{payload.platform}-{payload.account_name}",
        status="connected",
        connection_mode=mode,
        access_token=payload.access_token,
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
