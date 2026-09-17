## What's new

**+6 rules** (W008–W013 + E010) for common skill failures:

- W008 — frontmatter key typos (`desription` → `description`)
- W009 — `skill_type` enum validation
- W010 — `version` semver validation
- W011 — `token_budget` positive-integer check
- W012 — `## Pitfalls to avoid` section recommendation
- W013 — tag kebab-case format
- E010 — duplicate tags detection

**JSON Schema** (Draft 2020-12) for the SKILL.md frontmatter block:

- Pure-Python validator (no extra runtime deps)
- Available as `skillmd_lint.validate_frontmatter(fm)` or via `--schema` on the CLI
- Schema findings are reported as `S001`..`S999` so they don't collide with rule codes
- Published as `skillmd_frontmatter.schema.json` in the repo

**Cross-platform** verified on Linux, macOS, and Windows (CI matrix). Handles CRLF, LF, and CR transparently; strips UTF-8 BOMs.

**New CLI flags**: `--schema`, `--list-rules`.

**Public Python API additions**: `get_schema()`, `validate_frontmatter()`, `RULE_INDEX`.

## Stats

- 100 tests pass, 91% line coverage
- Lint clean (ruff), format clean
- No new runtime dependencies (still just PyYAML)

## Install

```bash
pip install skillmd-lint==1.1.0
```

## Companion projects

- [Mine-FNL/LLM-Skill-Factory-Tool](https://github.com/Mine-FNL/LLM-Skill-Factory-Tool) — author + measure + run skill loops.
- [Mine-FNL/skillmd-lint-action](https://github.com/Mine-FNL/skillmd-lint-action) — official GitHub Action.

See [CHANGELOG.md](CHANGELOG.md) for the full diff.