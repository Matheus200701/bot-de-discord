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

## Fase 2/3 implementada

A persistência de produtos saiu do armazenamento em memória e passou para PostgreSQL. O domínio agora possui `Cart`, `CartItem`, `OrderItem` e `InventoryReservation`, com migrations Alembic (`0001_core` e `0002_cart_checkout`). O checkout recalcula os preços no servidor, bloqueia as linhas de produto dentro da transação, reserva estoque e transforma o carrinho em pedido de forma atômica.

A chave de idempotência do pedido continua protegida por constraint única. A máquina de estados impede transições arbitrárias e mantém estados terminais explícitos.

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
- `POST /webhooks/payments/{provider}`

## Regras financeiras

Valores de dinheiro usam unidades menores inteiras (`price_minor`) no domínio persistente. O cliente nunca define o preço final; a aplicação recalcula o checkout no servidor. Eventos de pagamento devem ser persistidos com `provider_event_id` único antes de executar efeitos.

## Produção

Antes do primeiro deploy, configure PostgreSQL gerenciado, Redis gerenciado, secrets manager, domínio HTTPS, OAuth2 redirect URI, Discord Application ID/public key/token, PSPs e políticas de retenção/LGPD. Rode CI, migrations e testes de restauração antes de habilitar vendas reais.

## Próximas fases

1. Adaptadores PIX/Mercado Pago/Stripe com assinatura e reconciliação reais.
2. Reserva com expiração/release e workers assíncronos.
3. Entrega digital e Discord Roles.
4. Cupons, cashback, afiliados e VIP.
5. Tickets, reembolsos e disputas.
6. Dashboard Next.js/TypeScript + OAuth2/account linking.
7. OpenTelemetry, métricas, Sentry e alertas.
8. Hardening, testes de concorrência E2E e deploy de produção.
