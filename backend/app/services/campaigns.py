"""Campaign and lead helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models import Campaign, CampaignContent, ContentItem, Lead, SocialInteraction

LEAD_STATUSES = ["new", "contacted", "interested", "demo", "proposal", "converted", "lost"]
OPEN_STATUSES = {"new", "contacted", "interested", "demo", "proposal"}


def platforms_to_str(platforms: list[str] | None) -> str | None:
    if not platforms:
        return None
    return ",".join(p.strip() for p in platforms if p.strip())


def platforms_from_str(value: str | None) -> list[str]:
    if not value:
        return []
    return [p.strip() for p in value.split(",") if p.strip()]


def campaign_to_dict(campaign: Campaign) -> dict:
    return {
        "id": campaign.id,
        "organization_id": campaign.organization_id,
        "brand_id": campaign.brand_id,
        "name": campaign.name,
        "objective": campaign.objective,
        "platforms": campaign.platforms,
        "status": campaign.status,
        "start_date": campaign.start_date,
        "end_date": campaign.end_date,
        "kpi_targets": campaign.kpi_targets,
        "notes": campaign.notes,
        "created_by": campaign.created_by,
        "created_at": campaign.created_at,
        "updated_at": campaign.updated_at,
        "content_item_ids": [link.content_item_id for link in (campaign.content_links or [])],
    }


def append_status_history(existing: str | None, status: str, note: str | None = None) -> str:
    history = []
    if existing:
        try:
            history = json.loads(existing)
            if not isinstance(history, list):
                history = []
        except Exception:  # noqa: BLE001
            history = []
    history.append(
        {
            "status": status,
            "at": datetime.now(timezone.utc).isoformat(),
            "note": note,
        }
    )
    return json.dumps(history[-20:])


def convert_interaction_to_lead(
    db: Session,
    *,
    interaction: SocialInteraction,
    created_by: UUID | None,
    campaign_id: UUID | None = None,
    product_interest: str | None = None,
    notes: str | None = None,
) -> Lead:
    existing = (
        db.query(Lead)
        .filter(
            Lead.organization_id == interaction.organization_id,
            Lead.interaction_id == interaction.id,
        )
        .first()
    )
    if existing:
        return existing

    score = max(interaction.lead_probability or 0, 10)
    if interaction.intent == "sales_enquiry":
        score = max(score, 75)
    elif interaction.intent == "partnership":
        score = max(score, 55)

    lead = Lead(
        organization_id=interaction.organization_id,
        brand_id=interaction.brand_id,
        name=interaction.author_name or interaction.author_handle or "Social lead",
        source_platform=interaction.platform,
        social_account_id=interaction.social_account_id,
        interaction_id=interaction.id,
        content_item_id=interaction.content_item_id,
        campaign_id=campaign_id,
        intent=interaction.intent,
        score=score,
        status="new",
        product_interest=product_interest,
        source_message=interaction.body,
        notes=notes,
        status_history=append_status_history(None, "new", "Converted from inbox"),
        created_by=created_by,
    )
    db.add(lead)
    db.flush()
    return lead


def lead_pipeline(db: Session, organization_id: UUID, brand_id: UUID | None = None) -> dict:
    q = db.query(Lead).filter(Lead.organization_id == organization_id)
    if brand_id:
        q = q.filter(Lead.brand_id == brand_id)
    leads = q.all()
    by_status = {status: 0 for status in LEAD_STATUSES}
    for lead in leads:
        by_status[lead.status] = by_status.get(lead.status, 0) + 1
    scores = [lead.score for lead in leads]
    return {
        "total": len(leads),
        "by_status": by_status,
        "converted": by_status.get("converted", 0),
        "open_count": sum(by_status.get(s, 0) for s in OPEN_STATUSES),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0.0,
    }


def get_campaign(db: Session, organization_id: UUID, campaign_id: UUID) -> Campaign | None:
    return (
        db.query(Campaign)
        .options(joinedload(Campaign.content_links))
        .filter(Campaign.id == campaign_id, Campaign.organization_id == organization_id)
        .first()
    )


def link_content(db: Session, campaign: Campaign, content: ContentItem) -> CampaignContent:
    existing = (
        db.query(CampaignContent)
        .filter(
            CampaignContent.campaign_id == campaign.id,
            CampaignContent.content_item_id == content.id,
        )
        .first()
    )
    if existing:
        return existing
    link = CampaignContent(campaign_id=campaign.id, content_item_id=content.id)
    db.add(link)
    db.flush()
    return link
