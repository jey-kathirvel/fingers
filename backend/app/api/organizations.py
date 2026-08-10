from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.utils import slugify
from app.db.session import get_db
from app.models import AuditLog, Organization, OrganizationMember, User
from app.schemas import OrganizationCreate, OrganizationOut, OrganizationUpdate

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("", response_model=list[OrganizationOut])
def list_organizations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Organization]:
    if user.is_superuser:
        return db.query(Organization).order_by(Organization.name.asc()).all()
    return (
        db.query(Organization)
        .join(OrganizationMember)
        .filter(OrganizationMember.user_id == user.id)
        .order_by(Organization.name.asc())
        .all()
    )


@router.post("", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Organization:
    slug = slugify(payload.slug or payload.name)
    if db.query(Organization).filter(Organization.slug == slug).first():
        raise HTTPException(status_code=400, detail="Organization slug already exists")
    org = Organization(name=payload.name, slug=slug, description=payload.description)
    db.add(org)
    db.flush()
    db.add(
        OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            role="admin",
            is_default=True,
        )
    )
    db.add(
        AuditLog(
            actor_user_id=user.id,
            organization_id=org.id,
            action="organization.create",
            entity_type="organization",
            entity_id=org.id,
            details=org.name,
        )
    )
    db.commit()
    db.refresh(org)
    return org


@router.patch("/{organization_id}", response_model=OrganizationOut)
def update_organization(
    organization_id: str,
    payload: OrganizationUpdate,
    membership: OrganizationMember = Depends(require_permission("org:manage")),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Organization:
    org = db.get(Organization, organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if membership.organization_id != organization_id and not user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(org, key, value)
    db.add(
        AuditLog(
            actor_user_id=user.id,
            organization_id=org.id,
            action="organization.update",
            entity_type="organization",
            entity_id=org.id,
        )
    )
    db.commit()
    db.refresh(org)
    return org
