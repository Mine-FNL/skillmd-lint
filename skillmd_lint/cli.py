"""``skillmd-lint`` command-line interface."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .rules import (
    LintResult,
    LintSeverity,
    lint_paths,
)

_HUMAN_GLYPHS = {
    LintSeverity.ERROR: "✗ error",
    LintSeverity.WARNING: "⚠ warning",
    LintSeverity.INFO: "info",
}


def _format_human(results: list[LintResult], strict: bool) -> str:
    lines: list[str] = []
    any_blocking_warning = False
    for r in results:
        if not r.findings and r.looks_like_skill:
            lines.append(f"  ✓ {r.path}: ok")
            continue
        lines.append(r.path)
        for f in r.findings:
            if f.severity == LintSeverity.WARNING and strict:
                # Treat as error for display.
                lines.append(f"  ✗ error   : {f.message}  [{f.code}]")
                any_blocking_warning = True
            else:
                lines.append(f"  {_HUMAN_GLYPHS[f.severity]:<11}: {f.message}  [{f.code}]")
    errors = sum(
        1
        for r in results
        for f in r.findings
        if f.severity == LintSeverity.ERROR or (f.severity == LintSeverity.WARNING and strict)
    )
    warnings = sum(
        1 for r in results for f in r.findings if f.severity == LintSeverity.WARNING and not strict
    )
    if any_blocking_warning:
        errors += 1  # already counted above
    if errors == 0 and warnings == 0:
        lines.append("")
        lines.append(f"✓ all {len(results)} file(s) passed")
    else:
        lines.append("")
        marker = "✗" if errors else "⚠"
        lines.append(f"{marker} {errors} error(s), {warnings} warning(s)")
    return "\n".join(lines)


def _format_github(results: list[LintResult], strict: bool) -> str:
    """GitHub Actions annotation format: ::error file=path,line=1::msg"""
    out: list[str] = []
    for r in results:
        for f in r.findings:
            sev = (
                "error"
                if f.severity == LintSeverity.ERROR
                or (f.severity == LintSeverity.WARNING and strict)
                else "warning"
            )
            out.append(f"::{sev} file={r.path},line=1::{f.code}: {f.message}")
    return "\n".join(out)


def _format_json(results: list[LintResult], strict: bool) -> str:
    out = []
    for r in results:
        d = r.to_dict()
        if strict:
            # Re-tag warnings as errors when strict.
            for w in d["warnings"]:
                w["severity"] = "error"
            d["errors"].extend(d["warnings"])
            d["warnings"] = []
            d["passed"] = not d["errors"]
        out.append(d)
    return json.dumps(out, indent=2)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="skillmd-lint",
        description=(
            "Lint and validate SKILL.md files against the open SKILL.md spec. "
            "CI-friendly, offline, no API key."
        ),
    )
    p.add_argument(
        "paths",
        nargs="+",
        help="SKILL.md file or skill folder to lint (folders ending in 'skills' are walked).",
    )
    p.add_argument(
        "--format",
        choices=["human", "json", "github"],
        default="human",
        help="Output format (default: human).",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors.",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"skillmd-lint {__version__}",
    )
    p.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress per-finding output; only print the summary line.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    results = lint_paths(args.paths)

    if args.format == "json":
        sys.stdout.write(_format_json(results, args.strict))
        sys.stdout.write("\n")
    elif args.format == "github":
        sys.stdout.write(_format_github(results, args.strict))
        sys.stdout.write("\n")
    elif not args.quiet:
        sys.stdout.write(_format_human(results, args.strict))
        sys.stdout.write("\n")

    # Exit code: 0 on success, 1 on any error (or any warning if --strict).
    has_errors = any((not r.passed) or (args.strict and r.warnings) for r in results)
    return 1 if has_errors else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
