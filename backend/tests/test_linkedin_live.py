"""LinkedIn live adapter unit tests."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.social.linkedin import compose_post_text, normalize_author_urn, publish_live


def test_normalize_author_urn() -> None:
    assert normalize_author_urn("abc123") == "urn:li:person:abc123"
    assert normalize_author_urn("urn:li:person:abc123") == "urn:li:person:abc123"
    assert normalize_author_urn("urn:li:organization:99") == "urn:li:organization:99"


def test_compose_post_text() -> None:
    version = SimpleNamespace(headline="Hook", body="Body copy", hashtags="#irrigation", cta="Learn more")
    text = compose_post_text(version)  # type: ignore[arg-type]
    assert "Hook" in text and "Body copy" in text and "#irrigation" in text


def test_publish_live_success() -> None:
    account = SimpleNamespace(
        access_token="tok",
        external_account_id="urn:li:person:42",
        account_name="Tester",
    )
    version = SimpleNamespace(headline=None, body="Hello LinkedIn", hashtags=None, cta=None)
    response = MagicMock()
    response.status_code = 201
    response.headers = {"x-restli-id": "urn:li:share:999"}
    response.text = ""
    response.json.return_value = {}

    with patch("app.social.linkedin.httpx.Client") as client_cls:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = False
        client.post.return_value = response
        client_cls.return_value = client
        result = publish_live(account, version)  # type: ignore[arg-type]

    assert result.ok is True
    assert result.simulated is False
    assert result.external_post_id == "urn:li:share:999"


def test_publish_live_requires_token() -> None:
    account = SimpleNamespace(access_token=None, external_account_id="urn:li:person:1")
    version = SimpleNamespace(headline=None, body="x", hashtags=None, cta=None)
    result = publish_live(account, version)  # type: ignore[arg-type]
    assert result.ok is False
