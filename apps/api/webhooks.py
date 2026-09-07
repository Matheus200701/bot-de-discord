from __future__ import annotations

import json
from hashlib import sha256
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import select

from packages.commerce.services import CommerceError, transition_order
from packages.database.models import Order, PaymentEvent, PaymentIntentRecord
from packages.database.session import SessionFactory
from packages.payments.mercadopago import MercadoPagoPixProvider

router = APIRouter(prefix="/webhooks/payments", tags=["webhooks"])


@router.post("/mercadopago_pix", status_code=202)
async def mercado_pago_webhook(
    request: Request,
    x_signature: str | None = Header(default=None),
    x_request_id: str | None = Header(default=None),
) -> dict[str, object]:
    raw = await request.body()
    if len(raw) > 2_000_000:
        raise HTTPException(413, "payload_too_large")
    data_id = request.query_params.get("data.id", "")
    if not x_signature or not x_request_id or not data_id:
        raise HTTPException(400, "missing_webhook_security_headers")

    provider = MercadoPagoPixProvider()
    headers = {
        "x-signature": x_signature,
        "x-request-id": x_request_id,
        "x-data-id": data_id,
    }
    if not await provider.validate_webhook(headers, raw):
        raise HTTPException(401, "invalid_webhook_signature")

    try:
        body = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "invalid_json") from exc

    provider_event_id = str(body.get("id") or f"{x_request_id}:{data_id}")
    async with SessionFactory() as session:
        async with session.begin():
            existing = await session.scalar(
                select(PaymentEvent).where(PaymentEvent.provider_event_id == provider_event_id).with_for_update()
            )
            if existing is not None:
                return {"accepted": True, "duplicate": True, "event_id": provider_event_id}

            event = PaymentEvent(
                provider="mercadopago_pix",
                provider_event_id=provider_event_id,
                event_type=str(body.get("type") or body.get("action") or "unknown"),
                payload=body,
            )
            session.add(event)
            await session.flush()

            if body.get("type") != "payment":
                return {"accepted": True, "event_id": provider_event_id}

            remote = await provider.get_payment(data_id)
            payment = await session.scalar(
                select(PaymentIntentRecord)
                .where(
                    PaymentIntentRecord.provider == provider.name,
                    PaymentIntentRecord.provider_payment_id == remote.provider_payment_id,
                )
                .with_for_update()
            )
            if payment is None:
                return {"accepted": True, "event_id": provider_event_id, "ignored": "unknown_payment"}
            if remote.amount_minor != payment.amount_minor or remote.currency != payment.currency:
                raise HTTPException(409, "payment_amount_mismatch")

            payment.status = remote.status
            if remote.status == "approved":
                order = await session.scalar(
                    select(Order).where(Order.id == payment.order_id, Order.tenant_id == payment.tenant_id).with_for_update()
                )
                if order is not None and order.status == "PAYMENT_PENDING":
                    await transition_order(session, payment.order_id, payment.tenant_id, "PAID")
            elif remote.status in {"cancelled", "rejected", "expired"}:
                order = await session.scalar(
                    select(Order).where(Order.id == payment.order_id, Order.tenant_id == payment.tenant_id).with_for_update()
                )
                if order is not None and order.status == "PAYMENT_PENDING":
                    target = "EXPIRED" if remote.status == "expired" else "CANCELLED"
                    await transition_order(session, payment.order_id, payment.tenant_id, target)

    return {"accepted": True, "event_id": provider_event_id, "fingerprint": sha256(raw).hexdigest()}


@router.post("/{provider}", status_code=202)
async def unsupported_provider_webhook(provider: str, request: Request) -> dict[str, object]:
    # Generic boundary kept for providers that are not yet implemented. It does
    # not accept payment truth; production adapters must provide verification.
    raw = await request.body()
    if len(raw) > 2_000_000:
        raise HTTPException(413, "payload_too_large")
    raise HTTPException(501, f"payment_provider_not_implemented:{provider}")
