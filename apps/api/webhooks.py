from __future__ import annotations

import json
from decimal import Decimal
from hashlib import sha256

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import select

from packages.commerce.services import transition_order
from packages.database.models import DisputeRecord, Order, PaymentEvent, PaymentIntentRecord
from packages.database.session import SessionFactory
from packages.payments.factory import PaymentProviderFactory
from packages.payments.mercadopago import MercadoPagoPixProvider
from packages.payments.finance import post_ledger_transaction
from packages.payments.reliability import enqueue_outbox, next_reconcile_time

router = APIRouter(prefix="/webhooks/payments", tags=["webhooks"])
payment_providers = PaymentProviderFactory()

async def _read_json(request: Request) -> tuple[bytes, dict]:
    raw = await request.body()
    if len(raw) > 2_000_000:
        raise HTTPException(413, "payload_too_large")
    try:
        return raw, json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "invalid_json") from exc

async def _verify_for_payment(request: Request, raw: bytes, payment: PaymentIntentRecord | None) -> MercadoPagoPixProvider:
    if payment is None:
        raise HTTPException(401, "unknown_payment_webhook")
    x_signature = request.headers.get("x-signature")
    x_request_id = request.headers.get("x-request-id")
    data_id = request.query_params.get("data.id", "")
    if not x_signature or not x_request_id or not data_id:
        raise HTTPException(400, "missing_webhook_security_headers")
    provider = await payment_providers.mercadopago_pix(payment.tenant_id)
    if not await provider.validate_webhook({"x-signature": x_signature, "x-request-id": x_request_id, "x-data-id": data_id}, raw):
        raise HTTPException(401, "invalid_webhook_signature")
    return provider

@router.post("/mercadopago_pix", status_code=202)
async def mercado_pago_webhook(request: Request, x_signature: str | None = Header(default=None), x_request_id: str | None = Header(default=None)) -> dict[str, object]:
    raw, body = await _read_json(request)
    data_id = request.query_params.get("data.id", "")
    if not x_signature or not x_request_id or not data_id:
        raise HTTPException(400, "missing_webhook_security_headers")
    async with SessionFactory() as session:
        payment = await session.scalar(select(PaymentIntentRecord).where(PaymentIntentRecord.provider == "mercadopago_pix", PaymentIntentRecord.provider_payment_id == data_id))
        provider = await _verify_for_payment(request, raw, payment)
        await session.rollback()
        provider_event_id = str(body.get("id") or f"{x_request_id}:{data_id}")
        async with session.begin():
            existing = await session.scalar(select(PaymentEvent).where(PaymentEvent.provider == provider.name, PaymentEvent.provider_event_id == provider_event_id).with_for_update())
            if existing is not None:
                return {"accepted": True, "duplicate": True, "event_id": provider_event_id}
            session.add(PaymentEvent(provider=provider.name, provider_event_id=provider_event_id, event_type=str(body.get("type") or body.get("action") or "unknown"), payload=body))
            await session.flush()
            if body.get("type") != "payment":
                return {"accepted": True, "event_id": provider_event_id}
            remote = await provider.get_payment(data_id)
            payment = await session.scalar(select(PaymentIntentRecord).where(PaymentIntentRecord.provider == provider.name, PaymentIntentRecord.provider_payment_id == remote.provider_payment_id).with_for_update())
            if payment is None:
                raise HTTPException(401, "unknown_payment_webhook")
            if remote.amount_minor != payment.amount_minor or remote.currency != payment.currency:
                raise HTTPException(409, "payment_amount_mismatch")
            previous_status = payment.status
            payment.status = remote.status
            payment.next_reconcile_at = next_reconcile_time(remote.status)
            payment.reconcile_attempts = 0
            payment.last_reconcile_error = None
            if remote.status == "approved":
                await post_ledger_transaction(session, tenant_id=payment.tenant_id, idempotency_key=f"payment-approved:{payment.id}", reference_type="payment", reference_id=str(payment.id), currency=payment.currency, debit_account=f"cash:{payment.provider}", credit_account="revenue:sales", amount_minor=payment.amount_minor)
                order = await session.scalar(select(Order).where(Order.id == payment.order_id, Order.tenant_id == payment.tenant_id).with_for_update())
                if order is not None and order.status == "PAYMENT_PENDING":
                    await transition_order(session, payment.order_id, payment.tenant_id, "PAID")
            elif remote.status in {"cancelled", "rejected", "expired"}:
                order = await session.scalar(select(Order).where(Order.id == payment.order_id, Order.tenant_id == payment.tenant_id).with_for_update())
                if order is not None and order.status == "PAYMENT_PENDING":
                    await transition_order(session, payment.order_id, payment.tenant_id, "EXPIRED" if remote.status == "expired" else "CANCELLED")
            if previous_status != remote.status:
                enqueue_outbox(session, tenant_id=payment.tenant_id, aggregate_type="payment", aggregate_id=str(payment.id), event_type=f"payment.status.{remote.status}", payload={"order_id": str(payment.order_id), "provider": payment.provider, "provider_payment_id": payment.provider_payment_id})
    return {"accepted": True, "event_id": provider_event_id, "fingerprint": sha256(raw).hexdigest()}

@router.post("/mercadopago_chargebacks", status_code=202)
async def mercado_pago_chargeback_webhook(request: Request) -> dict[str, object]:
    raw, body = await _read_json(request)
    data_id = request.query_params.get("data.id", "")
    provider_payment_id = str(body.get("data", {}).get("payment_id") or "") or None
    async with SessionFactory() as session:
        payment = None
        if provider_payment_id:
            payment = await session.scalar(select(PaymentIntentRecord).where(PaymentIntentRecord.provider == "mercadopago_pix", PaymentIntentRecord.provider_payment_id == provider_payment_id))
        if payment is None:
            raise HTTPException(401, "unknown_chargeback_webhook")
        x_signature = request.headers.get("x-signature")
        x_request_id = request.headers.get("x-request-id")
        if not x_signature or not x_request_id or not data_id:
            raise HTTPException(400, "missing_webhook_security_headers")
        provider = await payment_providers.mercadopago_pix(payment.tenant_id)
        if not await provider.validate_webhook({"x-signature": x_signature, "x-request-id": x_request_id, "x-data-id": data_id}, raw):
            raise HTTPException(401, "invalid_webhook_signature")
        await session.rollback()
        provider_event_id = str(body.get("id") or f"chargeback:{data_id}")
        async with session.begin():
            existing_event = await session.scalar(select(PaymentEvent).where(PaymentEvent.provider == provider.name, PaymentEvent.provider_event_id == provider_event_id).with_for_update())
            if existing_event is not None:
                return {"accepted": True, "duplicate": True, "event_id": provider_event_id}
            session.add(PaymentEvent(provider=provider.name, provider_event_id=provider_event_id, event_type="chargeback", payload=body))
            await session.flush()
            chargeback_id = str(body.get("data", {}).get("id") or data_id)
            remote = await provider.get_chargeback(chargeback_id)
            provider_payment_id = str(remote.get("payment_id") or provider_payment_id or "") or None
            payment = await session.scalar(select(PaymentIntentRecord).where(PaymentIntentRecord.provider == provider.name, PaymentIntentRecord.provider_payment_id == provider_payment_id).with_for_update()) if provider_payment_id else None
            amount_minor = int((Decimal(str(remote["amount"])) * 100).quantize(Decimal("1"))) if remote.get("amount") is not None else None
            dispute = await session.scalar(select(DisputeRecord).where(DisputeRecord.provider == provider.name, DisputeRecord.provider_dispute_id == chargeback_id).with_for_update())
            if dispute is None:
                dispute = DisputeRecord(provider=provider.name, provider_dispute_id=chargeback_id)
                session.add(dispute)
            if payment is not None:
                dispute.tenant_id = payment.tenant_id
                dispute.order_id = payment.order_id
                dispute.payment_intent_id = payment.id
            dispute.provider_payment_id = provider_payment_id
            dispute.status = str(remote.get("status", "unknown"))
            dispute.amount_minor = amount_minor
            dispute.currency = payment.currency if payment is not None else "BRL"
            dispute.coverage_applied = remote.get("coverage_applied")
            dispute.reason = str(remote.get("reason") or remote.get("reason_code") or "")[:500] or None
            dispute.payload = remote
            await session.flush()
            status = dispute.status.lower()
            if payment is not None and dispute.coverage_applied is False and status in {"closed", "resolved", "finished", "finalized"}:
                await post_ledger_transaction(session, tenant_id=payment.tenant_id, idempotency_key=f"chargeback-loss:{dispute.id}", reference_type="chargeback", reference_id=str(dispute.id), currency=payment.currency, debit_account="chargebacks:loss", credit_account=f"cash:{payment.provider}", amount_minor=amount_minor or payment.amount_minor)
            enqueue_outbox(session, tenant_id=dispute.tenant_id, aggregate_type="dispute", aggregate_id=str(dispute.id), event_type="dispute.updated", payload={"provider": provider.name, "provider_dispute_id": chargeback_id, "status": dispute.status})
    return {"accepted": True, "event_id": provider_event_id, "fingerprint": sha256(raw).hexdigest()}

@router.post("/{provider}", status_code=202)
async def unsupported_provider_webhook(provider: str, request: Request) -> dict[str, object]:
    raw = await request.body()
    if len(raw) > 2_000_000:
        raise HTTPException(413, "payload_too_large")
    raise HTTPException(501, f"payment_provider_not_implemented:{provider}")
