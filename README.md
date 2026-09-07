# Discord Commerce Platform 2026

Plataforma de comércio para Discord, estruturada como App + API + banco + pagamentos + entrega + observabilidade, em vez de um bot monolítico.

## Arquitetura

Discord App → Discord Layer → Service Layer → Commerce / Payments / Inventory / Fulfillment / Support / Customers → Event System → PostgreSQL + Redis → External APIs.

## Stack

- Python 3.12+
- discord.py 2.x
- FastAPI + Pydantic
- SQLAlchemy 2.x + asyncpg + Alembic
- PostgreSQL 17
- Redis 8
- httpx
- Docker + GitHub Actions

## Fase 8 — entrega digital e Discord Roles

A confirmação do pagamento agora dispara fulfillment assíncrono através do outbox. O produto declara seu tipo de entrega em `metadata_json.delivery`.

Exemplo de cargo Discord:

```json
{
  "delivery": {
    "type": "discord_role",
    "guild_id": "123456789012345678",
    "role_id": "234567890123456789"
  }
}
```

Exemplo de link digital externo:

```json
{
  "delivery": {
    "type": "digital_link",
    "url": "https://storage.example.invalid/object"
  }
}
```

O conteúdo privado não é armazenado no banco como texto bruto; a plataforma guarda somente a referência de entrega. O endpoint `GET /api/v1/orders/{order_id}/deliveries` permite ao comprador consultar suas entregas, e links digitais só são expostos quando o fulfillment está `DELIVERED`.

Entregas possuem estados persistentes (`PENDING`, `PROCESSING`, `DELIVERED`, `FAILED`, `REVOKED`) e são idempotentes por pedido/produto/tipo. Refund total agenda revogação de cargos entregues. Uma proteção de corrida impede que uma entrega pendente seja executada depois que o pedido foi revertido/refundado.

### Discord Role Delivery

A integração usa a API HTTP oficial do Discord. Adicionar/remover cargo requer `MANAGE_ROLES`; cargos gerenciados não são aceitos. A API também aplica as restrições de hierarquia dos cargos. O worker usa o outbox para repetir operações transitórias sem duplicar a concessão lógica do fulfillment.

## Fases 2–7

A base anterior já inclui checkout transacional, reservas de estoque com expiração, Mercado Pago Pix, webhooks assinados, reconciliação, outbox, retries/circuit breaker, refunds, disputes/chargebacks e ledger de partidas dobradas.

## Endpoints atuais

- `GET /health`
- `GET /ready`
- `GET /api/v1/products`
- `POST /api/v1/products`
- `GET /api/v1/products/{product_id}`
- `POST /api/v1/cart/items`
- `POST /api/v1/checkout`
- `POST /api/v1/payments/mercadopago/pix`
- `GET /api/v1/orders/{order_id}/deliveries`
- `POST /api/v1/orders/{order_id}/refund` (admin)
- `POST /webhooks/payments/mercadopago_pix`
- `POST /webhooks/payments/mercadopago_chargebacks`

## Regras de entrega

O fulfillment nunca libera acesso somente porque o pedido foi criado. O gatilho é um estado de pagamento confirmado. Toda mutação externa ocorre no worker e pode ser repetida com segurança. Falhas permanentes são marcadas e permanecem recuperáveis pelo outbox/DLQ.

## Produção

Antes do primeiro deploy, configure PostgreSQL gerenciado, Redis gerenciado, secret manager, HTTPS, OAuth2 redirect URI, Discord credentials, credenciais PSP, `COMMERCE_ADMIN_KEY` forte, permissões mínimas do bot e políticas de retenção/LGPD. Rode CI, migrations, testes de restauração e testes sandbox antes de habilitar vendas reais.

## Próximas fases

1. Cupons, cashback, afiliados e VIP.
2. Dashboard Next.js/TypeScript + OAuth2/account linking.
3. OpenTelemetry, métricas, Sentry e alertas.
4. Hardening, testes de concorrência E2E, sandbox e deploy de produção.
