# Discord Commerce Platform 2026

Plataforma de comércio para Discord, estruturada como App + API + banco + pagamentos + entrega + observabilidade, em vez de um bot monolítico.

## Fase 13 — Security & Production Release Gate

A plataforma agora possui uma camada adicional de hardening e automação de segurança:

- Limite de body aplicado tanto a `Content-Length` quanto a requisições HTTP em streaming.
- Allowlist de métodos HTTP; métodos não utilizados como `TRACE` são rejeitados.
- `TRUSTED_HOSTS`, HSTS opcional e headers de segurança centralizados.
- Testes para headers, request ID, payload oversized em streaming e métodos proibidos.
- GitHub Actions separado para CodeQL, Gitleaks e `pip-audit`.
- Workflow de container com Trivy para vulnerabilidades HIGH/CRITICAL de SO e bibliotecas.
- `.env.example` documenta os controles de hardening.
- Checklist de release atualizado em `docs/SECURITY.md`.

A Fase 13 não declara certificação ASVS nem readiness automático para produção. Ainda são necessários E2E reais, testes de concorrência contra PostgreSQL/Redis, sandbox de PSP, secret manager, isolamento de credenciais por tenant, rate limiting distribuído, CSRF completo do dashboard e validação do ambiente HTTPS/load balancer.

## Fase 12 — Hardening de segurança

- Middleware ASGI de segurança e headers defensivos.
- Request ID/correlação e limites de request.
- Trusted hosts e HSTS opcional.
- Baseline de segurança documentado em `docs/SECURITY.md`.

## Fase 11 — Observabilidade

A plataforma possui uma camada de observabilidade opcional e segura:

- **OpenTelemetry:** traces e métricas com atributos de serviço, versão e ambiente.
- **Instrumentação:** FastAPI, SQLAlchemy e HTTPX.
- **Sentry:** captura opcional de exceções e tracing, sem PII padrão; cookies, headers e payloads de request são removidos antes do envio.
- **Bootstrap precoce:** `sitecustomize.py` inicializa a telemetria antes dos imports da aplicação.
- **OTLP:** endpoints separados para traces e metrics, com suporte a headers de autenticação.
- **Operação:** SLOs, alertas e runbook em `docs/OBSERVABILITY.md`.

Configuração principal no `.env`:

```dotenv
SENTRY_DSN=
SENTRY_TRACES_SAMPLE_RATE=0.05
SENTRY_PROFILES_SAMPLE_RATE=0
OTEL_SERVICE_NAME=discord-commerce-platform
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=
OTEL_EXPORTER_OTLP_HEADERS=
```

Sem DSN ou endpoints OTLP configurados, a telemetria externa permanece desativada e a aplicação continua funcionando.

## Fase 10 — Dashboard / OAuth2 / RBAC

- Dashboard Next.js/TypeScript operacional.
- Login OAuth2 Authorization Code com Discord.
- `state` aleatório de uso único + cookie `HttpOnly` para proteção CSRF.
- Sessões web com token aleatório armazenado somente como hash.
- `DashboardUser`, `Tenant` e `TenantMembership`.
- Isolamento multi-tenant no backend.
- Papéis `OWNER`, `ADMIN`, `OPERATOR`, `VIEWER`.
- APIs de overview, pedidos, produtos e membros protegidas por RBAC.
- Estrutura de auditoria com `AuditLog`.

## Fase 9 — cupons, cashback, afiliados e VIP

O checkout suporta promoções e fidelização sem usar `float` para valores financeiros.

- Cupons percentuais/fixos, validade, moeda, pedido mínimo, limites global/por usuário e limite de desconto.
- Cashback com carteira + ledger append-only e idempotência.
- Afiliados e comissão em basis points.
- VIP baseado em gasto confirmado.
- Snapshot das promoções no pedido.

## Fase 8 — entrega digital e Discord Roles

A confirmação do pagamento dispara fulfillment assíncrono através do outbox. Adicionar/remover cargo usa a API oficial do Discord e requer `MANAGE_ROLES`; o bot não precisa de `ADMINISTRATOR`.

## Fases 2–7

A base anterior inclui checkout transacional, reservas de estoque, Mercado Pago Pix, webhooks assinados, reconciliação, outbox/retries/circuit breaker, refunds, disputes/chargebacks e ledger de partidas dobradas.

## Produção

Antes de vendas reais, configure PostgreSQL/Redis gerenciados, secret manager, HTTPS, OAuth2, credenciais Discord/PSP, Sentry/OTLP, permissões mínimas e políticas LGPD. Execute CI, migrations, testes de restauração, concorrência, sandbox e E2E antes de remover o estado Draft do PR.

## Próximas fases

1. E2E real com PostgreSQL/Redis em CI e testes de concorrência.
2. Sandbox/certificação de pagamentos, refunds e fulfillment.
3. Secret manager e isolamento de credenciais PSP por tenant.
4. Rate limiting distribuído, CSRF completo e remoção do admin key legado.
5. Deploy de produção com backups/restauração, HTTPS/load balancer e políticas de retenção.
