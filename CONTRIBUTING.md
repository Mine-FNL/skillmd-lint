# Contributing to skillmd-lint

Thanks for your interest in making `skillmd-lint` better. This document
covers the development workflow, how to add new rules, and how to
submit a high-quality pull request.

## Quick start

```bash
git clone https://github.com/Mine-FNL/skillmd-lint.git
cd skillmd-lint
python -m pip install -e ".[dev]"
pytest            # runs the 139 tests with coverage
ruff check .      # lints
ruff format --check .   # formatting check
```

The full quality bar is:

- `pytest` passes with **100% line + branch coverage** (`fail_under = 100`
  in `pyproject.toml`).
- `ruff check .` reports zero issues.
- `ruff format --check .` reports zero diffs.

The CI workflow (`.github/workflows/ci.yml`) runs all three on every
push and PR across Python 3.10, 3.11, 3.12, and 3.13.

## Adding a new rule

Each rule is a function in `skillmd_lint/rules.py` with the signature:

```python
def _rule_<short_name>(
    path: str,
    fm: dict,
    body: str,
) -> Iterable[LintFinding]:
    ...
```

Steps:

1. **Pick a free code** (`E###` for an error, `W###` for a warning).
2. **Implement the rule** as a generator. Guard against missing or
   wrong-type frontmatter keys with `isinstance(..., str)` checks —
   YAML commonly returns ints, bools, or null where strings are
   expected.
3. **Register the rule** in the `_RULES` list at the bottom of
   `skillmd_lint/rules.py`, in the order rules should be evaluated.
4. **Update `RULE_INDEX`** so `--list-rules` and the docs pick it up.
5. **Add tests** in `tests/test_rules.py`. Cover the happy path,
   each branch of any conditional, and the type-guard edge cases.
6. **Run the suite** — `pytest --cov` should still report 100%.
7. **Update `RULES.md`** with the rule's rationale and a minimal
   example. Other agents will use this file as a reference.
8. **Open a PR** with the rule code, rationale, and a sample input
   that triggers it.

## Adding a new JSON Schema constraint

The schema lives at `skillmd_frontmatter.schema.json` (root) and is
mirrored at `skillmd_lint/schema.json` (bundled in the wheel). To add
a constraint:

1. Edit the root `skillmd_frontmatter.schema.json`.
2. Copy the change into `skillmd_lint/schema.json` so the wheel ships
   the same content (the Python validator reads the bundled copy).
3. Add a test in `tests/test_schema.py` driving `_check_one` directly.
4. Run `pytest --cov` — must stay at 100%.

The validator implements a small subset of Draft 2020-12 (type,
pattern, enum, minLength, maxLength, minimum, uniqueItems, required).
If you need a construct outside that subset, prefer extending the
embedded validator over pulling in the `jsonschema` package — we
keep the runtime footprint at one transitive dep (PyYAML).

## Coding conventions

- **Type annotations everywhere.** Public functions get full annotations.
- **No third-party runtime deps** beyond PyYAML. Test deps (pytest,
  pytest-cov, ruff) are dev-only.
- **Prefer stdlib** (`pathlib`, `dataclasses`, `re`) over new libraries.
- **Lint passes** before commit. Run `ruff check . && ruff format .`
  and verify both come back clean.
- **One rule per commit.** Keeps `git log` readable and bisects sane.

## Commit messages

We follow Conventional Commits loosely:

```
<type>(<scope>): <short description>

<optional longer body>

<optional footer>
```

Examples in this repo:

- `feat(v1.1): +6 rules, JSON Schema, --schema flag, cross-platform tests`
- `fix: bump __version__ to 1.2.0 + update test_cli_version assertion`
- `docs(changelog): v1.2.0 entry for 100% line + branch coverage`

## Pull request checklist

- [ ] Tests added for every new behavior.
- [ ] `pytest --cov` still reports 100%.
- [ ] `ruff check .` clean.
- [ ] `ruff format .` clean.
- [ ] `RULES.md` updated (if adding a rule).
- [ ] `CHANGELOG.md` updated under an "Unreleased" section.
- [ ] PR description links any related issues.

## Reporting issues

- **Bug reports** — use the "Bug report" issue template. Include a
  minimal SKILL.md that reproduces the issue and the exact linter
  command + output.
- **Feature requests** — use the "Feature request" template. New
  rules should ideally come with a counter-example: a real skill
  the rule would catch.
- **Questions** — use the "Question" template. For quick questions,
  GitHub Discussions (when enabled) is usually faster than an issue.

## License

By contributing, you agree that your contributions will be licensed
under the MIT License — see [`LICENSE`](LICENSE).