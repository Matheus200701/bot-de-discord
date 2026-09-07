# Fase 17 — Full Multi-Tenant Security & Financial RBAC

## Objetivo

Eliminar a autorização financeira legada baseada em segredo compartilhado e tornar o tenant explícito nas operações comerciais públicas.

## Entregas

- Removido o endpoint legado de refund com `X-Commerce-Admin-Key`/`COMMERCE_ADMIN_KEY`.
- Refund administrativo agora exige sessão Discord, membership ativo, papel `ADMIN` ou `OWNER` e CSRF.
- Criação administrativa de produtos foi movida para o Dashboard com tenant derivado do contexto autenticado e papel `OPERATOR+`.
- Catálogo, carrinho, checkout, pagamento e entregas não dependem mais de `DEFAULT_TENANT_ID`.
- Operações comerciais exigem `tenant_id` explícito e consultas cruzam `tenant_id` com IDs de objetos.
- Credenciais Mercado Pago são resolvidas por tenant.
- Testes de CSRF e RBAC adicionados.

## Modelo de autorização

`VIEWER`: leitura operacional.

`OPERATOR`: catálogo e operações não financeiras.

`ADMIN`: operações administrativas e financeiras, incluindo refund.

`OWNER`: privilégios administrativos máximos do tenant.

A identidade do Dashboard vem da sessão OAuth2; um Discord user ID fornecido pelo cliente não é tratado como prova de identidade administrativa.

## Limitação importante

O tenant informado nas APIs de checkout/customer-facing ainda precisa ser associado a uma identidade de instalação/guild ou contexto confiável do Discord em uma etapa posterior. Um cliente arbitrário não deve receber autorização para escolher qualquer tenant. A separação de dados no banco impede cross-tenant object lookup, mas a autorização do contexto de entrada deve ser fechada no gateway/bot antes do go-live.

## Produção

Ainda não declarar readiness. Executar CI, testes E2E, validação de isolamento com dois tenants, sandbox PSP, Secret Manager real, webhooks tenant-aware, rate limits por rota, backup/restore e HTTPS/load balancer.