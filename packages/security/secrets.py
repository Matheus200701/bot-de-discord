from __future__ import annotations

import os
from typing import Protocol
from uuid import UUID


class SecretProvider(Protocol):
    def get(self, name: str) -> str: ...


class EnvironmentSecretProvider:
    """Development-only secret provider.

    Production deployments should replace this implementation with a managed
    secret backend without changing payment/domain code.
    """

    def get(self, name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise RuntimeError(f"missing_secret:{name}")
        return value


class TenantSecretResolver:
    """Resolves provider credentials using a tenant-specific secret namespace."""

    def __init__(self, provider: SecretProvider) -> None:
        self.provider = provider

    def mercadopago_access_token(self, tenant_id: UUID) -> str:
        return self.provider.get(f"MERCADOPAGO_{tenant_id.hex.upper()}_ACCESS_TOKEN")

    def mercadopago_webhook_secret(self, tenant_id: UUID) -> str:
        return self.provider.get(f"MERCADOPAGO_{tenant_id.hex.upper()}_WEBHOOK_SECRET")
