# Fase 14 — Integration, Concurrency & Distributed Protection

## Objetivo

Transformar os gates de produção documentados na Fase 13 em verificações executáveis no CI, sem afirmar que o sistema está pronto para vendas reais antes de os workflows passarem.

## Entregas

- PostgreSQL 16 e Redis 7 como serviços no GitHub Actions.
- `alembic upgrade head` contra banco descartável.
- Smoke integration test real para PostgreSQL e Redis.
- Verificação concorrente de `INCR` no Redis.
- Rate limiter distribuído reutilizável com Redis, janela fixa e expiração.
- Testes de `TRACE` e `TRUSTED_HOSTS`.
- Configuração de limites documentada no `.env.example`.

## Rate limiting

`packages/security/rate_limit.py` fornece um componente reutilizável para endpoints de alto risco. A chave deve incorporar tenant e identidade autenticada quando disponíveis.

O limiter não é instalado globalmente nesta fase para evitar impor limites sem uma política por rota. Autenticação, mutations financeiras, administração e webhooks devem receber limites específicos antes do go-live.

## Concorrência

O checkout existente utiliza locks de linha no PostgreSQL e o worker utiliza `SKIP LOCKED`. O workflow da Fase 14 cria a infraestrutura real para testes concorrentes contra serviços descartáveis.

## Limitações

Ainda faltam E2E completo de checkout/webhook/fulfillment/refund, sandbox/certificação PSP, secret manager, isolamento de credenciais PSP por tenant, CSRF completo, remoção do admin key legado, backup/restore e validação HTTPS/load balancer.
