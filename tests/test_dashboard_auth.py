from packages.api.auth import _allowed
from packages.auth.service import _hash, oauth_authorize_url


def test_rbac_role_levels() -> None:
    assert _allowed("OWNER", "ADMIN")
    assert _allowed("ADMIN", "OPERATOR")
    assert _allowed("OPERATOR", "VIEWER")
    assert not _allowed("VIEWER", "OPERATOR")


def test_oauth_state_is_one_way_hash() -> None:
    value = "state-example"
    assert len(_hash(value)) == 64
    assert _hash(value) != value


def test_oauth_authorize_url_contains_required_parameters(monkeypatch) -> None:
    monkeypatch.setenv("DISCORD_APPLICATION_ID", "123456")
    monkeypatch.setenv("OAUTH_REDIRECT_URI", "https://example.test/callback")
    url = oauth_authorize_url("state123")
    assert "response_type=code" in url
    assert "client_id=123456" in url
    assert "scope=identify+guilds" in url
    assert "state=state123" in url
