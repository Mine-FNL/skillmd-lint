---
name: refactor-rename
description: >-
  Use when renaming a class, function, type, file, module, or public
  symbol across a codebase. Applies when the user asks for "rename
  this symbol", "rename a file safely", or "refactor the API name". Do
  not use for adding a new symbol (use the language's author flow), or
  for renaming a database column or a public URL — those have their own
  migration playbooks.
skill_type: workflow
domain_focus: code-quality
tags:
  - refactor
  - rename
  - refactoring
  - code-quality
  - ide
version: 1.0.0
version_notes: Gallery workflow skill covering IDE-assisted renames and verification.
token_budget: 1300
---

## When to use

Use when a rename touches more than one file and you need the change to
land atomically. The three principles:

1. **Always use the IDE's project-wide refactor, never find-and-replace.**
   Project-wide refactors understand scope: rename a class without
   renaming an unrelated field of the same name; rename a method without
   renaming every property that starts with the same prefix.
3. **Move in one commit, never across commits.** Half-renamed symbols
   break every CI run between the partial commits. If the rename is too
   big for one commit, branch it and merge via the platform's atomic
   merge (GitHub merge queue, GitLab MR squash) — not via a manual
   rebase.
4. **Verify with the compiler and the test suite, not with grep.** Grep
   finds string matches; the compiler finds symbol matches. After the
   refactor, the build must succeed with no errors and no new warnings.

## Examples

For example, renaming a class `UserService` to `AccountService` in a
TypeScript repo using the VS Code command palette:

```text
1. Right-click the class identifier → "Rename Symbol" (F2)
2. Type "AccountService" and press Enter
3. Review the diff: every reference in src/ and tests/ updated
4. Run `pnpm tsc --noEmit` to confirm zero type errors
5. Run the test suite — every fixture that imports the symbol updates
```

Renaming a Python module from `utils.py` to `string_utils.py` using
PyCharm:

```text
1. Right-click the file → Refactor → Rename (Shift+F6)
2. PyCharm updates imports across the project, including
   `from .utils import …` and `from package.utils import …`
3. The stale `__pycache__` and `.pyc` files for the old module must be
   removed manually; IDE refactors do not delete cache files
```

A verification command sequence for the renamed tree:

```bash
git grep -nE '\bUserService\b' -- ':!*.lock' || echo "no remaining references"
pnpm test --silent
```

## Pitfalls to avoid

- Do not use `sed` or `awk` for renames; they cannot distinguish a
  symbol from a string, comment, or unrelated identifier that shares
  the name.
- Do not rename across a rebase; the rebase will re-touch every commit
  that mentioned the old name, ballooning the diff and confusing blame.
- Do not skip the string-literal scan; renames miss strings, generated
  docs, JSON keys, and i18n catalogues. Grep for the old name with a
  word boundary.
- Do not forget to update `CHANGELOG.md`, the public docs site, and any
  generated API reference; those are out of scope for the IDE refactor
  and must be edited by hand.
- Do not rename and refactor behaviour in the same commit; if the test
  suite fails after the rename, you cannot tell whether the rename or
  the behaviour change is responsible.