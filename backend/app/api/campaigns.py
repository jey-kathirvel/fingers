from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentUser, DbDep, require_roles
from app.models import Brand, Campaign, ContentItem, Lead, OrganizationMember, Role
from app.schemas import (
    CampaignCreate,
    CampaignLinkContentRequest,
    CampaignOut,
    CampaignUpdate,
    ConvertLeadRequest,
    LeadCreate,
    LeadOut,
    LeadPipelineOut,
    LeadUpdate,
)
from app.services import campaigns as campaign_service
from app.services.engagement import get_interaction

router = APIRouter(tags=["phase6"])


def _campaign_out(campaign: Campaign) -> CampaignOut:
    return CampaignOut(**campaign_service.campaign_to_dict(campaign))


@router.get("/campaigns", response_model=list[CampaignOut])
def list_campaigns(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID | None = None,
    status: str | None = None,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> list[CampaignOut]:
    q = (
        db.query(Campaign)
        .options(joinedload(Campaign.content_links))
        .filter(Campaign.organization_id == membership.organization_id)
    )
    if brand_id:
        q = q.filter(Campaign.brand_id == brand_id)
    if status:
        q = q.filter(Campaign.status == status)
    return [_campaign_out(c) for c in q.order_by(Campaign.created_at.desc()).all()]


@router.post("/campaigns", response_model=CampaignOut)
def create_campaign(
    payload: CampaignCreate,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator)),
) -> CampaignOut:
    brand = db.get(Brand, payload.brand_id)
    if not brand or brand.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Brand not found")
    campaign = Campaign(
        organization_id=membership.organization_id,
        brand_id=payload.brand_id,
        name=payload.name,
        objective=payload.objective,
        platforms=campaign_service.platforms_to_str(payload.platforms),
        status=payload.status if payload.status in {"draft", "active", "paused", "completed"} else "draft",
        start_date=payload.start_date,
        end_date=payload.end_date,
        kpi_targets=payload.kpi_targets,
        notes=payload.notes,
        created_by=user.id,
    )
    db.add(campaign)
    db.commit()
    return _campaign_out(campaign_service.get_campaign(db, membership.organization_id, campaign.id))


@router.get("/campaigns/{campaign_id}", response_model=CampaignOut)
def get_campaign(
    campaign_id: UUID,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> CampaignOut:
    campaign = campaign_service.get_campaign(db, membership.organization_id, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _campaign_out(campaign)


@router.patch("/campaigns/{campaign_id}", response_model=CampaignOut)
def update_campaign(
    campaign_id: UUID,
    payload: CampaignUpdate,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator)),
) -> CampaignOut:
    campaign = campaign_service.get_campaign(db, membership.organization_id, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    data = payload.model_dump(exclude_unset=True)
    if "platforms" in data:
        campaign.platforms = campaign_service.platforms_to_str(data.pop("platforms"))
    for key, value in data.items():
        setattr(campaign, key, value)
    db.commit()
    return _campaign_out(campaign_service.get_campaign(db, membership.organization_id, campaign_id))


@router.post("/campaigns/{campaign_id}/content", response_model=CampaignOut)
def link_campaign_content(
    campaign_id: UUID,
    payload: CampaignLinkContentRequest,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator)),
) -> CampaignOut:
    campaign = campaign_service.get_campaign(db, membership.organization_id, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    content = db.get(ContentItem, payload.content_item_id)
    if not content or content.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Content not found")
    if content.brand_id != campaign.brand_id:
        raise HTTPException(status_code=400, detail="Content brand mismatch")
    campaign_service.link_content(db, campaign, content)
    db.commit()
    return _campaign_out(campaign_service.get_campaign(db, membership.organization_id, campaign_id))


@router.get("/leads", response_model=list[LeadOut])
def list_leads(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID | None = None,
    status: str | None = None,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> list[Lead]:
    q = db.query(Lead).filter(Lead.organization_id == membership.organization_id)
    if brand_id:
        q = q.filter(Lead.brand_id == brand_id)
    if status:
        q = q.filter(Lead.status == status)
    return q.order_by(Lead.created_at.desc()).limit(200).all()


@router.get("/leads/pipeline", response_model=LeadPipelineOut)
def leads_pipeline(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID | None = None,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> LeadPipelineOut:
    return LeadPipelineOut(**campaign_service.lead_pipeline(db, membership.organization_id, brand_id))


@router.post("/leads", response_model=LeadOut)
def create_lead(
    payload: LeadCreate,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.approver)),
) -> Lead:
    brand = db.get(Brand, payload.brand_id)
    if not brand or brand.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Brand not found")
    lead = Lead(
        organization_id=membership.organization_id,
        brand_id=payload.brand_id,
        name=payload.name,
        source_platform=payload.source_platform,
        interaction_id=payload.interaction_id,
        content_item_id=payload.content_item_id,
        campaign_id=payload.campaign_id,
        intent=payload.intent,
        score=payload.score,
        status=payload.status if payload.status in campaign_service.LEAD_STATUSES else "new",
        product_interest=payload.product_interest,
        follow_up_at=payload.follow_up_at,
        source_message=payload.source_message,
        notes=payload.notes,
        status_history=campaign_service.append_status_history(None, payload.status or "new", "Manual create"),
        created_by=user.id,
        owner_id=user.id,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.patch("/leads/{lead_id}", response_model=LeadOut)
def update_lead(
    lead_id: UUID,
    payload: LeadUpdate,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.approver)),
) -> Lead:
    lead = db.get(Lead, lead_id)
    if not lead or lead.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Lead not found")
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] != lead.status:
        if data["status"] not in campaign_service.LEAD_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid lead status")
        lead.status_history = campaign_service.append_status_history(lead.status_history, data["status"])
    for key, value in data.items():
        setattr(lead, key, value)
    db.commit()
    db.refresh(lead)
    return lead


@router.post("/interactions/{interaction_id}/convert-lead", response_model=LeadOut)
def convert_interaction_lead(
    interaction_id: UUID,
    payload: ConvertLeadRequest,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.approver)),
) -> Lead:
    interaction = get_interaction(db, membership.organization_id, interaction_id)
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    if payload.campaign_id:
        campaign = campaign_service.get_campaign(db, membership.organization_id, payload.campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
    lead = campaign_service.convert_interaction_to_lead(
        db,
        interaction=interaction,
        created_by=user.id,
        campaign_id=payload.campaign_id,
        product_interest=payload.product_interest,
        notes=payload.notes,
    )
    db.commit()
    db.refresh(lead)
    return lead
