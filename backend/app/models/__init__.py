import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
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


class SocialInteraction(Base):
    __tablename__ = "social_interactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), index=True, nullable=False
    )
    social_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("social_accounts.id", ondelete="SET NULL"), index=True
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    interaction_type: Mapped[str] = mapped_column(String(32), nullable=False)  # comment|message|mention|review
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    author_name: Mapped[str | None] = mapped_column(String(255))
    author_handle: Mapped[str | None] = mapped_column(String(255))
    author_external_id: Mapped[str | None] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    permalink: Mapped[str | None] = mapped_column(String(1000))
    sentiment: Mapped[str] = mapped_column(String(32), default="neutral", nullable=False)
    intent: Mapped[str] = mapped_column(String(64), default="other", nullable=False)
    priority: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)
    lead_probability: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="new", nullable=False)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    content_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    scheduled_post_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    parent_external_id: Mapped[str | None] = mapped_column(String(255))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    drafts: Mapped[list["AiReplyDraft"]] = relationship(
        back_populates="interaction", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "platform", "external_id", name="uq_interaction_external"),
    )


class AiReplyDraft(Base):
    __tablename__ = "ai_reply_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    interaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("social_interactions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    tone: Mapped[str | None] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(64), default="local", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="suggested", nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    external_reply_id: Mapped[str | None] = mapped_column(String(255))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    interaction: Mapped[SocialInteraction] = relationship(back_populates="drafts")


class AccountMetric(Base):
    __tablename__ = "account_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), index=True, nullable=False
    )
    social_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("social_accounts.id", ondelete="SET NULL"), index=True
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    metric_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    followers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reach: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    profile_visits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    website_clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shares: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    saves: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    video_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    leads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "brand_id",
            "platform",
            "social_account_id",
            "metric_date",
            name="uq_account_metric_day",
        ),
    )


class PostMetric(Base):
    __tablename__ = "post_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), index=True, nullable=False
    )
    content_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="SET NULL"), index=True
    )
    scheduled_post_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scheduled_posts.id", ondelete="SET NULL"), index=True
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reach: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shares: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    saves: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    video_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "scheduled_post_id", name="uq_post_metric_scheduled"),
    )


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str | None] = mapped_column(String(100))
    platforms: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    kpi_targets: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    content_links: Mapped[list["CampaignContent"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )


class CampaignContent(Base):
    __tablename__ = "campaign_contents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), index=True, nullable=False
    )
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    campaign: Mapped[Campaign] = relationship(back_populates="content_links")

    __table_args__ = (UniqueConstraint("campaign_id", "content_item_id", name="uq_campaign_content"),)


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_platform: Mapped[str | None] = mapped_column(String(32))
    social_account_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    interaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("social_interactions.id", ondelete="SET NULL"), index=True
    )
    content_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"), index=True
    )
    intent: Mapped[str | None] = mapped_column(String(64))
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="new", nullable=False)
    product_interest: Mapped[str | None] = mapped_column(String(255))
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_message: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    status_history: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AiRecommendation(Base):
    __tablename__ = "ai_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    evidence_json: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(64), default="rules", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AutomationRule(Base):
    __tablename__ = "automation_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_config_json: Mapped[str | None] = mapped_column(Text)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    action_config_json: Mapped[str | None] = mapped_column(Text)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    runs: Mapped[list["AutomationRun"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )


class AutomationRun(Base):
    __tablename__ = "automation_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("automation_rules.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="success", nullable=False)
    trigger_entity_type: Mapped[str | None] = mapped_column(String(64))
    trigger_entity_id: Mapped[str | None] = mapped_column(String(100))
    result_json: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    rule: Mapped[AutomationRule] = relationship(back_populates="runs")


class ListeningTerm(Base):
    __tablename__ = "listening_terms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), index=True, nullable=False
    )
    term: Mapped[str] = mapped_column(String(255), nullable=False)
    term_type: Mapped[str] = mapped_column(String(32), default="custom", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "brand_id", "term", name="uq_listening_term"),
    )


class SocialMention(Base):
    __tablename__ = "social_mentions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), index=True, nullable=False
    )
    term_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listening_terms.id", ondelete="SET NULL"), index=True
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    author_name: Mapped[str | None] = mapped_column(String(255))
    author_handle: Mapped[str | None] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    permalink: Mapped[str | None] = mapped_column(String(1000))
    sentiment: Mapped[str] = mapped_column(String(32), default="neutral", nullable=False)
    share_weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="simulation", nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    mentioned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("organization_id", "platform", "external_id", name="uq_mention_external"),
    )
