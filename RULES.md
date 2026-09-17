# Rules reference

Every check `skillmd-lint` runs, with rationale. Rules follow the open
[SKILL.md spec](https://agentskills.io) and are organised by severity.

## Errors (block CI)

These are mandatory spec violations. The CLI exits non-zero when any
appear (and `lint_text()` returns `passed=False`).

### `E001` — file not found
The path passed to `lint_file()` doesn't exist on disk.

### `E002` — frontmatter missing or invalid
A valid `SKILL.md` must start with a YAML frontmatter block delimited by
`---` on its own lines. Either the block is missing entirely, or the YAML
inside it can't be parsed (e.g. an unclosed list).

### `E003` — `name` missing
The `name` field is required in the frontmatter. The agent uses it as the
folder name when the skill is installed.

### `E004` — `name` invalid format
`name` must be lowercase kebab-case: letters, digits, and single hyphens.
No uppercase, no underscores, no leading/trailing hyphens, no double
hyphens. Examples:
- ✓ `backend-api-engineer`
- ✓ `qnb-specialist`
- ✗ `Backend-Engineer` (uppercase)
- ✗ `my_skill` (underscore)
- ✗ `-leading-hyphen` (leading hyphen)

### `E005` — `name` collides with a reserved word
Windows device names (`con`, `prn`, `com1`, …) and filesystem specials
(`.`, `..`, `~`) are off-limits. The open SKILL.md spec also rejects
`anthropic`, `claude`, `openai`, `gpt`, `grok` — these shadow platform /
model names that show up in the agent's UI.

### `E006` — `name` too long
Spec limit is 64 characters. Some agent UIs truncate at 32.

### `E007` — `description` missing
`description` is the agent's primary signal for whether to load the skill.
A skill without a description is invisible.

### `E008` — `description` too long
Spec limit is 1024 characters.

### `E009` — `description` contains XML tags
The spec forbids `<...>` in any field. The description is rendered as
plain text.

## Warnings (don't block by default)

These flag best-practice deviations. Pass `--strict` to fail on any warning.

### `W001` — no positive trigger phrase
The description should include a phrase like `use when …`, `whenever`,
`for …`, or `if the user …`. The agent uses these to decide whether to
load the skill.

### `W002` — no negative trigger phrase
The description should also include `do not use when …`, `not for …`, or
`skip when …`. Negative triggers cut over-firing — without them, a skill
will load in any vaguely related conversation.

### `W003` — body too short
Body has fewer than 20 lines. A skill this thin usually lacks the
context the agent needs to actually apply it.

### `W004` — body too long
Body has more than 200 lines. The agent's context budget is finite; move
detail into `references/` and link from the body. This is the progressive
disclosure pattern.

### `W005` — no `## When to use` (or equivalent) section
The body should have a clearly-labelled section that states the activation
conditions. Common labels: `## When to use`, `## Usage`, `## When`,
`## How to use`.

### `W006` — no concrete examples in body
Skills with examples are significantly more reliable in practice. The
checker looks for `example`, `e.g.`, `for example`, or `for instance`.

### `W007` — no SKILL.md in folder
You passed a folder that doesn't contain a `SKILL.md` (at root or under
`skills/`). Nothing to lint; add a skill first.

## Adding new rules

Each rule is a function `(path, fm, body) -> Iterable[LintFinding]`. Add
yours to the `_RULES` list in `skillmd_lint/rules.py` with a unique
`code` and a `LintSeverity`. Tests live in `tests/test_rules.py`.
