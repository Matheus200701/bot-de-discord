# Fase 16 — Multi-Tenant Security, Managed Secrets & CSRF

## Objetivo

Reduzir o blast radius entre tenants e remover a dependência de credenciais PSP globais. OWASP ASVS 5.0 é usado como referência de verificação, sem alegar certificação.

## Entregas

- Double-submit CSRF para mutações autenticadas por cookie do Dashboard.
- Token CSRF aleatório por sessão/login, cookie `Secure` + `SameSite=Lax` e header obrigatório em mutações.
- Logout e mutations financeiras/admin do Dashboard exigem CSRF.
- `TenantSecretResolver` cria namespace de segredo por tenant para Mercado Pago.
- Em `APP_ENV=production`, o provider baseado apenas em ambiente é recusado.
- Adapter HashiCorp Vault KV v2 disponível para secrets gerenciados.
- `PaymentProviderFactory` cria Mercado Pago Pix com credenciais específicas do tenant.
- Criação de pagamento usa o factory tenant-scoped.
- Webhooks Mercado Pago identificam o PaymentIntent/tenant antes de validar a assinatura, evitando uma chave global compartilhada.
- Webhooks desconhecidos são rejeitados em vez de processados com segredo global.
- Testes verificam isolamento de namespace e bloqueio do provider de ambiente em produção.

## Secret management

Desenvolvimento/teste podem usar variáveis de ambiente. Produção deve usar um secret manager com least privilege, rotação, auditoria e revogação. Segredos não são persistidos no banco nem incluídos em artefatos de build.

## Segurança multi-tenant

Consultas administrativas usam `tenant_context`, validando sessão, membership ativo e papel mínimo. Credenciais PSP são resolvidas por `tenant_id`; um tenant sem seu próprio segredo não pode cair para a credencial de outro tenant em produção.

## Limitações

O adapter Vault não configura sozinho a infraestrutura: políticas ACL, autenticação da workload, rotação e auditoria precisam ser configuradas no ambiente de produção. Ainda permanecem backup/restore, HTTPS/load balancer, execução real do sandbox PSP, cobertura completa de todas as mutations e remoção/depreciação formal do admin key legado.
