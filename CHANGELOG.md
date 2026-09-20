# Changelog

All notable changes to `skillmd-lint` are recorded here. Dates are
ISO-8601 (YYYY-MM-DD).

## [1.4.1] — 2026-09-20

### Fixed

- **LSP server `python -m skillmd_lint.lsp_server` was a silent no-op**.
  `lsp_server.py` was missing the `if __name__ == "__main__": main()`
  guard, so running the module directly loaded the file but never
  started the server. The `skillmd-lsp` console script entry point
  worked (it calls `main()` explicitly), but anyone reaching for
  `python -m skillmd_lint.lsp_server` — including the CI smoke test
  we just added — got an empty process.
- **4 tests hard-coded `/tmp/skillmd-lint-init`** as a working
  directory. The repo is not testable from a fresh clone unless that
  exact path exists. Replaced with `tmp_path`, `sys.executable`, and
  a `Path(__file__).resolve().parent.parent / "examples"` so the
  suite runs from any checkout location.

### Added

- **`tests/test_lsp_smoke.py`** — end-to-end smoke test for the LSP
  server. Spawns `python -m skillmd_lint.lsp_server` as a subprocess
  and exchanges real JSON-RPC messages (initialize, malformed frame,
  partial headers). Three tests; the malformed-frame and
  partial-headers cases verify the server stays alive across
  non-fatal protocol errors instead of crashing on bad input.
- **`lsp-smoke` CI job** — installs with `[lsp]` extra and runs a
  one-shot LSP initialize handshake. This is the canary that fails
  loudly if a future regression removes the `[lsp]` extra
  declaration from `pyproject.toml` or makes the LSP server
  unstartable from a subprocess.

## [1.4.0] — 2026-09-19

### Added

- **LSP server** (`skillmd-lsp` console script). Optional `pip
  install skillmd-lint[lsp]` ships a `pygls`-based Language Server
  Protocol server wrapping `skillmd-lint --format json`. One
  codebase unlocks Neovim (`none-ls.nvim`), Vim (`ALE`), Helix
  (`languages.toml`), Emacs (`eglot`), and Zed (extension scaffold)
  via the standard LSP integration. Optional dependency — the
  core `pip install skillmd-lint` is unchanged.
- **11 new rules** (22 → 33 total). Closes the rule-count gap with
  `agent-sh/agnix`'s 31 SKILL.md rules. New codes:
  - `E011` — `version` is not a string
  - `W014` — frontmatter uses tab indentation (YAML correctness)
  - `W015` — description contains placeholder text (`TODO`,
    `FIXME`, `lorem`, `placeholder`)
  - `W016` — body contains raw HTML tags (prefer Markdown)
  - `W017` — name has leading or trailing hyphen
  - `W018` — description starts with redundant prefix
    (`this skill`, `this is a skill`)
  - `W019` — `tags` count is outside the 1-10 range
  - `W020` — `version_notes` doesn't reference current version
  - `W021` — `base_skill` references unknown skill
  - `W022` — `## Examples` lacks concrete input/output example
- **Robustness**: `lint_file` now wraps `read_text` in a
  try/except and emits a proper `E001` finding on OSError, so a
  file that becomes unreadable between discovery and parse
  produces a deterministic error instead of an unhandled
  exception.

### Changed

- Test count: 254 → 304. Coverage: 100% lines + branches across
  every module.
- Fixed two test fixtures (`tests/test_cli.py`, `tests/test_rules.py`)
  that had `## Examples` sections without concrete examples —
  the new `W022` rule is what surfaced them.

### Competitive positioning

- **22 → 33 rules**: closes the SKILL.md rule-count gap with
  `agent-sh/agnix` (which has 31 SKILL.md-specific rules).
- **LSP server**: most major editor surfaces now reachable from
  one codebase, with optional install to keep the core
  lean.
- **Unchanged differentiators**: 100% line + branch coverage,
  pure Python, single transitive dep (PyYAML), published JSON
  Schema, MIT.

## [1.3.0] — 2026-09-19

### Added

- **`--fix` flag**: applies 6 safe mechanical fixes in-place:
  - **W008** frontmatter typo rename (e.g. `desription` → `description`)
  - **E010** deduplicate tag list (preserving first occurrence)
  - **W013** normalise tags to lowercase kebab-case
  - **W010** strip `v`/`V` prefix from version when otherwise valid semver
  - **W011** coerce string `token_budget` to positive int
- **`--unsafe-fix` flag** (gated on `--fix`): adds 2 riskier fixes:
  - **E004** coerce `name` to lowercase kebab-case (handles camelCase boundaries)
  - **W009** alias-map common `skill_type` values (`code` → `specialist`, etc.)
- **`--schema-export PATH` flag**: writes the published JSON Schema for
  SKILL.md frontmatter to PATH and exits. Useful for editors, IDEs, and
  other validators that want to consume the spec contract without
  depending on Python.
- **`--migrate` flag**: converts CLAUDE.md / AGENTS.md / .cursorrules
  files to SKILL.md with best-effort name + description extraction.
  Supports `--migrate-out PATH` and `--migrate-format` overrides.
- **`skillmd_lint.migrate` Python API**: `migrate_file()`, `migrate_path()`,
  `detect_format()` for programmatic conversion.
- 5 new sample skills under `examples/`:
  - `security-review-checklist/` — STRIDE-driven PR security audit
  - `sql-query-optimization/` — diagnose-then-fix loop with anti-patterns
  - `api-error-response-format/` — canonical four-field error envelope
  - `python-package-release/` — 12-step release checklist with gates
  - `incident-postmortem/` — blameless template with 5-phase structure

### Changed

- `cli.py` now imports the schema only when `--schema-export` is
  requested, keeping the import path lighter for the lint code path.
- `_apply_fixes_to_paths` is file-scoped; folders in the path list are
  skipped (lint still walks them, but fixes only apply to explicit
  file paths).
- Test count: 254 (up from 139). Coverage: 100% lines + branches across
  all new modules (`fix.py`, `migrate.py`) and existing ones.

### Notes

- The `pragma: no cover` markers on unreachable defensive branches are
  intentional. The branch coverage gate requires explicit annotation
  for paths the rule engine gates upstream; we keep the defensive code
  for runtime safety rather than deleting it.

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