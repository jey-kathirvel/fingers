from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas import HealthDependency, HealthOut

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health", response_model=HealthOut)
def health(db: Session = Depends(get_db)) -> HealthOut:
    dependencies: list[HealthDependency] = []
    status = "ok"

    try:
        db.execute(text("SELECT 1"))
        dependencies.append(HealthDependency(name="postgresql", status="ok"))
    except Exception as exc:  # noqa: BLE001
        status = "degraded"
        dependencies.append(HealthDependency(name="postgresql", status="error", detail=str(exc)))

    try:
        import redis

        client = redis.from_url(settings.redis_url)
        client.ping()
        dependencies.append(HealthDependency(name="redis", status="ok"))
    except Exception as exc:  # noqa: BLE001
        # Redis is optional in early Phase 1 foundation.
        dependencies.append(HealthDependency(name="redis", status="degraded", detail=str(exc)))

    return HealthOut(
        status=status,
        version=settings.app_version,
        environment=settings.environment,
        dependencies=dependencies,
    )


@router.get("/version")
def version() -> dict:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }
