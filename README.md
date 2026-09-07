# Discord Commerce Platform 2026

Plataforma de comércio para Discord, estruturada como App + API + banco + pagamentos + entrega + observabilidade, em vez de um bot monolítico.

## Fase 15 — E2E, Concurrency & Payment Sandbox

- CI com PostgreSQL e Redis reais e migrations executáveis.
- Smoke tests de conectividade e concorrência no Redis.
- Rate limiter distribuído com operação Redis atômica via Lua.
- Suite de integração dedicada ao rate limiting.
- Contratos de sandbox PSP preparados sem colocar credenciais reais no repositório.
- Gates de integração separados da suíte unitária.

A Fase 15 melhora a confiança operacional, mas não certifica Mercado Pago nem declara readiness de produção. O sandbox precisa ser executado com credenciais de teste do provedor e os cenários completos checkout → pagamento → webhook → fulfillment → refund devem passar antes do go-live.

## Fase 14 — Integration, Concurrency & Distributed Protection

- PostgreSQL e Redis como serviços descartáveis no GitHub Actions.
- `alembic upgrade head` contra PostgreSQL do CI.
- Integration tests reais para PostgreSQL e Redis.
- Verificação concorrente de `INCR` no Redis.
- Rate limiter distribuído reutilizável.
- Testes de `TRACE`, `TRUSTED_HOSTS` e limite de body.

## Fase 13 — Security & Production Release Gate

- Limite de body em `Content-Length` e streaming.
- Allowlist de métodos HTTP e rejeição de `TRACE`.
- `TRUSTED_HOSTS`, HSTS opcional e headers centralizados.
- CodeQL, Gitleaks, `pip-audit` e Trivy.

## Fase 12 — Hardening

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
