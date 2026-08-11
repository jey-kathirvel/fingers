from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import Role


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(ORMModel):
    id: UUID
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")


class OrganizationOut(ORMModel):
    id: UUID
    name: str
    slug: str
    created_at: datetime


class MembershipOut(ORMModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    role: Role
    organization: OrganizationOut | None = None


class BrandCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    website: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    tone_of_voice: str | None = None
    target_audience: str | None = None


class BrandUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    website: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    tone_of_voice: str | None = None
    target_audience: str | None = None
    is_active: bool | None = None


class BrandOut(ORMModel):
    id: UUID
    organization_id: UUID
    name: str
    slug: str
    description: str | None
    website: str | None
    logo_url: str | None
    primary_color: str | None
    tone_of_voice: str | None
    target_audience: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DashboardOverview(BaseModel):
    followers: int = 0
    reach: int = 0
    impressions: int = 0
    engagement_rate: float = 0.0
    clicks: int = 0
    leads: int = 0
    published_posts: int = 0
    response_backlog: int = 0
    brands_count: int = 0
    connected_accounts: int = 0
    failed_posts: int = 0
    scheduled_posts: int = 0
    approval_items: int = 0
    draft_count: int = 0
    integration_health: list[dict] = Field(default_factory=list)
    action_queue: list[dict] = Field(default_factory=list)
    recommendations: list[dict] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    database: str
    redis: str
    ai_provider: str = "local"
    timestamp: datetime


class ContentVersionIn(BaseModel):
    platform: str
    format: str | None = None
    headline: str | None = None
    body: str | None = None
    hashtags: str | None = None
    cta: str | None = None
    image_prompt: str | None = None
    video_script: str | None = None
    score_clarity: int | None = None
    score_brand_fit: int | None = None
    score_cta: int | None = None
    score_platform_fit: int | None = None


class ContentVersionOut(ContentVersionIn, ORMModel):
    id: UUID
    content_item_id: UUID
    created_at: datetime


class ContentCreate(BaseModel):
    brand_id: UUID
    title: str = Field(min_length=2, max_length=255)
    objective: str | None = None
    topic: str | None = None
    master_concept: str | None = None
    status: str = "draft"
    versions: list[ContentVersionIn] = Field(default_factory=list)


class ContentUpdate(BaseModel):
    title: str | None = None
    objective: str | None = None
    topic: str | None = None
    master_concept: str | None = None
    status: str | None = None


class ContentOut(ORMModel):
    id: UUID
    organization_id: UUID
    brand_id: UUID
    created_by: UUID | None
    title: str
    objective: str | None
    topic: str | None
    master_concept: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    versions: list[ContentVersionOut] = Field(default_factory=list)


class AIGenerateRequest(BaseModel):
    brand_id: UUID
    topic: str = Field(min_length=3)
    objective: str = "awareness"
    platforms: list[str] = Field(default_factory=lambda: ["linkedin", "instagram", "facebook"])
    save: bool = True


class AIRewriteRequest(BaseModel):
    brand_id: UUID
    platform: str = "linkedin"
    text: str = Field(min_length=1)
    instruction: str = "Make the hook stronger and CTA clearer"


class AIIdeasRequest(BaseModel):
    brand_id: UUID
    count: int = Field(default=5, ge=1, le=12)
    persist: bool = True


class ContentIdeaOut(ORMModel):
    id: UUID
    organization_id: UUID
    brand_id: UUID
    title: str
    format: str | None
    goal: str | None
    platforms: str | None
    confidence: str | None
    rationale: str | None
    created_at: datetime


class MediaAssetCreate(BaseModel):
    brand_id: UUID | None = None
    name: str = Field(min_length=2, max_length=255)
    asset_type: str = "image"
    url_or_path: str = Field(min_length=1, max_length=1000)
    prompt: str | None = None
    tags: str | None = None


class MediaAssetOut(ORMModel):
    id: UUID
    organization_id: UUID
    brand_id: UUID | None
    name: str
    asset_type: str
    url_or_path: str
    prompt: str | None
    tags: str | None
    created_by: UUID | None
    created_at: datetime


class SocialAccountCreate(BaseModel):
    brand_id: UUID
    platform: str = Field(pattern=r"^(linkedin|instagram|facebook)$")
    account_name: str = Field(min_length=2, max_length=255)
    external_account_id: str | None = None
    connection_mode: str = "simulation"
    access_token: str | None = None


class SocialAccountOut(ORMModel):
    id: UUID
    organization_id: UUID
    brand_id: UUID
    platform: str
    account_name: str
    external_account_id: str | None
    status: str
    connection_mode: str
    created_at: datetime
    updated_at: datetime


class SchedulePostRequest(BaseModel):
    content_item_id: UUID
    content_version_id: UUID
    social_account_id: UUID
    scheduled_for: datetime


class PublishNowRequest(BaseModel):
    content_item_id: UUID
    social_account_id: UUID
    content_version_id: UUID | None = None


class ScheduledPostOut(ORMModel):
    id: UUID
    organization_id: UUID
    brand_id: UUID
    content_item_id: UUID
    content_version_id: UUID
    social_account_id: UUID
    platform: str
    status: str
    scheduled_for: datetime
    attempt_count: int
    max_attempts: int
    last_error: str | None
    published_at: datetime | None
    external_post_id: str | None
    created_at: datetime
    updated_at: datetime


class PublishingLogOut(ORMModel):
    id: UUID
    organization_id: UUID
    scheduled_post_id: UUID | None
    content_item_id: UUID | None
    platform: str
    action: str
    status: str
    message: str | None
    external_post_id: str | None
    created_at: datetime


class CalendarItemOut(BaseModel):
    id: UUID
    title: str
    platform: str
    status: str
    scheduled_for: datetime
    content_item_id: UUID
    brand_id: UUID
    account_name: str | None = None


class AiReplyDraftOut(ORMModel):
    id: UUID
    organization_id: UUID
    interaction_id: UUID
    body: str
    tone: str | None
    provider: str
    status: str
    created_by: UUID | None
    external_reply_id: str | None
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime


class InteractionOut(ORMModel):
    id: UUID
    organization_id: UUID
    brand_id: UUID
    social_account_id: UUID | None
    platform: str
    interaction_type: str
    external_id: str
    author_name: str | None
    author_handle: str | None
    author_external_id: str | None
    body: str
    permalink: str | None
    sentiment: str
    intent: str
    priority: str
    lead_probability: int
    status: str
    assigned_to: UUID | None
    content_item_id: UUID | None
    scheduled_post_id: UUID | None
    parent_external_id: str | None
    received_at: datetime
    responded_at: datetime | None
    created_at: datetime
    updated_at: datetime
    drafts: list[AiReplyDraftOut] = Field(default_factory=list)


class InteractionUpdate(BaseModel):
    status: str | None = None
    priority: str | None = None
    sentiment: str | None = None
    intent: str | None = None
    assigned_to: UUID | None = None


class ReplyDraftRequest(BaseModel):
    tone: str = "helpful"
    instruction: str | None = None


class ApproveSendRequest(BaseModel):
    draft_id: UUID | None = None
    body: str | None = None


class InboxStatsOut(BaseModel):
    total: int
    new_count: int
    draft_reply_count: int
    responded_count: int
    high_priority: int
    backlog: int


class AnalyticsSyncOut(BaseModel):
    post_metrics: int
    account_metrics: int


class AccountMetricTrendOut(BaseModel):
    date: str
    followers: int
    reach: int
    impressions: int
    clicks: int
    likes: int
    comments: int
    shares: int
    leads: int
    engagement_rate: float


class PlatformBreakdownOut(BaseModel):
    platform: str
    followers: int
    reach: int
    impressions: int
    clicks: int
    likes: int
    comments: int
    leads: int
    engagement_rate: float


class PostMetricOut(BaseModel):
    id: str
    platform: str
    title: str | None = None
    content_item_id: str | None = None
    scheduled_post_id: str | None = None
    impressions: int
    reach: int
    likes: int
    comments: int
    shares: int
    saves: int
    clicks: int
    video_views: int
    engagement_rate: float
    measured_at: str


class CampaignCreate(BaseModel):
    brand_id: UUID
    name: str = Field(min_length=2, max_length=255)
    objective: str | None = None
    platforms: list[str] = Field(default_factory=list)
    status: str = "draft"
    start_date: datetime | None = None
    end_date: datetime | None = None
    kpi_targets: str | None = None
    notes: str | None = None


class CampaignUpdate(BaseModel):
    name: str | None = None
    objective: str | None = None
    platforms: list[str] | None = None
    status: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    kpi_targets: str | None = None
    notes: str | None = None


class CampaignOut(ORMModel):
    id: UUID
    organization_id: UUID
    brand_id: UUID
    name: str
    objective: str | None
    platforms: str | None
    status: str
    start_date: datetime | None
    end_date: datetime | None
    kpi_targets: str | None
    notes: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    content_item_ids: list[UUID] = Field(default_factory=list)


class CampaignLinkContentRequest(BaseModel):
    content_item_id: UUID


class LeadCreate(BaseModel):
    brand_id: UUID
    name: str = Field(min_length=1, max_length=255)
    source_platform: str | None = None
    interaction_id: UUID | None = None
    content_item_id: UUID | None = None
    campaign_id: UUID | None = None
    intent: str | None = None
    score: int = 0
    status: str = "new"
    product_interest: str | None = None
    follow_up_at: datetime | None = None
    source_message: str | None = None
    notes: str | None = None


class LeadUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    score: int | None = None
    intent: str | None = None
    product_interest: str | None = None
    campaign_id: UUID | None = None
    follow_up_at: datetime | None = None
    notes: str | None = None
    owner_id: UUID | None = None


class LeadOut(ORMModel):
    id: UUID
    organization_id: UUID
    brand_id: UUID
    name: str
    source_platform: str | None
    social_account_id: UUID | None
    interaction_id: UUID | None
    content_item_id: UUID | None
    campaign_id: UUID | None
    intent: str | None
    score: int
    status: str
    product_interest: str | None
    owner_id: UUID | None
    follow_up_at: datetime | None
    source_message: str | None
    notes: str | None
    status_history: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class LeadPipelineOut(BaseModel):
    total: int
    by_status: dict[str, int]
    converted: int
    open_count: int
    avg_score: float


class ConvertLeadRequest(BaseModel):
    campaign_id: UUID | None = None
    product_interest: str | None = None
    notes: str | None = None
