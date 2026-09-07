# Fase 15 — E2E, Concurrency & Payment Sandbox

## Objetivo

Transformar os gates de integração da Fase 14 em uma base executável para validar PostgreSQL/Redis, concorrência e limites distribuídos antes do go-live.

## Entregas

- CI executa PostgreSQL e Redis reais como services.
- Migrations são aplicadas em banco descartável antes dos testes.
- Testes de integração validam conectividade PostgreSQL/Redis.
- Teste concorrente valida atomicidade de `INCR` no Redis.
- Rate limiter distribuído usa operação Lua atômica (`INCR` + `EXPIRE`) para evitar janela de corrida entre incrementação e expiração.
- Teste de integração dedicado ao rate limiter.
- Suite unitária e suite de integração são executadas separadamente.

## Pagamentos

O adapter Mercado Pago continua separado da camada de domínio. A Fase 15 não coloca credenciais reais no CI nem simula uma certificação do provedor. O sandbox deve ser executado com credenciais de teste armazenadas como secrets do ambiente e com validação dos cenários checkout → pagamento → webhook → fulfillment → refund.

## Concorrência

O Redis é exercitado com múltiplas operações concorrentes. O checkout PostgreSQL já utiliza locks transacionais; a certificação de corrida de estoque/idempotência ainda precisa executar cenários com múltiplas conexões e dados descartáveis no CI.

## Limitações

A Fase 15 não declara certificação do PSP nem readiness de produção. Permanecem secret manager, isolamento de credenciais PSP por tenant, CSRF completo, remoção do admin key legado, E2E completo de negócio, backup/restore e validação HTTPS/load balancer.
