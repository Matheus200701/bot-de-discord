# Security Hardening — Phase 15

Phase 15 extends the production gate with executable PostgreSQL/Redis integration checks, atomic distributed rate limiting, and a defined PSP sandbox validation gate.

## API boundary

- `SecurityMiddleware` adds `X-Request-ID` and security headers.
- `MAX_REQUEST_BODY_BYTES` rejects oversized requests using `Content-Length` and streamed-body accounting.
- `TRUSTED_HOSTS` restricts accepted HTTP Host headers when configured.
- Unsupported HTTP methods such as `TRACE` are rejected.
- HSTS is opt-in with `ENFORCE_HSTS=true` and must only be enabled for HTTPS-only deployments.

## Distributed rate limiting

`packages/security/rate_limit.py` provides a Redis-backed fixed-window limiter. Counter increment and first-use expiration are atomic through a Redis Lua script. The primitive is intentionally not attached globally: production limits must be selected per route and threat model. Before go-live, apply explicit limits to authentication, financial mutations, administrative mutations and webhook endpoints where appropriate.

The limiter must not replace authorization or financial idempotency. Database/PSP idempotency remains authoritative for mutations involving money.

## Integration gate

GitHub Actions starts disposable PostgreSQL and Redis services, installs the project, applies `alembic upgrade head`, and runs integration-marked tests. The suite performs real PostgreSQL `SELECT 1`, Redis `PING`, concurrent Redis `INCR`, and distributed rate-limit checks.

## Payment sandbox gate

The Mercado Pago adapter remains isolated from the domain layer. Real credentials must never be committed. Sandbox execution must use provider test credentials stored as CI/environment secrets and validate checkout, payment creation, signed webhook processing, fulfillment and refund paths. This phase defines the gate but does not claim provider certification until those scenarios have actually passed against the provider sandbox.

## Automated security gates

Dedicated workflows cover CodeQL, Gitleaks, `pip-audit`, and Trivy container scanning. They must be green or explicitly reviewed before release.

## Release blockers

Production sales remain blocked until E2E checkout/payment/fulfillment/refund, multi-connection PostgreSQL concurrency/idempotency tests, PSP sandbox validation, managed secret storage, per-tenant PSP credential isolation, complete dashboard CSRF protection, removal/deprecation of the legacy admin key, backup/restore drills, and HTTPS/load-balancer validation are completed.

OWASP ASVS 5.0 is used as a security framework and verification baseline; the project does not claim ASVS certification.
