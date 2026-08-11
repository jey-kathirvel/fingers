from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentUser, DbDep, require_roles
from app.models import AutomationRule, AutomationRun, Brand, OrganizationMember, Role
from app.schemas import (
    AutomationRuleCreate,
    AutomationRuleOut,
    AutomationRuleUpdate,
    AutomationRunOut,
    AutomationRunSummary,
)
from app.services import automations as automation_service

router = APIRouter(tags=["phase8"])


@router.get("/automations", response_model=list[AutomationRuleOut])
def list_automations(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID | None = None,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> list[AutomationRule]:
    q = db.query(AutomationRule).filter(AutomationRule.organization_id == membership.organization_id)
    if brand_id:
        q = q.filter((AutomationRule.brand_id == brand_id) | (AutomationRule.brand_id.is_(None)))
    return q.order_by(AutomationRule.created_at.desc()).all()


@router.post("/automations", response_model=AutomationRuleOut)
def create_automation(
    payload: AutomationRuleCreate,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator)),
) -> AutomationRule:
    if payload.trigger_type not in automation_service.TRIGGER_TYPES:
        raise HTTPException(status_code=400, detail="Invalid trigger_type")
    if payload.action_type not in automation_service.ACTION_TYPES:
        raise HTTPException(status_code=400, detail="Invalid action_type")
    if payload.brand_id:
        brand = db.get(Brand, payload.brand_id)
        if not brand or brand.organization_id != membership.organization_id:
            raise HTTPException(status_code=404, detail="Brand not found")
    rule = AutomationRule(
        organization_id=membership.organization_id,
        brand_id=payload.brand_id,
        name=payload.name.strip(),
        description=payload.description,
        enabled=payload.enabled,
        trigger_type=payload.trigger_type,
        trigger_config_json=payload.trigger_config_json,
        action_type=payload.action_type,
        action_config_json=payload.action_config_json,
        created_by=user.id,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.post("/automations/seed-defaults", response_model=list[AutomationRuleOut])
def seed_default_automations(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID | None = None,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator)),
) -> list[AutomationRule]:
    if brand_id:
        brand = db.get(Brand, brand_id)
        if not brand or brand.organization_id != membership.organization_id:
            raise HTTPException(status_code=404, detail="Brand not found")
    return automation_service.seed_default_rules(
        db,
        organization_id=membership.organization_id,
        brand_id=brand_id,
        created_by=user.id,
    )


@router.post("/automations/run", response_model=AutomationRunSummary)
def run_automations(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID | None = None,
    rule_id: UUID | None = None,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.approver)),
) -> AutomationRunSummary:
    summary = automation_service.run_automations(
        db,
        organization_id=membership.organization_id,
        brand_id=brand_id,
        rule_id=rule_id,
    )
    return AutomationRunSummary(**summary)


@router.get("/automations/runs", response_model=list[AutomationRunOut])
def list_automation_runs(
    user: CurrentUser,
    db: DbDep,
    rule_id: UUID | None = None,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> list[AutomationRun]:
    q = db.query(AutomationRun).filter(AutomationRun.organization_id == membership.organization_id)
    if rule_id:
        q = q.filter(AutomationRun.rule_id == rule_id)
    return q.order_by(AutomationRun.created_at.desc()).limit(100).all()


@router.patch("/automations/{rule_id}", response_model=AutomationRuleOut)
def update_automation(
    rule_id: UUID,
    payload: AutomationRuleUpdate,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator)),
) -> AutomationRule:
    rule = db.get(AutomationRule, rule_id)
    if not rule or rule.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    data = payload.model_dump(exclude_unset=True)
    if "trigger_type" in data and data["trigger_type"] not in automation_service.TRIGGER_TYPES:
        raise HTTPException(status_code=400, detail="Invalid trigger_type")
    if "action_type" in data and data["action_type"] not in automation_service.ACTION_TYPES:
        raise HTTPException(status_code=400, detail="Invalid action_type")
    if "name" in data and data["name"]:
        data["name"] = data["name"].strip()
    for key, value in data.items():
        setattr(rule, key, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/automations/{rule_id}")
def delete_automation(
    rule_id: UUID,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin)),
) -> dict:
    rule = db.get(AutomationRule, rule_id)
    if not rule or rule.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    db.delete(rule)
    db.commit()
    return {"ok": True}
