"""AI Advisor: generate actionable recommendations from stored metrics."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import (
    AiRecommendation,
    Brand,
    Campaign,
    ContentItem,
    Lead,
    PostMetric,
    SocialInteraction,
)
from app.services.analytics import list_post_metrics, platform_breakdown, summarize_overview, trend_series


def _evidence(**kwargs) -> str:
    return json.dumps(kwargs)


def generate_rule_recommendations(
    db: Session,
    *,
    organization_id: UUID,
    brand_id: UUID | None = None,
) -> list[dict]:
    brand = db.get(Brand, brand_id) if brand_id else None
    brand_name = brand.name if brand else "your brand"
    kpi = summarize_overview(db, organization_id, brand_id)
    trends = trend_series(db, organization_id, brand_id, days=14)
    platforms = platform_breakdown(db, organization_id, brand_id)
    posts = list_post_metrics(db, organization_id, brand_id)
    backlog = (
        db.query(SocialInteraction)
        .filter(
            SocialInteraction.organization_id == organization_id,
            SocialInteraction.status.in_(["new", "assigned", "draft_reply"]),
        )
    )
    if brand_id:
        backlog = backlog.filter(SocialInteraction.brand_id == brand_id)
    backlog_count = backlog.count()

    open_leads = db.query(Lead).filter(
        Lead.organization_id == organization_id,
        Lead.status.in_(["new", "contacted", "interested", "demo", "proposal"]),
    )
    if brand_id:
        open_leads = open_leads.filter(Lead.brand_id == brand_id)
    open_lead_count = open_leads.count()

    active_campaigns = db.query(Campaign).filter(
        Campaign.organization_id == organization_id,
        Campaign.status == "active",
    )
    if brand_id:
        active_campaigns = active_campaigns.filter(Campaign.brand_id == brand_id)
    campaign_count = active_campaigns.count()

    drafts = db.query(ContentItem).filter(
        ContentItem.organization_id == organization_id,
        ContentItem.status.in_(["draft", "review"]),
    )
    if brand_id:
        drafts = drafts.filter(ContentItem.brand_id == brand_id)
    draft_count = drafts.count()

    recs: list[dict] = []

    # Top post / format insight
    if posts:
        top = posts[0]
        avg_er = sum(p["engagement_rate"] for p in posts) / len(posts)
        multiple = round(top["engagement_rate"] / avg_er, 1) if avg_er else 1.0
        recs.append(
            {
                "category": "content",
                "title": f"Double down on {top['platform']} winners",
                "detail": (
                    f"“{top['title']}” is at {top['engagement_rate']}% ER "
                    f"({multiple}× your recent average). Publish a follow-up on the same topic this week."
                ),
                "rationale": "Ranked by stored post_metrics.engagement_rate",
                "priority": "high" if multiple >= 1.5 else "medium",
                "evidence_json": _evidence(top_post=top, avg_engagement_rate=round(avg_er, 2)),
            }
        )
        if top["platform"] == "linkedin":
            recs.append(
                {
                    "category": "repurpose",
                    "title": "Repurpose the LinkedIn winner into a Reel script",
                    "detail": (
                        f"Turn “{top['title']}” into a 30–45s Reel + Instagram caption. "
                        f"It already earned {top['impressions']} impressions and {top['likes']} likes."
                    ),
                    "rationale": "High-performing LinkedIn post is a strong repurposing source",
                    "priority": "medium",
                    "evidence_json": _evidence(source_post=top),
                }
            )
        if top["platform"] in {"instagram", "facebook"}:
            recs.append(
                {
                    "category": "repurpose",
                    "title": "Expand the visual post into LinkedIn education",
                    "detail": (
                        f"Rewrite “{top['title']}” as a LinkedIn insight post with a clear CTA for {brand_name}."
                    ),
                    "rationale": "Cross-platform expansion from a high-ER visual post",
                    "priority": "medium",
                    "evidence_json": _evidence(source_post=top),
                }
            )

    # Platform comparison
    if len(platforms) >= 2:
        ranked = sorted(platforms, key=lambda p: p["engagement_rate"], reverse=True)
        best, worst = ranked[0], ranked[-1]
        if best["engagement_rate"] > worst["engagement_rate"]:
            recs.append(
                {
                    "category": "format",
                    "title": f"Shift next creative toward {best['platform']}",
                    "detail": (
                        f"{best['platform'].title()} leads at {best['engagement_rate']}% ER vs "
                        f"{worst['platform']} at {worst['engagement_rate']}%. "
                        f"Allocate the next 2 assets primarily to {best['platform']}."
                    ),
                    "rationale": "Compared latest account_metrics by platform",
                    "priority": "high",
                    "evidence_json": _evidence(platforms=ranked),
                }
            )

    # Timing from trend shape
    if len(trends) >= 7:
        best_day = max(trends, key=lambda t: t["impressions"])
        recs.append(
            {
                "category": "timing",
                "title": "Schedule around your recent peak day",
                "detail": (
                    f"{best_day['date']} was your strongest recent day "
                    f"({best_day['impressions']} impressions, {best_day['engagement_rate']}% ER). "
                    f"Queue the next approved post for a similar weekday slot."
                ),
                "rationale": "Peak day selected from analytics trend series",
                "priority": "medium",
                "evidence_json": _evidence(best_day=best_day, window_days=len(trends)),
            }
        )

    # Ops / inbox
    if backlog_count:
        recs.append(
            {
                "category": "ops",
                "title": "Clear the engagement backlog",
                "detail": (
                    f"{backlog_count} open inbox item(s) need replies. "
                    f"Prioritize sales_enquiry and negative sentiment threads first."
                ),
                "rationale": "Count of social_interactions in new/assigned/draft_reply",
                "priority": "high" if backlog_count >= 3 else "medium",
                "evidence_json": _evidence(backlog=backlog_count),
            }
        )

    # Leads
    if open_lead_count:
        recs.append(
            {
                "category": "leads",
                "title": "Advance open leads this week",
                "detail": (
                    f"You have {open_lead_count} open lead(s). Move contacted → interested or book demos "
                    f"for scores above 70."
                ),
                "rationale": "Open leads from leads table",
                "priority": "high" if open_lead_count >= 2 else "medium",
                "evidence_json": _evidence(open_leads=open_lead_count),
            }
        )
    elif kpi.get("leads", 0) == 0 and posts:
        recs.append(
            {
                "category": "leads",
                "title": "Add a stronger lead CTA to top content",
                "detail": (
                    f"Metrics show engagement but few leads. Add a demo/pricing CTA to the next "
                    f"{posts[0]['platform']} post for {brand_name}."
                ),
                "rationale": "Engagement without lead conversion signal",
                "priority": "medium",
                "evidence_json": _evidence(kpi=kpi),
            }
        )

    # Campaigns / drafts
    if campaign_count == 0:
        recs.append(
            {
                "category": "content",
                "title": "Create an active campaign wrapper",
                "detail": "No active campaign found. Group this week's posts under one objective so leads can be attributed.",
                "rationale": "Zero campaigns with status=active",
                "priority": "low",
                "evidence_json": _evidence(active_campaigns=0),
            }
        )
    if draft_count:
        recs.append(
            {
                "category": "ops",
                "title": "Ship stalled studio drafts",
                "detail": f"{draft_count} draft/review item(s) are waiting. Approve and schedule the strongest variant.",
                "rationale": "Content items in draft/review",
                "priority": "medium",
                "evidence_json": _evidence(draft_count=draft_count),
            }
        )

    if not recs:
        recs.append(
            {
                "category": "ops",
                "title": "Sync metrics to unlock sharper advice",
                "detail": "Not enough stored analytics yet. Sync Analytics and publish at least one post, then regenerate.",
                "rationale": "Fallback when evidence tables are empty",
                "priority": "low",
                "evidence_json": _evidence(kpi=kpi, posts=len(posts), trends=len(trends)),
            }
        )

    return recs


def persist_recommendations(
    db: Session,
    *,
    organization_id: UUID,
    brand_id: UUID | None,
    recommendations: list[dict],
    provider: str = "rules",
) -> list[AiRecommendation]:
    # Deactivate previous active recs for this brand scope
    q = db.query(AiRecommendation).filter(
        AiRecommendation.organization_id == organization_id,
        AiRecommendation.status == "active",
    )
    if brand_id:
        q = q.filter(AiRecommendation.brand_id == brand_id)
    for old in q.all():
        old.status = "dismissed"

    created: list[AiRecommendation] = []
    for item in recommendations:
        rec = AiRecommendation(
            organization_id=organization_id,
            brand_id=brand_id,
            category=item["category"],
            title=item["title"],
            detail=item["detail"],
            rationale=item.get("rationale"),
            priority=item.get("priority") or "medium",
            status="active",
            evidence_json=item.get("evidence_json"),
            provider=provider,
        )
        db.add(rec)
        created.append(rec)
    db.flush()
    return created


async def generate_recommendations(
    db: Session,
    *,
    organization_id: UUID,
    brand_id: UUID | None,
    use_llm: bool = True,
) -> list[AiRecommendation]:
    base = generate_rule_recommendations(db, organization_id=organization_id, brand_id=brand_id)
    provider = "rules"

    if use_llm:
        try:
            from app.core.config import get_settings
            from app.services import ai_studio

            settings = get_settings()
            if settings.llm_provider != "local":
                brand = db.get(Brand, brand_id) if brand_id else None
                raw, provider_name = await ai_studio.llm_chat(
                    [
                        {
                            "role": "system",
                            "content": (
                                "You are Fingers AI Advisor. Return JSON "
                                "{recommendations:[{category,title,detail,priority,rationale}]} "
                                "with 3-5 concise actionable items. Categories: timing,content,format,repurpose,ops,leads."
                            ),
                        },
                        {
                            "role": "user",
                            "content": json.dumps(
                                {
                                    "brand": brand.name if brand else None,
                                    "seed_recommendations": base[:5],
                                    "instruction": "Refine and keep evidence-grounded; do not invent metrics.",
                                }
                            ),
                        },
                    ]
                )
                data = ai_studio._extract_json(raw)
                llm_recs = data.get("recommendations") if isinstance(data, dict) else None
                if isinstance(llm_recs, list) and llm_recs:
                    refined = []
                    for item in llm_recs[:6]:
                        if not isinstance(item, dict) or not item.get("title") or not item.get("detail"):
                            continue
                        refined.append(
                            {
                                "category": str(item.get("category") or "content"),
                                "title": str(item["title"])[:255],
                                "detail": str(item["detail"]),
                                "rationale": str(item.get("rationale") or "LLM refinement of metric-grounded seeds"),
                                "priority": str(item.get("priority") or "medium"),
                                "evidence_json": _evidence(seed=base[:3]),
                            }
                        )
                    if refined:
                        base = refined
                        provider = provider_name
        except Exception:
            provider = "rules_fallback"

    created = persist_recommendations(
        db,
        organization_id=organization_id,
        brand_id=brand_id,
        recommendations=base,
        provider=provider,
    )
    db.commit()
    for rec in created:
        db.refresh(rec)
    return created
