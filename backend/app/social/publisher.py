"""Publishing orchestration with retries and audit logs."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models import ContentItem, ContentStatus, ContentVersion, PublishingLog, ScheduledPost, SocialAccount
from app.social.adapters import get_adapter


def make_idempotency_key(*parts: str) -> str:
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:48]


def add_log(
    db: Session,
    *,
    organization_id: UUID,
    scheduled_post_id: UUID | None,
    content_item_id: UUID | None,
    platform: str,
    action: str,
    status: str,
    message: str | None = None,
    external_post_id: str | None = None,
) -> None:
    db.add(
        PublishingLog(
            organization_id=organization_id,
            scheduled_post_id=scheduled_post_id,
            content_item_id=content_item_id,
            platform=platform,
            action=action,
            status=status,
            message=message,
            external_post_id=external_post_id,
        )
    )


def schedule_version(
    db: Session,
    *,
    organization_id: UUID,
    brand_id: UUID,
    content_item: ContentItem,
    version: ContentVersion,
    account: SocialAccount,
    scheduled_for: datetime,
    created_by: UUID | None,
) -> ScheduledPost:
    key = make_idempotency_key(
        str(content_item.id),
        str(version.id),
        str(account.id),
        scheduled_for.astimezone(timezone.utc).isoformat(),
    )
    existing = db.query(ScheduledPost).filter(ScheduledPost.idempotency_key == key).first()
    if existing:
        return existing

    post = ScheduledPost(
        organization_id=organization_id,
        brand_id=brand_id,
        content_item_id=content_item.id,
        content_version_id=version.id,
        social_account_id=account.id,
        platform=version.platform,
        status="scheduled",
        scheduled_for=scheduled_for,
        idempotency_key=key,
        created_by=created_by,
    )
    db.add(post)
    content_item.status = ContentStatus.scheduled.value
    add_log(
        db,
        organization_id=organization_id,
        scheduled_post_id=None,
        content_item_id=content_item.id,
        platform=version.platform,
        action="schedule",
        status="ok",
        message=f"Scheduled for {scheduled_for.isoformat()}",
    )
    db.flush()
    add_log(
        db,
        organization_id=organization_id,
        scheduled_post_id=post.id,
        content_item_id=content_item.id,
        platform=version.platform,
        action="schedule_created",
        status="ok",
        message=f"scheduled_post={post.id}",
    )
    return post


def process_scheduled_post(db: Session, post: ScheduledPost) -> ScheduledPost:
    if post.status in {"published", "publishing"}:
        return post

    account = db.get(SocialAccount, post.social_account_id)
    version = db.get(ContentVersion, post.content_version_id)
    item = db.get(ContentItem, post.content_item_id)
    if not account or not version or not item:
        post.status = "failed"
        post.last_error = "Missing account/version/content"
        add_log(
            db,
            organization_id=post.organization_id,
            scheduled_post_id=post.id,
            content_item_id=post.content_item_id,
            platform=post.platform,
            action="publish",
            status="failed",
            message=post.last_error,
        )
        return post

    post.status = "publishing"
    post.attempt_count += 1
    db.flush()

    adapter = get_adapter(post.platform)
    result = adapter.publish(account, version)

    if result.ok:
        post.status = "published"
        post.published_at = datetime.now(timezone.utc)
        post.external_post_id = result.external_post_id
        post.last_error = None
        item.status = ContentStatus.published.value
        add_log(
            db,
            organization_id=post.organization_id,
            scheduled_post_id=post.id,
            content_item_id=item.id,
            platform=post.platform,
            action="publish",
            status="published",
            message=result.message,
            external_post_id=result.external_post_id,
        )
    else:
        if post.attempt_count >= post.max_attempts:
            post.status = "failed"
            item.status = ContentStatus.failed.value
        else:
            post.status = "scheduled"
        post.last_error = result.message
        add_log(
            db,
            organization_id=post.organization_id,
            scheduled_post_id=post.id,
            content_item_id=item.id,
            platform=post.platform,
            action="publish",
            status="failed" if post.status == "failed" else "retry",
            message=result.message,
        )
    return post


def publish_due_posts(db: Session, limit: int = 20) -> int:
    now = datetime.now(timezone.utc)
    due = (
        db.query(ScheduledPost)
        .filter(ScheduledPost.status == "scheduled", ScheduledPost.scheduled_for <= now)
        .order_by(ScheduledPost.scheduled_for.asc())
        .limit(limit)
        .all()
    )
    for post in due:
        process_scheduled_post(db, post)
    if due:
        db.commit()
    return len(due)
