---
name: python-package-release
description: >-
  Use when releasing a new version of a Python package — bumping
  version, cutting a tag, publishing to PyPI, writing the changelog,
  or announcing the release. Triggers: "cut a release", "publish to
  PyPI", "bump version", "this is ready to ship", "tag and release".
  Do not use for first-time repo setup, for the inner loop of writing
  code, or for releasing non-Python artifacts.
skill_type: workflow
domain_focus: release-engineering
tags:
  - python
  - packaging
  - pypi
  - release
  - changelog
  - semver
version: 1.0.0
version_notes: Gallery release workflow. Twelve-step checklist with explicit gates.
token_budget: 1700
---

## When to use

Use when a piece of code is "ready to ship" and the next action is
mechanical: tag, build, publish, announce. Apply this checklist in
order. Skipping a step is the leading cause of "the release went out
and X broke".

Run the checklist on the maintainer's machine, not on CI. Releases
are a maintainer activity; CI handles the build, not the decision.

## Examples

For example, releasing `mylib` from `1.4.2` to `1.5.0`:

```text
[✓] 1. All in-flight PRs merged or punted
[✓] 2. `git checkout main && git pull` — branch is current
[✓] 3. CI green on the latest commit (run `gh run list --branch main`)
[✓] 4. `pyproject.toml`: bump version 1.4.2 → 1.5.0
[✓] 5. `CHANGELOG.md`: move [Unreleased] entry to a dated 1.5.0 section
[✓] 6. Open the version-bump PR; wait for CI; merge
[✓] 7. Tag: `git tag -s v1.5.0 -m 'v1.5.0'` (annotated + signed)
[✓] 8. Push tag: `git push origin v1.5.0`
[✓] 9. CI release workflow builds sdist + wheel, uploads to PyPI
[✓] 10. Verify on PyPI: `pip download mylib==1.5.0 --no-deps -d /tmp/x`
[✓] 11. Smoke test: `pip install mylib==1.5.0` in a fresh venv, import it
[✓] 12. Announce: GitHub release notes, mailing list, internal Slack
```

The signing step (7) is the only one without a parallel in a hosted
CI. If you do not have a GPG key set up yet, use `--no-sign` for the
first release and add signing before the next.

A patch release (`1.4.2` → `1.4.3`) follows the same checklist but
with a hotfix branch instead of `main`:

```text
[✓] 1. `git checkout -b release/1.4.3 main`
[✓] 2. Cherry-pick the fix commit(s)
[✓] 3. Bump version, update changelog (Hotfix section)
[✓] 4. Open PR, get review, merge
[✓] 5. Tag and push from main (after merge)
[✓] 6. CI publishes; verify; announce
```

## Pitfalls to avoid

- **Do not** tag a commit that has not been merged to `main`. The
  release artifact must be reproducible from the main branch's
  history, not from a topic branch that may later be force-pushed or
  rebased.
- **Do not** bump the version in a commit that also changes code.
  Separate the version bump so `git log` shows the bump as its own
  step and `git diff v1.4.2..v1.5.0 -- pyproject.toml` is one line.
- **Do not** publish without verifying the artifact. The cheapest
  verification is `pip download` + a smoke import in a fresh venv;
  ten seconds that catch the common "wheel is broken on Linux"
  failures.
- **Do not** skip the changelog. "Look at the commits" is not a
  changelog. Users reading release notes need the human-readable
  summary, not a `git log --oneline` dump.
- **Do not** publish to PyPI before the GitHub release exists. If the
  GitHub release fails after the PyPI publish, you have shipped a
  version that no one can find the source for.
- **Do not** reuse a tag. If a tag was pushed by mistake, delete it
  and re-tag the correct commit. The history of tags is the history
  of releases; rewriting it silently is worse than a brief gap.
- **Do not** announce a release until the smoke test passes. A
  release announcement that says "out now, broken" is worse than a
  short delay.
- **Do not** publish the same version twice. If you need to fix a
  broken release, cut a new patch version (`1.5.1`), do not re-upload
  `1.5.0`. PyPI does not let you overwrite, and users with the
  broken version pinned will not see the fix.
