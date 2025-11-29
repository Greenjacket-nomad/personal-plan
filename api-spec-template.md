# API Spec Template (Architect Draft)

## Overview
- Purpose: What problem does this API solve?
- Audience: Internal/External
- Version: v1

## Authentication & Authorization
- Auth mechanism: Sessions (cookies) or JWT (bearer)?
- Scopes/Roles: Define RBAC roles and required scopes per endpoint.

## Resources & Endpoints
- Base URL: `/v1`
- Conventions: kebab-case for paths, snake_case for JSON fields, UTC timestamps

### Example Resource: `users`
- `GET /v1/users` — List users (pagination)
- `POST /v1/users` — Create user
- `GET /v1/users/{id}` — Get user
- `PUT /v1/users/{id}` — Replace user
- `PATCH /v1/users/{id}` — Update user
- `DELETE /v1/users/{id}` — Delete user

## Request/Response Models
- Define Pydantic/JSON schemas for each endpoint.
- Include examples for success and error responses.

## Pagination/Filtering/Sorting
- Pagination: `limit`, `cursor` or `page`, `per_page`
- Filtering: `?status=active`
- Sorting: `?sort=created_at:desc`

## Idempotency & Safety
- Idempotent methods: `PUT`, `DELETE` should be idempotent.
- Use `Idempotency-Key` header where needed.

## Errors
- Standard error envelope: `{ code, message, details?, trace_id }`
- 4xx vs 5xx split; map to domain codes.

## Rate Limiting & Caching
- Describe per-user/IP limits and relevant headers.
- Caching: ETag/Last-Modified where appropriate.

## Webhooks (if applicable)
- Event names, payload schema, signature scheme, retry/backoff.

## Observability
- Logging: request IDs, trace IDs, structured logs.
- Metrics: latency, error rates, rate limit hits.

## Non-Functional Requirements
- SLOs: availability, latency.
- Security: OWASP alignment, secret handling.

## Checklist
- [ ] Schemas validated server-side
- [ ] Auth required on protected endpoints
- [ ] Errors standardized
- [ ] Pagination/filters consistent
- [ ] Rate limits documented
- [ ] Webhook signatures verified
