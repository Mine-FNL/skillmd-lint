---
name: security-review-checklist
description: >-
  Use when reviewing a code change for security implications — pull
  requests touching auth, secrets, crypto, input handling, deserialization,
  network calls, file system access, or any user-controlled data flow.
  Triggered by "security review", "is this safe to ship", "any vulns
  here", or "audit this change". Do not use for general code review
  (use code-review-checklist), threat modelling new systems (use a
  dedicated threat-modelling skill), or compliance audits.
skill_type: workflow
domain_focus: security
tags:
  - security
  - audit
  - pr-review
  - secrets
  - auth
version: 1.0.0
version_notes: Gallery security-review workflow. STRIDE-driven checklist with concrete fail conditions.
token_budget: 1600
---

## When to use

Use when a change touches any of the following surface area:

- Authentication, session handling, password reset, MFA
- Authorization checks (RBAC, ABAC, ownership, multi-tenancy)
- Secret handling, key rotation, KMS access
- Cryptographic operations (encryption, hashing, signing, RNG)
- Deserialization of untrusted input (JSON with allowlists, pickle, YAML load)
- Network egress and ingress (URL handling, SSRF, DNS rebinding)
- File system access (path traversal, symlink attacks, temp file races)
- Database queries (SQL injection, ORM pitfalls, transaction boundaries)
- HTML/email rendering (XSS, content sniffing, URL sanitization)
- Process execution (shell injection, command arguments)
- Dependency changes (new package, version bump)

Skip this checklist if the change is documentation-only, test-only, or
purely cosmetic. Run it once per PR, even if the change feels small.

## Examples

For example, a PR that adds a new `POST /api/v2/users/{id}/avatar` endpoint:

```text
[✓] Auth: the route requires an authenticated session (not just any token)
[✓] Authz: the loader enforces the caller owns {id} OR has admin role
[ ] Input: file MIME type is sniffed, not trusted from Content-Type
[ ] Input: file size limit enforced before streaming to disk
[✓] Path: filename is sanitised — no ../, no NUL, length capped
[ ] Storage: files written outside the web root, served via signed URL
[✓] Secrets: the S3 credentials are loaded from the secret manager,
    not from environment variables
[ ] Logging: the request body is NOT logged (PII + secrets)
[ ] Errors: 4xx and 5xx return JSON, not HTML or stack traces
[ ] Tests: a request without auth returns 401 (not 500, not 302)
[ ] Tests: a path-traversal payload returns 400 (not 500, not 200)
```

A PR that bumps a dependency from `requests==2.31.0` to `requests==2.32.0`:

```text
[✓] Changelog entry links the CVE-2024-35195 fix
[✓] The pinned hash matches the upstream release
[✓] No transitive regression in urllib3 (lock file diff reviewed)
[✓] CI re-runs the full integration suite on the bumped version
[ ] Dependabot / Renovate config updated if needed
```

## Pitfalls to avoid

- **Do not** treat a passing security linter as a complete review. Bandit,
  Semgrep, and CodeQL catch known patterns; they do not catch missing
  auth checks, broken object-level authorisation, or business-logic flaws.
- **Do not** approve a change because "we already do this elsewhere".
  Each instance is a new attack surface until proven otherwise.
- **Do not** flag findings without a concrete reproduction. "Looks
  suspicious" is not actionable; "POST /api with `Authorization: Bearer`
  plus a tampered JWT signature returns 200" is.
- **Do not** defer security fixes to follow-up PRs. A separate fix PR
  is fine; a separate fix sprint is not.
- **Do not** assume secrets in environment variables are safe. They show
  up in `ps`, in crash dumps, in error reports, in container images, and
  in CI logs.
- **Do not** approve a change that adds a new dependency without
  checking the package's history, the maintainer's reputation, and
  whether it has had a security incident in the last 12 months.
