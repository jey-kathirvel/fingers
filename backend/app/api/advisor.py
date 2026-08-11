from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentUser, DbDep, require_roles
from app.models import AiRecommendation, Brand, OrganizationMember, Role
from app.schemas import RecommendationGenerateRequest, RecommendationOut, RecommendationUpdate
from app.services import advisor as advisor_service

router = APIRouter(tags=["phase7"])


@router.get("/advisor/recommendations", response_model=list[RecommendationOut])
def list_recommendations(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID | None = None,
    status: str = "active",
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> list[AiRecommendation]:
    q = db.query(AiRecommendation).filter(AiRecommendation.organization_id == membership.organization_id)
    if brand_id:
        q = q.filter(AiRecommendation.brand_id == brand_id)
    if status != "all":
        q = q.filter(AiRecommendation.status == status)
    return q.order_by(AiRecommendation.created_at.desc()).limit(50).all()


@router.post("/advisor/generate", response_model=list[RecommendationOut])
async def generate_recommendations(
    payload: RecommendationGenerateRequest,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.analyst, Role.approver)),
) -> list[AiRecommendation]:
    brand_id = payload.brand_id
    if brand_id:
        brand = db.get(Brand, brand_id)
        if not brand or brand.organization_id != membership.organization_id:
            raise HTTPException(status_code=404, detail="Brand not found")
    return await advisor_service.generate_recommendations(
        db,
        organization_id=membership.organization_id,
        brand_id=brand_id,
        use_llm=payload.use_llm,
    )


@router.patch("/advisor/recommendations/{recommendation_id}", response_model=RecommendationOut)
def update_recommendation(
    recommendation_id: UUID,
    payload: RecommendationUpdate,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.analyst, Role.approver)),
) -> AiRecommendation:
    rec = db.get(AiRecommendation, recommendation_id)
    if not rec or rec.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if payload.status not in {"active", "accepted", "dismissed"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    rec.status = payload.status
    db.commit()
    db.refresh(rec)
    return rec
