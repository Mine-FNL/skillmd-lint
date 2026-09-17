## Summary

One-paragraph description of the change.

## Why

The problem this solves, or the feature it adds.

## Changes

- Bullet list of substantive changes
- File by file when the diff is non-obvious

## Test plan

- [ ] `pytest --cov` reports 100%.
- [ ] `ruff check .` clean.
- [ ] `ruff format --check .` clean.
- [ ] New behavior is exercised by a test.
- [ ] If a new rule was added, `RULES.md` documents it.
- [ ] `CHANGELOG.md` updated.

## Related issues

Fixes #<n>, relates to #<m>, etc.

## Risk

Anything reviewers should look at carefully. Anything that might
break downstream consumers (the GitHub Action, the VS Code
extension, the browser playground).

## Screenshots / output

If the change is visible to users, attach a screenshot or sample
output before/after.