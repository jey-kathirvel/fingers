"""Social listening: terms, simulated mentions, share-of-voice."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Brand, BrandGuidelines, ListeningTerm, SocialMention

SAMPLE_MENTIONS = [
    ("linkedin", "positive", "Asha N.", "@asha", "Loving how {term} explains field irrigation simply."),
    ("instagram", "neutral", "FieldOps Daily", "@fieldops", "Comparing options — {term} showed up in our shortlist."),
    ("facebook", "negative", "Ravi K", "@ravik", "Still waiting on support from {term} after last week's outage."),
    ("x", "positive", "AgTech Watch", "@agtechwatch", "Thread: why teams evaluate {term} for multi-brand social ops."),
    ("linkedin", "neutral", "Priya M", "@priyam", "Anyone using {term} vs competitor stacks for SME workflows?"),
]


def seed_default_terms(
    db: Session,
    *,
    organization_id: UUID,
    brand_id: UUID,
) -> list[ListeningTerm]:
    brand = db.get(Brand, brand_id)
    if not brand or brand.organization_id != organization_id:
        return []
    existing = (
        db.query(ListeningTerm)
        .filter(
            ListeningTerm.organization_id == organization_id,
            ListeningTerm.brand_id == brand_id,
        )
        .count()
    )
    if existing:
        return (
            db.query(ListeningTerm)
            .filter(
                ListeningTerm.organization_id == organization_id,
                ListeningTerm.brand_id == brand_id,
            )
            .order_by(ListeningTerm.created_at.asc())
            .all()
        )

    terms: list[ListeningTerm] = [
        ListeningTerm(
            organization_id=organization_id,
            brand_id=brand_id,
            term=brand.name,
            term_type="brand",
            enabled=True,
        )
    ]
    guidelines = (
        db.query(BrandGuidelines).filter(BrandGuidelines.brand_id == brand_id).first()
    )
    if guidelines and guidelines.competitors:
        for raw in guidelines.competitors.split(","):
            competitor = raw.strip()
            if competitor:
                terms.append(
                    ListeningTerm(
                        organization_id=organization_id,
                        brand_id=brand_id,
                        term=competitor,
                        term_type="competitor",
                        enabled=True,
                    )
                )
    if guidelines and guidelines.approved_keywords:
        for raw in guidelines.approved_keywords.split(",")[:5]:
            keyword = raw.strip().lstrip("#")
            if keyword:
                terms.append(
                    ListeningTerm(
                        organization_id=organization_id,
                        brand_id=brand_id,
                        term=keyword,
                        term_type="product" if " " not in keyword else "hashtag",
                        enabled=True,
                    )
                )
    # Always include a product-ish fallback
    if len(terms) == 1:
        terms.append(
            ListeningTerm(
                organization_id=organization_id,
                brand_id=brand_id,
                term=f"{brand.name} irrigation",
                term_type="product",
                enabled=True,
            )
        )
        terms.append(
            ListeningTerm(
                organization_id=organization_id,
                brand_id=brand_id,
                term="CompetitorCo",
                term_type="competitor",
                enabled=True,
            )
        )

    db.add_all(terms)
    db.commit()
    for term in terms:
        db.refresh(term)
    return terms


def _stable_external_id(term_id: UUID, platform: str, idx: int, day_key: str) -> str:
    raw = f"{term_id}:{platform}:{idx}:{day_key}"
    return "listen-" + hashlib.sha1(raw.encode()).hexdigest()[:24]


def sync_simulated_mentions(
    db: Session,
    *,
    organization_id: UUID | None = None,
    brand_id: UUID | None = None,
) -> int:
    q = db.query(ListeningTerm).filter(ListeningTerm.enabled.is_(True))
    if organization_id:
        q = q.filter(ListeningTerm.organization_id == organization_id)
    if brand_id:
        q = q.filter(ListeningTerm.brand_id == brand_id)
    terms = q.all()
    if not terms:
        return 0

    now = datetime.now(timezone.utc)
    day_key = now.strftime("%Y%m%d")
    created = 0
    for term in terms:
        for idx, (platform, sentiment, author, handle, template) in enumerate(SAMPLE_MENTIONS):
            # Competitors skew neutral/negative weight slightly for SOV demos
            weight = 1.2 if term.term_type == "brand" else 0.9 if term.term_type == "competitor" else 1.0
            if term.term_type == "competitor" and sentiment == "positive":
                sentiment = "neutral"
            external_id = _stable_external_id(term.id, platform, idx, day_key)
            exists = (
                db.query(SocialMention)
                .filter(
                    SocialMention.organization_id == term.organization_id,
                    SocialMention.platform == platform,
                    SocialMention.external_id == external_id,
                )
                .first()
            )
            if exists:
                continue
            db.add(
                SocialMention(
                    organization_id=term.organization_id,
                    brand_id=term.brand_id,
                    term_id=term.id,
                    platform=platform,
                    author_name=author,
                    author_handle=handle,
                    body=template.format(term=term.term),
                    permalink=f"https://example.com/{platform}/{external_id}",
                    sentiment=sentiment,
                    share_weight=weight,
                    source="simulation",
                    external_id=external_id,
                    mentioned_at=now - timedelta(hours=idx + 1),
                )
            )
            created += 1
    if created:
        db.commit()
    return created


def summarize_listening(
    db: Session,
    *,
    organization_id: UUID,
    brand_id: UUID | None = None,
    days: int = 14,
) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    q = db.query(SocialMention).filter(
        SocialMention.organization_id == organization_id,
        SocialMention.mentioned_at >= cutoff,
    )
    if brand_id:
        q = q.filter(SocialMention.brand_id == brand_id)
    mentions = q.all()

    by_sentiment: dict[str, int] = {"positive": 0, "neutral": 0, "negative": 0}
    by_term_type: dict[str, float] = {}
    by_platform: dict[str, int] = {}
    term_weights: dict[str, float] = {}
    term_labels: dict[str, str] = {}

    term_ids = {m.term_id for m in mentions if m.term_id}
    terms = (
        db.query(ListeningTerm).filter(ListeningTerm.id.in_(term_ids)).all() if term_ids else []
    )
    term_map = {t.id: t for t in terms}

    for mention in mentions:
        by_sentiment[mention.sentiment] = by_sentiment.get(mention.sentiment, 0) + 1
        by_platform[mention.platform] = by_platform.get(mention.platform, 0) + 1
        term = term_map.get(mention.term_id) if mention.term_id else None
        ttype = term.term_type if term else "unknown"
        by_term_type[ttype] = by_term_type.get(ttype, 0.0) + float(mention.share_weight)
        if term:
            key = str(term.id)
            term_weights[key] = term_weights.get(key, 0.0) + float(mention.share_weight)
            term_labels[key] = f"{term.term} ({term.term_type})"

    total_weight = sum(term_weights.values()) or 1.0
    share_of_voice = [
        {
            "term_id": tid,
            "label": term_labels[tid],
            "weight": round(weight, 2),
            "share_pct": round(100.0 * weight / total_weight, 1),
        }
        for tid, weight in sorted(term_weights.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "window_days": days,
        "mention_count": len(mentions),
        "by_sentiment": by_sentiment,
        "by_term_type": {k: round(v, 2) for k, v in by_term_type.items()},
        "by_platform": by_platform,
        "share_of_voice": share_of_voice,
    }
