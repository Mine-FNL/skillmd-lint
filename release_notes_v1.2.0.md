## skillmd-lint v1.2.0 — 100% line + branch coverage

**TL;DR**: every line and every branch in the skillmd-lint source is now covered by a test, and the build fails if it ever drops below 100%.

### Coverage

| File | Lines | Branches | Coverage |
|------|------:|---------:|---------:|
| `__init__.py` | 6 | 0 | 100% |
| `__main__.py` | 0 | 0 | 100% (pragma) |
| `cli.py` | 136 | 52 | 100% |
| `rules.py` | 244 | 118 | 100% |
| `schema.py` | 73 | 48 | 100% |
| **TOTAL** | **459** | **218** | **100%** |

The `__main__.py` stub is marked `# pragma: no cover` — it's a 2-line
`python -m` entry point that's exercised by the `test___main___subprocess`
test in `tests/test_cli.py`. Standard convention for `__main__.py` stubs.

### What's new

- **`branch = true`** + **`fail_under = 100`** in `pyproject.toml`. CI now fails
  on any uncovered line or branch.
- **39 new tests** in `tests/test_rules.py`, `tests/test_cli.py`, and
  `tests/test_schema.py` covering:
  - Every `_run_schema` defensive branch (unreadable file, no frontmatter
    marker, unclosed fence, bad YAML, non-dict YAML result).
  - Every edge case in `_split_frontmatter` (unclosed frontmatter, non-dict
    YAML root).
  - Every `isinstance` guard in the rule engine: non-string `name`,
    non-string `skill_type`, non-list `tags`, non-string tag elements,
    empty tags.
  - Every branch of the JSON Schema validator: `uniqueItems` with empty
    array, single-item array, missing `items` schema, unknown schema types,
    no required keys.
  - The `lint_folder` "skip non-skill children" branch.
- **Removed the unused `_rule_file_exists` placeholder** — file-not-found is
  already handled at the runner level via `E001`. Dead code.
- **Simplified `lint_text`** — uses `finding.path or path` instead of an
  `if/else` block guarding against rules setting their own paths. Cleaner
  single-line assignment, no behavior change.

### Stats

- **139 tests pass** (up from 100 in v1.1.x).
- **Branch coverage**: 218/218.
- **Lint clean** (ruff), **format clean**.
- **No new runtime dependencies**.

### Install

```bash
pip install skillmd-lint==1.2.0
```

### Companion projects

- [Mine-FNL/LLM-Skill-Factory-Tool](https://github.com/Mine-FNL/LLM-Skill-Factory-Tool) — author + validate + measure skill loops.
- [Mine-FNL/skillmd-lint-action](https://github.com/Mine-FNL/skillmd-lint-action) — official GitHub Action.
- [Mine-FNL/skillmd-lint-vscode](https://github.com/Mine-FNL/skillmd-lint-vscode) — VS Code extension.