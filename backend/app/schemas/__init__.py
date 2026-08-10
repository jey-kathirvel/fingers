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
    timestamp: datetime
