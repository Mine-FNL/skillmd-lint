# Changelog

All notable changes to `skillmd-lint` are recorded here. Dates are
ISO-8601 (YYYY-MM-DD).

## [1.2.0] — 2026-09-17

### Added

- **100% line + branch coverage** (139 tests pass). Configured
  `branch = true` + `fail_under = 100` in `pyproject.toml`.
- 39 new tests covering: every `_run_schema` defensive branch
  (unreadable file, no frontmatter marker, unclosed fence, bad YAML,
  non-dict YAML), every edge case in `_split_frontmatter`, every
  `isinstance` guard in the rule engine (non-string `name`, non-string
  `skill_type`, non-list `tags`, non-string tag elements, empty tags),
  every branch of the JSON Schema validator (`uniqueItems` with empty
  array, missing `items` schema, unknown schema types, no required
  keys), and the `lint_folder` "skip non-skill children" path.
- **`pragma: no cover`** on `__main__.py` lines (the standard
  `python -m` entry-point stub — exercised by the existing subprocess
  test in `test_cli.py::test___main___subprocess`).

### Changed

- `lint_text` now uses `finding.path or path` instead of an `if/else`
  block that guarded against rules setting their own paths. Cleaner
  single-line assignment; no behavior change.
- Removed the unused `_rule_file_exists` placeholder (file-not-found is
  handled at the runner level via `E001`).

### Coverage breakdown

| File | Lines | Branches | Coverage |
|------|------:|---------:|---------:|
| `__init__.py` | 6 | 0 | 100% |
| `__main__.py` | 0 | 0 | 100% (pragma) |
| `cli.py` | 136 | 52 | 100% |
| `rules.py` | 244 | 118 | 100% |
| `schema.py` | 73 | 48 | 100% |
| **TOTAL** | **459** | **218** | **100%** |

## [1.1.2] — 2026-09-17

### Added

- **`examples/` skill gallery** — 10 curated reference SKILL.md files
  that all pass `skillmd-lint --strict --schema` with zero findings.
  Covers a `specialist` (api-pagination), a `domain-expert`
  (postgres-migrations), a `workflow` (git-bisect-bugs), and a `hybrid`
  meta-skill (skillmd-authoring), plus six more across REST API
  pagination, TypeScript strict-mode migration, code review checklists,
  distributed tracing, refactor/rename, WireGuard VPN, and CSP headers.
- **`examples/README.md`** — gallery index with one-line descriptions.
- **`examples/run_lint.sh`** — CI-friendly script that lints every
  skill in the gallery and exits non-zero on any finding.

### Changed

- Top-level `README.md` now links to the gallery and calls out
  `examples/run_lint.sh` as the recommended regression check.

## [1.1.0] — 2026-09-17

### Added

- **Six new rules** (`W008`–`W013` + `E010`):
  - `W008` frontmatter key typo detection (e.g. `desription` → `description`).
  - `W009` `skill_type` is one of the four recognised values.
  - `W010` `version` is valid semver (`X.Y.Z[-prerelease]`).
  - `W011` `token_budget` is a positive integer; rejects `True`/`False`
    explicitly because `bool` is a subclass of `int` in Python.
  - `W012` `## Pitfalls to avoid` (or equivalent) section in body.
  - `W013` each tag is lowercase kebab-case.
  - `E010` `tags` list contains no duplicates.
- **JSON Schema** (`skillmd_frontmatter.schema.json` + bundled
  `skillmd_lint/schema.json`): Draft 2020-12 schema for the frontmatter
  block, with pure-Python validator (`validate_frontmatter()`) — no extra
  runtime dependency.
- **`--schema` CLI flag** to opt into schema validation on top of the
  rule engine; schema findings are reported with codes `S001`..`S999`.
- **`--list-rules` CLI flag** to print the canonical rule table; same
  table is exposed as `RULE_INDEX` from Python.
- **`get_schema()` / `validate_frontmatter()`** public API.
- **Cross-platform tests** (`tests/test_cross_platform.py`) covering CRLF,
  CR, mixed line endings, UTF-8 BOM, non-ASCII, and `pathlib.Path` paths.
- **CI matrix** now runs on Ubuntu, macOS, and Windows.

### Changed

- Bumped Python to `>=3.10` (unchanged) but added explicit 3.13 classifier.
- README reorganised around the new rules and the JSON Schema section.

### Coverage

- 100 tests pass.
- 91% line coverage (`cli.py` 90%, `rules.py` 95%, `schema.py` 84%).

## [1.0.0] — 2026-09-17

### Added

- Initial release.
- 16 rules: `E001`–`E009`, `W001`–`W007`.
- `--format {human,json,github}`, `--strict`, `--quiet`, `--version` flags.
- GitHub Action: [`Mine-FNL/skillmd-lint-action`](https://github.com/Mine-FNL/skillmd-lint-action).
- Pre-commit hook config.
- 39 tests, 74% coverage.

[1.1.2]: https://github.com/Mine-FNL/skillmd-lint/compare/v1.1.0...v1.1.2
[1.1.0]: https://github.com/Mine-FNL/skillmd-lint/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Mine-FNL/skillmd-lint/releases/tag/v1.0.0