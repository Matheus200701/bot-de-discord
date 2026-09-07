# Discord Commerce Platform 2026

Plataforma de comércio para Discord, estruturada como App + API + banco + pagamentos + entrega + dashboard + observabilidade, em vez de um bot monolítico.

## Fase 10 — Dashboard + OAuth2 + Account Linking + RBAC

O painel administrativo agora possui autenticação baseada no Discord e isolamento multi-tenant.

- **OAuth2 Authorization Code:** login pelo Discord com `identify guilds`, callback HTTPS e `state` de uso único armazenado com hash; o cookie `state` também é validado para reduzir risco de CSRF.
- **Sessão web:** cookie `HttpOnly`, `Secure`, `SameSite=Lax`, token aleatório armazenado somente como hash no PostgreSQL e revogação no logout.
- **Identidade Discord:** `DashboardUser` vincula o usuário do painel ao `discord_user_id`.
- **Account linking:** a conta Discord é a identidade autenticada do dashboard; o backend nunca aceita um Discord user ID enviado pelo cliente para definir o administrador.
- **Multi-tenant:** cada servidor autorizado é representado por `Tenant`; o usuário recebe membership somente em guilds onde é owner ou possui `MANAGE_GUILD`.
- **RBAC:** `OWNER`, `ADMIN`, `OPERATOR` e `VIEWER`, aplicados no backend antes de consultar dados do tenant.
- **Auditoria:** estrutura `AuditLog` preparada para registrar ações administrativas e recursos afetados.
- **Dashboard:** visão geral, faturamento, pedidos recentes, produtos, tenant selecionado e papel RBAC.

As APIs OAuth do Discord usam `application/x-www-form-urlencoded` no token endpoint e recomendam o parâmetro `state` para proteção contra CSRF. Os escopos utilizados são `identify` e `guilds`. citeturn829118view0

### Rotas de autenticação

- `GET /api/v1/auth/discord/login`
- `GET /api/v1/auth/discord/callback`
- `POST /api/v1/auth/discord/logout`
- `GET /api/v1/auth/discord/me`

### APIs do dashboard

- `GET /api/v1/dashboard/{tenant_id}/overview`
- `GET /api/v1/dashboard/{tenant_id}/products`
- `GET /api/v1/dashboard/{tenant_id}/orders`
- `GET /api/v1/dashboard/{tenant_id}/members`

## Fase 9 — cupons, cashback, afiliados e VIP

O checkout suporta promoções e fidelização com valores financeiros em unidades menores e percentuais em basis points.

## Fase 8 — entrega digital e Discord Roles

A confirmação do pagamento dispara fulfillment assíncrono através do outbox. O produto declara seu tipo de entrega em `metadata_json.delivery`. Adicionar/remover cargo usa a API oficial do Discord e requer `MANAGE_ROLES`; o bot não precisa de `ADMINISTRATOR`.

## Fases 2–7

A base anterior inclui checkout transacional, reservas de estoque, Mercado Pago Pix, webhooks assinados, reconciliação, outbox/retries/circuit breaker, refunds, disputes/chargebacks e ledger de partidas dobradas.

## Produção

Configure HTTPS real para OAuth2, `OAUTH_REDIRECT_URI` registrado no Developer Portal, secrets manager, PostgreSQL/Redis gerenciados, credenciais Discord/PSP, permissões mínimas e políticas LGPD. O painel não deve voltar a usar `X-Discord-User-ID` ou `X-Commerce-Admin-Key` como substituto de autenticação administrativa quando exposto em produção.

Execute CI, migrations, testes de restauração, concorrência, OAuth2 e sandbox E2E antes de habilitar vendas reais.

## Próximas fases

1. OpenTelemetry, métricas, Sentry e alertas.
2. Hardening, testes E2E de concorrência, sandbox, segurança e deploy de produção.
