from __future__ import annotations

import os
from typing import Protocol
from uuid import UUID


class SecretProvider(Protocol):
    def get(self, name: str) -> str: ...


class EnvironmentSecretProvider:
    """Development-only secret provider; production must use managed secrets."""

    def get(self, name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise RuntimeError(f"missing_secret:{name}")
        return value


class TenantSecretResolver:
    """Resolves PSP credentials from a tenant-specific secret namespace."""

    def __init__(self, provider: SecretProvider | None = None) -> None:
        self.provider = provider or EnvironmentSecretProvider()

    def _tenant_secret(self, tenant_id: UUID, suffix: str, legacy: str) -> str:
        try:
            return self.provider.get(f"MERCADOPAGO_{tenant_id.hex.upper()}_{suffix}")
        except RuntimeError:
            if os.getenv("APP_ENV", "development").lower() == "production":
                raise
            return self.provider.get(legacy)

    def mercadopago_access_token(self, tenant_id: UUID) -> str:
        return self._tenant_secret(tenant_id, "ACCESS_TOKEN", "MERCADOPAGO_ACCESS_TOKEN")

    def mercadopago_webhook_secret(self, tenant_id: UUID) -> str:
        return self._tenant_secret(tenant_id, "WEBHOOK_SECRET", "MERCADOPAGO_WEBHOOK_SECRET")
