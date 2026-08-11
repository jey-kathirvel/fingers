from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.studio import router as studio_router
from app.api.publishing import router as publishing_router
from app.api.engagement import router as engagement_router
from app.api.analytics import router as analytics_router
from app.api.campaigns import router as campaigns_router
from app.api.advisor import router as advisor_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix=settings.api_prefix)
app.include_router(studio_router, prefix=settings.api_prefix)
app.include_router(publishing_router, prefix=settings.api_prefix)
app.include_router(engagement_router, prefix=settings.api_prefix)
app.include_router(analytics_router, prefix=settings.api_prefix)
app.include_router(campaigns_router, prefix=settings.api_prefix)
app.include_router(advisor_router, prefix=settings.api_prefix)


@app.get("/")
def root() -> dict:
    return {"app": settings.app_name, "docs": "/docs", "health": "/api/health"}
