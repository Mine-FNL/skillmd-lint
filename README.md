<div align="center">

# 🩺 skillmd-lint

**Lint and validate `SKILL.md` files against the open SKILL.md spec.**
CI-friendly. Offline. No API key. Schema-validated.

[![CI](https://github.com/Mine-FNL/skillmd-lint/actions/workflows/ci.yml/badge.svg)](https://github.com/Mine-FNL/skillmd-lint/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![v1.1](https://img.shields.io/badge/version-1.1.0-blueviolet.svg)](CHANGELOG.md)
[![Schema](https://img.shields.io/badge/json--schema-2020--12-blue)](skillmd_frontmatter.schema.json)

</div>

---

## Why

`SKILL.md` is the open standard for modular AI expertise. A skill is a folder
with `SKILL.md` at the root, plus optional `scripts/`, `references/`, `assets/`,
`examples/`. The format is open at [agentskills.io](https://agentskills.io) and
adopted across Claude Code, the Claude API, ChatGPT, OpenAI Codex, and the
broader agent ecosystem.

But the spec is easy to get wrong:

- Name collisions with reserved words (`anthropic`, `claude`, `com1`, …)
- Frontmatter key typos (`desription` instead of `description`)
- Description missing the trigger phrases the agent uses to decide whether to
  load the skill
- Body too short or too long for the model's context budget
- XML tags in the name (forbidden by the spec)
- Description without "do not use when…" — the spec calls for negative triggers
  so skills don't over-fire
- `skill_type` typos or `version` strings that aren't valid semver

`skillmd-lint` checks every one of these, plus a published
[JSON Schema](skillmd_frontmatter.schema.json), and exits non-zero when
something is wrong, so you can wire it into pre-commit or CI in 30 seconds.

## Install

```bash
pip install skillmd-lint
```

Or with `uv` / `pipx`:

```bash
uv tool install skillmd-lint
pipx install skillmd-lint
```

Or via the GitHub Action (see [CI integration](#ci-integration)).

## Use

```bash
# Lint a single skill folder.
skillmd-lint path/to/skill/

# Lint many skills in one go.
skillmd-lint skills/*/

# JSON output for CI / pre-commit hooks.
skillmd-lint --format json path/to/skill/

# Strict mode: warnings become errors.
skillmd-lint --strict path/to/skill/

# Run the published JSON Schema on top of the rule engine.
skillmd-lint --schema path/to/skill/

# Print the full rule table.
skillmd-lint --list-rules
```

Example output:

```text
path/to/skill/SKILL.md
  ✗ error   : name 'My Skill!' contains uppercase characters; spec requires lowercase kebab-case
  ⚠ warning : description missing 'use when' or equivalent trigger phrase
  ✓ ok      : frontmatter is well-formed YAML
  ⚠ warning : body length 320 lines exceeds recommended 200; consider progressive disclosure

✗ 1 error, 2 warnings
```

Exit code: **0** when all rules pass (warnings allowed); **1** on any error.

## Rules

### Errors (block CI)

| Code    | Rule                                          |
|---------|-----------------------------------------------|
| `E001`  | `SKILL.md` file not found at folder root      |
| `E002`  | frontmatter is missing or not valid YAML      |
| `E003`  | `name` missing or empty                        |
| `E004`  | `name` contains uppercase / underscores / XML |
| `E005`  | `name` collides with a reserved word           |
| `E006`  | `name` exceeds 64 characters                   |
| `E007`  | `description` missing or empty                 |
| `E008`  | `description` exceeds 1024 characters          |
| `E009`  | `description` contains XML tags                |
| `E010`  | `tags` list contains duplicates (v1.1)         |

### Warnings (don't block)

| Code    | Rule                                                       |
|---------|------------------------------------------------------------|
| `W001`  | description missing a positive trigger phrase              |
| `W002`  | description missing a negative trigger ("do not use when…") |
| `W003`  | body has fewer than 20 lines                               |
| `W004`  | body exceeds 200 lines — consider progressive disclosure  |
| `W005`  | no `## When to use` or similar section                     |
| `W006`  | no concrete examples in body                              |
| `W007`  | skills/ subfolder present but no `SKILL.md` inside         |
| `W008`  | frontmatter key looks like a typo (v1.1)                   |
| `W009`  | `skill_type` is not a recognised value (v1.1)              |
| `W010`  | `version` is not valid semver (v1.1)                       |
| `W011`  | `token_budget` is not a positive integer (v1.1)            |
| `W012`  | no `## Pitfalls to avoid` section in body (v1.1)           |
| `W013`  | tag is not lowercase kebab-case (v1.1)                     |

All rules and their rationale are documented in [`RULES.md`](RULES.md).
The full machine-readable rule table is available via `skillmd-lint --list-rules`.

## JSON Schema

The repo ships a published [JSON Schema 2020-12](skillmd_frontmatter.schema.json)
for the SKILL.md frontmatter block. It is bundled into the wheel as
`skillmd_lint/schema.json` and exposed via the Python API:

```python
from skillmd_lint import get_schema, validate_frontmatter

print(get_schema()["properties"]["name"])           # → { "type": "string", ... }
print(validate_frontmatter({"name": "Bad"}))        # → ['$.description: missing required key 'description'']
```

The same schema is exposed on the CLI via `--schema`:

```bash
skillmd-lint --schema path/to/skill/
```

Schema findings are reported with codes `S001`..`S999` so they don't collide
with rule codes (`E001`..`E010`, `W001`..`W013`).

## CI integration

`.github/workflows/lint.yml`:

```yaml
name: skill-lint
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Mine-FNL/skillmd-lint-action@v1
        with:
          path: skills/
          strict: "true"
```

Or, equivalently, with the Python CLI:

```yaml
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install skillmd-lint==1.1.0
      - run: skillmd-lint --strict skills/
```

## Pre-commit

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/Mine-FNL/skillmd-lint
    rev: v1.1.0
    hooks:
      - id: skillmd-lint
        args: ["--strict"]
```

## Output formats

```bash
# Default: human-readable
skillmd-lint path/to/skill/

# JSON, one object per file
skillmd-lint --format json path/to/skill/ | jq

# GitHub Actions annotation format
skillmd-lint --format github path/to/skill/

# Add JSON Schema validation on top of either format
skillmd-lint --format json --schema path/to/skill/
```

## Python API

```python
from skillmd_lint import lint_file, lint_text, validate_frontmatter, get_schema

result = lint_file("path/to/SKILL.md")
if not result.passed:
    for finding in result.errors:
        print(finding.code, finding.message)

# Schema validation (returns a list of human-readable violation strings).
violations = validate_frontmatter({"name": "my-skill"})
```

## Cross-platform

Pure-Python (only depends on `PyYAML`). Verified on:

- Linux (Ubuntu 22.04, GitHub Actions)
- macOS (Apple Silicon, M-series)
- Windows (Windows Server 2022, GitHub Actions)

`skillmd-lint` handles CRLF, LF, CR line endings transparently and strips a
leading BOM if present. See `tests/test_cross_platform.py` for the full
test matrix.

## Related

- **[Mine-FNL/LLM-Skill-Factory-Tool](https://github.com/Mine-FNL/LLM-Skill-Factory-Tool)** — the authoring tool that produces SKILL.md files. Use it to author + validate + measure skill lift.
- **[Mine-FNL/skillmd-lint-action](https://github.com/Mine-FNL/skillmd-lint-action)** — the official composite GitHub Action wrapping this CLI.
- **[agentskills.io](https://agentskills.io)** — the open SKILL.md spec.

## License

MIT — see [LICENSE](LICENSE).