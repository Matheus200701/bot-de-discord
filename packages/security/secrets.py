from __future__ import annotations

import os
from typing import Protocol
from uuid import UUID

import httpx


class SecretNotFound(RuntimeError):
    pass


class SecretProvider(Protocol):
    async def get(self, name: str) -> str: ...


class EnvironmentSecretProvider:
    """Development/test provider. Production must use a managed secret backend."""

    async def get(self, name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise SecretNotFound(name)
        return value


class VaultSecretProvider:
    """HashiCorp Vault KV-v2 provider; the Vault token is supplied out-of-band."""

    def __init__(self, address: str, token: str, mount: str = "secret") -> None:
        self.address = address.rstrip("/")
        self.token = token
        self.mount = mount

    async def get(self, name: str) -> str:
        path = f"/v1/{self.mount}/data/{name.lstrip('/')}"
        async with httpx.AsyncClient(base_url=self.address, timeout=5.0) as client:
            response = await client.get(path, headers={"X-Vault-Token": self.token})
        if response.status_code == 404:
            raise SecretNotFound(name)
        response.raise_for_status()
        value = response.json().get("data", {}).get("data", {}).get("value")
        if not isinstance(value, str) or not value:
            raise SecretNotFound(name)
        return value


def build_secret_provider() -> SecretProvider:
    backend = os.getenv("SECRET_PROVIDER", "env").lower()
    environment = os.getenv("APP_ENV", "development").lower()
    if backend == "vault":
        return VaultSecretProvider(
            os.environ["VAULT_ADDR"],
            os.environ["VAULT_TOKEN"],
            os.getenv("VAULT_MOUNT", "secret"),
        )
    if backend == "env" and environment in {"development", "test"}:
        return EnvironmentSecretProvider()
    raise RuntimeError("managed_secret_provider_required")


class TenantSecretResolver:
    """Tenant-isolated PSP secret namespace; no cross-tenant fallback in production."""

    def __init__(self, provider: SecretProvider | None = None) -> None:
        self.provider = provider or build_secret_provider()

    async def _tenant_secret(self, tenant_id: UUID, suffix: str, legacy: str) -> str:
        name = f"MERCADOPAGO_{tenant_id.hex.upper()}_{suffix}"
        try:
            return await self.provider.get(name)
        except SecretNotFound:
            if os.getenv("APP_ENV", "development").lower() == "production":
                raise
            return await self.provider.get(legacy)

    async def mercadopago_access_token(self, tenant_id: UUID) -> str:
        return await self._tenant_secret(tenant_id, "ACCESS_TOKEN", "MERCADOPAGO_ACCESS_TOKEN")

    async def mercadopago_webhook_secret(self, tenant_id: UUID) -> str:
        return await self._tenant_secret(tenant_id, "WEBHOOK_SECRET", "MERCADOPAGO_WEBHOOK_SECRET")
