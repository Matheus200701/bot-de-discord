from fastapi import APIRouter, Header, HTTPException, Request
from hashlib import sha256
from typing import Callable, Awaitable

router = APIRouter(prefix="/webhooks/payments", tags=["webhooks"])

# Provider adapters must perform provider-specific signature verification.
# This boundary deliberately does not trust payload fields as payment truth.

@router.post("/{provider}", status_code=202)
async def payment_webhook(
    provider: str,
    request: Request,
    x_signature: str | None = Header(default=None),
    x_timestamp: str | None = Header(default=None),
    x_event_id: str | None = Header(default=None),
):
    raw = await request.body()
    if not x_event_id or not x_timestamp or not x_signature:
        raise HTTPException(400, "missing_webhook_security_headers")
    if len(raw) > 2_000_000:
        raise HTTPException(413, "payload_too_large")
    fingerprint = sha256(raw).hexdigest()
    # Persist provider event id with a UNIQUE constraint before dispatching.
    # A real provider adapter is responsible for cryptographic verification.
    return {"accepted": True, "provider": provider, "event_id": x_event_id, "fingerprint": fingerprint}
