<div align="center">

# 🩺 skillmd-lint

**Lint and validate `SKILL.md` files against the open SKILL.md spec.**
CI-friendly. Offline. No API key.

[![CI](https://github.com/Mine-FNL/skillmd-lint/actions/workflows/ci.yml/badge.svg)](https://github.com/Mine-FNL/skillmd-lint/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![v1.0](https://img.shields.io/badge/version-1.0.0-blueviolet.svg)](CHANGELOG.md)

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

`skillmd-lint` checks every one of these and exits non-zero when something is
wrong, so you can wire it into pre-commit or CI in 30 seconds.

## Install

```bash
pip install skillmd-lint
```

Or with `uv` / `pipx`:

```bash
uv tool install skillmd-lint
pipx install skillmd-lint
```

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

All rules and their rationale are documented in [`RULES.md`](RULES.md).

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
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install skillmd-lint
      - run: skillmd-lint --strict skills/
```

## Pre-commit

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/Mine-FNL/skillmd-lint
    rev: v1.0.0
    hooks:
      - id: skillmd-lint
        args: ["--strict"]
```

## Output formats

```bash
# Default: human-readable
skillmd-lint path/to/skill/

# JSON, one object per file (or per error)
skillmd-lint --format json path/to/skill/ | jq

# GitHub Actions annotation format
skillmd-lint --format github path/to/skill/
```

## Related

- **[Mine-FNL/LLM-Skill-Factory-Tool](https://github.com/Mine-FNL/LLM-Skill-Factory-Tool)** — the authoring tool that produces SKILL.md files. Use it to author + validate + measure skill lift.
- **[agentskills.io](https://agentskills.io)** — the open SKILL.md spec.

## License

MIT — see [LICENSE](LICENSE).
