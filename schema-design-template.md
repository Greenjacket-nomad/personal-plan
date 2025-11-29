# Schema Design Template

## Domain Overview
- Core entities and relationships (ERD sketch).
- Boundaries: which services own which data.

## Entities
- `users` — id, email (unique), password_hash, created_at
- `organizations` — id, name, created_at
- `memberships` — user_id, organization_id, role

## Keys & Constraints
- Primary keys, foreign keys, unique constraints.
- Not null vs nullable fields.

## Indexes
- List indexes to support queries; include composite indexes.

## Migrations
- Migration plan and tooling (Alembic, Prisma, Flyway).
- Backfill strategy; zero-downtime notes.

## Security & Privacy
- Store only necessary PII; encrypt at rest where needed.
- Row-level permissions considerations.

## Performance
- Query patterns; avoid N+1; pagination strategies.
- Caching layers if applicable.

## Checklist
- [ ] Entities normalized (or justified denormalization)
- [ ] Constraints prevent invalid states
- [ ] Indexes support critical queries
- [ ] Migrations safe and reversible
- [ ] Sensitive data protected
