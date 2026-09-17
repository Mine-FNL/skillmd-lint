"""skillmd-lint: lint and validate SKILL.md files against the open spec.

Public API:

- :class:`LintFinding` — a single rule violation (error / warning / info).
- :class:`LintResult` — findings for one file plus pass/fail status.
- :func:`lint_file` — lint a single file by path.
- :func:`lint_text` — lint SKILL.md content from a string.
- :func:`lint_folder` — lint a folder; returns the union of file-level results.
- :func:`main` — CLI entrypoint (``python -m skillmd_lint``).

Quick start::

    from skillmd_lint import lint_file
    result = lint_file("path/to/SKILL.md")
    print(result)
    if not result.passed:
        raise SystemExit(1)
"""

__version__ = "1.0.0"

from .cli import main as _cli_main
from .rules import (
    LintFinding,
    LintResult,
    LintSeverity,
    lint_file,
    lint_folder,
    lint_text,
)

# Re-export ``main`` under its natural name for ``python -m skillmd_lint``.
main = _cli_main

__all__ = [
    "LintFinding",
    "LintResult",
    "LintSeverity",
    "__version__",
    "lint_file",
    "lint_folder",
    "lint_text",
    "main",
]
