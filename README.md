# Architecture & Git Syllabus (AI-First SaaS Curriculum)

Document Version: 1.0 — November 2025
## Master Track: CTO/Architect Led, AI-Implemented

### Phase 0: Prereqs & Core Concepts
- REST API: GET, POST, PUT, DELETE
- JSON: Universal data language
- Authentication vs Authorization: AuthN (who) vs AuthZ (permissions)
- Webhooks: Automated notifications between services
- Environment Variables: Secrets management
- Git: Repo, Commit, Branch, Merge, Pull Request

Deliverable: Audit/read any AI-generated code with confidence

---
## Phase 1: Security & Architecture (Weeks 4-6)
CRITICAL - NOT covered in basic curricula

Hours: 40-55 hrs
| Week | Focus | Hours | Your Role |
|------|-------|-------|-----------|
| 4 | OWASP Top 10, SQL injection, XSS, CSRF | 12-15 | AUDIT AI code for vulnerabilities |
| 5 | Auth patterns (JWT, OAuth, sessions, RBAC) | 12-15 | SPECIFY auth requirements, review implementation |
| 6 | API security, rate limiting, input validation, secrets management | 12-15 | CREATE security checklist for all projects |

### Security Topics Overview
- OWASP Top 10: Most critical risks
- SQL Injection/XSS/CSRF: Mitigation & audit
- Auth Patterns: JWT vs Sessions, OAuth 2.0, RBAC
- Password Security: bcrypt, argon2, never plain text
- Rate Limiting, Input Validation: Prevent abuse
- Secrets Management, HTTPS/TLS: Always encrypted

Resources: PortSwigger Academy (FREE) • OWASP Guide • Auth0 Learning Hub
Deliverable: Security audit checklist for all AI output

#### Security Audit Checklist (Actionable)
- Verify input validation: server-side schema validation on all endpoints.
- Sanitize outputs: HTML escaping to prevent XSS; CSP headers present.
- Prevent SQLi: use parameterized queries/ORM; no string concatenation.
- CSRF defense: anti-CSRF tokens on state-changing requests; SameSite cookies.
- AuthN: secure login/registration; MFA optional; brute-force protection.
- AuthZ: RBAC roles enforced in handlers; deny-by-default.
- Session/JWT: httpOnly/secure cookies; short-lived JWT + refresh rotation.
- Secrets: stored in environment variables or secret manager; never in repo.
- Transport: HTTPS/TLS enforced; HSTS enabled; redirect HTTP→HTTPS.
- Rate limiting: per-IP/user; burst + sustained limits; 429 handling.
- Logging: security events, auth failures, admin actions; PII redaction.
- Error handling: generic messages; no stack traces in prod.
- Dependencies: SCA scan (e.g., `pip-audit`, `npm audit`), pinned versions.
- Webhooks: signature verification; replay protection; allowlist endpoints.

---
## Phase 2: Backend Architecture (Weeks 7-9)
FastAPI + Database Design

Hours: 35-45 hrs
| Week | Focus | Hours | Your Role |
|------|-------|-------|-----------|
| 7 | FastAPI patterns + API design principles | 12-15 | DESIGN endpoints, AI implements |
| 8 | Database schema architecture, migrations | 10-12 | YOU design schema, AI writes SQL |
| 9 | Webhooks, background jobs, async | 10-12 | UNDERSTAND flow, direct AI implementation |

### Backend Topics
- FastAPI Patterns: Request/response models, Pydantic
- API Design: RESTful, versioning, spec contract
- Schema Architecture: Entities, normalization, migrations
- Webhooks/Background Jobs: High-level flow
- Error Handling: Logging, fail gracefully

Deliverable: Can spec and architect full backend for AI build
#### API Review Checklist (Actionable)
- Clear versioning (e.g., `/v1`), consistent resource naming.
- Idempotency for PUT/PATCH; safe semantics for GET.
- Pagination, filtering, sorting standardized across endpoints.
- Request/response schemas documented; validation enforced.
- Error model with codes; 4xx vs 5xx separation; trace IDs.
- Auth required on non-public endpoints; scopes documented.
- Rate limits and caching headers where applicable.
- Background jobs: retries, dead-letter queues, observability.
- Webhooks: spec, retries with exponential backoff, signature check.

---
## Phase 3: Frontend Architecture (Weeks 10-11)
React/Next.js at Architect Level

Hours: 25-35 hrs
| Week | Focus | Hours | Your Role |
|------|-------|-------|-----------|
| 10 | React components, state, hooks | 12-15 | REVIEW AI for anti-patterns |
| 11 | Next.js App Router, data/server actions | 12-15 | SPECIFY page structure, AI builds |

### Frontend Topics
- Component Patterns: Split, props, composition
- State/Hooks: useState, useEffect, anti-patterns
- Next.js Router/Data Fetching: Layout, caching
- Server Actions & Responsive Design: Page flow

Deliverable: Spec UI, review AI for issues
---
## Phase 4: AI Integration (Weeks 12-14)
Your Differentiator

Hours: 45-55 hrs
| Week | Focus | Hours | Your Role |
|------|-------|-------|-----------|
| 12 | MCP, LLM APIs (OpenAI/Claude) | 12-15 | UNDERSTAND AI integration |
| 13 | Prompt engineering, streaming, tokens | 12-15 | DESIGN prompts, SPECIFY UX |
| 14 | RAG, vector databases, embeddings | 15-20 | ARCHITECT retrieval system |

### AI Topics
- MCP: Protocol for connecting AI to tools/data
- LLM APIs/Prompt Eng: Efficient, cost-optimized
- Streaming/Error Handling: Real-time responses
- RAG/Vector Search: Semantic search, Pinecone

Deliverable: Design/spec AI features, cost audit, retrieval architecture
---
## Phase 5: Payments & DevOps (Weeks 15-16)
Money + Deployment

Hours: 25-35 hrs
| Week | Focus | Hours | Your Role |
|------|-------|-------|-----------|
| 15 | Stripe integration, flows, edge cases | 12-15 | AUDIT, understand payment flow |
| 16 | Deployment, monitoring, environment | 12-15 | DEBUG production issues |

### Payments/DevOps
- Stripe Concepts: Products, webhooks, error testing
- Deployment: Vercel, Railway, environment variables
- Monitoring/Debugging: Sentry, logs, DNS connections

Deliverable: Can audit payment flow, deploy/debug
---
## Phase 6: MVP Build Sprint (Weeks 17-20)
Ship the Product

Hours: 60-80 hrs
| Week | Focus | Hours | Your Role |
|------|-------|-------|-----------|
| 17 | Spec MVP (schemas/endpoints/pages/AI) | 15-20 | YOU architect everything |
| 18 | Direct AI to build, review output | 15-20 | Continuous review |
| 19 | Integration, bug fixes, testing | 15-20 | Debug, direct fixes |
| 20 | Launch, beta users, iterate | 15-20 | Ship & learn |

### Build Steps
1. Spec all essentials (Week 17)
2. Iterate/Review AI code (Week 18)
3. Test & integrate, fix bugs (Week 19)
4. Deploy, collect feedback, iterate (Week 20)

Deliverable: Live MVP with paying users
---
## Skills Matrix

### MUST KNOW DEEPLY (Your architect/CTO scope)
- Security audit/patterns
- Schema design
- API architecture
- Code review/anti-pattern
- Debugging strategies
- Prompt specification
- System architecture
- Payment flows

### CAN DELEGATE TO AI (You review)
- Boilerplate code
- Styling
- CRUD endpoints
- Tests/configs
- Components/docs
- SQL migrations

---
## Weekly Commitment
- 3-4 hrs/day × 5-6 days = 15-24 hrs/week
- 20 weeks × 15-20 hrs = 300-400 hrs total

---
## Success Metrics

### Phase Success Checklist
- Phase 0 ✓ Read Python/JS & explain/code schema
- Phase 1 ✓ Audit for OWASP, own checklist, auth requirements
- Phase 2-3 ✓ Backend arch, frontend spec, anti-pattern review
- Phase 4 ✓ Spec AI features, cost/audit, RAG architecture
- Phase 5 ✓ Stripe flow, production debug
- Phase 6 ✓ MVP live, paying users, shipped

---
## Curriculum Reference

| Metric      | Old Track B     | New Track B       |
|-------------|-----------------|-------------------|
| Duration    | 9 months        | 4-5 months        |
| Hours       | 540-780         | 250-350           |
| Focus       | Write code      | Architect/Review  |
| AI Role     | Assist          | Primary builder   |
| Your Role   | Developer       | CTO/Architect     |

---
## Learning Resources

- Codecademy (SQL, Python 3, JavaScript)
- YouTube: Corey Schafer, Web Dev Simplified, Fireship, Theo
- Udemy: Complete SQL Bootcamp
- OWASP, PortSwigger, Auth0, FastAPI/Next.js Official Docs
- OpenAI/Anthropic API Docs
- Pinecone Docs
- Stripe/Vercel/Railway Docs

---
Purpose: Revised SaaS dev curriculum, AI-optimized

---

## Weekly Planner (Weeks 1-20)

| Week | Phase | Focus | Target Hours |
|------|-------|-------|--------------|
| 1 | 0 | Core concepts (REST, JSON, Git) | 15-20 |
| 2 | 0 | AuthN/AuthZ, webhooks, env vars | 15-20 |
| 3 | 0 | Code reading/audit fundamentals | 15-20 |
| 4 | 1 | OWASP Top 10, SQLi/XSS/CSRF | 12-15 |
| 5 | 1 | Auth patterns: JWT/OAuth/Sessions/RBAC | 12-15 |
| 6 | 1 | API security, rate limit, validation, secrets | 12-15 |
| 7 | 2 | FastAPI patterns, API design | 12-15 |
| 8 | 2 | DB schema architecture, migrations | 10-12 |
| 9 | 2 | Webhooks, background jobs, async | 10-12 |
| 10 | 3 | React components/state/hooks | 12-15 |
| 11 | 3 | Next.js App Router, data/server actions | 12-15 |
| 12 | 4 | MCP, LLM APIs integration | 12-15 |
| 13 | 4 | Prompt engineering, streaming, tokens | 12-15 |
| 14 | 4 | RAG, embeddings, vector DB | 15-20 |
| 15 | 5 | Stripe integration, flows, edge cases | 12-15 |
| 16 | 5 | Deployment, monitoring, environment | 12-15 |
| 17 | 6 | Spec MVP (schemas/endpoints/pages/AI) | 15-20 |
| 18 | 6 | AI build, code review loop | 15-20 |
| 19 | 6 | Integration, bug fixes, testing | 15-20 |
| 20 | 6 | Launch, beta users, iterate | 15-20 |

### Time Commitment Summary
- Weekly: 15-24 hrs (3-4 hrs/day × 5-6 days)
- Total: 300-400 hrs across 20 weeks

### Templates
- Security Checklist: `security-checklist.md`
- API Spec Template: `api-spec-template.md`
- Schema Design Template: `schema-design-template.md`
- Weekly Planner: `weekly-planner.md`
# personal-plan