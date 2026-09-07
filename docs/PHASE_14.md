# Fase 14 — Integration, Concurrency & Distributed Protection

## Entregas

- PostgreSQL 16 e Redis 7 como serviços descartáveis no GitHub Actions.
- `alembic upgrade head` contra banco descartável.
- Smoke integration test real para PostgreSQL e Redis.
- Verificação concorrente de `INCR` no Redis.
- Rate limiter distribuído reutilizável com Redis, janela fixa e expiração.
- Testes de `TRACE` e `TRUSTED_HOSTS`.
- Configuração de limites no `.env.example`.

## Rate limiting

`packages/security/rate_limit.py` é uma primitiva reutilizável para endpoints de alto risco. A chave deve incorporar tenant e identidade autenticada quando disponíveis.

O limiter não é aplicado globalmente: limites devem ser definidos por rota e risco operacional. Autenticação, mutations financeiras, administração e webhooks devem receber políticas específicas antes do go-live.

## Concorrência

O checkout existente utiliza locks de linha no PostgreSQL e o worker utiliza `SKIP LOCKED`. A infraestrutura da Fase 14 permite executar testes concorrentes reais contra PostgreSQL/Redis descartáveis. O smoke test não substitui o E2E de corrida do checkout.

## Status

A Fase 14 foi implementada na branch, mas a readiness de produção continua condicionada à execução e aprovação dos workflows do GitHub.

## Próximos bloqueadores de produção

E2E completo de checkout/webhook/fulfillment/refund, sandbox/certificação PSP, secret manager, isolamento de credenciais PSP por tenant, aplicação das políticas de rate limit por rota, CSRF completo do dashboard, remoção/depreciação do admin key legado, backup/restore e validação HTTPS/load balancer.
