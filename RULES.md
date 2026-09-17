# Rules reference

Every rule `skillmd-lint` checks, with rationale and a minimal example.

> Tip: `skillmd-lint --list-rules` prints the same table at the terminal, and
> `RULE_INDEX` in `skillmd_lint.rules` exposes it programmatically.

## Errors (`E001`–`E010`)

### `E001` — SKILL.md file not found

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | `lint_file()` / `lint_folder()` is called on a missing path |
| Why     | Can't lint what doesn't exist          |
| Action  | Verify the path passed to the linter   |

### `E002` — Frontmatter missing or invalid

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | The file doesn't start with `---\n…\n---` or YAML is unparseable |
| Why     | Every skill declares name + description in YAML frontmatter; without it the agent can't load the skill |
| Action  | Add a frontmatter block delimited by `---`; check for unclosed YAML constructs |

### `E003` — `name` missing or empty

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | Frontmatter has no `name` key, or it's an empty string |
| Why     | The skill's identifier — required for routing, registry, and CLI targeting |
| Action  | Add `name: my-kebab-case-skill`        |

### `E004` — `name` not lowercase kebab-case

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | `name` contains uppercase letters, underscores, leading/trailing/double hyphens, or starts with a digit-after-letter |
| Why     | The spec requires lowercase kebab-case to keep identifiers portable across file systems and CLI tooling |
| Action  | Rename to `^[a-z0-9]+(-[a-z0-9]+)*$`    |

### `E005` — `name` collides with a reserved word

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | `name` matches a Windows device (`com1`..`com9`, `lpt1`..`lpt9`, `nul`, `prn`, `con`, `aux`), filesystem special (`.`, `..`, `~`), or platform-reserved name (`anthropic`, `claude`, `openai`, `gpt`, `grok`) |
| Why     | These names break cross-platform paths or shadow established products |
| Action  | Rename to something distinctive        |

### `E006` — `name` exceeds 64 characters

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | `name` is longer than 64 characters    |
| Why     | Spec limit; longer names break CLI arg limits and registry UIs |
| Action  | Shorten or use `description` for the long form |

### `E007` — `description` missing or empty

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | Frontmatter has no `description` key   |
| Why     | The agent uses `description` to decide whether to load the skill |
| Action  | Add a sentence that explains when to use the skill |

### `E008` — `description` exceeds 1024 characters

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | `description` is longer than 1024 characters |
| Why     | Spec limit; longer descriptions won't fit the discovery UI |
| Action  | Compress; move detail into the body    |

### `E009` — `description` contains XML tags

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | `description` contains `<...>` markup |
| Why     | Spec forbids markup in frontmatter strings; some parsers break on it |
| Action  | Strip the tags; use plain Markdown     |

### `E010` — `tags` list contains duplicates

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | The `tags` array lists the same string twice |
| Why     | Duplicates inflate the routing index for no benefit and confuse downstream filters |
| Action  | De-duplicate; each tag should appear once |

## Warnings (`W001`–`W013`)

### `W001` — Description missing a positive trigger phrase

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | `description` does not contain any of `use when`, `use this`, `when`, `whenever`, `for`, `trigger`, `applies when`, `if the user`, `whenever you need` |
| Why     | Positive triggers tell the agent *when to load* the skill; without them the agent guesses |
| Action  | Add `Use when …` to the description    |

### `W002` — Description missing a negative trigger

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | `description` does not contain `do not use`, `don't use`, `not for`, `do not apply`, `not appropriate`, `not applicable`, or `skip when` |
| Why     | Negative triggers reduce over-firing — they tell the agent *when NOT to load* the skill |
| Action  | Add `Don't use for …` or `Not for …`   |

### `W003` — Body has fewer than 20 lines

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | Body markdown is shorter than 20 lines |
| Why     | Skills shorter than 20 lines rarely have enough context for reliable behaviour |
| Action  | Add a `## When to use` section, an example, and a pitfalls note |

### `W004` — Body exceeds 200 lines

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | Body markdown is longer than 200 lines |
| Why     | Long bodies blow past context budgets and lose the agent's attention |
| Action  | Move detail into `references/` and link from the body |

### `W005` — No `## When to use` section

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | Body does not contain `## When to use` (or `## Usage`, `## When`, `## How to use`) |
| Why     | Readers (human and agent) need a one-paragraph map of activation conditions |
| Action  | Add a `## When to use` heading near the top of the body |

### `W006` — No concrete examples in body

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | Body does not contain `example`, `e.g.`, `for example`, or `for instance` |
| Why     | Skills with worked examples are significantly more reliable in practice |
| Action  | Add an `## Examples` section with 1–3 worked examples |

### `W007` — `skills/` subfolder has no `SKILL.md`

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | The folder contains a `skills/` subdirectory but no `SKILL.md` inside it |
| Why     | Suggests a partially authored skill that hasn't been finished |
| Action  | Either author the `SKILL.md` or remove the empty folder |

### `W008` — Frontmatter key looks like a typo

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | A key like `desription`, `desc`, `nme`, `tokkens`, `tokn_budget`, `tagss`, `entites`, `domian` matches a known typo in `FRONTMATTER_TYPO_MAP` |
| Why     | Common typos silently disable a frontmatter field; the linter catches them and suggests the canonical key |
| Action  | Rename to the canonical key (`description`, `name`, `token_budget`, `tags`, `entities`, `domain`) |

### `W009` — `skill_type` is not a recognised value

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | `skill_type` is set to something other than `domain-expert`, `specialist`, `workflow`, `hybrid` |
| Why     | Downstream consumers (catalogues, routing indexes) rely on these four values |
| Action  | Pick the closest match or remove the field |

### `W010` — `version` is not valid semver

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | `version` doesn't match `^X.Y.Z` with optional pre-release / build suffix |
| Why     | Version comparisons and registry filters break on non-semver strings |
| Action  | Use `1.0.0` or `1.0.0-rc.1` (no `v` prefix, no trailing notes) |

### `W011` — `token_budget` is not a positive integer

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | `token_budget` is missing, zero, negative, a boolean, or not an integer |
| Why     | Token-budget routing needs a real positive integer; `True`/`False` are subclasses of `int` and would otherwise slip through |
| Action  | Set to a positive integer like `1500`  |

### `W012` — No `## Pitfalls to avoid` section

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | Body doesn't contain `## Pitfalls`, `## Gotchas`, `## Common mistakes`, or `## What to avoid` |
| Why     | Skills that document what NOT to do are dramatically more reliable; the agent learns the failure modes |
| Action  | Add a `## Pitfalls to avoid` section near the end of the body |

### `W013` — Tag is not lowercase kebab-case

| Field   | Value                                  |
|---------|----------------------------------------|
| When    | A tag contains uppercase letters, underscores, spaces, or other non-kebab characters |
| Why     | Routing filters and tag clouds expect a stable token form |
| Action  | Rename to lowercase kebab-case (`my-tag`, not `My_Tag`) |

## JSON Schema

The full machine-readable contract is in
[`skillmd_frontmatter.schema.json`](skillmd_frontmatter.schema.json).
Use `--schema` on the CLI to enable schema validation on top of the rule
engine, or `validate_frontmatter(fm)` from Python. Schema findings are
reported with codes `S001`..`S999`.

## Adding new rules

Rules live in `skillmd_lint/rules.py`. Each rule is a function with the
signature `(path, fm, body) -> Iterable[LintFinding]`. To add a rule:

1. Pick a free `E###` or `W###` code; update `RULE_INDEX`.
2. Implement the rule as a generator. Guard against missing / wrong-type
   frontmatter keys with `isinstance(..., str)` checks.
3. Add tests in `tests/test_rules.py`.
4. Update this file.
5. Open a PR with rationale in the description.