# Fase 17 — Full Multi-Tenant Security & Financial RBAC

## Objetivo

Eliminar autorização administrativa por segredo compartilhado, remover o tenant padrão das rotas administrativas e tornar as operações financeiras e de loyalty tenant-scoped.

## Entregas

- Refund administrativo usa Dashboard OAuth2 + membership ativo + `ADMIN/OWNER` + CSRF.
- Criação de produtos usa Dashboard + `OPERATOR+` + CSRF.
- Coupons, affiliates e VIP tiers usam `tenant_id` explícito na rota e sessão Dashboard + `ADMIN` + CSRF.
- Cashback administrativo usa `tenant_id` explícito e sessão Dashboard + `ADMIN`.
- Removido o uso de `COMMERCE_ADMIN_KEY` das operações de promotions.
- Removido o uso de `DEFAULT_TENANT_ID` de promotions.
- `starts_at`/`ends_at` de coupons agora são persistidos e validados.
- Catálogo, carrinho, checkout, pagamento e entregas usam tenant explícito e consultas tenant-scoped.
- Credenciais Mercado Pago continuam resolvidas por tenant através do `PaymentProviderFactory`.

## Modelo de autorização

`VIEWER`: leitura operacional.

`OPERATOR`: catálogo e operações não financeiras.

`ADMIN`: operações administrativas e financeiras.

`OWNER`: privilégios administrativos máximos do tenant.

A identidade administrativa vem de sessão OAuth2 do Discord; IDs enviados pelo cliente não são prova de privilégio.

## Segurança

OWASP ASVS 5.0 exige que controles de acesso sejam aplicados no servidor, com least privilege e proteção contra manipulação de atributos usados pela autorização. citeturn945026search5turn945026search7

As APIs customer-facing ainda precisam de um mecanismo confiável de binding entre a requisição e o guild/instalação Discord antes do go-live. OAuth2 do Discord suporta `GUILD_INSTALL` e `USER_INSTALL`, e recomenda `state` para proteger o fluxo OAuth2. citeturn557521view0

## Produção

Ainda não declarar readiness. Executar CI, E2E, isolamento com dois tenants, sandbox PSP, Secret Manager real, tenant binding Discord no gateway/bot, rate limits por rota, backup/restore e HTTPS/load balancer.
