---
name: code-review-checklist
description: >-
  Use when reviewing a pull request, merge request, or diff for any
  nontrivial change. Applies when the user asks for "review this PR",
  "checklist for code review", or "what to look at when reviewing". Do
  not use for reviewing marketing copy, design mockups, or non-code
  artifacts; use a domain-appropriate review skill instead.
skill_type: workflow
domain_focus: code-quality
tags:
  - code-review
  - pull-request
  - pr
  - review
  - checklist
version: 1.0.0
version_notes: Gallery workflow skill covering correctness, tests, and ops hygiene.
token_budget: 1400
---

## When to use

Use when the agent (human or AI) is asked to give a structured review of a
change set rather than an opinion. A good review answers four questions
in order, and stops when each is satisfied:

1. **Is it correct?** Does the change do what the PR description claims?
   Read the diff against the linked ticket before reading the surrounding
   code.
2. **Is it tested?** Are the new branches covered? Are the boundary
   conditions covered? Are failure modes covered?
3. **Is it safe to ship?** Does it roll back cleanly? Does it move any
   locks? Does it depend on data that may not exist yet?
4. **Is it readable?** Six months from now, will the next on-caller
   understand the change without a Slack thread?

Skim for the blockers first (correctness, safety), then re-read for the
polish items (style, naming). Reviewers who start with style never reach
correctness.

## Examples

For example, a checklist applied to a 200-line PR that adds a new
background job processor:

```text
[✓] Ticket linked and matches the diff
[✓] New job is idempotent — re-running produces the same DB state
[ ] Backoff policy defined; no infinite-retry loops on poison messages
[✓] Cancellation handled — context propagation checked
[✓] Metric emitted on each terminal state (success, failure, retry)
[ ] Migration is expand-only; the contract migration is in a follow-up PR
[✓] Tests cover the happy path AND the poison-message path
[ ] Changelog entry present
```

A minimal review comment template:

```markdown
**What**
One-sentence description of what the change does.

**Why**
Why the change is needed (link the ticket).

**Risk**
What could go wrong, and how the change is rolled back.
```

## Pitfalls to avoid

- Do not request stylistic changes that the linter should enforce; point
  the author at `prettier`, `ruff`, or whatever the repo uses, not at
  the line.
- Do not approve a change because the tests pass; tests can be tautological.
  Read the assertions and ask whether they would fail on a regression.
- Do not block on nits in a final-round review; ship the polish items
  in a follow-up PR so the primary change can land.
- Do not merge a change with a `console.log`, a stray debugger, or a
  commented-out block left in the diff.
- Do not skip the rollback section; every PR needs an answer to "if this
  breaks in prod at 03:00, what do you do?".