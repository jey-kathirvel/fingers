from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.rbac import MemberRole
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import Brand, BrandGuideline, Organization, OrganizationMember, User
from app.core.utils import slugify


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_defaults(db)
    finally:
        db.close()


def seed_defaults(db: Session) -> None:
    settings = get_settings()
    user = db.query(User).filter(User.email == settings.initial_admin_email).first()
    if user is None:
        user = User(
            email=settings.initial_admin_email,
            full_name=settings.initial_admin_name,
            hashed_password=hash_password(settings.initial_admin_password),
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        db.flush()

    org = db.query(Organization).filter(Organization.slug == slugify(settings.initial_org_name)).first()
    if org is None:
        org = Organization(
            name=settings.initial_org_name,
            slug=slugify(settings.initial_org_name),
            description="Default organization for Fingers Phase 1",
        )
        db.add(org)
        db.flush()

    membership = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.organization_id == org.id, OrganizationMember.user_id == user.id)
        .first()
    )
    if membership is None:
        membership = OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            role=MemberRole.ADMIN.value,
            is_default=True,
        )
        db.add(membership)

    brand = (
        db.query(Brand)
        .filter(Brand.organization_id == org.id, Brand.slug == slugify(settings.initial_brand_name))
        .first()
    )
    if brand is None:
        brand = Brand(
            organization_id=org.id,
            name=settings.initial_brand_name,
            slug=slugify(settings.initial_brand_name),
            description="Seed brand for dashboard and workflow testing",
            website="https://fingers.ads-ai.in",
            primary_color="#0F6B5C",
            tone_of_voice="Clear, confident, practical",
            target_audience="Multi-brand social and growth teams",
            default_cta="Learn more",
            created_by=user.id,
        )
        db.add(brand)
        db.flush()
        db.add(
            BrandGuideline(
                brand_id=brand.id,
                approved_keywords="social,campaign,irrigation,engagement",
                restricted_words="guaranteed results,best in world",
                competitors="Hootsuite,Buffer,Sprout Social",
                visual_style="Clean product photography, soft gradients, strong brand mark",
                notes="Phase 1 seed guidelines",
            )
        )

    db.commit()


def get_default_context(db: Session, user: User):
    membership = (
        db.query(OrganizationMember)
        .options(joinedload(OrganizationMember.organization))
        .filter(OrganizationMember.user_id == user.id)
        .order_by(OrganizationMember.is_default.desc(), OrganizationMember.created_at.asc())
        .first()
    )
    brand = None
    if membership:
        brand = (
            db.query(Brand)
            .options(joinedload(Brand.guidelines))
            .filter(Brand.organization_id == membership.organization_id, Brand.is_active.is_(True))
            .order_by(Brand.created_at.asc())
            .first()
        )
    return membership, brand
