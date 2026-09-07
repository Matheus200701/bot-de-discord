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
- validação usando `x-request-id` + `data.id`
- `PaymentEvent` idempotente antes dos efeitos de negócio
- confirmação server-to-server do pagamento
- conferência de valor e moeda
- transições `PAYMENT_PENDING -> PAID/CANCELLED/EXPIRED`

As credenciais ficam fora do código e devem ser fornecidas por secret manager/ambiente. Stripe permanece apenas como contrato/estrutura até sua implementação ser validada contra a documentação atual do provedor.

## Discord 2026

O projeto foi auditado contra a documentação oficial atual. Application Commands, user/guild installation, OAuth2, Components, Modals, Account Linking e monetização oficial são tratados segundo o suporte e as restrições documentadas. Veja `DISCORD_COMPATIBILITY.md`.

A arquitetura não assume que Premium Apps seja um gateway universal para qualquer mercadoria: SKUs/assinaturas nativas do Discord ficam separados da camada externa de pagamentos e dependem de elegibilidade do Discord.

## Desenvolvimento

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
alembic upgrade head
uvicorn apps.api.main:app --reload
```

Bot:

```bash
python -m apps.bot.main
```

Docker:

```bash
docker compose up --build
```

## Endpoints atuais

- `GET /health`
- `GET /ready`
- `GET /api/v1/products`
- `POST /api/v1/products`
- `GET /api/v1/products/{product_id}`
- `POST /api/v1/cart/items` com `X-Discord-User-ID`
- `POST /api/v1/checkout` com `X-Discord-User-ID` e `idempotency_key`
- `POST /api/v1/payments/mercadopago/pix` com `X-Discord-User-ID`
- `POST /webhooks/payments/mercadopago_pix`

## Regras financeiras

Valores de dinheiro usam unidades menores inteiras (`price_minor`) no domínio persistente. O cliente nunca define o preço final; a aplicação recalcula o checkout no servidor. Eventos de pagamento devem ser persistidos com `provider_event_id` único antes de executar efeitos.

## Produção

Antes do primeiro deploy, configure PostgreSQL gerenciado, Redis gerenciado, secrets manager, domínio HTTPS, OAuth2 redirect URI, Discord Application ID/public key/token, credenciais PSP e políticas de retenção/LGPD. Rode CI, migrations, testes de restauração e testes sandbox antes de habilitar vendas reais.

## Próximas fases

1. Reconciliação periódica de pagamentos + retries/backoff/circuit breaker.
2. Outbox/event bus e processamento assíncrono confiável.
3. Refund workflow e disputas/chargebacks.
4. Entrega digital e Discord Roles.
5. Cupons, cashback, afiliados e VIP.
6. Dashboard Next.js/TypeScript + OAuth2/account linking.
7. OpenTelemetry, métricas, Sentry e alertas.
8. Hardening, testes de concorrência E2E e deploy de produção.
