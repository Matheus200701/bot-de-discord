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

## Discord 2026

O projeto foi auditado contra a documentação oficial atual. Application Commands, user/guild installation, OAuth2, Components, Modals, Account Linking e monetização oficial são tratados segundo o suporte e as restrições documentadas. Veja `DISCORD_COMPATIBILITY.md`.

A arquitetura não assume que Premium Apps seja um gateway universal para qualquer mercadoria: SKUs/assinaturas nativas do Discord ficam separados da camada externa de pagamentos e dependem de elegibilidade do Discord.

## Desenvolvimento

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
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

## Endpoints iniciais

- `GET /health`
- `GET /ready`
- `GET /api/v1/products`
- `POST /api/v1/products`
- `GET /api/v1/products/{product_id}`
- `POST /webhooks/payments/{provider}`

## Regras financeiras

Valores de dinheiro usam unidades menores inteiras (`price_minor`) no domínio persistente. O cliente nunca define o preço final; a aplicação deve recalcular o checkout no servidor. Eventos de pagamento devem ser persistidos com `provider_event_id` único antes de executar efeitos.

## Produção

Antes do primeiro deploy, configure PostgreSQL gerenciado, Redis gerenciado, secrets manager, domínio HTTPS, OAuth2 redirect URI, Discord Application ID/public key/token, PSPs e políticas de retenção/LGPD. Rode CI, migrations e testes de restauração antes de habilitar vendas reais.

## Próximas fases

1. Persistência completa e Alembic.
2. Carrinho, reservas transacionais e state machine de pedidos.
3. Adaptadores PIX/Mercado Pago/Stripe.
4. Entrega digital e Discord Roles.
5. Cupons, cashback, afiliados e VIP.
6. Tickets, reembolsos e disputas.
7. Dashboard Next.js/TypeScript.
8. OpenTelemetry, métricas, Sentry e reconciliação.
9. Hardening, testes de concorrência e deploy.
