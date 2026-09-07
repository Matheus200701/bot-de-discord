# Fase 16 — Multi-Tenant Security, Secret Isolation & CSRF

## Objetivo

Reduzir os principais riscos restantes de autorização administrativa e credenciais PSP antes da preparação de produção.

## Entregas desta fase

- Double-submit CSRF para mutações autenticadas por cookie do Dashboard.
- Token CSRF aleatório por sessão/login, cookie `Secure` + `SameSite=Lax` e header obrigatório em mutações.
- Logout do Dashboard atualizado para enviar o token CSRF.
- Resolver de secrets com namespace por tenant para credenciais Mercado Pago.
- Fallback para `MERCADOPAGO_ACCESS_TOKEN`/`MERCADOPAGO_WEBHOOK_SECRET` somente fora de `APP_ENV=production`, facilitando migração.
- Em produção, ausência de secret tenant-scoped falha explicitamente.
- Provider Mercado Pago recebe credenciais por instância, mantendo secrets fora do domínio.
- Teste unitário do bloqueio CSRF.

## Segurança multi-tenant

Todas as consultas administrativas existentes continuam usando `tenant_context`, que valida sessão, membership ativo e papel mínimo. A camada de credenciais agora também exige namespace por tenant em produção.

O catálogo/checkout legado ainda usa `DEFAULT_TENANT_ID` e o endpoint administrativo de refund legado ainda existe. Esses pontos permanecem bloqueadores para declarar isolamento multi-tenant completo.

## Produção

Esta fase não declara readiness. É necessário executar CI, testes E2E, validar todas as mutações administrativas com RBAC, migrar credenciais para Secret Manager real, validar cada webhook por tenant e remover/depreciar formalmente o admin key legado.
