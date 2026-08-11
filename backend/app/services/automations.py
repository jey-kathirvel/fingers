"""Rule-based automation engine with auditable runs."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import (
    AiReplyDraft,
    AuditLog,
    AutomationRule,
    AutomationRun,
    Brand,
    Lead,
    Notification,
    OrganizationMember,
    PostMetric,
    PublishingLog,
    ScheduledPost,
    SocialInteraction,
)
from app.services.campaigns import convert_interaction_to_lead
from app.services.engagement import local_reply_draft

TRIGGER_TYPES = {
    "inbox_keyword",
    "negative_sentiment",
    "unanswered_sla",
    "publish_failed",
    "high_engagement",
}
ACTION_TYPES = {
    "create_lead",
    "notify",
    "draft_reply",
    "classify_intent",
    "escalate",
}


def _parse_json(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def default_rules(*, organization_id: UUID, brand_id: UUID | None, created_by: UUID | None) -> list[AutomationRule]:
    specs = [
        {
            "name": "Price enquiry → lead + draft",
            "description": "When inbox text mentions price/pricing/cost, create a lead and draft a reply.",
            "trigger_type": "inbox_keyword",
            "trigger_config_json": json.dumps({"keywords": ["price", "pricing", "cost", "quote"]}),
            "action_type": "create_lead",
            "action_config_json": json.dumps({"also_draft_reply": True, "intent": "sales_enquiry"}),
        },
        {
            "name": "Escalate negative sentiment",
            "description": "Notify owners when negative/complaint inbox items arrive unanswered.",
            "trigger_type": "negative_sentiment",
            "trigger_config_json": json.dumps({}),
            "action_type": "escalate",
            "action_config_json": json.dumps({"priority": "high"}),
        },
        {
            "name": "Unanswered inbox SLA",
            "description": "Notify when interactions sit unanswered longer than 24 hours.",
            "trigger_type": "unanswered_sla",
            "trigger_config_json": json.dumps({"hours": 24}),
            "action_type": "notify",
            "action_config_json": json.dumps({"title": "Unanswered conversation"}),
        },
        {
            "name": "Publish failure alert",
            "description": "Notify when a scheduled publish fails.",
            "trigger_type": "publish_failed",
            "trigger_config_json": json.dumps({}),
            "action_type": "notify",
            "action_config_json": json.dumps({"title": "Publishing failed"}),
        },
        {
            "name": "High engagement → notify",
            "description": "Notify when a post engagement rate exceeds 4%.",
            "trigger_type": "high_engagement",
            "trigger_config_json": json.dumps({"engagement_rate": 4.0}),
            "action_type": "notify",
            "action_config_json": json.dumps({"title": "High-performing post"}),
        },
    ]
    rules: list[AutomationRule] = []
    for spec in specs:
        rules.append(
            AutomationRule(
                organization_id=organization_id,
                brand_id=brand_id,
                created_by=created_by,
                enabled=True,
                **spec,
            )
        )
    return rules


def seed_default_rules(
    db: Session,
    *,
    organization_id: UUID,
    brand_id: UUID | None = None,
    created_by: UUID | None = None,
) -> list[AutomationRule]:
    existing = (
        db.query(AutomationRule)
        .filter(AutomationRule.organization_id == organization_id)
        .count()
    )
    if existing:
        return (
            db.query(AutomationRule)
            .filter(AutomationRule.organization_id == organization_id)
            .order_by(AutomationRule.created_at.asc())
            .all()
        )
    rules = default_rules(organization_id=organization_id, brand_id=brand_id, created_by=created_by)
    db.add_all(rules)
    db.commit()
    for rule in rules:
        db.refresh(rule)
    return rules


def _already_ran(db: Session, rule_id: UUID, entity_type: str, entity_id: str) -> bool:
    return (
        db.query(AutomationRun)
        .filter(
            AutomationRun.rule_id == rule_id,
            AutomationRun.trigger_entity_type == entity_type,
            AutomationRun.trigger_entity_id == entity_id,
            AutomationRun.status.in_(["success", "skipped"]),
        )
        .first()
        is not None
    )


def _notify_org_admins(
    db: Session,
    *,
    organization_id: UUID,
    title: str,
    body: str,
) -> int:
    members = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.organization_id == organization_id)
        .all()
    )
    count = 0
    for member in members:
        db.add(
            Notification(
                user_id=member.user_id,
                organization_id=organization_id,
                title=title,
                body=body,
            )
        )
        count += 1
    return count


def _record_run(
    db: Session,
    *,
    rule: AutomationRule,
    status: str,
    entity_type: str | None,
    entity_id: str | None,
    result: dict | None = None,
    error: str | None = None,
) -> AutomationRun:
    run = AutomationRun(
        organization_id=rule.organization_id,
        rule_id=rule.id,
        status=status,
        trigger_entity_type=entity_type,
        trigger_entity_id=entity_id,
        result_json=json.dumps(result) if result else None,
        error_message=error,
    )
    db.add(run)
    db.add(
        AuditLog(
            organization_id=rule.organization_id,
            user_id=None,
            action=f"automation.{status}",
            entity_type="automation_rule",
            entity_id=str(rule.id),
            detail=json.dumps(
                {
                    "rule": rule.name,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "result": result,
                    "error": error,
                }
            ),
        )
    )
    rule.last_run_at = datetime.now(timezone.utc)
    return run


def _match_inbox_candidates(db: Session, rule: AutomationRule) -> list[SocialInteraction]:
    cfg = _parse_json(rule.trigger_config_json)
    q = db.query(SocialInteraction).filter(
        SocialInteraction.organization_id == rule.organization_id,
        SocialInteraction.status.in_(["new", "assigned", "draft_reply"]),
    )
    if rule.brand_id:
        q = q.filter(SocialInteraction.brand_id == rule.brand_id)

    if rule.trigger_type == "inbox_keyword":
        keywords = [str(k).lower() for k in cfg.get("keywords", [])]
        items = q.order_by(SocialInteraction.received_at.desc()).limit(100).all()
        return [i for i in items if any(k in (i.body or "").lower() for k in keywords)]

    if rule.trigger_type == "negative_sentiment":
        return (
            q.filter(
                (SocialInteraction.sentiment == "negative")
                | (SocialInteraction.intent == "complaint")
            )
            .order_by(SocialInteraction.received_at.desc())
            .limit(50)
            .all()
        )

    if rule.trigger_type == "unanswered_sla":
        hours = int(cfg.get("hours", 24))
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return (
            q.filter(
                SocialInteraction.responded_at.is_(None),
                SocialInteraction.received_at <= cutoff,
            )
            .order_by(SocialInteraction.received_at.asc())
            .limit(50)
            .all()
        )
    return []


def _match_publish_failures(db: Session, rule: AutomationRule) -> list[ScheduledPost]:
    q = db.query(ScheduledPost).filter(
        ScheduledPost.organization_id == rule.organization_id,
        ScheduledPost.status == "failed",
    )
    if rule.brand_id:
        q = q.filter(ScheduledPost.brand_id == rule.brand_id)
    return q.order_by(ScheduledPost.updated_at.desc()).limit(30).all()


def _match_high_engagement(db: Session, rule: AutomationRule) -> list[PostMetric]:
    cfg = _parse_json(rule.trigger_config_json)
    threshold = float(cfg.get("engagement_rate", 4.0))
    q = db.query(PostMetric).filter(
        PostMetric.organization_id == rule.organization_id,
        PostMetric.engagement_rate >= threshold,
    )
    if rule.brand_id:
        q = q.filter(PostMetric.brand_id == rule.brand_id)
    return q.order_by(PostMetric.engagement_rate.desc()).limit(30).all()


def _execute_action_on_interaction(
    db: Session,
    *,
    rule: AutomationRule,
    interaction: SocialInteraction,
) -> dict:
    action_cfg = _parse_json(rule.action_config_json)
    result: dict = {"interaction_id": str(interaction.id)}

    if rule.action_type == "classify_intent":
        intent = action_cfg.get("intent") or "sales_enquiry"
        interaction.intent = intent
        if action_cfg.get("priority"):
            interaction.priority = action_cfg["priority"]
        result["intent"] = intent
        return result

    if rule.action_type == "create_lead":
        intent = action_cfg.get("intent")
        if intent:
            interaction.intent = intent
        lead = convert_interaction_to_lead(
            db,
            interaction=interaction,
            created_by=rule.created_by,
            product_interest=action_cfg.get("product_interest"),
            notes=f"Auto-created by rule: {rule.name}",
        )
        result["lead_id"] = str(lead.id)
        if action_cfg.get("also_draft_reply"):
            brand = db.get(Brand, interaction.brand_id)
            if brand:
                draft = AiReplyDraft(
                    organization_id=interaction.organization_id,
                    interaction_id=interaction.id,
                    body=local_reply_draft(brand, interaction),
                    tone="helpful",
                    provider="automation",
                    status="suggested",
                    created_by=rule.created_by,
                )
                db.add(draft)
                interaction.status = "draft_reply"
                result["draft"] = True
        return result

    if rule.action_type == "draft_reply":
        brand = db.get(Brand, interaction.brand_id)
        if not brand:
            raise ValueError("Brand missing for draft reply")
        draft = AiReplyDraft(
            organization_id=interaction.organization_id,
            interaction_id=interaction.id,
            body=local_reply_draft(brand, interaction, tone=action_cfg.get("tone", "helpful")),
            tone=action_cfg.get("tone", "helpful"),
            provider="automation",
            status="suggested",
            created_by=rule.created_by,
        )
        db.add(draft)
        interaction.status = "draft_reply"
        result["draft"] = True
        return result

    if rule.action_type in {"notify", "escalate"}:
        title = action_cfg.get("title") or (
            "Escalated conversation" if rule.action_type == "escalate" else "Automation alert"
        )
        if rule.action_type == "escalate":
            interaction.priority = action_cfg.get("priority", "high")
        body = (
            f"Rule “{rule.name}” matched @{interaction.author_handle or interaction.author_name}: "
            f"{(interaction.body or '')[:180]}"
        )
        result["notifications"] = _notify_org_admins(
            db, organization_id=rule.organization_id, title=title, body=body
        )
        return result

    raise ValueError(f"Unsupported action for interaction: {rule.action_type}")


def _execute_notify_generic(
    db: Session,
    *,
    rule: AutomationRule,
    title: str,
    body: str,
) -> dict:
    action_cfg = _parse_json(rule.action_config_json)
    notify_title = action_cfg.get("title") or title
    count = _notify_org_admins(
        db, organization_id=rule.organization_id, title=notify_title, body=body
    )
    return {"notifications": count}


def run_rule(db: Session, rule: AutomationRule, *, limit: int = 20) -> list[AutomationRun]:
    if not rule.enabled:
        return []
    runs: list[AutomationRun] = []

    try:
        if rule.trigger_type in {"inbox_keyword", "negative_sentiment", "unanswered_sla"}:
            for interaction in _match_inbox_candidates(db, rule)[:limit]:
                entity_id = str(interaction.id)
                if _already_ran(db, rule.id, "social_interaction", entity_id):
                    continue
                try:
                    result = _execute_action_on_interaction(db, rule=rule, interaction=interaction)
                    runs.append(
                        _record_run(
                            db,
                            rule=rule,
                            status="success",
                            entity_type="social_interaction",
                            entity_id=entity_id,
                            result=result,
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    runs.append(
                        _record_run(
                            db,
                            rule=rule,
                            status="failed",
                            entity_type="social_interaction",
                            entity_id=entity_id,
                            error=str(exc),
                        )
                    )

        elif rule.trigger_type == "publish_failed":
            for post in _match_publish_failures(db, rule)[:limit]:
                entity_id = str(post.id)
                if _already_ran(db, rule.id, "scheduled_post", entity_id):
                    continue
                log = (
                    db.query(PublishingLog)
                    .filter(PublishingLog.scheduled_post_id == post.id)
                    .order_by(PublishingLog.created_at.desc())
                    .first()
                )
                body = f"Publish failed for {post.platform} post {entity_id[:8]}: {post.last_error or (log.message if log else 'unknown')}"
                result = _execute_notify_generic(
                    db, rule=rule, title="Publishing failed", body=body
                )
                runs.append(
                    _record_run(
                        db,
                        rule=rule,
                        status="success",
                        entity_type="scheduled_post",
                        entity_id=entity_id,
                        result=result,
                    )
                )

        elif rule.trigger_type == "high_engagement":
            for metric in _match_high_engagement(db, rule)[:limit]:
                entity_id = str(metric.id)
                if _already_ran(db, rule.id, "post_metric", entity_id):
                    continue
                body = (
                    f"{metric.platform} post engagement {metric.engagement_rate:.2f}% "
                    f"(impressions {metric.impressions}). Consider repurposing."
                )
                result = _execute_notify_generic(
                    db, rule=rule, title="High-performing post", body=body
                )
                runs.append(
                    _record_run(
                        db,
                        rule=rule,
                        status="success",
                        entity_type="post_metric",
                        entity_id=entity_id,
                        result=result,
                    )
                )
        else:
            runs.append(
                _record_run(
                    db,
                    rule=rule,
                    status="failed",
                    entity_type=None,
                    entity_id=None,
                    error=f"Unknown trigger_type {rule.trigger_type}",
                )
            )
    finally:
        db.commit()
    return runs


def run_automations(
    db: Session,
    *,
    organization_id: UUID | None = None,
    brand_id: UUID | None = None,
    rule_id: UUID | None = None,
) -> dict:
    q = db.query(AutomationRule).filter(AutomationRule.enabled.is_(True))
    if organization_id:
        q = q.filter(AutomationRule.organization_id == organization_id)
    if brand_id:
        q = q.filter((AutomationRule.brand_id == brand_id) | (AutomationRule.brand_id.is_(None)))
    if rule_id:
        q = q.filter(AutomationRule.id == rule_id)
    rules = q.order_by(AutomationRule.created_at.asc()).all()
    total_runs = 0
    success = 0
    failed = 0
    for rule in rules:
        for run in run_rule(db, rule):
            total_runs += 1
            if run.status == "success":
                success += 1
            elif run.status == "failed":
                failed += 1
    return {"rules_evaluated": len(rules), "runs": total_runs, "success": success, "failed": failed}
