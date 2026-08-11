from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentUser, DbDep, require_roles
from app.models import Brand, ListeningTerm, OrganizationMember, Role, SocialMention
from app.schemas import (
    ListeningSummaryOut,
    ListeningTermCreate,
    ListeningTermOut,
    ListeningTermUpdate,
    SocialMentionOut,
)
from app.services import listening as listening_service

router = APIRouter(tags=["phase8"])

TERM_TYPES = {"brand", "product", "competitor", "hashtag", "custom"}


@router.get("/listening/terms", response_model=list[ListeningTermOut])
def list_terms(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID | None = None,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> list[ListeningTerm]:
    q = db.query(ListeningTerm).filter(ListeningTerm.organization_id == membership.organization_id)
    if brand_id:
        q = q.filter(ListeningTerm.brand_id == brand_id)
    return q.order_by(ListeningTerm.created_at.asc()).all()


@router.post("/listening/terms", response_model=ListeningTermOut)
def create_term(
    payload: ListeningTermCreate,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.analyst)),
) -> ListeningTerm:
    brand = db.get(Brand, payload.brand_id)
    if not brand or brand.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Brand not found")
    term_type = payload.term_type if payload.term_type in TERM_TYPES else "custom"
    term = ListeningTerm(
        organization_id=membership.organization_id,
        brand_id=payload.brand_id,
        term=payload.term.strip(),
        term_type=term_type,
        enabled=payload.enabled,
    )
    db.add(term)
    try:
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=400, detail="Term already exists for this brand") from exc
    db.refresh(term)
    return term


@router.post("/listening/terms/seed-defaults", response_model=list[ListeningTermOut])
def seed_terms(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.analyst)),
) -> list[ListeningTerm]:
    brand = db.get(Brand, brand_id)
    if not brand or brand.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Brand not found")
    return listening_service.seed_default_terms(
        db, organization_id=membership.organization_id, brand_id=brand_id
    )


@router.patch("/listening/terms/{term_id}", response_model=ListeningTermOut)
def update_term(
    term_id: UUID,
    payload: ListeningTermUpdate,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.analyst)),
) -> ListeningTerm:
    term = db.get(ListeningTerm, term_id)
    if not term or term.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Listening term not found")
    data = payload.model_dump(exclude_unset=True)
    if "term_type" in data and data["term_type"] not in TERM_TYPES:
        raise HTTPException(status_code=400, detail="Invalid term_type")
    if "term" in data and data["term"]:
        data["term"] = data["term"].strip()
    for key, value in data.items():
        setattr(term, key, value)
    db.commit()
    db.refresh(term)
    return term


@router.delete("/listening/terms/{term_id}")
def delete_term(
    term_id: UUID,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin)),
) -> dict:
    term = db.get(ListeningTerm, term_id)
    if not term or term.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Listening term not found")
    db.delete(term)
    db.commit()
    return {"ok": True}


@router.post("/listening/sync")
def sync_listening(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID | None = None,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.analyst)),
) -> dict:
    created = listening_service.sync_simulated_mentions(
        db, organization_id=membership.organization_id, brand_id=brand_id
    )
    return {"created": created, "source": "simulation"}


@router.get("/listening/mentions", response_model=list[SocialMentionOut])
def list_mentions(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID | None = None,
    term_id: UUID | None = None,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> list[SocialMention]:
    q = db.query(SocialMention).filter(SocialMention.organization_id == membership.organization_id)
    if brand_id:
        q = q.filter(SocialMention.brand_id == brand_id)
    if term_id:
        q = q.filter(SocialMention.term_id == term_id)
    return q.order_by(SocialMention.mentioned_at.desc()).limit(100).all()


@router.get("/listening/summary", response_model=ListeningSummaryOut)
def listening_summary(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID | None = None,
    days: int = 14,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> ListeningSummaryOut:
    days = max(1, min(days, 90))
    return ListeningSummaryOut(
        **listening_service.summarize_listening(
            db,
            organization_id=membership.organization_id,
            brand_id=brand_id,
            days=days,
        )
    )
