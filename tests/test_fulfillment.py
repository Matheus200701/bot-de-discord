from packages.delivery.service import _int_or_none, _string_or_none


def test_delivery_metadata_helpers() -> None:
    assert _int_or_none("123456") == 123456
    assert _int_or_none("0") is None
    assert _int_or_none("not-a-snowflake") is None
    assert _string_or_none("  https://example.test/file.zip  ") == "https://example.test/file.zip"
    assert _string_or_none("   ") is None


def test_supported_delivery_types_are_explicit() -> None:
    supported = {"discord_role", "digital_link"}
    assert "discord_role" in supported
    assert "digital_link" in supported
    assert "secret_text" not in supported
