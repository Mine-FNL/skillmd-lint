---
name: api-pagination
description: >-
  Use when designing or implementing pagination for a REST or HTTP API.
  Applies when the user asks for "page numbers", "cursor pagination",
  "infinite scroll", "load more", or "next/prev links". Do not use for
  GraphQL pagination (use a GraphQL-specific skill), batch exports, or
  single-shot endpoints that fit under the response size limit.
skill_type: specialist
domain_focus: api-design
tags:
  - api
  - pagination
  - rest
  - http
  - backend
version: 1.0.0
version_notes: Initial gallery entry covering offset, cursor, and keyset pagination.
token_budget: 1500
---

## When to use

Use when the user is designing, reviewing, or implementing a list endpoint
in a REST or HTTP API and the result set may exceed a single response.
Pick the pagination strategy that matches the dataset's mutation profile
and the client's access pattern, not the one that's easiest to code on
day one.

The four canonical strategies are:

| Strategy     | Best for                                          | Avoid when                          |
|--------------|---------------------------------------------------|-------------------------------------|
| Offset / page | Small, stable datasets; admin UIs with page jumps | Datasets that mutate frequently     |
| Cursor       | Feeds, infinite scroll, real-time streams         | Clients need a specific page number |
| Keyset       | Large, append-mostly datasets (events, logs)       | Rows are re-ordered mid-query       |
| Link header  | HATEOAS / REST purists, hypermedia clients        | Browser JSON consumers              |

## Examples

A concrete offset-based endpoint for an orders API:

```http
GET /v1/orders?limit=50&offset=200
Link: <https://api.example.com/v1/orders?limit=50&offset=250>; rel="next",
      <https://api.example.com/v1/orders?limit=50&offset=150>; rel="prev"
```

A cursor-based equivalent that survives inserts and deletes:

```http
GET /v1/orders?limit=50&cursor=eyJpZCI6MTIzNDV9
```

Keyset pagination for a logs endpoint, indexed by `(created_at, id)`:

```sql
SELECT *
FROM orders
WHERE (created_at, id) > ($cursor_ts, $cursor_id)
ORDER BY created_at, id
LIMIT 50;
```

For example, if the previous page returned the row
`(2026-09-17 10:00:00, 12345)`, the next cursor encodes that pair and the
query resumes cleanly even if rows were inserted ahead of it.

## Pitfalls to avoid

- Do not use `OFFSET` for very large page numbers; the database still reads
  and discards every skipped row, so `OFFSET 1000000` becomes a linear scan.
- Do not leak opaque cursor internals in error messages; treat cursors as
  untrusted input and validate their schema before decoding.
- Do not mix strategies on the same endpoint between releases; clients
  that pinned a cursor cannot pivot to offset mid-flight without a version
  bump.
- Do not forget to return a stable `total` only when it is cheap; counting
  on every request defeats the point of pagination.
- Do not skip rate-limiting paginated endpoints; a hostile client can
  enumerate the entire dataset by walking pages.