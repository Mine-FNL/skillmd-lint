---
name: git-bisect-bugs
description: >-
  Use when a regression has been introduced in a long-lived codebase and
  the user knows the bug is present in `HEAD` but absent in some older
  release. Applies when the user asks for "find the bad commit", "git
  bisect", "binary search the history", or "which commit introduced
  this bug". Do not use for bug hunts that do not have a known-good
  commit (use `git log -S` or a manual review), or for bisecting test
  runtime rather than correctness.
skill_type: workflow
domain_focus: vcs
tags:
  - git
  - bisect
  - debugging
  - regression
  - vcs
version: 1.0.0
version_notes: Gallery workflow skill covering manual and scripted git bisect.
token_budget: 1300
---

## When to use

Use when the user can answer "is this commit good or bad?" with a
deterministic check — a failing test, a CLI exit code, a database
state assertion. The bisect algorithm does a binary search over the
linear commit history and converges in `O(log n)` steps; for 1,024
commits it needs at most 10 judgements.

The discipline:

1. Confirm the bug is reproducible on `HEAD` and absent on a known
   good commit (a release tag, the previous release branch tip, a
   commit the bug reporter remembers working).
2. Write the deterministic check before starting the bisect. The
   check must run in seconds; if it takes minutes, the bisect will
   take hours.
3. `git bisect start`, mark the bad commit (`bisect bad`) and the
   good commit (`bisect good <sha>`).
4. For each bisect step, run the check, then mark `bisect good` or
   `bisect bad`. Git picks the next commit to test.
5. When git prints "`<sha>` is the first bad commit", verify by
   checking out that commit and running the check yourself.
6. `git bisect reset` to return to `HEAD`.

## Examples

A scripted bisect for a Rust regression using `cargo test`:

```bash
git bisect start
git bisect bad HEAD
git bisect good v1.4.0

# Run a single failing test; exit 0 = bad, exit 1 = good.
git bisect run sh -c 'cargo test --test regression -- --exact bug_1234 || exit 1 && exit 0'
```

When `cargo test` exits non-zero (the test failed — the bug is
present), the run script exits `1` and git records the commit as
*bad*. When the test passes (the bug is absent), the script exits
`0` and git records the commit as *good*.

For example, a manual bisect with a small history:

```text
$ git bisect start
$ git bisect bad HEAD
$ git bisect good abc1234
Bisecting: 4 revisions left to test after this (roughly 2 steps)
[def5678] refactor: extract OrderValidator
$ cargo test parser    # passes
$ git bisect good
Bisecting: 2 revisions left to test after this (roughly 1 step)
[hij9012] feat(orders): add loyalty discount
$ cargo test parser    # fails
$ git bisect bad
[hij9012] feat(orders): add loyalty discount is the first bad commit
```

## Pitfalls to avoid

- Do not skip writing the deterministic check; "look at the output and
  decide" is biased and inconsistent. The check must be a single
  command whose exit code encodes the answer.
- Do not run `git bisect run` with anything that depends on the working
  tree from a previous step; bisect checks out commits automatically
  and any untracked artefacts from earlier steps will leak in.
- Do not use `git bisect skip` to escape a hard-to-test commit unless
  the bug genuinely cannot be reproduced at that revision; over-using
  `skip` defeats the binary search.
- Do not forget to `git bisect reset` after you finish; the bisect
  state marks `refs/bisect/*` and a forgotten reset leaves the
  repository in a confusing state.
- Do not trust the first bad commit blindly; verify it by checking
  out the parent and running the same check. Bisect is statistical in
  the face of flaky checks, not a proof.