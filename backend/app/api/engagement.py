from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentUser, DbDep, require_roles
from app.models import AiReplyDraft, Brand, BrandGuidelines, OrganizationMember, Role, SocialInteraction
from app.schemas import (
    ApproveSendRequest,
    AiReplyDraftOut,
    InboxStatsOut,
    InteractionOut,
    InteractionUpdate,
    ReplyDraftRequest,
)
from app.services import engagement as engagement_service
from app.services.engagement_classify import classify_text

router = APIRouter(tags=["phase4"])


def _interaction(db, membership: OrganizationMember, interaction_id: UUID) -> SocialInteraction:
    item = engagement_service.get_interaction(db, membership.organization_id, interaction_id)
    if not item:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return item


@router.get("/inbox", response_model=list[InteractionOut])
def list_inbox(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID | None = None,
    status: str | None = None,
    interaction_type: str | None = None,
    platform: str | None = None,
    priority: str | None = None,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> list[SocialInteraction]:
    q = (
        db.query(SocialInteraction)
        .options(joinedload(SocialInteraction.drafts))
        .filter(SocialInteraction.organization_id == membership.organization_id)
    )
    if brand_id:
        q = q.filter(SocialInteraction.brand_id == brand_id)
    if status:
        q = q.filter(SocialInteraction.status == status)
    if interaction_type:
        q = q.filter(SocialInteraction.interaction_type == interaction_type)
    if platform:
        q = q.filter(SocialInteraction.platform == platform)
    if priority:
        q = q.filter(SocialInteraction.priority == priority)
    return q.order_by(SocialInteraction.received_at.desc()).limit(200).all()


@router.get("/inbox/stats", response_model=InboxStatsOut)
def inbox_stats(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID | None = None,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> InboxStatsOut:
    return InboxStatsOut(**engagement_service.inbox_stats(db, membership.organization_id, brand_id))


@router.post("/inbox/sync")
def sync_inbox(
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.approver)),
) -> dict:
    created = engagement_service.sync_simulated_inbox(db, organization_id=membership.organization_id)
    return {"ok": True, "created": created}


@router.get("/interactions/{interaction_id}", response_model=InteractionOut)
def get_interaction(
    interaction_id: UUID,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> SocialInteraction:
    return _interaction(db, membership, interaction_id)


@router.patch("/interactions/{interaction_id}", response_model=InteractionOut)
def update_interaction(
    interaction_id: UUID,
    payload: InteractionUpdate,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.approver, Role.analyst)),
) -> SocialInteraction:
    item = _interaction(db, membership, interaction_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(item, key, value)
    if payload.status == "ignored" or payload.status == "closed":
        item.responded_at = item.responded_at or datetime.now(timezone.utc)
    db.commit()
    return _interaction(db, membership, interaction_id)


@router.post("/interactions/{interaction_id}/classify", response_model=InteractionOut)
def classify_interaction(
    interaction_id: UUID,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.approver)),
) -> SocialInteraction:
    item = _interaction(db, membership, interaction_id)
    labels = classify_text(item.body)
    item.sentiment = str(labels["sentiment"])
    item.intent = str(labels["intent"])
    item.priority = str(labels["priority"])
    item.lead_probability = int(labels["lead_probability"])
    db.commit()
    return _interaction(db, membership, interaction_id)


@router.post("/interactions/{interaction_id}/reply-draft", response_model=AiReplyDraftOut)
async def create_reply_draft(
    interaction_id: UUID,
    payload: ReplyDraftRequest,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.approver)),
) -> AiReplyDraft:
    item = _interaction(db, membership, interaction_id)
    brand = db.get(Brand, item.brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    guidelines = db.query(BrandGuidelines).filter(BrandGuidelines.brand_id == brand.id).first()
    draft = await engagement_service.generate_reply_draft(
        db,
        interaction=item,
        brand=brand,
        guidelines=guidelines,
        created_by=user.id,
        tone=payload.tone,
        instruction=payload.instruction,
    )
    db.commit()
    db.refresh(draft)
    return draft


@router.post("/interactions/{interaction_id}/approve-send", response_model=AiReplyDraftOut)
def approve_send(
    interaction_id: UUID,
    payload: ApproveSendRequest,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.approver)),
) -> AiReplyDraft:
    item = _interaction(db, membership, interaction_id)
    draft = None
    if payload.draft_id:
        draft = db.get(AiReplyDraft, payload.draft_id)
        if not draft or draft.interaction_id != item.id:
            raise HTTPException(status_code=404, detail="Reply draft not found")
    try:
        sent = engagement_service.approve_and_send(db, interaction=item, draft=draft, body=payload.body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(sent)
    return sent


@router.post("/ai/reply", response_model=AiReplyDraftOut)
async def ai_reply(
    payload: dict,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.approver)),
) -> AiReplyDraft:
    interaction_id = payload.get("interaction_id")
    if not interaction_id:
        raise HTTPException(status_code=400, detail="interaction_id is required")
    req = ReplyDraftRequest(tone=payload.get("tone") or "helpful", instruction=payload.get("instruction"))
    return await create_reply_draft(UUID(str(interaction_id)), req, user, db, membership)
