"""Seed admin user, organization, and sample brands."""

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import Brand, BrandGuidelines, Organization, OrganizationMember, Role, User

settings = get_settings()


def seed(db: Session) -> None:
    user = db.query(User).filter(User.email == settings.seed_admin_email.lower()).first()
    if not user:
        user = User(
            email=settings.seed_admin_email.lower(),
            full_name=settings.seed_admin_name,
            hashed_password=hash_password(settings.seed_admin_password),
            is_active=True,
        )
        db.add(user)
        db.flush()

    org = db.query(Organization).filter(Organization.slug == "ads-ai").first()
    if not org:
        org = Organization(name="Ads AI", slug="ads-ai")
        db.add(org)
        db.flush()

    membership = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.organization_id == org.id, OrganizationMember.user_id == user.id)
        .first()
    )
    if not membership:
        db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role=Role.admin))

    samples = [
        {
            "name": "Fingers",
            "slug": "fingers",
            "description": "Social Media Engineering & Engagement platform",
            "website": "https://fingers.ads-ai.in",
            "primary_color": "#0F766E",
            "tone_of_voice": "Clear, confident, practical, operator-friendly",
            "target_audience": "Marketing teams and founders managing multi-brand social programs",
        },
        {
            "name": "Ads AI",
            "slug": "ads-ai",
            "description": "AI-powered growth systems",
            "website": "https://ads-ai.in",
            "primary_color": "#1D4ED8",
            "tone_of_voice": "Expert, concise, outcome-driven",
            "target_audience": "Businesses adopting AI for marketing and operations",
        },
    ]
    for sample in samples:
        brand = (
            db.query(Brand)
            .filter(Brand.organization_id == org.id, Brand.slug == sample["slug"])
            .first()
        )
        if not brand:
            brand = Brand(organization_id=org.id, **sample)
            db.add(brand)
            db.flush()
            db.add(BrandGuidelines(brand_id=brand.id, default_cta="Learn more"))
    db.commit()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
        print("Seed complete")
    finally:
        db.close()


if __name__ == "__main__":
    main()
