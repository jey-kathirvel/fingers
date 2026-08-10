from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_membership
from app.core.utils import slugify
from app.db.session import get_db
from app.models import AuditLog, Brand, BrandGuideline, OrganizationMember, User
from app.schemas import BrandCreate, BrandOut, BrandUpdate

router = APIRouter(prefix="/brands", tags=["brands"])


@router.get("", response_model=list[BrandOut])
def list_brands(
    organization_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Brand]:
    membership = get_membership(organization_id=organization_id, user=user, db=db)
    if not membership and not user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    return (
        db.query(Brand)
        .options(joinedload(Brand.guidelines))
        .filter(Brand.organization_id == organization_id)
        .order_by(Brand.name.asc())
        .all()
    )


@router.post("", response_model=BrandOut, status_code=status.HTTP_201_CREATED)
def create_brand(
    payload: BrandCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Brand:
    membership = get_membership(organization_id=payload.organization_id, user=user, db=db)
    if not user.is_superuser and membership.role not in {"admin"}:
        # brand:manage required
        from app.core.rbac import role_has_permission

        if not role_has_permission(membership.role, "brand:manage"):
            raise HTTPException(status_code=403, detail="Insufficient permissions")

    slug = slugify(payload.slug or payload.name)
    exists = (
        db.query(Brand)
        .filter(Brand.organization_id == payload.organization_id, Brand.slug == slug)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="Brand slug already exists in organization")

    brand = Brand(
        organization_id=payload.organization_id,
        name=payload.name,
        slug=slug,
        description=payload.description,
        website=payload.website,
        logo_url=payload.logo_url,
        primary_color=payload.primary_color,
        tone_of_voice=payload.tone_of_voice,
        target_audience=payload.target_audience,
        default_cta=payload.default_cta,
        created_by=user.id,
    )
    db.add(brand)
    db.flush()
    if payload.guidelines:
        db.add(BrandGuideline(brand_id=brand.id, **payload.guidelines.model_dump()))
    db.add(
        AuditLog(
            actor_user_id=user.id,
            organization_id=payload.organization_id,
            brand_id=brand.id,
            action="brand.create",
            entity_type="brand",
            entity_id=brand.id,
            details=brand.name,
        )
    )
    db.commit()
    brand = (
        db.query(Brand)
        .options(joinedload(Brand.guidelines))
        .filter(Brand.id == brand.id)
        .one()
    )
    return brand


@router.get("/{brand_id}", response_model=BrandOut)
def get_brand(
    brand_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Brand:
    brand = (
        db.query(Brand)
        .options(joinedload(Brand.guidelines))
        .filter(Brand.id == brand_id)
        .first()
    )
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    get_membership(organization_id=brand.organization_id, user=user, db=db)
    return brand


@router.patch("/{brand_id}", response_model=BrandOut)
def update_brand(
    brand_id: str,
    payload: BrandUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Brand:
    brand = (
        db.query(Brand)
        .options(joinedload(Brand.guidelines))
        .filter(Brand.id == brand_id)
        .first()
    )
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    membership = get_membership(organization_id=brand.organization_id, user=user, db=db)
    from app.core.rbac import role_has_permission

    if not user.is_superuser and not role_has_permission(membership.role, "brand:manage"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    data = payload.model_dump(exclude_unset=True)
    guidelines_data = data.pop("guidelines", None)
    for key, value in data.items():
        setattr(brand, key, value)

    if guidelines_data is not None:
        if brand.guidelines is None:
            brand.guidelines = BrandGuideline(brand_id=brand.id)
        for key, value in guidelines_data.items():
            setattr(brand.guidelines, key, value)

    db.add(
        AuditLog(
            actor_user_id=user.id,
            organization_id=brand.organization_id,
            brand_id=brand.id,
            action="brand.update",
            entity_type="brand",
            entity_id=brand.id,
        )
    )
    db.commit()
    db.refresh(brand)
    return brand
