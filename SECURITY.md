# Security Policy

## Supported versions

| Version | Supported          |
|---------|--------------------|
| 1.2.x   | ✅ active          |
| 1.1.x   | ✅ bug-fix only    |
| 1.0.x   | ❌ end-of-life     |
| < 1.0   | ❌ not supported   |

## Reporting a vulnerability

If you discover a security vulnerability in `skillmd-lint`, please
report it privately via one of these channels (in order of preference):

1. **GitHub Security Advisories** — open a
   [draft security advisory](https://github.com/Mine-FNL/skillmd-lint/security/advisories/new)
   on this repository. The maintainers get a private channel for
   disclosure and can coordinate a fix + CVE if needed.
2. **Email** — `security@Mine-FNL.dev` (replace with the actual
   contact once the maintainer publishes one; in the meantime, use
   GitHub).

Please **do not** open a public issue for security problems. Public
disclosure before a fix is available helps attackers more than users.

## What to include

A useful security report has:

- A description of the vulnerability and its impact.
- Reproduction steps (a SKILL.md sample + the linter command).
- The version of `skillmd-lint` and the Python version.
- Any workarounds you've found.
- Whether you'd like credit in the advisory (and how to attribute).

## Response timeline

- **Acknowledge** within 3 business days.
- **Triage and assess** within 7 days.
- **Fix or document** as soon as feasible. Critical issues may
  trigger an out-of-band release.

## Out-of-scope

`skillmd-lint` is a static-analysis tool that reads SKILL.md files and
emits findings. It does not execute any of the contents of those files
(no `eval`, no network calls at runtime beyond PyPI for installation,
no filesystem writes outside its own cache). The threat model is
small:

- A malformed SKILL.md that crashes the linter → bug, not security.
- A SKILL.md with embedded prompts targeting the agent that loads it →
  out of scope. The linter only *validates* the skill; it doesn't load
  or execute it. Callers are responsible for sandboxing skill bodies.

If you're unsure whether something is a security bug or a regular
bug, report it as security and we can downgrade if needed.