---
name: Bug report
about: Something is broken or behaves incorrectly
title: "bug: "
labels: ["bug"]
assignees: []
---

## What happened

A clear, one-paragraph description of the bug.

## Reproduction

A minimal SKILL.md that triggers the bug, plus the exact command you
ran and the output you got.

````markdown
```yaml
---
name: example
description: ...
---
# Body
```
````

```bash
$ skillmd-lint path/to/SKILL.md
<actual output>
```

## Expected

What you expected to happen.

## Environment

- `skillmd-lint` version (`skillmd-lint --version`)
- Python version (`python --version`)
- OS (Linux / macOS / Windows; distribution if relevant)
- Install method (pip / uv / pipx / from source)

## Anything else

Screenshots, related issues, workarounds you've tried.