from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentUser, DbDep, require_roles
from app.models import (
    Brand,
    BrandGuidelines,
    ContentIdea,
    ContentItem,
    ContentStatus,
    ContentVersion,
    MediaAsset,
    OrganizationMember,
    Role,
)
from app.schemas import (
    AIGenerateRequest,
    AIIdeasRequest,
    AIRewriteRequest,
    ContentCreate,
    ContentIdeaOut,
    ContentOut,
    ContentUpdate,
    ContentVersionIn,
    ContentVersionOut,
    MediaAssetCreate,
    MediaAssetOut,
)
from app.services import ai_studio

router = APIRouter(tags=["phase2"])


def _get_brand(db, membership: OrganizationMember, brand_id: UUID) -> Brand:
    brand = db.get(Brand, brand_id)
    if not brand or brand.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand


def _guidelines(db, brand_id: UUID) -> BrandGuidelines | None:
    return db.query(BrandGuidelines).filter(BrandGuidelines.brand_id == brand_id).first()


@router.post("/ai/generate", response_model=ContentOut)
async def ai_generate(
    payload: AIGenerateRequest,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator)),
) -> ContentItem:
    brand = _get_brand(db, membership, payload.brand_id)
    result = await ai_studio.generate_content(
        brand,
        _guidelines(db, brand.id),
        payload.topic,
        payload.objective,
        payload.platforms,
    )
    item = ContentItem(
        organization_id=membership.organization_id,
        brand_id=brand.id,
        created_by=user.id,
        title=result.get("title") or payload.topic[:120],
        objective=payload.objective,
        topic=payload.topic,
        master_concept=result.get("master_concept"),
        status=ContentStatus.draft.value,
    )
    db.add(item)
    db.flush()
    for v in result.get("versions", []):
        db.add(
            ContentVersion(
                content_item_id=item.id,
                platform=v["platform"],
                format=v.get("format"),
                headline=v.get("headline"),
                body=v.get("body"),
                hashtags=v.get("hashtags"),
                cta=v.get("cta"),
                image_prompt=v.get("image_prompt"),
                video_script=v.get("video_script"),
                score_clarity=v.get("score_clarity"),
                score_brand_fit=v.get("score_brand_fit"),
                score_cta=v.get("score_cta"),
                score_platform_fit=v.get("score_platform_fit"),
            )
        )
    db.commit()
    return (
        db.query(ContentItem)
        .options(joinedload(ContentItem.versions))
        .filter(ContentItem.id == item.id)
        .one()
    )


@router.post("/ai/rewrite")
async def ai_rewrite(
    payload: AIRewriteRequest,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.reviewer)),
) -> dict:
    brand = _get_brand(db, membership, payload.brand_id)
    return await ai_studio.rewrite_content(payload.text, payload.platform, payload.instruction, brand)


@router.post("/ai/ideas", response_model=list[ContentIdeaOut])
async def ai_ideas(
    payload: AIIdeasRequest,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.analyst)),
) -> list[ContentIdea]:
    brand = _get_brand(db, membership, payload.brand_id)
    result = await ai_studio.generate_ideas(brand, _guidelines(db, brand.id), payload.count)
    ideas = result.get("ideas", [])
    saved: list[ContentIdea] = []
    for idea in ideas:
        row = ContentIdea(
            organization_id=membership.organization_id,
            brand_id=brand.id,
            title=idea["title"],
            format=idea.get("format"),
            goal=idea.get("goal"),
            platforms=idea.get("platforms"),
            confidence=idea.get("confidence"),
            rationale=idea.get("rationale"),
        )
        db.add(row)
        saved.append(row)
    db.commit()
    for row in saved:
        db.refresh(row)
    return saved


@router.get("/ai/ideas", response_model=list[ContentIdeaOut])
def list_ideas(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID | None = None,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> list[ContentIdea]:
    q = db.query(ContentIdea).filter(ContentIdea.organization_id == membership.organization_id)
    if brand_id:
        q = q.filter(ContentIdea.brand_id == brand_id)
    return q.order_by(ContentIdea.created_at.desc()).limit(50).all()


@router.get("/content", response_model=list[ContentOut])
def list_content(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID | None = None,
    status: str | None = None,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> list[ContentItem]:
    q = (
        db.query(ContentItem)
        .options(joinedload(ContentItem.versions))
        .filter(ContentItem.organization_id == membership.organization_id)
    )
    if brand_id:
        q = q.filter(ContentItem.brand_id == brand_id)
    if status:
        q = q.filter(ContentItem.status == status)
    return q.order_by(ContentItem.updated_at.desc()).all()


@router.post("/content", response_model=ContentOut)
def create_content(
    payload: ContentCreate,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator)),
) -> ContentItem:
    _get_brand(db, membership, payload.brand_id)
    item = ContentItem(
        organization_id=membership.organization_id,
        brand_id=payload.brand_id,
        created_by=user.id,
        title=payload.title,
        objective=payload.objective,
        topic=payload.topic,
        master_concept=payload.master_concept,
        status=payload.status or ContentStatus.draft.value,
    )
    db.add(item)
    db.flush()
    for v in payload.versions:
        db.add(ContentVersion(content_item_id=item.id, **v.model_dump()))
    db.commit()
    return (
        db.query(ContentItem)
        .options(joinedload(ContentItem.versions))
        .filter(ContentItem.id == item.id)
        .one()
    )


@router.get("/content/{content_id}", response_model=ContentOut)
def get_content(
    content_id: UUID,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> ContentItem:
    item = (
        db.query(ContentItem)
        .options(joinedload(ContentItem.versions))
        .filter(ContentItem.id == content_id, ContentItem.organization_id == membership.organization_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    return item


@router.patch("/content/{content_id}", response_model=ContentOut)
def update_content(
    content_id: UUID,
    payload: ContentUpdate,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator, Role.reviewer, Role.approver)),
) -> ContentItem:
    item = (
        db.query(ContentItem)
        .options(joinedload(ContentItem.versions))
        .filter(ContentItem.id == content_id, ContentItem.organization_id == membership.organization_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.post("/content/{content_id}/versions", response_model=ContentVersionOut)
def add_version(
    content_id: UUID,
    payload: ContentVersionIn,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator)),
) -> ContentVersion:
    item = db.get(ContentItem, content_id)
    if not item or item.organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Content not found")
    version = ContentVersion(content_item_id=item.id, **payload.model_dump())
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


@router.get("/assets", response_model=list[MediaAssetOut])
def list_assets(
    user: CurrentUser,
    db: DbDep,
    brand_id: UUID | None = None,
    membership: OrganizationMember = Depends(require_roles(*Role)),
) -> list[MediaAsset]:
    q = db.query(MediaAsset).filter(MediaAsset.organization_id == membership.organization_id)
    if brand_id:
        q = q.filter(MediaAsset.brand_id == brand_id)
    return q.order_by(MediaAsset.created_at.desc()).all()


@router.post("/assets", response_model=MediaAssetOut)
def create_asset(
    payload: MediaAssetCreate,
    user: CurrentUser,
    db: DbDep,
    membership: OrganizationMember = Depends(require_roles(Role.admin, Role.creator)),
) -> MediaAsset:
    if payload.brand_id:
        _get_brand(db, membership, payload.brand_id)
    asset = MediaAsset(
        organization_id=membership.organization_id,
        brand_id=payload.brand_id,
        name=payload.name,
        asset_type=payload.asset_type,
        url_or_path=payload.url_or_path,
        prompt=payload.prompt,
        tags=payload.tags,
        created_by=user.id,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset
