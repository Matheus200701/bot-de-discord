# Fase 14 — Integration, Concurrency & Distributed Protection

## Objetivo

Transformar os gates de produção documentados na Fase 13 em verificações executáveis no CI, sem afirmar que o sistema está pronto para vendas reais antes de os workflows passarem.

## Entregas

- PostgreSQL 16 e Redis 7 como serviços no GitHub Actions.
- `alembic upgrade head` executado contra banco descartável.
- Smoke integration test real para PostgreSQL e Redis.
- Verificação concorrente de `INCR` no Redis.
- Primitiva de rate limiting distribuído com Redis usando janela fixa e expiração da chave.
- Teste unitário do limite distribuído.
- Testes adicionais de security middleware para `TRACE` e `TRUSTED_HOSTS`.

## Rate limiting

`packages/security/rate_limit.py` fornece um componente reutilizável para endpoints de alto risco. O chamador deve construir uma chave que inclua o tenant e a identidade autenticada, por exemplo `tenant:user` ou `tenant:ip` conforme o endpoint.

A implementação não é instalada automaticamente em todos os endpoints nesta fase para evitar alterar limites de produção sem definição operacional por rota. Mutations financeiras, login e webhooks devem receber limites específicos antes do go-live.

## Concorrência

O checkout existente já usa locks de produto e o worker usa `SKIP LOCKED`. A Fase 14 cria o ambiente real para testes concorrentes; a suíte específica de corrida de checkout deve ser executada com múltiplas conexões contra PostgreSQL antes do release.

## Limitações

Ainda permanecem: sandbox/certificação PSP, secret manager, credenciais PSP isoladas por tenant, CSRF completo do dashboard, remoção do admin key legado, E2E completo de checkout/webhook/fulfillment/refund e validação de HTTPS/load balancer.
