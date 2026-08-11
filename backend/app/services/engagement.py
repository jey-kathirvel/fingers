"""Engagement inbox sync and reply helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, joinedload

from app.models import (
    AiReplyDraft,
    Brand,
    BrandGuidelines,
    ScheduledPost,
    SocialAccount,
    SocialInteraction,
)
from app.services.engagement_classify import classify_text


SAMPLE_THREADS = [
    ("comment", "Priya N.", "@priya_n", "What's the pricing for the irrigation-management plan?"),
    ("comment", "Omar K.", "@omar_k", "Great tip — this was really helpful, thanks!"),
    ("message", "Anita S.", "@anita", "Can you help? Our dashboard sync is not working today."),
    ("mention", "Dev Farm Co", "@devfarm", "Anyone tried @brand for irrigation monitoring? Looking for feedback."),
    ("review", "Local Grower", "@grower", "Support was slow and the setup felt broken at first."),
    ("comment", "Lee M.", "@lee_m", "Do you offer a demo this week?"),
    ("message", "Spam Bot", "@crypto_bot", "Click here to make money with crypto NFT tips"),
    ("comment", "Sara T.", "@sara_t", "Love the practical tone of these posts."),
]


def upsert_interaction(
    db: Session,
    *,
    organization_id: UUID,
    brand_id: UUID,
    account: SocialAccount | None,
    platform: str,
    interaction_type: str,
    external_id: str,
    author_name: str | None,
    author_handle: str | None,
    body: str,
    received_at: datetime,
    content_item_id: UUID | None = None,
    scheduled_post_id: UUID | None = None,
    parent_external_id: str | None = None,
) -> tuple[SocialInteraction, bool]:
    existing = (
        db.query(SocialInteraction)
        .filter(
            SocialInteraction.organization_id == organization_id,
            SocialInteraction.platform == platform,
            SocialInteraction.external_id == external_id,
        )
        .first()
    )
    if existing:
        return existing, False

    labels = classify_text(body)
    item = SocialInteraction(
        organization_id=organization_id,
        brand_id=brand_id,
        social_account_id=account.id if account else None,
        platform=platform,
        interaction_type=interaction_type,
        external_id=external_id,
        author_name=author_name,
        author_handle=author_handle,
        body=body,
        permalink=None,
        sentiment=str(labels["sentiment"]),
        intent=str(labels["intent"]),
        priority=str(labels["priority"]),
        lead_probability=int(labels["lead_probability"]),
        status="new",
        content_item_id=content_item_id,
        scheduled_post_id=scheduled_post_id,
        parent_external_id=parent_external_id,
        received_at=received_at,
    )
    db.add(item)
    db.flush()
    return item, True


def sync_simulated_inbox(db: Session, *, organization_id: UUID | None = None, limit_per_account: int = 4) -> int:
    """Create deterministic simulation interactions for connected accounts."""
    q = db.query(SocialAccount).filter(SocialAccount.status == "connected")
    if organization_id:
        q = q.filter(SocialAccount.organization_id == organization_id)
    accounts = q.all()
    created = 0
    now = datetime.now(timezone.utc)

    for account in accounts:
        published = (
            db.query(ScheduledPost)
            .filter(
                ScheduledPost.social_account_id == account.id,
                ScheduledPost.status == "published",
            )
            .order_by(ScheduledPost.published_at.desc().nullslast())
            .limit(3)
            .all()
        )
        for idx, sample in enumerate(SAMPLE_THREADS[:limit_per_account]):
            itype, author, handle, body = sample
            body_text = body.replace("@brand", f"@{account.account_name}")
            parent = published[idx % len(published)].external_post_id if published else None
            content_id = published[idx % len(published)].content_item_id if published else None
            scheduled_id = published[idx % len(published)].id if published else None
            external_id = f"sim-{account.id.hex[:8]}-{itype}-{idx}"
            _, was_new = upsert_interaction(
                db,
                organization_id=account.organization_id,
                brand_id=account.brand_id,
                account=account,
                platform=account.platform,
                interaction_type=itype,
                external_id=external_id,
                author_name=author,
                author_handle=handle,
                body=body_text,
                received_at=now - timedelta(hours=idx + 1),
                content_item_id=content_id,
                scheduled_post_id=scheduled_id,
                parent_external_id=parent,
            )
            if was_new:
                created += 1
    if created:
        db.commit()
    return created


def local_reply_draft(brand: Brand, interaction: SocialInteraction, tone: str = "helpful") -> str:
    name = interaction.author_name or "there"
    if interaction.intent == "sales_enquiry":
        return (
            f"Hi {name}, thanks for asking about pricing. "
            f"{brand.name} can share a tailored plan based on your irrigation setup — "
            f"happy to send options or book a quick demo."
        )
    if interaction.intent == "support":
        return (
            f"Hi {name}, sorry you're hitting an issue. "
            f"Please share the account email and a short description of what you see — "
            f"we'll help get {brand.name} syncing again."
        )
    if interaction.intent == "complaint" or interaction.sentiment == "negative":
        return (
            f"Hi {name}, thanks for flagging this — we take it seriously. "
            f"A {brand.name} teammate will follow up shortly to make this right."
        )
    if interaction.intent == "praise":
        return f"Thanks {name}! Glad it helped — more practical {brand.name} tips coming soon."
    if interaction.intent == "spam":
        return "Thanks for reaching out. We're unable to help with this request."
    return (
        f"Hi {name}, thanks for writing in. "
        f"A {tone} note from {brand.name}: we’d love to help — could you share a bit more detail?"
    )


async def generate_reply_draft(
    db: Session,
    *,
    interaction: SocialInteraction,
    brand: Brand,
    guidelines: BrandGuidelines | None,
    created_by: UUID | None,
    tone: str = "helpful",
    instruction: str | None = None,
) -> AiReplyDraft:
    from app.services import ai_studio

    provider = "local"
    body = local_reply_draft(brand, interaction, tone=tone)
    try:
        result = await ai_studio.llm_chat(
            [
                {
                    "role": "system",
                    "content": (
                        "You write short social media replies for Fingers. "
                        "Return JSON {body}. Keep under 500 characters. Be on-brand."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Brand: {brand.name}. Tone of voice: {brand.tone_of_voice or 'practical'}. "
                        f"Desired tone: {tone}. Instruction: {instruction or 'Approve-ready reply'}. "
                        f"Platform: {interaction.platform}. Type: {interaction.interaction_type}. "
                        f"Intent: {interaction.intent}. Sentiment: {interaction.sentiment}. "
                        f"Incoming message: {interaction.body}"
                    ),
                },
            ]
        )
        raw, provider = result
        data = ai_studio._extract_json(raw)
        if isinstance(data, dict) and data.get("body"):
            body = str(data["body"]).strip()
    except Exception:
        provider = "local_fallback"

    draft = AiReplyDraft(
        organization_id=interaction.organization_id,
        interaction_id=interaction.id,
        body=body,
        tone=tone,
        provider=provider,
        status="suggested",
        created_by=created_by,
    )
    db.add(draft)
    interaction.status = "draft_reply"
    db.flush()
    return draft


def approve_and_send(
    db: Session,
    *,
    interaction: SocialInteraction,
    draft: AiReplyDraft | None,
    body: str | None,
) -> AiReplyDraft:
    reply_body = (body or (draft.body if draft else "")).strip()
    if not reply_body:
        raise ValueError("Reply body is required")

    if draft is None:
        draft = AiReplyDraft(
            organization_id=interaction.organization_id,
            interaction_id=interaction.id,
            body=reply_body,
            tone="manual",
            provider="manual",
            status="suggested",
        )
        db.add(draft)
        db.flush()
    else:
        draft.body = reply_body

    # Phase 4 MVP: simulation send for all platforms (live reply APIs vary by network).
    draft.status = "sent"
    draft.external_reply_id = f"sim_reply_{uuid4().hex[:12]}"
    draft.sent_at = datetime.now(timezone.utc)
    interaction.status = "responded"
    interaction.responded_at = draft.sent_at
    db.flush()
    return draft


def inbox_stats(db: Session, organization_id: UUID, brand_id: UUID | None = None) -> dict[str, int]:
    q = db.query(SocialInteraction).filter(SocialInteraction.organization_id == organization_id)
    if brand_id:
        q = q.filter(SocialInteraction.brand_id == brand_id)
    items = q.all()
    return {
        "total": len(items),
        "new_count": sum(1 for i in items if i.status == "new"),
        "draft_reply_count": sum(1 for i in items if i.status == "draft_reply"),
        "responded_count": sum(1 for i in items if i.status == "responded"),
        "high_priority": sum(1 for i in items if i.priority in {"high", "critical"}),
        "backlog": sum(1 for i in items if i.status in {"new", "assigned", "draft_reply"}),
    }


def get_interaction(db: Session, organization_id: UUID, interaction_id: UUID) -> SocialInteraction | None:
    return (
        db.query(SocialInteraction)
        .options(joinedload(SocialInteraction.drafts))
        .filter(
            SocialInteraction.id == interaction_id,
            SocialInteraction.organization_id == organization_id,
        )
        .first()
    )
