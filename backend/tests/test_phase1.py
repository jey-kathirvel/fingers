import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=True)
TEST_DB = ROOT / "storage" / "fingers_test.db"
TEST_DB.parent.mkdir(parents=True, exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{TEST_DB}"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["INITIAL_ADMIN_EMAIL"] = "admin@ads-ai.in"
os.environ["INITIAL_ADMIN_PASSWORD"] = "ChangeMe123!"

sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.core.rbac import MemberRole, role_has_permission  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.bootstrap import seed_defaults  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_defaults(db)
    finally:
        db.close()
    yield


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def auth_header(client: TestClient) -> dict[str, str]:
    res = client.post(
        "/api/auth/login",
        json={"email": "admin@ads-ai.in", "password": "ChangeMe123!"},
    )
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health(client: TestClient):
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["version"]
    assert body["status"] in {"ok", "degraded"}


def test_login_and_me(client: TestClient):
    headers = auth_header(client)
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    data = me.json()
    assert data["user"]["email"] == "admin@ads-ai.in"
    assert data["organization"]["name"]
    assert data["brand"]["name"]
    assert "brand:manage" in data["permissions"]


def test_brand_crud_and_tenant_scope(client: TestClient):
    headers = auth_header(client)
    orgs = client.get("/api/organizations", headers=headers).json()
    org_id = orgs[0]["id"]

    created = client.post(
        "/api/brands",
        headers=headers,
        json={
            "organization_id": org_id,
            "name": "Second Brand",
            "description": "Irrigation brand",
            "guidelines": {"approved_keywords": "irrigation,farmers"},
        },
    )
    assert created.status_code == 201, created.text
    brand = created.json()
    assert brand["name"] == "Second Brand"
    assert brand["guidelines"]["approved_keywords"] == "irrigation,farmers"

    listed = client.get(f"/api/brands?organization_id={org_id}", headers=headers)
    assert listed.status_code == 200
    names = {b["name"] for b in listed.json()}
    assert "Second Brand" in names

    updated = client.patch(
        f"/api/brands/{brand['id']}",
        headers=headers,
        json={"default_cta": "Book a demo"},
    )
    assert updated.status_code == 200
    assert updated.json()["default_cta"] == "Book a demo"


def test_dashboard_overview_requires_auth(client: TestClient):
    denied = client.get("/api/analytics/overview")
    assert denied.status_code == 401
    headers = auth_header(client)
    ok = client.get("/api/analytics/overview", headers=headers)
    assert ok.status_code == 200
    assert "ai_recommendations" in ok.json()


def test_rbac_matrix():
    assert role_has_permission(MemberRole.ADMIN, "org:manage")
    assert role_has_permission(MemberRole.CREATOR, "content:manage")
    assert not role_has_permission(MemberRole.ANALYST, "publish:manage")
