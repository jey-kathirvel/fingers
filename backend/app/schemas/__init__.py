from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.rbac import MemberRole


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=200)
    password: str = Field(min_length=8, max_length=128)


class UserOut(ORMModel):
    id: str
    email: EmailStr
    full_name: str
    is_active: bool
    is_superuser: bool
    created_at: datetime


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: Optional[str] = Field(default=None, max_length=120)
    description: Optional[str] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = None


class OrganizationOut(ORMModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    created_at: datetime


class BrandGuidelineIn(BaseModel):
    approved_keywords: Optional[str] = None
    restricted_words: Optional[str] = None
    competitors: Optional[str] = None
    visual_style: Optional[str] = None
    notes: Optional[str] = None


class BrandCreate(BaseModel):
    organization_id: str
    name: str = Field(min_length=2, max_length=200)
    slug: Optional[str] = Field(default=None, max_length=120)
    description: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    tone_of_voice: Optional[str] = None
    target_audience: Optional[str] = None
    default_cta: Optional[str] = None
    guidelines: Optional[BrandGuidelineIn] = None


class BrandUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    tone_of_voice: Optional[str] = None
    target_audience: Optional[str] = None
    default_cta: Optional[str] = None
    is_active: Optional[bool] = None
    guidelines: Optional[BrandGuidelineIn] = None


class BrandGuidelineOut(ORMModel):
    approved_keywords: Optional[str]
    restricted_words: Optional[str]
    competitors: Optional[str]
    visual_style: Optional[str]
    notes: Optional[str]


class BrandOut(ORMModel):
    id: str
    organization_id: str
    name: str
    slug: str
    description: Optional[str]
    website: Optional[str]
    logo_url: Optional[str]
    primary_color: Optional[str]
    tone_of_voice: Optional[str]
    target_audience: Optional[str]
    default_cta: Optional[str]
    is_active: bool
    created_at: datetime
    guidelines: Optional[BrandGuidelineOut] = None


class MembershipOut(ORMModel):
    id: str
    organization_id: str
    user_id: str
    role: MemberRole
    is_default: bool
    organization: Optional[OrganizationOut] = None


class ActiveContextOut(BaseModel):
    user: UserOut
    organization: Optional[OrganizationOut] = None
    brand: Optional[BrandOut] = None
    role: Optional[MemberRole] = None
    permissions: list[str] = []


class DashboardOverviewOut(BaseModel):
    followers: int = 0
    reach: int = 0
    impressions: int = 0
    engagement_rate: float = 0.0
    clicks: int = 0
    leads: int = 0
    published_posts: int = 0
    response_backlog: int = 0
    failed_posts: int = 0
    scheduled_posts: int = 0
    approval_items: int = 0
    integration_health: list[dict] = []
    ai_recommendations: list[str] = []


class HealthDependency(BaseModel):
    name: str
    status: str
    detail: Optional[str] = None


class HealthOut(BaseModel):
    status: str
    version: str
    environment: str
    dependencies: list[HealthDependency]
