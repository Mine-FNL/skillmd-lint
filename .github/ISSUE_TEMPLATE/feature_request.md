---
name: Feature request
about: Propose a new rule, schema field, or CLI feature
title: "feat: "
labels: ["enhancement"]
assignees: []
---

## Problem

What real-world issue would this feature solve? If it's a new rule,
include a sample SKILL.md that the rule should flag.

## Proposed solution

A short description of what the feature does and how the user
interacts with it (CLI flag, new rule code, new schema field, etc.).

## Alternatives considered

What else did you consider? What were the trade-offs?

## Acceptance criteria

- [ ] When the rule fires, the finding has a stable `code` (E### or W###).
- [ ] Tests in `tests/test_rules.py` cover the rule.
- [ ] `pytest --cov` still reports 100%.
- [ ] `RULES.md` documents the rule with rationale.
- [ ] The new behavior is mentioned in `CHANGELOG.md`.

## Out of scope

Anything you explicitly don't want to ship with this feature.