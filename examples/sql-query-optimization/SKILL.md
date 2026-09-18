---
name: sql-query-optimization
description: >-
  Use when a SQL query is slow, when EXPLAIN ANALYZE output is confusing,
  or when designing a query that will run against a non-trivial dataset
  (millions of rows, multi-tenant table, partitioned data). Triggers:
  "why is this slow", "this query times out", "optimize this query",
  "the report takes 20 minutes". Do not use for query syntax errors
  (use the database's error message), schema design questions (use a
  dedicated schema skill), or NoSQL / document-store queries.
skill_type: domain-expert
domain_focus: databases
tags:
  - sql
  - postgres
  - mysql
  - performance
  - query-tuning
  - explain
version: 1.0.0
version_notes: Gallery performance skill. Drives a four-step diagnose-then-fix loop with explicit anti-patterns.
token_budget: 1500
---

## When to use

Use when the user reports a query is slow, when designing a new query
against a large or busy table, or when reviewing a query that someone
else wrote. The diagnose-then-fix loop is the same in every case:

1. **Capture the original.** Save the query text, the parameters, and
   the row counts in / out. You cannot optimise what you cannot measure.
2. **Run EXPLAIN ANALYZE.** Read it top-down. Look for the node with
   the largest actual time; that is where to optimise.
3. **Identify the bottleneck.** Classify it (see below) before reaching
   for an index.
4. **Apply one change.** Measure again. If the new plan is worse,
   revert and try the next hypothesis.

If the query is already fast enough (< 100ms p95, returns the rows the
user needs), stop. Optimisation is a means, not a goal.

## Examples

For example, a query that runs 8 seconds on a 12M-row table:

```sql
EXPLAIN ANALYZE
SELECT u.id, u.email, COUNT(o.id) AS order_count
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
WHERE u.created_at > '2024-01-01'
GROUP BY u.id;
```

Plan output reveals:

```text
HashAggregate  (cost=412000..415000 rows=50000) (actual time=7821..7912 rows=50000)
  ->  Hash Left Join  (cost=20000..395000 rows=50000) (actual time=210..7400 rows=1200000)
        Hash Cond: (o.user_id = u.id)
        ->  Seq Scan on orders o  (cost=0..180000 rows=12000000) (actual time=0.1..4200 rows=12000000)
        ->  Hash
              ->  Index Scan using users_created_at_idx on users u
                    Index Cond: (created_at > '2024-01-01')
                    rows=50000
```

The bottleneck is the Seq Scan on `orders`. Apply the most selective
filter first; with the users already narrowed, the join becomes a
nested-loop with an index lookup instead of a hash over 12M rows.
Re-write:

```sql
SELECT u.id, u.email, COALESCE(oc.cnt, 0) AS order_count
FROM users u
LEFT JOIN (
    SELECT user_id, COUNT(*) AS cnt
    FROM orders
    GROUP BY user_id
) oc ON oc.user_id = u.id
WHERE u.created_at > '2024-01-01';
```

Or, more conventionally: add a covering index on
`orders(user_id) INCLUDE (id)` and let the planner do the right thing.

## Pitfalls to avoid

- **Do not** add an index without checking whether the query can be
  restructured first. A missing predicate rewrite can turn a 12M-row
  scan into a 50k-row scan; no index can match that.
- **Do not** trust row-count estimates. `EXPLAIN ANALYZE` shows
  actual vs estimated; if the gap is > 10×, the statistics are stale
  and the planner is choosing bad plans. Run `ANALYZE` first.
- **Do not** use `SELECT *` in production queries. The planner cannot
  use a covering index if you select columns you do not need, and the
  schema can drift under you.
- **Do not** write a correlated subquery when a JOIN would do. The
  planner can sometimes un-correlate them, but not always, and the
  fallback is an N+1 plan.
- **Do not** introduce `DISTINCT` to paper over a JOIN that produces
  duplicates. The duplicates are a signal that the JOIN is wrong, not
  that you need a deduplicator.
- **Do not** disable the planner's choices (disable_seqscan,
  enable_indexscan=off) to "force" the plan. The planner is usually
  right. If it is wrong, the answer is better statistics, not a sledgehammer.
- **Do not** ship a query that you have not run against production-
  sized data. The EXPLAIN on a 10k-row dev table lies. If you do not
  have access to a representative dataset, ask for one before merging.
