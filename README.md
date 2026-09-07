# Discord Commerce Platform 2026

Plataforma de comércio para Discord, estruturada como App + API + banco + pagamentos + entrega + observabilidade, em vez de um bot monolítico.

## Fase 17 — Full Multi-Tenant Security & Financial RBAC

- `DEFAULT_TENANT_ID` removido das operações comerciais da API.
- Tenant explícito em catálogo, carrinho, checkout, pagamento e entregas.
- Refund financeiro movido para Dashboard OAuth2 + RBAC `ADMIN/OWNER` + CSRF.
- Criação administrativa de produtos movida para Dashboard + RBAC `OPERATOR+` + CSRF.
- Credenciais Mercado Pago resolvidas por tenant.
- Testes de CSRF/RBAC adicionados.

A Fase 17 melhora a separação de tenant e remove o admin key legado, mas não declara readiness. APIs customer-facing ainda precisam vincular o tenant a um contexto confiável de instalação/guild do Discord antes do go-live.

## Fase 16 — Multi-Tenant Security, Secret Isolation & CSRF

- Double-submit CSRF.
- Cookie de sessão `Secure`/`SameSite=Lax`.
- Resolver de secrets por tenant.
- Provider Mercado Pago com credenciais por instância.

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

Ainda bloqueada. Antes de vendas reais: Secret Manager gerenciado, isolamento PSP por tenant, tenant binding confiável via Discord, E2E completo, concorrência PostgreSQL, sandbox PSP, webhooks tenant-aware, rate limits por rota, backup/restore, HTTPS/load balancer e validação dos gates de CI. 
