# Discord Commerce Platform 2026

Plataforma de comércio para Discord, estruturada como App + API + banco + pagamentos + entrega + observabilidade, em vez de um bot monolítico.

## Fase 17 — Full Multi-Tenant Security & Financial RBAC

- `DEFAULT_TENANT_ID` removido das operações de promotions.
- `COMMERCE_ADMIN_KEY` removido das operações administrativas de promotions.
- Coupons, affiliates, VIP tiers e cashback usam `tenant_id` explícito.
- Mutations administrativas exigem Dashboard OAuth2 + RBAC + CSRF.
- Refund financeiro continua protegido por `ADMIN/OWNER` + CSRF.
- Credenciais Mercado Pago permanecem isoladas por tenant.
- Validade de coupons (`starts_at`/`ends_at`) é persistida.
- API version `0.17.0`.

A Fase 17 fecha um bypass legado importante, mas não declara readiness. O vínculo das APIs customer-facing ao contexto confiável do guild/instalação Discord ainda precisa ser fechado no gateway/bot; IDs arbitrários enviados pelo cliente não devem determinar o tenant em produção.

## Fase 16 — Multi-Tenant Security, Managed Secrets & CSRF

- Double-submit CSRF.
- Cookie de sessão `Secure`/`SameSite=Lax`.
- Resolver de secrets por tenant.
- Provider Mercado Pago com credenciais por instância.
- Vault KV v2 como adapter de secret manager.

## Fase 15 — E2E, Concurrency & Payment Sandbox

- CI com PostgreSQL e Redis reais e migrations executáveis.
- Smoke tests de conectividade e concorrência no Redis.
- Rate limiter distribuído com operação Redis atômica via Lua.
- Suite de integração dedicada ao rate limiting.
- Contratos de sandbox PSP preparados sem credenciais reais no repositório.

## Fase 14 — Integration, Concurrency & Distributed Protection

- PostgreSQL e Redis descartáveis no GitHub Actions.
- `alembic upgrade head` no banco do CI.
- Testes de integração reais.
- Proteções HTTP e limite de request.

## Fase 13 — Security & Production Release Gate

- Limite de body em `Content-Length` e streaming.
- Allowlist de métodos HTTP.
- `TRUSTED_HOSTS`, HSTS opcional e headers centralizados.
- CodeQL, Gitleaks, `pip-audit` e Trivy.

## Fases anteriores

OAuth2/RBAC, observabilidade OpenTelemetry/Sentry, catálogo, checkout transacional, reservas de estoque, Mercado Pago Pix, webhooks assinados, reconciliação, outbox/retries/circuit breaker, refunds, disputes/chargebacks, ledger, fulfillment, Discord Roles, cashback, afiliados, VIP e Dashboard.

## Produção

Ainda bloqueada. Antes de vendas reais: tenant binding confiável via Discord, E2E completo, concorrência PostgreSQL, sandbox PSP, Secret Manager gerenciado, webhooks tenant-aware, rate limits por rota, backup/restore, HTTPS/load balancer e validação dos gates de CI.
