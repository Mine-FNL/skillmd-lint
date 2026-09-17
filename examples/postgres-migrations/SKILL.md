---
name: postgres-migrations
description: >-
  Use when authoring or reviewing a PostgreSQL schema migration that runs
  against a live production database. Applies when the user asks for
  "add a column", "add an index", "backfill", "ALTER TABLE safely", or
  "zero-downtime migration". Do not use for application-level ORM
  migrations on a dev database, for greenfield schemas with no traffic,
  or for non-PostgreSQL databases (MySQL, SQLite).
skill_type: domain-expert
domain_focus: database
tags:
  - postgres
  - postgresql
  - migrations
  - sql
  - database
  - schema
version: 1.0.0
version_notes: Reference playbook for expand-and-contract migrations on PG ≥ 12.
token_budget: 1700
---

## When to use

Use when a schema change has to roll forward against a database that
already carries traffic. The cardinal rule is that every migration is
two migrations: the *expand* step that adds the new shape in parallel
with the old, and the *contract* step that removes the old shape once
every caller has moved over. In between, you backfill, you dual-write,
and you read from both sides.

Always think about the lock each statement takes before issuing it:

- `ALTER TABLE ... ADD COLUMN` (nullable, no default) → `AccessExclusive`
  briefly, but metadata-only since PostgreSQL 11.
- `CREATE INDEX` (without `CONCURRENTLY`) → blocks writes for the
  duration of the build.
- `ALTER TABLE ... ALTER COLUMN ... SET NOT NULL` → scans and rewrites
  the whole table; plan a separate expand step.
- `ALTER TABLE ... ADD CONSTRAINT FOREIGN KEY` → takes a
  `ShareRowExclusive` lock that queues behind every write.

## Examples

A safe three-step rollout for adding a `status` column with a NOT NULL
default to a 100M-row table:

```sql
-- 1. Expand: nullable, no default. Cheap metadata-only on PG ≥ 11.
ALTER TABLE orders ADD COLUMN status text;

-- 2. Backfill in batches so no single transaction holds the row lock
--    long enough to stall writes.
UPDATE orders SET status = 'pending' WHERE status IS NULL AND id BETWEEN $1 AND $2;

-- 3. Contract: flip to NOT NULL only when every row is populated.
ALTER TABLE ALTER COLUMN status SET NOT NULL;
```

For example, building the supporting index without blocking writes:

```sql
CREATE INDEX CONCURRENTLY orders_status_idx ON orders (status);
```

The `CONCURRENTLY` keyword lets the index build take two passes over the
table while reads and writes proceed normally. It cannot run inside an
explicit transaction block.

## Pitfalls to avoid

- Do not run `CREATE INDEX` (without `CONCURRENTLY`) on a hot table; the
  build will queue every write behind the lock and look like an outage.
- Do not `ALTER TABLE ... ALTER COLUMN ... TYPE` in place on a wide
  table; the rewrite takes a long lock. Add a new column, dual-write,
  backfill, swap, drop.
- Do not backfill in one transaction; the row lock and the WAL volume
  will stall replication. Always chunk by `id` or `created_at` and
  commit per batch.
- Do not forget to commit between steps; a half-applied expand that
  fails between deploys leaves the schema inconsistent across rolling
  restarts.
- Do not name constraints without an explicit identifier; PostgreSQL
  auto-generates long names that are awkward to reference in the
  contract migration.