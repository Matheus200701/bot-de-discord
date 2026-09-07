# Security Hardening — Phase 13

Phase 13 turns the Phase 12 security baseline into a repeatable production release gate. The controls are mapped conceptually to OWASP ASVS 5.0 across API security, configuration, secure coding, session management and logging.

## API boundary

- `SecurityMiddleware` adds a correlation `X-Request-ID` when one is not supplied.
- Security response headers are added centrally.
- `MAX_REQUEST_BODY_BYTES` rejects oversized requests using both `Content-Length` and streamed-body accounting.
- `TRUSTED_HOSTS` can restrict accepted HTTP Host headers.
- Unsupported HTTP methods such as `TRACE` are rejected.
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

## Automated security gates

The repository now includes dedicated GitHub Actions for:

- CodeQL analysis for Python.
- Secret scanning with Gitleaks.
- Python dependency auditing with `pip-audit`.
- Container vulnerability scanning with Trivy for HIGH/CRITICAL OS and library vulnerabilities.

These checks are additional release gates; a green local test suite alone is not sufficient for production deployment.

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
9. No unreviewed HIGH/CRITICAL container vulnerabilities.
10. Release commit and image provenance reviewed before deployment.

## Current limitations

Phase 13 does not claim production readiness by itself. The following remain deployment responsibilities unless explicitly implemented later: managed secret storage, per-tenant PSP credential isolation, full Redis-backed rate limiting, complete dashboard CSRF protection, live payment-provider sandbox certification, disposable PostgreSQL/Redis E2E execution in CI, and production HTTPS/load-balancer validation.

OWASP ASVS 5.0 provides the verification baseline; the project uses it as a security framework rather than claiming full ASVS certification.
