---
name: skillmd-authoring
description: >-
  Use when authoring, reviewing, or refactoring a SKILL.md file that
  follows the open SKILL.md spec at agentskills.io. Applies when the
  user asks for "write a skill", "review my SKILL.md", or "what should
  go in the frontmatter". Do not use for authoring plain Markdown
  documentation, for writing prompt templates, or for designing
  product features — SKILL.md is one specific file format with strict
  rules.
skill_type: hybrid
domain_focus: skill-authoring
tags:
  - skill-md
  - authoring
  - meta
  - documentation
  - agentskills
version: 1.0.0
version_notes: Meta-skill that links the rules in skillmd-lint to authoring practice.
token_budget: 1700
---

## When to use

Use when the deliverable is a SKILL.md file and the user wants the file
to validate against `skillmd-lint --strict --schema`. The format is
strict but the authoring is opinionated: each frontmatter field has a
job, each body section has a purpose, and every line either helps the
agent decide to load the skill or helps the agent execute it well.

Frontmatter fields, in priority order:

- **`name`** (required): the slug the agent uses to identify the skill.
  Lowercase kebab-case, ≤ 64 chars, must not collide with a reserved
  word (`anthropic`, `claude`, `openai`, `gpt`, `grok`, Windows device
  names like `com1`, filesystem specials like `.` and `..`).
- **`description`** (required): the activation signal. Must contain a
  positive trigger ("use when", "whenever", "for", "applies when")
  and a negative trigger ("do not use when", "not for", "skip when").
  The agent uses these to decide whether to load the skill.
- **`skill_type`** (recommended): one of `domain-expert`, `specialist`,
  `workflow`, `hybrid`. Routing indexes use this for cataloguing.
- **`domain_focus`** (optional): a short string naming the focus area.
- **`tags`** (optional): lowercase kebab-case strings, no duplicates.
- **`version`** (recommended): strict semver (`1.2.3` or `1.0.0-rc.1`).
- **`token_budget`** (recommended): a positive integer approximating
  the cost of loading the skill.

Body sections, in order of value to the agent:

1. `## When to use` — the activation paragraph.
2. `## Examples` — at least one concrete worked example.
3. `## Pitfalls to avoid` — failure modes the agent should not repeat.

## Examples

For example, a minimal SKILL.md that passes every rule:

```markdown
---
name: short-slug
description: >-
  Use when the user asks to do X. Applies to Y and Z. Do not use for W;
  use a different skill instead.
skill_type: specialist
domain_focus: example
tags:
  - example
  - skill-md
version: 1.0.0
token_budget: 800
---

## When to use

Use when the user asks to do X.

## Examples

For example, a one-line invocation:

\`\`\`bash
do-the-thing --flag value
\`\`\`

## Pitfalls to avoid

- Do not run `do-the-thing` without `--flag`; the default behaviour is
  destructive.
```

The same file linted:

```bash
$ skillmd-lint --strict --schema examples/short-slug/
✓ examples/short-slug/SKILL.md: ok
✓ all 1 file(s) passed
```

## Pitfalls to avoid

- Do not put XML tags in the description; for example `<code>` and
  `</code>` are forbidden and trip `E009`.
- Do not use uppercase, underscores, or spaces in the `name`; the
  kebab-case pattern is `^[a-z0-9]+(-[a-z0-9]+)*$` and anything else
  trips `E004`.
- Do not skip the negative trigger phrase in the description; even
  one occurrence of "not for" or "do not use" turns off `W002`.
- Do not write a body shorter than 20 lines; add a worked example and
  a pitfalls section before declaring the skill done.
- Do not duplicate a tag in the `tags` array; duplicates trip the
  `E010` error and block CI.
- Do not leave the version field empty or as a `v`-prefixed string;
  `v1.0` trips `W010`, while `1.0.0` passes.