import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Role(str, enum.Enum):
    admin = "admin"
    creator = "creator"
    reviewer = "reviewer"
    approver = "approver"
    analyst = "analyst"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    memberships: Mapped[list["OrganizationMember"]] = relationship(back_populates="user")


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    members: Mapped[list["OrganizationMember"]] = relationship(back_populates="organization")
    brands: Mapped[list["Brand"]] = relationship(back_populates="organization")


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_org_user"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[Role] = mapped_column(Enum(Role, name="role_enum", native_enum=False), nullable=False, default=Role.creator)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization: Mapped[Organization] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="memberships")


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(String(255))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    primary_color: Mapped[str | None] = mapped_column(String(20))
    tone_of_voice: Mapped[str | None] = mapped_column(Text)
    target_audience: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped[Organization] = relationship(back_populates="brands")
    guidelines: Mapped["BrandGuidelines | None"] = relationship(back_populates="brand", uselist=False)

    __table_args__ = (UniqueConstraint("organization_id", "slug", name="uq_org_brand_slug"),)


class BrandGuidelines(Base):
    __tablename__ = "brand_guidelines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    products_services: Mapped[str | None] = mapped_column(Text)
    differentiators: Mapped[str | None] = mapped_column(Text)
    approved_keywords: Mapped[str | None] = mapped_column(Text)
    restricted_words: Mapped[str | None] = mapped_column(Text)
    competitors: Mapped[str | None] = mapped_column(Text)
    default_cta: Mapped[str | None] = mapped_column(Text)
    contact_destinations: Mapped[str | None] = mapped_column(Text)
    visual_style: Mapped[str | None] = mapped_column(Text)

    brand: Mapped[Brand] = relationship(back_populates="guidelines")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(100))
    entity_id: Mapped[str | None] = mapped_column(String(100))
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContentStatus(str, enum.Enum):
    draft = "draft"
    review = "review"
    approved = "approved"
    scheduled = "scheduled"
    published = "published"
    failed = "failed"


class Platform(str, enum.Enum):
    linkedin = "linkedin"
    instagram = "instagram"
    facebook = "facebook"
    x = "x"
    youtube = "youtube"


class ContentItem(Base):
    __tablename__ = "content_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str | None] = mapped_column(String(100))
    topic: Mapped[str | None] = mapped_column(Text)
    master_concept: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default=ContentStatus.draft.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    versions: Mapped[list["ContentVersion"]] = relationship(
        back_populates="content_item", cascade="all, delete-orphan"
    )


class ContentVersion(Base):
    __tablename__ = "content_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), index=True, nullable=False
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    format: Mapped[str | None] = mapped_column(String(64))
    headline: Mapped[str | None] = mapped_column(String(500))
    body: Mapped[str | None] = mapped_column(Text)
    hashtags: Mapped[str | None] = mapped_column(Text)
    cta: Mapped[str | None] = mapped_column(Text)
    image_prompt: Mapped[str | None] = mapped_column(Text)
    video_script: Mapped[str | None] = mapped_column(Text)
    score_clarity: Mapped[int | None] = mapped_column(Integer)
    score_brand_fit: Mapped[int | None] = mapped_column(Integer)
    score_cta: Mapped[int | None] = mapped_column(Integer)
    score_platform_fit: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    content_item: Mapped[ContentItem] = relationship(back_populates="versions")


class ContentIdea(Base):
    __tablename__ = "content_ideas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    format: Mapped[str | None] = mapped_column(String(64))
    goal: Mapped[str | None] = mapped_column(String(100))
    platforms: Mapped[str | None] = mapped_column(String(255))
    confidence: Mapped[str | None] = mapped_column(String(32))
    rationale: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    brand_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(64), default="image", nullable=False)
    url_or_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    prompt: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SocialAccount(Base):
    __tablename__ = "social_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), index=True, nullable=False
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_account_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="connected", nullable=False)
    connection_mode: Mapped[str] = mapped_column(String(32), default="simulation", nullable=False)
    access_token: Mapped[str | None] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), index=True, nullable=False
    )
    content_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_versions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    social_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("social_accounts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="scheduled", nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_post_id: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PublishingLog(Base):
    __tablename__ = "publishing_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    scheduled_post_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scheduled_posts.id", ondelete="SET NULL"), index=True
    )
    content_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    external_post_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
