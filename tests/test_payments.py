import hashlib
import hmac

import pytest

from packages.payments.mercadopago import MercadoPagoPixProvider


@pytest.mark.asyncio
async def test_mercado_pago_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "test-secret"
    provider = MercadoPagoPixProvider(access_token="token", webhook_secret=secret)
    ts = "1704908010"
    data_id = "999999"
    request_id = "req-123"
    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
    digest = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    assert await provider.validate_webhook(
        {
            "x-signature": f"ts={ts},v1={digest}",
            "x-request-id": request_id,
            "x-data-id": data_id,
        },
        b"{}",
    )


@pytest.mark.asyncio
async def test_mercado_pago_rejects_tampered_signature() -> None:
    provider = MercadoPagoPixProvider(access_token="token", webhook_secret="test-secret")
    assert not await provider.validate_webhook(
        {
            "x-signature": "ts=1704908010,v1=invalid",
            "x-request-id": "req-123",
            "x-data-id": "999999",
        },
        b"{}",
    )
