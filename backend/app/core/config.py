from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Fingers"
    app_version: str = "0.4.0"
    environment: str = "development"
    api_prefix: str = "/api"

    database_url: str = "postgresql+psycopg2://fingers_user:fingers_pass@127.0.0.1:5432/fingers_db"
    redis_url: str = "redis://127.0.0.1:6379/0"

    secret_key: str = "change-me-in-production-fingers-secret"
    access_token_expire_minutes: int = 60 * 12
    algorithm: str = "HS256"

    cors_origins: str = "http://localhost:3090,https://fingers.ads-ai.in"

    seed_admin_email: str = "admin@fingers.ads-ai.in"
    seed_admin_password: str = "FingersAdmin!2026"
    seed_admin_name: str = "Fingers Admin"

    # Provider priority: OpenRouter → OpenAI → local
    openrouter_api_key: str | None = None
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_site_url: str = "https://fingers.ads-ai.in"
    openrouter_app_name: str = "Fingers"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"

    # Optional Phase 3 social credentials (LinkedIn live enabled; Meta deferred)
    meta_app_id: str | None = None
    meta_app_secret: str | None = None
    linkedin_client_id: str | None = None
    linkedin_client_secret: str | None = None
    linkedin_redirect_uri: str = "https://fingers.ads-ai.in/api/integrations/linkedin/callback"
    linkedin_api_version: str = "202507"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_provider(self) -> str:
        if self.openrouter_api_key:
            return "openrouter"
        if self.openai_api_key:
            return "openai"
        return "local"

    @property
    def meta_configured(self) -> bool:
        return bool(self.meta_app_id and self.meta_app_secret)

    @property
    def linkedin_configured(self) -> bool:
        return bool(self.linkedin_client_id and self.linkedin_client_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()
