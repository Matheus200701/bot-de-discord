import os
from uuid import UUID

import pytest

from packages.security.secrets import EnvironmentSecretProvider, SecretNotFound, TenantSecretResolver, build_secret_provider


@pytest.mark.asyncio
async def test_tenant_secret_names_are_isolated(monkeypatch) -> None:
    tenant = UUID("11111111-1111-1111-1111-111111111111")
    monkeypatch.setenv("MERCADOPAGO_11111111111111111111111111111111_ACCESS_TOKEN", "tenant-token")
    resolver = TenantSecretResolver(EnvironmentSecretProvider())
    assert await resolver.mercadopago_access_token(tenant) == "tenant-token"


@pytest.mark.asyncio
async def test_missing_tenant_secret_does_not_fallback_in_production(monkeypatch) -> None:
    tenant = UUID("22222222-2222-2222-2222-222222222222")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "legacy-token")
    resolver = TenantSecretResolver(EnvironmentSecretProvider())
    with pytest.raises(SecretNotFound):
        await resolver.mercadopago_access_token(tenant)


def test_production_requires_managed_secret_provider(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_PROVIDER", "env")
    with pytest.raises(RuntimeError, match="managed_secret_provider_required"):
        build_secret_provider()
