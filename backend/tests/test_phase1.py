"""API smoke tests for Phase 1 foundation."""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Brand, Organization, OrganizationMember, Role, User
from app.core.security import hash_password


engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def setup_module() -> None:
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    user = User(
        email="admin@example.com",
        full_name="Admin",
        hashed_password=hash_password("secret123"),
        is_active=True,
    )
    org = Organization(name="Ads AI", slug="ads-ai")
    db.add_all([user, org])
    db.flush()
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role=Role.admin))
    db.add(
        Brand(
            organization_id=org.id,
            name="Fingers",
            slug="fingers",
            description="Test brand",
            is_active=True,
        )
    )
    db.commit()
    db.close()


client = TestClient(app)


def test_health() -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["app"] == "Fingers"


def test_login_and_brands() -> None:
    login = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "secret123"})
    assert login.status_code == 200
    token = login.json()["access_token"]

    orgs = client.get("/api/organizations", headers={"Authorization": f"Bearer {token}"})
    assert orgs.status_code == 200
    org_id = orgs.json()[0]["id"]

    brands = client.get(
        "/api/brands",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Id": org_id},
    )
    assert brands.status_code == 200
    assert any(b["slug"] == "fingers" for b in brands.json())

    overview = client.get(
        "/api/analytics/overview",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Id": org_id},
    )
    assert overview.status_code == 200
    assert overview.json()["brands_count"] >= 1
