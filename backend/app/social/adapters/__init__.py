"""Social platform adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from app.models import ContentVersion, SocialAccount


@dataclass
class PublishResult:
    ok: bool
    external_post_id: str | None = None
    message: str = ""
    simulated: bool = True


class SocialAdapter(Protocol):
    platform: str

    def publish(self, account: SocialAccount, version: ContentVersion) -> PublishResult: ...


class SimulationAdapter:
    def __init__(self, platform: str):
        self.platform = platform

    def publish(self, account: SocialAccount, version: ContentVersion) -> PublishResult:
        external_id = f"sim_{self.platform}_{uuid4().hex[:12]}"
        preview = (version.body or version.headline or "")[:80]
        return PublishResult(
            ok=True,
            external_post_id=external_id,
            message=f"Simulated {self.platform} publish for @{account.account_name}: {preview}",
            simulated=True,
        )


class MetaAdapter:
    platform = "meta"

    def __init__(self, target: str = "facebook"):
        self.target = target
        self.platform = target

    def publish(self, account: SocialAccount, version: ContentVersion) -> PublishResult:
        # Live Graph API publishing requires META credentials + page token.
        # Phase 3 uses simulation until live OAuth tokens are connected.
        if account.connection_mode != "live" or not account.access_token:
            return SimulationAdapter(self.platform).publish(account, version)
        return PublishResult(
            ok=False,
            message="Live Meta publishing is configured but not fully enabled in Phase 3 yet.",
            simulated=False,
        )


class LinkedInAdapter:
    platform = "linkedin"

    def publish(self, account: SocialAccount, version: ContentVersion) -> PublishResult:
        if account.connection_mode != "live" or not account.access_token:
            return SimulationAdapter(self.platform).publish(account, version)
        return PublishResult(
            ok=False,
            message="Live LinkedIn publishing is configured but not fully enabled in Phase 3 yet.",
            simulated=False,
        )


def get_adapter(platform: str) -> SocialAdapter:
    platform = platform.lower()
    if platform in {"facebook", "instagram"}:
        return MetaAdapter(target=platform)
    if platform == "linkedin":
        return LinkedInAdapter()
    return SimulationAdapter(platform)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
