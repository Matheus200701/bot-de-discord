# Discord Commerce Platform 2026

Plataforma de comércio para Discord, estruturada como App + API + banco + pagamentos + entrega + observabilidade, em vez de um bot monolítico.

## Fase 9 — cupons, cashback, afiliados e VIP

O checkout agora suporta promoções e fidelização sem usar `float` para valores financeiros.

- **Cupons:** percentual em basis points ou valor fixo, validade, moeda, pedido mínimo, limite global e por usuário, limite de desconto e consumo idempotente.
- **Cashback:** carteira por tenant/usuário e ledger append-only; créditos são gerados após pagamento confirmado e possuem chave de idempotência.
- **Afiliados:** códigos únicos por tenant, comissão configurável em basis points e atribuição idempotente por pedido.
- **VIP:** níveis baseados em gasto confirmado, com desconto e cashback próprios; o nível é recalculado a partir dos pedidos pagos em vez de depender de contador financeiro mutável.
- **Snapshot do pedido:** `order_promotions` registra cupom, afiliado, desconto e cashback aplicado no checkout.

### Exemplos

Checkout com promoção:

`POST /api/v1/checkout` com `coupon_code` e/ou `affiliate_code`.

Administração:

- `POST /api/v1/promotions/coupons`
- `POST /api/v1/promotions/affiliates`
- `POST /api/v1/promotions/vip/tiers`
- `GET /api/v1/promotions/cashback/{discord_user_id}`

As rotas administrativas usam a credencial existente `X-Commerce-Admin-Key`; autenticação/RBAC granular continua planejada para a camada administrativa definitiva.

## Fase 8 — entrega digital e Discord Roles

A confirmação do pagamento dispara fulfillment assíncrono através do outbox. O produto declara seu tipo de entrega em `metadata_json.delivery`. Adicionar/remover cargo usa a API oficial do Discord e requer `MANAGE_ROLES`; o bot não precisa de `ADMINISTRATOR`.

## Fases 2–7

A base anterior inclui checkout transacional, reservas de estoque, Mercado Pago Pix, webhooks assinados, reconciliação, outbox/retries/circuit breaker, refunds, disputes/chargebacks e ledger de partidas dobradas.

## Endpoints principais

- `GET /health`
- `GET /ready`
- `GET /api/v1/products`
- `POST /api/v1/products`
- `POST /api/v1/cart/items`
- `POST /api/v1/checkout`
- `POST /api/v1/payments/mercadopago/pix`
- `GET /api/v1/orders/{order_id}/deliveries`
- `POST /api/v1/orders/{order_id}/refund`
- `POST /api/v1/promotions/coupons`
- `POST /api/v1/promotions/affiliates`
- `POST /api/v1/promotions/vip/tiers`
- `GET /api/v1/promotions/cashback/{discord_user_id}`

## Regras financeiras

Valores monetários permanecem em unidades menores inteiras. Percentuais são representados em basis points. Cashback, comissão e descontos são idempotentes e associados ao tenant. O preço final é calculado no servidor.

## Produção

Antes de vendas reais, configure PostgreSQL/Redis gerenciados, secret manager, HTTPS, OAuth2, credenciais Discord/PSP, `COMMERCE_ADMIN_KEY` forte, permissões mínimas e políticas LGPD. Execute CI, migrations, testes de restauração, concorrência e sandbox E2E antes de remover o estado Draft do PR.

## Próximas fases

1. Dashboard Next.js/TypeScript + OAuth2/account linking + RBAC.
2. OpenTelemetry, métricas, Sentry e alertas.
3. Hardening, testes E2E de concorrência, sandbox, segurança e deploy de produção.
