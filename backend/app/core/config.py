from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Fingers"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_prefix: str = "/api"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 12
    algorithm: str = "HS256"

    database_url: str = "postgresql+psycopg://fingers_user:fingers_pass@localhost:5432/fingers_db"
    redis_url: str = "redis://localhost:6379/0"

    cors_origins: str = "http://localhost:3090,https://fingers.ads-ai.in"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8090

    initial_admin_email: str = "admin@ads-ai.in"
    initial_admin_password: str = "ChangeMe123!"
    initial_admin_name: str = "Fingers Admin"
    initial_org_name: str = "Ads AI"
    initial_brand_name: str = "Fingers Demo"

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
