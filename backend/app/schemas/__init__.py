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
