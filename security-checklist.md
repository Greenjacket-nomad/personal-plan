# Security Audit Checklist

Use this checklist to audit AI-generated code and project configurations.

## Input & Output Safety
- Validate all inputs server-side (schema validation).
- Enforce type/length/range constraints; reject unknown fields.
- Escape/encode outputs; set CSP headers to mitigate XSS.

## Injection & CSRF
- Use parameterized queries/ORM only; no string concatenation in SQL.
- Apply CSRF tokens on state-changing requests; SameSite cookies.

## Authentication & Authorization
- Enforce RBAC with deny-by-default authorization checks per handler.
- Use secure sessions (httpOnly, secure) or short-lived JWT + refresh rotation.
- Rate-limit login; lockout/brute-force protection; MFA optional.

## Secrets & Config
- Store secrets only in environment variables or a secret manager.
- Never commit secrets; rotate keys periodically.

## Transport & Cookies
- Enforce HTTPS/TLS; enable HSTS; redirect HTTP→HTTPS.
- Mark cookies as `HttpOnly`, `Secure`, and `SameSite` appropriately.

## Rate Limiting & Abuse Prevention
- Implement per-IP and per-user limits; handle 429 gracefully.
- Protect expensive endpoints; add caching where appropriate.

## Logging & Errors
- Log security events, auth failures, admin actions; redact PII.
- Return generic error messages; no stack traces in production.

## Dependencies & Build
- Run `pip-audit` / `npm audit`; pin versions; review licenses.
- Monitor CVEs; patch vulnerable packages quickly.

## Webhooks
- Verify signatures; prevent replays; retry with backoff.
- Allowlist webhook sources and endpoints.

## Verification Commands (examples)
```bash
# Python
pip install pip-audit
pip-audit

# Node.js
npm audit --production

# Headers (curl examples)
curl -I https://yourdomain.com | grep -E "Strict-Transport-Security|Content-Security-Policy|X-Content-Type-Options|X-Frame-Options"
```
