from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Fingers"
    app_version: str = "0.1.0"
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

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
