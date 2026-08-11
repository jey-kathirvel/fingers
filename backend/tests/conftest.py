"""Shared test database for API tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Brand, Organization, OrganizationMember, Role, User

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="session", autouse=True)
def prepare_db():
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

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
            description="SME platform",
            tone_of_voice="practical",
            is_active=True,
        )
    )
    db.commit()
    db.close()
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    token = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "secret123"}).json()[
        "access_token"
    ]
    org_id = client.get("/api/organizations", headers={"Authorization": f"Bearer {token}"}).json()[0]["id"]
    brand_id = client.get(
        "/api/brands", headers={"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}
    ).json()[0]["id"]
    return {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}, brand_id
