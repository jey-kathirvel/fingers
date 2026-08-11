"""LinkedIn live OAuth + Posts API helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
from jose import jwt

from app.core.config import Settings, get_settings
from app.models import ContentVersion, SocialAccount
from app.social.adapters import PublishResult

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
LINKEDIN_POSTS_URL = "https://api.linkedin.com/rest/posts"
DEFAULT_SCOPES = "openid profile w_member_social"
DEFAULT_API_VERSION = "202507"


@dataclass
class LinkedInTokenBundle:
    access_token: str
    expires_in: int | None
    refresh_token: str | None
    id_token: str | None
    scope: str | None


@dataclass
class LinkedInProfile:
    person_urn: str
    name: str | None
    email: str | None


def _settings(settings: Settings | None = None) -> Settings:
    return settings or get_settings()


def linkedin_redirect_uri(settings: Settings | None = None) -> str:
    cfg = _settings(settings)
    return (cfg.linkedin_redirect_uri or "https://fingers.ads-ai.in/api/integrations/linkedin/callback").rstrip("/")


def normalize_author_urn(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    if raw.startswith("urn:li:person:") or raw.startswith("urn:li:organization:"):
        return raw
    if raw.startswith("person:"):
        return f"urn:li:{raw}"
    if raw.startswith("organization:"):
        return f"urn:li:{raw}"
    # bare member id from OpenID `sub`
    return f"urn:li:person:{raw}"


def compose_post_text(version: ContentVersion) -> str:
    parts: list[str] = []
    if version.headline:
        parts.append(version.headline.strip())
    if version.body:
        parts.append(version.body.strip())
    if version.hashtags:
        tags = version.hashtags.strip()
        if tags:
            parts.append(tags if tags.startswith("#") else tags)
    if version.cta:
        parts.append(version.cta.strip())
    text = "\n\n".join(p for p in parts if p).strip()
    return text or "Shared via Fingers"


def build_oauth_state(
    *,
    organization_id: str,
    brand_id: str,
    user_id: str,
    settings: Settings | None = None,
) -> str:
    cfg = _settings(settings)
    payload = {
        "org": organization_id,
        "brand": brand_id,
        "user": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=20),
        "purpose": "linkedin_oauth",
    }
    return jwt.encode(payload, cfg.secret_key, algorithm=cfg.algorithm)


def parse_oauth_state(state: str, settings: Settings | None = None) -> dict[str, str]:
    cfg = _settings(settings)
    payload = jwt.decode(state, cfg.secret_key, algorithms=[cfg.algorithm])
    if payload.get("purpose") != "linkedin_oauth":
        raise ValueError("Invalid LinkedIn OAuth state")
    return {
        "organization_id": str(payload["org"]),
        "brand_id": str(payload["brand"]),
        "user_id": str(payload["user"]),
    }


def build_authorize_url(
    *,
    organization_id: str,
    brand_id: str,
    user_id: str,
    settings: Settings | None = None,
) -> dict[str, str]:
    cfg = _settings(settings)
    if not cfg.linkedin_client_id or not cfg.linkedin_client_secret:
        raise ValueError("LinkedIn app credentials are not configured")
    state = build_oauth_state(
        organization_id=organization_id,
        brand_id=brand_id,
        user_id=user_id,
        settings=cfg,
    )
    query = urlencode(
        {
            "response_type": "code",
            "client_id": cfg.linkedin_client_id,
            "redirect_uri": linkedin_redirect_uri(cfg),
            "state": state,
            "scope": DEFAULT_SCOPES,
        }
    )
    return {"authorize_url": f"{LINKEDIN_AUTH_URL}?{query}", "state": state, "scopes": DEFAULT_SCOPES}


def exchange_code_for_token(code: str, settings: Settings | None = None) -> LinkedInTokenBundle:
    cfg = _settings(settings)
    if not cfg.linkedin_client_id or not cfg.linkedin_client_secret:
        raise ValueError("LinkedIn app credentials are not configured")
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": linkedin_redirect_uri(cfg),
        "client_id": cfg.linkedin_client_id,
        "client_secret": cfg.linkedin_client_secret,
    }
    with httpx.Client(timeout=30.0) as client:
        res = client.post(
            LINKEDIN_TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if res.status_code >= 400:
        raise ValueError(f"LinkedIn token exchange failed ({res.status_code}): {res.text[:300]}")
    body = res.json()
    return LinkedInTokenBundle(
        access_token=body["access_token"],
        expires_in=body.get("expires_in"),
        refresh_token=body.get("refresh_token"),
        id_token=body.get("id_token"),
        scope=body.get("scope"),
    )


def fetch_profile(access_token: str) -> LinkedInProfile:
    with httpx.Client(timeout=30.0) as client:
        res = client.get(
            LINKEDIN_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if res.status_code >= 400:
        raise ValueError(f"LinkedIn profile fetch failed ({res.status_code}): {res.text[:300]}")
    body = res.json()
    sub = body.get("sub")
    if not sub:
        raise ValueError("LinkedIn profile response missing sub")
    name = body.get("name") or " ".join(
        p for p in [body.get("given_name"), body.get("family_name")] if p
    ).strip() or None
    return LinkedInProfile(
        person_urn=normalize_author_urn(str(sub)) or f"urn:li:person:{sub}",
        name=name,
        email=body.get("email"),
    )


def publish_live(account: SocialAccount, version: ContentVersion, settings: Settings | None = None) -> PublishResult:
    cfg = _settings(settings)
    if not account.access_token:
        return PublishResult(ok=False, message="LinkedIn live account is missing an access token", simulated=False)

    author = normalize_author_urn(account.external_account_id)
    if not author:
        return PublishResult(
            ok=False,
            message="LinkedIn live account needs a person/organization URN in external_account_id",
            simulated=False,
        )

    commentary = compose_post_text(version)
    headers = {
        "Authorization": f"Bearer {account.access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": cfg.linkedin_api_version or DEFAULT_API_VERSION,
    }
    payload: dict[str, Any] = {
        "author": author,
        "commentary": commentary,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            res = client.post(LINKEDIN_POSTS_URL, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        return PublishResult(ok=False, message=f"LinkedIn request error: {exc}", simulated=False)

    if res.status_code in {200, 201}:
        post_id = res.headers.get("x-restli-id") or res.headers.get("X-RestLi-Id")
        if not post_id:
            try:
                post_id = res.json().get("id")
            except Exception:  # noqa: BLE001
                post_id = None
        return PublishResult(
            ok=True,
            external_post_id=post_id or f"linkedin_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            message="Published to LinkedIn",
            simulated=False,
        )

    detail = res.text[:500]
    try:
        detail = json.dumps(res.json())[:500]
    except Exception:  # noqa: BLE001
        pass
    return PublishResult(
        ok=False,
        message=f"LinkedIn publish failed ({res.status_code}): {detail}",
        simulated=False,
    )
