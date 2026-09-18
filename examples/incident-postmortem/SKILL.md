---
name: incident-postmortem
description: >-
  Use when an incident has been resolved and the team needs to write up
  what happened, why, and what changes. Triggers: "write the postmortem",
  "incident review", "what happened during the outage", "let's schedule
  the postmortem". Do not use during an active incident (use an
  incident-response skill instead), for near-miss reviews that did not
  cause user impact, or for security-incident write-ups (those have
  different disclosure requirements).
skill_type: workflow
domain_focus: operations
tags:
  - incident
  - postmortem
  - sre
  - ops
  - review
  - retrospective
version: 1.0.0
version_notes: Gallery ops skill. Blameless template with a 5-phase structure that resists hindsight bias.
token_budget: 1500
---

## When to use

Use within 5 business days of an incident's resolution. The longer the
write-up is delayed, the more memory drift sets in and the less useful
the action items become. A postmortem that ships three weeks after the
event is a postmortem in name only.

Write it as a group. The incident commander, the responders who
debugged it, and a representative of the affected customer/product team
should all be in the room. The author's job is to take notes and write
the first draft; the team's job is to argue about the timeline until
they agree.

The output is a document. The document has a fixed structure (below).
The structure is non-negotiable. It is the structure that makes the
write-up useful for the next incident, not for the one that just
happened.

## Examples

For example, a 43-minute partial outage of the public API on 2024-09-14:

```markdown
# Incident 2024-09-14: API 5xx rate at 23:08 UTC

## Summary
At 23:08 UTC on 2024-09-14, the public API began returning HTTP 503 for
approximately 7% of requests. Root cause was a connection-pool exhaustion
in the auth-service triggered by a slow query on the sessions table.
Total impact: 43 minutes of degraded service for ~3,200 users.

## Timeline (all times UTC)
- 23:08 — Alert fires: api_5xx_rate > 1% for 2 minutes
- 23:09 — On-call paged; acknowledges at 23:11
- 23:13 — First responder connects; sees 5xx concentrated in /login
- 23:18 — Auth-service identified; connection pool at 100% (50/50)
- 23:24 — Slow query found: `SELECT * FROM sessions WHERE last_seen > ...`
  running 38 seconds (expected 50ms)
- 23:31 — Mitigated by killing the slow query's connection
- 23:51 — Service fully restored; alert cleared

## Root cause
The sessions table grew past the threshold where the existing index
was selective (last_seen cardinality dropped). The query planner
switched to a Seq Scan; the slow query held connections from the pool
until auth-service ran out. There was no circuit breaker to short-
circuit the dependent service.

## What went well
- Alert fired within 90 seconds of the SLO breach
- On-call response time was within target (5 min)
- The slow-query identification was fast (under 10 minutes)

## What went poorly
- No circuit breaker on auth-service's downstream calls
- Index on `sessions(last_seen)` had not been re-evaluated in 8 months
- The 5xx alert threshold (1%) was too lax for the affected endpoint

## Action items
- [ ] Add circuit breaker to auth-service's session-loader (owner: @alex)
- [ ] Re-evaluate all `last_seen` indexes (owner: @sam, due 2024-10-15)
- [ ] Tighten alert to 0.5% 5xx on /login and /logout (owner: @jordan)
- [ ] Schedule a load-test scenario that exercises this path (owner: @alex)

## Lessons
Slow queries don't fail loudly until they cascade. Pool exhaustion is a
downstream signal of an upstream slowness; we need to detect the
slowness itself, not the exhaustion it eventually causes.
```

## Pitfalls to avoid

- **Do not** assign blame. "Sam's commit caused this" is not actionable
  and damages trust. "The migration was missing a backfill" or "the
  test did not cover the 10M-row case" is actionable and accurate.
- **Do not** write the postmortem before the timeline is settled. The
  first draft of "what happened" is always wrong; let the responders
  argue it out before committing to a sequence.
- **Do not** leave action items without owners or due dates. An action
  item without a name is a wish. Without a date, it is a forgotten wish.
- **Do not** aim for completeness. The postmortem is a forcing
  function for the next change, not the full history. If a detail does
  not lead to a change, cut it.
- **Do not** skip the "what went well" section. It is not a victory
  lap; it is a record of which mechanisms worked under stress. Without
  it, every postmortem looks like everything failed.
- **Do not** publish before the action items have owners. A
  postmortem with unowned action items is a postmortem with no
  follow-through.
- **Do not** let the postmortem become the change. The postmortem
  describes; the change implements. If the implementation requires
  more than a couple of weeks of work, that is a follow-up project,
  not an action item.
- **Do not** close the postmortem with a vague "we'll monitor". Every
  "we'll monitor" should be a specific alert, threshold, and runbook
  link — or it is not a real action item.
