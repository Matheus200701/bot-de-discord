from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any

import httpx

from packages.payments.base import PaymentIntent, PaymentProvider


class MercadoPagoError(RuntimeError):
    pass


class MercadoPagoPixProvider(PaymentProvider):
    name = "mercadopago_pix"

    def __init__(self, access_token: str | None = None, webhook_secret: str | None = None) -> None:
        self.access_token = access_token or os.environ["MERCADOPAGO_ACCESS_TOKEN"]
        self.webhook_secret = webhook_secret or os.environ["MERCADOPAGO_WEBHOOK_SECRET"]
        self.base_url = os.getenv("MERCADOPAGO_BASE_URL", "https://api.mercadopago.com")

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"
        headers.setdefault("Content-Type", "application/json")
        async with httpx.AsyncClient(base_url=self.base_url, timeout=15.0) as client:
            response = await client.request(method, path, headers=headers, **kwargs)
        if response.is_error:
            raise MercadoPagoError(f"mercadopago_http_{response.status_code}")
        return response.json()

    async def create_payment(self, *, order_id: str, amount_minor: int, currency: str, metadata: dict[str, str]) -> PaymentIntent:
        if currency.upper() != "BRL":
            raise MercadoPagoError("pix_currency_must_be_brl")
        # Mercado Pago's Pix Payment API uses decimal major units and requires
        # X-Idempotency-Key. Never derive the amount from client input here.
        amount = f"{amount_minor / 100:.2f}"
        payload = {
            "transaction_amount": float(amount),
            "description": metadata.get("description", f"Pedido {order_id}"),
            "payment_method_id": "pix",
            "payer": {"email": metadata["payer_email"]},
            "external_reference": order_id,
        }
        data = await self._request(
            "POST",
            "/v1/payments",
            json=payload,
            headers={"X-Idempotency-Key": metadata.get("idempotency_key", order_id)},
        )
        point = data.get("point_of_interaction", {}).get("transaction_data", {})
        return PaymentIntent(
            provider_payment_id=str(data["id"]),
            status=str(data.get("status", "pending")),
            amount_minor=amount_minor,
            currency=currency.upper(),
            checkout_url=point.get("ticket_url"),
            qr_code=point.get("qr_code_base64"),
            qr_code_text=point.get("qr_code"),
        )

    async def get_payment(self, provider_payment_id: str) -> PaymentIntent:
        data = await self._request("GET", f"/v1/payments/{provider_payment_id}")
        amount_minor = round(float(data.get("transaction_amount", 0)) * 100)
        point = data.get("point_of_interaction", {}).get("transaction_data", {})
        return PaymentIntent(
            provider_payment_id=str(data["id"]),
            status=str(data.get("status", "unknown")),
            amount_minor=amount_minor,
            currency="BRL",
            checkout_url=point.get("ticket_url"),
            qr_code=point.get("qr_code_base64"),
            qr_code_text=point.get("qr_code"),
        )

    async def cancel_payment(self, provider_payment_id: str) -> None:
        await self._request("PUT", f"/v1/payments/{provider_payment_id}", json={"status": "cancelled"})

    async def refund_payment(self, provider_payment_id: str, amount_minor: int | None = None) -> None:
        payload = {} if amount_minor is None else {"amount": amount_minor / 100}
        await self._request("POST", f"/v1/payments/{provider_payment_id}/refunds", json=payload)

    async def validate_webhook(self, headers: dict[str, str], raw_body: bytes) -> bool:
        # Mercado Pago signs the notification manifest using x-signature and
        # x-request-id plus the data.id query parameter. The API adapter receives
        # data.id through the normalized header supplied by the webhook boundary.
        signature = headers.get("x-signature", "")
        request_id = headers.get("x-request-id", "")
        data_id = headers.get("x-data-id", "")
        values = dict(item.split("=", 1) for item in signature.split(",") if "=" in item)
        ts, provided = values.get("ts"), values.get("v1")
        if not ts or not provided or not request_id or not data_id:
            return False
        manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
        expected = hmac.new(self.webhook_secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, provided)

    async def parse_webhook_event(self, raw_body: bytes) -> dict[str, Any]:
        import json
        return json.loads(raw_body)
