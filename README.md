# Discord Commerce Platform 2026

Plataforma de comércio para Discord, estruturada como App + API + banco + pagamentos + observabilidade, em vez de um bot monolítico.

## Arquitetura

Discord App → Discord Layer → Service Layer → Commerce / Payments / Inventory / Support / Customers → Event System → PostgreSQL + Redis → External APIs.

## Stack

- Python 3.12+
- discord.py 2.x
- FastAPI + Pydantic
- SQLAlchemy 2.x + asyncpg + Alembic
- PostgreSQL 17
- Redis 8
- httpx
- Docker + GitHub Actions

## Fase 2/3

A persistência de produtos saiu do armazenamento em memória e passou para PostgreSQL. O domínio possui `Cart`, `CartItem`, `OrderItem` e `InventoryReservation`, com migrations Alembic. O checkout recalcula os preços no servidor, bloqueia linhas de produto dentro da transação, reserva estoque e transforma o carrinho em pedido de forma atômica.

Reservas possuem expiração/release por worker, reduzindo o risco de estoque ficar preso quando um pagamento não é concluído.

## Fase 5 — pagamentos

Foi adicionado o primeiro adapter PSP real: **Mercado Pago Pix**.

- `POST /api/v1/payments/mercadopago/pix`
- API oficial de pagamentos `/v1/payments`
- `X-Idempotency-Key` no request ao PSP
- persistência de `PaymentIntentRecord`
- webhook dedicado `/webhooks/payments/mercadopago_pix`
- validação HMAC de `x-signature`
- confirmação server-to-server do pagamento
- conferência de valor e moeda
- transições `PAYMENT_PENDING -> PAID/CANCELLED/EXPIRED`

## Fase 6 — reliability / event bus

A camada de pagamentos agora possui mecanismos para recuperação de falhas sem depender exclusivamente de webhooks:

- outbox transacional em PostgreSQL (`outbox_events`);
- processamento assíncrono com `FOR UPDATE SKIP LOCKED`;
- retries com exponential backoff + jitter;
- DLQ lógica via estado `DEAD`;
- circuit breaker por PSP;
- timeout nas consultas de reconciliação;
- reconciliação periódica de `PaymentIntentRecord` pendentes;
- recuperação de locks antigos do outbox;
- idempotência adicional por `(tenant_id, order_id, provider)` e `(provider, idempotency_key)`.

## Fase 7 — refunds / disputes / ledger

A contabilidade financeira deixa de depender apenas dos estados do pedido e passa a ter um ledger de partidas dobradas:

- `ledger_transactions` + `ledger_entries` com débito/crédito em unidades menores inteiras;
- constraint de idempotência por transação financeira;
- lançamento de venda aprovado: `cash:<provider>` → `revenue:sales`;
- lançamento de reembolso aprovado: `refunds:customer` → `cash:<provider>`;
- lançamento de perda por chargeback: `chargebacks:loss` → `cash:<provider>`;
- refunds parciais ou totais com idempotência por tenant + chave da operação;
- execução do refund pelo worker através do outbox;
- falhas permanentes de refund entram em `FAILED` e no DLQ do outbox;
- endpoint administrativo protegido por `X-Commerce-Admin-Key` para solicitar refund;
- webhook assinado para chargebacks do Mercado Pago em `/webhooks/payments/mercadopago_chargebacks`;
- `DisputeRecord` persistido e reconciliável por `provider_dispute_id`;
- resolução negativa de chargeback gera lançamento contábil idempotente.

O Mercado Pago documenta refunds parciais/totais pelo endpoint `/v1/payments/{id}/refunds` e exige `X-Idempotency-Key`; chargebacks possuem notificações específicas e consulta em `/v1/chargebacks/{id}`. citeturn456701search1turn395899search6

## Discord 2026

O projeto foi auditado contra a documentação oficial atual. Application Commands, user/guild installation, OAuth2, Components, Modals, Account Linking e monetização oficial são tratados segundo o suporte e as restrições documentadas. Veja `DISCORD_COMPATIBILITY.md`.

A arquitetura não assume que Premium Apps seja um gateway universal para qualquer mercadoria: SKUs/assinaturas nativas do Discord ficam separados da camada externa de pagamentos e dependem de elegibilidade do Discord.

## Endpoints atuais

- `GET /health`
- `GET /ready`
- `GET /api/v1/products`
- `POST /api/v1/products`
- `GET /api/v1/products/{product_id}`
- `POST /api/v1/cart/items`
- `POST /api/v1/checkout`
- `POST /api/v1/payments/mercadopago/pix`
- `POST /api/v1/orders/{order_id}/refund` (admin)
- `POST /webhooks/payments/mercadopago_pix`
- `POST /webhooks/payments/mercadopago_chargebacks`

## Regras financeiras

Valores monetários usam unidades menores inteiras (`minor`) no domínio persistente. O cliente nunca define o preço final. Eventos externos são idempotentes e alterações financeiras relevantes precisam permanecer recuperáveis por outbox/reconciliação. O ledger só aceita lançamentos com exatamente um lado de débito e um lado de crédito.

## Produção

Antes do primeiro deploy, configure PostgreSQL gerenciado, Redis gerenciado, secret manager, HTTPS, OAuth2 redirect URI, Discord credentials, credenciais PSP, `COMMERCE_ADMIN_KEY` forte e políticas de retenção/LGPD. Rode CI, migrations, testes de restauração e testes sandbox antes de habilitar vendas reais.

## Próximas fases

1. Entrega digital e Discord Roles.
2. Cupons, cashback, afiliados e VIP.
3. Dashboard Next.js/TypeScript + OAuth2/account linking.
4. OpenTelemetry, métricas, Sentry e alertas.
5. Hardening, testes de concorrência E2E e deploy de produção.
