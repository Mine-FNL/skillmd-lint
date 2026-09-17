# Skill gallery

A curated set of high-quality `SKILL.md` files that pass
[`skillmd-lint --strict --schema`](../README.md) with **zero findings**.

The gallery is a reference corpus for downstream skill authors. Every entry:

- Uses lowercase kebab-case `name`.
- Has a `description` with both a positive *and* a negative trigger phrase.
- Declares `skill_type`, `domain_focus`, `tags`, `version`, `token_budget`.
- Includes a `## When to use`, `## Examples`, and `## Pitfalls to avoid`
  section in the body, with at least one concrete worked example.
- Body is between 20 and 200 lines (no truncated stubs, no runaway walls
  of text).

Use these files as starting points when authoring your own skill, or run
`./run_lint.sh` to verify the whole gallery still lints clean after your
edits.

## Index

| Skill                                    | Type           | What it covers                                           |
|------------------------------------------|----------------|----------------------------------------------------------|
| [`api-pagination/`](./api-pagination/)               | specialist     | REST API pagination patterns: offset, cursor, keyset, link header |
| [`typescript-strict-mode/`](./typescript-strict-mode/) | domain-expert  | Migrating a JS codebase to TypeScript with strict mode     |
| [`postgres-migrations/`](./postgres-migrations/)      | domain-expert  | Safe PostgreSQL schema migrations on a live database      |
| [`code-review-checklist/`](./code-review-checklist/)  | workflow       | Structured PR review checklist                            |
| [`debug-distributed-systems/`](./debug-distributed-systems/) | specialist | Debugging distributed traces with OpenTelemetry-style IDs |
| [`refactor-rename/`](./refactor-rename/)              | workflow       | Safe symbol rename across a codebase                     |
| [`wireguard-vpn/`](./wireguard-vpn/)                  | domain-expert  | WireGuard VPN setup on Linux                              |
| [`csp-headers/`](./csp-headers/)                      | specialist     | Content-Security-Policy header design                     |
| [`git-bisect-bugs/`](./git-bisect-bugs/)              | workflow       | Using `git bisect` to find regression-introducing commits |
| [`skillmd-authoring/`](./skillmd-authoring/)          | hybrid         | Meta-skill about authoring SKILL.md files                |

## One-line descriptions

- **api-pagination** — Pick the right pagination strategy (offset, cursor,
  keyset, link header) for a REST endpoint and ship it without leaking
  cursor internals.
- **typescript-strict-mode** — Migrate a JavaScript project to TypeScript
  in cohorts (`noImplicitAny`, then `strictNullChecks`, then the rest),
  instead of enabling `strict: true` on day one.
- **postgres-migrations** — Roll schema changes against a live PostgreSQL
  database using expand-and-contract, batched backfills, and
  `CREATE INDEX CONCURRENTLY`.
- **code-review-checklist** — Review a PR for correctness, tests,
  shippability, and readability in that order, with a minimal review
  comment template.
- **debug-distributed-systems** — Anchor on a trace ID, walk the span
  tree, correlate logs, and form one testable hypothesis at a time.
- **refactor-rename** — Use the IDE's project-wide refactor for renames,
  verify with the compiler not grep, and never split a rename across
  commits.
- **wireguard-vpn** — Configure `wg0` for a kernel-module WireGuard mesh,
  generate keys with `wg genkey`, and debug handshake failures.
- **csp-headers** — Design a strict Content-Security-Policy with
  nonce-based `script-src` and `'strict-dynamic'`, rolled out via
  `Report-Only`.
- **git-bisect-bugs** — Run `git bisect` against a known-good and
  known-bad commit, with a deterministic check whose exit code encodes
  the verdict.
- **skillmd-authoring** — Author a SKILL.md that validates against
  `skillmd-lint --strict --schema` and follows the open agentskills.io
  spec.

## Run the linter

```bash
./run_lint.sh
```

The script iterates every directory under `examples/`, runs the linter
in strict + schema mode, and exits non-zero on any finding. The exit
code is what CI should check; the printed summary is for humans.

## Adding a new skill

1. Create `examples/<kebab-case-slug>/SKILL.md`.
2. Follow the checklist in [`skillmd-authoring/`](./skillmd-authoring/).
3. Run `./run_lint.sh` — it must exit `0`.
4. Add a row to the table above and a one-line description in this
   README.
6. Open a PR.