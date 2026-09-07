# Discord Commerce Platform 2026

Plataforma de comércio para Discord, estruturada como App + API + banco + pagamentos + entrega + observabilidade, em vez de um bot monolítico.

## Fase 14 — Integration, Concurrency & Distributed Protection

A Fase 14 transforma parte do release gate em automação executável:

- PostgreSQL 16 e Redis 7 como serviços no GitHub Actions.
- Migrations executadas contra banco descartável.
- Smoke test real de conectividade PostgreSQL/Redis.
- Rate limiter distribuído reutilizável com Redis e janela fixa.
- Testes de rate limiting, `TRACE` e `TRUSTED_HOSTS`.
- Documentação específica em `docs/PHASE_14.md`.

O rate limiter não é aplicado globalmente nesta fase: limites precisam ser definidos por rota e risco operacional. Antes do go-live, mutations financeiras, autenticação e webhooks devem possuir limites apropriados.

A Fase 14 também não declara readiness de produção: o workflow precisa executar e passar, e ainda faltam E2E completos, sandbox/certificação PSP, secret manager, isolamento de credenciais PSP por tenant, CSRF completo do dashboard, remoção do admin key legado e validação de HTTPS/load balancer.

## Fase 13 — Security & Production Release Gate

A plataforma possui hardening e automação de segurança:

- Limite de body aplicado a `Content-Length` e streaming.
- Allowlist de métodos HTTP; `TRACE` é rejeitado.
- `TRUSTED_HOSTS`, HSTS opcional e headers centralizados.
- GitHub Actions para CodeQL, Gitleaks e `pip-audit`.
- Trivy para vulnerabilidades HIGH/CRITICAL de containers.
- Checklist de release em `docs/SECURITY.md`.

## Fase 12 — Hardening de segurança

- Middleware ASGI de segurança e headers defensivos.
- Request ID/correlação e limites de request.
- Trusted hosts e HSTS opcional.
- Baseline de segurança documentado.

## Fase 11 — Observabilidade

- OpenTelemetry para traces/metrics.
- Instrumentação FastAPI, SQLAlchemy e HTTPX.
- Sentry opcional com redução de PII.
- Configuração OTLP por ambiente.
- SLOs e runbook operacional.

## Fase 10 — Dashboard / OAuth2 / RBAC

- Dashboard Next.js/TypeScript.
- Login OAuth2 Authorization Code com Discord.
- `state` de uso único + cookie `HttpOnly`.
- Sessões web com token aleatório armazenado somente como hash.
- Multi-tenant e RBAC `OWNER`, `ADMIN`, `OPERATOR`, `VIEWER`.
- APIs administrativas protegidas por autenticação e tenant membership.

## Fase 9 — Promotions & Loyalty

- Cupons percentuais/fixos e limites.
- Cashback com wallet + ledger.
- Afiliados e comissão em basis points.
- VIP por gasto confirmado.
- Snapshot de promoção no pedido.

## Fase 8 — Fulfillment

- Entrega digital.
- Discord Roles via API oficial.
- Fulfillment assíncrono/idempotente.
- Revogação após refund.

## Fases 2–7

A base inclui checkout transacional, reservas de estoque, Mercado Pago Pix, webhooks assinados, reconciliação, outbox/retries/circuit breaker, refunds, disputes/chargebacks e ledger de partidas dobradas.

## Produção

Antes de vendas reais, configure PostgreSQL/Redis gerenciados, secret manager, HTTPS, OAuth2, credenciais Discord/PSP, Sentry/OTLP, permissões mínimas e políticas LGPD. Execute CI, migrations, testes de restauração, concorrência, sandbox e E2E antes de remover o estado Draft do PR.
