# Discord Commerce Platform 2026

Plataforma de comércio para Discord, estruturada como App + API + banco + pagamentos + entrega + observabilidade, em vez de um bot monolítico.

## Fase 14 — Integration, Concurrency & Distributed Protection

- PostgreSQL 16 e Redis 7 como serviços descartáveis no GitHub Actions.
- `alembic upgrade head` executado contra PostgreSQL do CI.
- Integration tests reais para PostgreSQL e Redis.
- Verificação concorrente de `INCR` no Redis.
- Rate limiter distribuído reutilizável em `packages/security/rate_limit.py`.
- Testes adicionais para `TRACE` e `TRUSTED_HOSTS`.
- Configuração de rate limiting documentada no `.env.example`.
- Checklist detalhado em `docs/PHASE_14.md` e `docs/SECURITY.md`.

O rate limiter não é aplicado globalmente: limites devem ser definidos por rota e risco operacional. Antes do go-live, autenticação, mutations financeiras, administração e webhooks devem receber políticas específicas.

A Fase 14 não declara readiness de produção. O workflow deve passar no GitHub e ainda faltam E2E completos, sandbox/certificação PSP, secret manager, isolamento de credenciais PSP por tenant, CSRF completo do dashboard, remoção do admin key legado e validação HTTPS/load balancer.

## Fase 13 — Security & Production Release Gate

- Limite de body em `Content-Length` e streaming.
- Allowlist de métodos HTTP e rejeição de `TRACE`.
- `TRUSTED_HOSTS`, HSTS opcional e headers centralizados.
- CodeQL, Gitleaks, `pip-audit` e Trivy.

## Fase 12 — Hardening de segurança

- Middleware ASGI de segurança e headers defensivos.
- Request ID/correlação e limites de request.
- Trusted hosts e HSTS opcional.

## Fase 11 — Observabilidade

- OpenTelemetry para traces/metrics.
- Instrumentação FastAPI, SQLAlchemy e HTTPX.
- Sentry opcional com redução de PII.
- SLOs e runbook operacional.

## Fase 10 — Dashboard / OAuth2 / RBAC

- Dashboard Next.js/TypeScript.
- OAuth2 Authorization Code com Discord.
- `state` de uso único e sessões web com tokens armazenados somente como hash.
- Multi-tenant e RBAC `OWNER`, `ADMIN`, `OPERATOR`, `VIEWER`.

## Fase 9 — Promotions & Loyalty

- Cupons percentuais/fixos e limites.
- Cashback com wallet + ledger.
- Afiliados e comissão em basis points.
- VIP por gasto confirmado.

## Fase 8 — Fulfillment

- Entrega digital.
- Discord Roles via API oficial.
- Fulfillment assíncrono/idempotente e revogação após refund.

## Fases 2–7

Checkout transacional, reservas de estoque, Mercado Pago Pix, webhooks assinados, reconciliação, outbox/retries/circuit breaker, refunds, disputes/chargebacks e ledger financeiro.

## Produção

Antes de vendas reais, configure PostgreSQL/Redis gerenciados, secret manager, HTTPS, OAuth2, credenciais Discord/PSP, Sentry/OTLP, permissões mínimas e políticas LGPD. Execute todos os gates de CI, migrations, restauração, concorrência, sandbox e E2E antes de remover o estado Draft do PR.
