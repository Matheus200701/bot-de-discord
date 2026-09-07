# Security Hardening — Phase 12

Phase 12 aligns the API hardening baseline with OWASP ASVS 5.0 concepts for session management, authorization, logging and secure configuration.

## API boundary

- `SecurityMiddleware` adds a correlation `X-Request-ID` when one is not supplied.
- Security response headers are added centrally.
- `MAX_REQUEST_BODY_BYTES` rejects oversized requests before application handlers.
- `TRUSTED_HOSTS` can restrict accepted HTTP Host headers.
- HSTS is opt-in with `ENFORCE_HSTS=true` and must only be enabled when the service is exclusively reached over HTTPS.

## Session and authentication

- Dashboard sessions remain opaque random tokens; only hashes are persisted.
- OAuth state is single-use and browser-bound.
- Administrative authentication must not use Discord user IDs supplied by clients as proof of identity.
- Sensitive administrative actions should use the authenticated dashboard/RBAC path rather than the legacy bootstrap admin key.

## Tenant isolation

Every commerce record must retain `tenant_id`, and queries crossing tenant boundaries must be rejected by authorization checks. New modules must not introduce unscoped lookups by object ID alone.

## Payments

- Provider webhooks remain signature-validated.
- Payment state is confirmed server-to-server.
- Idempotency keys are mandatory for financial mutations.
- Provider credentials must remain server-side and must be supplied through secret management in production.

## Logging and telemetry

Do not log access tokens, cookies, payment credentials, PIX payloads, full request bodies, or session tokens. Security events should include enough metadata to reconstruct who/what/when/where without storing the protected value itself.

## CI / release gate

A production release requires, at minimum:

1. Ruff and MyPy clean.
2. Unit/integration tests passing.
3. Bandit and dependency audit clean or explicitly reviewed.
4. Database migrations applied in a disposable environment.
5. E2E checkout + webhook + fulfillment + refund scenarios passing.
6. Concurrency tests for stock, idempotency and payment events.
7. Secret scanning and container/image scanning.
8. HTTPS termination and secure cookie configuration verified.

OWASP ASVS 5.0 groups these controls across authentication, session management, authorization, API security, configuration, logging and secure coding.
