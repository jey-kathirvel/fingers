from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analytics, auth, brands, health, organizations, users
from app.core.config import get_settings
from app.services.bootstrap import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # In production, prefer Alembic migrations; create_all + seed keeps Phase 1 bootable.
    try:
        init_db()
    except Exception as exc:  # noqa: BLE001
        # Allow API process to start for /health even if DB is temporarily unavailable.
        print(f"[fingers] bootstrap warning: {exc}")
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = settings.api_prefix
app.include_router(health.router, prefix=api)
app.include_router(auth.router, prefix=api)
app.include_router(users.router, prefix=api)
app.include_router(organizations.router, prefix=api)
app.include_router(brands.router, prefix=api)
app.include_router(analytics.router, prefix=api)


@app.get("/")
def root() -> dict:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": f"{api}/health",
    }
