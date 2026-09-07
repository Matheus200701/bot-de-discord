# Security Hardening — Phase 14

Phase 14 extends the Phase 13 production gate with executable PostgreSQL/Redis integration checks and a reusable distributed rate-limiting primitive.

## API boundary

- `SecurityMiddleware` adds `X-Request-ID` and security headers.
- `MAX_REQUEST_BODY_BYTES` rejects oversized requests using `Content-Length` and streamed-body accounting.
- `TRUSTED_HOSTS` restricts accepted HTTP Host headers when configured.
- Unsupported HTTP methods such as `TRACE` are rejected.
- HSTS is opt-in with `ENFORCE_HSTS=true` and must only be enabled for HTTPS-only deployments.

## Distributed rate limiting

`packages/security/rate_limit.py` provides a Redis-backed fixed-window limiter. The primitive is intentionally not attached globally: production limits must be selected per route and threat model. Before go-live, apply explicit limits to authentication, financial mutations, administrative mutations and webhook endpoints where appropriate.

The limiter must not replace authorization or financial idempotency. Database/PSP idempotency remains authoritative for mutations involving money.

## Integration gate

`.github/workflows/phase14-integration.yml` starts disposable PostgreSQL 16 and Redis 7 services, installs the project, applies `alembic upgrade head`, and runs integration-marked tests. The suite performs real PostgreSQL `SELECT 1`, Redis `PING`, and concurrent Redis `INCR` checks.

## Automated security gates

Dedicated workflows cover CodeQL, Gitleaks, `pip-audit`, and Trivy container scanning. They must be green or explicitly reviewed before release.

## Release checklist

1. Ruff and MyPy clean.
2. Unit and integration tests passing.
3. Bandit and dependency audit clean or explicitly reviewed.
4. Disposable database migrations pass.
5. E2E checkout + webhook + fulfillment + refund pass.
6. Multi-connection concurrency tests pass for stock and idempotency.
7. Secret and container scanning pass.
8. HTTPS termination and secure cookie configuration verified.
9. Managed secret storage and per-tenant PSP credential isolation verified.
10. Dashboard CSRF protection verified.
11. Legacy admin-key authentication removed or formally deprecated with migration controls.
12. Release commit and image provenance reviewed before deployment.

## Current limitations

Phase 14 does not claim production readiness. Remaining deployment work includes full E2E checkout/payment/fulfillment/refund tests, PSP sandbox certification, managed secret storage, per-tenant PSP credentials, applying route-specific Redis rate limits, complete dashboard CSRF protection, removal/deprecation of the legacy admin key, backup/restore drills, and production HTTPS/load-balancer validation.

OWASP ASVS 5.0 is used as a security framework and verification baseline; the project does not claim ASVS certification.
