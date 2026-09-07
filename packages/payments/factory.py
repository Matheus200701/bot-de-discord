from __future__ import annotations

from uuid import UUID

from packages.payments.mercadopago import MercadoPagoPixProvider
from packages.security.secrets import TenantSecretResolver


class PaymentProviderFactory:
    def __init__(self, secrets: TenantSecretResolver | None = None) -> None:
        self.secrets = secrets or TenantSecretResolver()

    async def mercadopago_pix(self, tenant_id: UUID) -> MercadoPagoPixProvider:
        return MercadoPagoPixProvider(
            access_token=await self.secrets.mercadopago_access_token(tenant_id),
            webhook_secret=await self.secrets.mercadopago_webhook_secret(tenant_id),
        )
