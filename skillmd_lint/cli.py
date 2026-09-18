"""``skillmd-lint`` command-line interface."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .rules import (
    RULE_INDEX,
    LintResult,
    LintSeverity,
    lint_paths,
)
from .schema import validate_frontmatter

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


def _format_rules_list() -> str:
    lines: list[str] = []
    lines.append("skillmd-lint rules (v" + __version__ + "):")
    lines.append("")
    lines.append(f"  {'CODE':<6}  {'SEVERITY':<8}  SUMMARY")
    lines.append(f"  {'----':<6}  {'--------':<8}  -------")
    for code, sev, summary in RULE_INDEX:
        lines.append(f"  {code:<6}  {sev:<8}  {summary}")
    n_err = sum(1 for c, s, _ in RULE_INDEX if s == "error")
    n_warn = sum(1 for c, s, _ in RULE_INDEX if s == "warning")
    lines.append("")
    lines.append(f"  {n_err} error rules, {n_warn} warning rules.")
    return "\n".join(lines)


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
        nargs="*",
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
        "--schema",
        action="store_true",
        help=(
            "Run JSON Schema validation on top of the rule engine. Schema "
            "violations are reported as warnings with code S001..S999."
        ),
    )
    p.add_argument(
        "--list-rules",
        action="store_true",
        help="Print the full rule table and exit.",
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
    p.add_argument(
        "--fix",
        action="store_true",
        help=(
            "Apply safe mechanical fixes (typos, dedup tags, kebab-case tags, "
            "semver prefix, token_budget coercion) and rewrite each affected "
            "file in place."
        ),
    )
    p.add_argument(
        "--unsafe-fix",
        action="store_true",
        help=(
            "When used with --fix, also apply unsafe fixes that may lose "
            "information (name format coercion, skill_type alias mapping)."
        ),
    )
    p.add_argument(
        "--schema-export",
        metavar="PATH",
        help=(
            "Write the published JSON Schema for SKILL.md frontmatter to PATH "
            "and exit. Useful for editors, IDEs, and other validators that want "
            "to consume the spec contract without depending on Python."
        ),
    )
    p.add_argument(
        "--migrate",
        action="store_true",
        help=(
            "Treat the positional paths as source files (CLAUDE.md, "
            "AGENTS.md, or .cursorrules) and convert each to a SKILL.md. "
            "Mutually exclusive with the default lint behaviour; the lint "
            "flags are ignored when --migrate is set."
        ),
    )
    p.add_argument(
        "--migrate-out",
        metavar="PATH",
        help=(
            "Output path for the migrated SKILL.md (only with --migrate). "
            "If multiple sources are given, this is treated as a directory."
        ),
    )
    p.add_argument(
        "--migrate-format",
        choices=["auto", "claude_md", "agents_md", "cursorrules"],
        default="auto",
        help="Override format detection when migrating (default: auto from filename).",
    )
    return p


def _run_schema(results: list[LintResult]) -> list[LintResult]:
    """Augment results with S001 schema findings for any frontmatter that
    violates the published JSON Schema. Operates per-file; non-SKILL.md files
    (no frontmatter) are skipped.
    """

    from .rules import LintFinding

    out: list[LintResult] = []
    for r in results:
        if not r.looks_like_skill:
            out.append(r)
            continue
        # Re-derive frontmatter from the path so we can validate it. We don't
        # carry the parsed fm through the result intentionally — schema
        # validation is opt-in.
        try:
            from pathlib import Path

            import yaml

            text = Path(r.path).read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeError):
            out.append(r)
            continue
        stripped = text.lstrip("\ufeff")
        if not stripped.startswith("---"):
            out.append(r)
            continue
        lines_text = stripped.splitlines()
        end = None
        for i in range(1, len(lines_text)):
            if lines_text[i].strip() == "---":
                end = i
                break
        if end is None:
            out.append(r)
            continue
        try:
            fm = yaml.safe_load("\n".join(lines_text[1:end])) or {}
        except yaml.YAMLError:
            out.append(r)
            continue
        if not isinstance(fm, dict):
            out.append(r)
            continue
        new_findings = list(r.findings)
        for i, msg in enumerate(validate_frontmatter(fm), start=1):
            new_findings.append(
                LintFinding(
                    code=f"S{i:03d}",
                    severity=LintSeverity.WARNING,
                    message=f"schema: {msg}",
                )
            )
        out.append(
            LintResult(
                path=r.path,
                findings=new_findings,
                looks_like_skill=r.looks_like_skill,
            )
        )
    return out


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.list_rules:
        sys.stdout.write(_format_rules_list() + "\n")
        return 0

    if args.schema_export:
        return _write_schema_export(args.schema_export)

    if args.migrate:
        return _cmd_migrate(args)

    if not args.paths:
        sys.stderr.write("skillmd-lint: error: at least one path is required\n")
        return 2

    results = lint_paths(args.paths)
    if args.schema:
        results = _run_schema(results)

    if args.fix:
        _apply_fixes_to_paths(args.paths, results, unsafe=args.unsafe_fix)
        # Re-lint so the report reflects the post-fix state.
        results = lint_paths(args.paths)
        if args.schema:
            results = _run_schema(results)

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


def _write_schema_export(path: str) -> int:
    """Write the published JSON Schema for SKILL.md frontmatter to ``path``."""

    from pathlib import Path

    from .schema import get_schema

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    import json as _json

    target.write_text(_json.dumps(get_schema(), indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(f"wrote schema to {target}\n")
    return 0


def _apply_fixes_to_paths(
    paths: list[str],
    results: list,
    unsafe: bool = False,
) -> None:
    """For each path with fixable findings, rewrite the file in place."""

    from pathlib import Path

    from .fix import apply_fixes

    # Map: path string → LintResult
    by_path: dict[str, object] = {r.path: r for r in results}

    for raw in paths:
        p = Path(raw)
        if not p.is_file():  # pragma: no cover
            continue
        result = by_path.get(str(p))
        if result is None:  # pragma: no cover
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            sys.stderr.write(f"skillmd-lint: cannot read {p}: {exc}\n")
            continue
        new_text, applied = apply_fixes(text, result, unsafe=unsafe)
        if not applied:
            continue
        try:
            p.write_text(new_text, encoding="utf-8")
        except OSError as exc:
            sys.stderr.write(f"skillmd-lint: cannot write {p}: {exc}\n")
            continue
        for fa in applied:
            marker = "fixed" if not fa.unsafe else "fixed (unsafe)"
            sys.stdout.write(f"  {marker:18s} {p}: [{fa.code}] {fa.description}\n")


def _cmd_migrate(args) -> int:
    """Handle the ``--migrate`` flag."""

    from pathlib import Path

    from .migrate import migrate_file, migrate_path

    fmt = None if args.migrate_format == "auto" else args.migrate_format
    out = Path(args.migrate_out) if args.migrate_out else None

    results: list = []
    if len(args.paths) == 1:
        src = Path(args.paths[0])
        if src.is_file():
            target = out if out else src.parent / "SKILL.md"
            results.append(migrate_file(src, target=target, fmt=fmt))
        elif src.is_dir():
            # Discover all candidate files in the directory
            discovered = migrate_path(src)
            if out:
                # Treat as a directory: ensure it exists and write each
                # migrated SKILL.md into it.
                out.mkdir(parents=True, exist_ok=True)
                for r in discovered:
                    new_target = out / "SKILL.md"
                    results.append(migrate_file(r.source, target=new_target, fmt=fmt))
            else:
                results.extend(discovered)
        else:
            sys.stderr.write(f"skillmd-lint: source not found: {src}\n")
            return 2
    else:
        # Multiple source files
        for raw in args.paths:
            src = Path(raw)
            if not src.is_file():
                sys.stderr.write(f"skillmd-lint: skipping non-file: {src}\n")
                continue
            target = (out / "SKILL.md") if (out and out.is_dir()) else None
            results.append(migrate_file(src, target=target, fmt=fmt))

    if not results:  # pragma: no cover
        sys.stderr.write("skillmd-lint: no recognised source files found\n")
        return 2

    rc = 0
    for r in results:
        if r.success:
            sys.stdout.write(f"  migrated  {r.source}\n")
            sys.stdout.write(f"  →         {r.target}\n")
            sys.stdout.write(f"  format    {r.format_detected}\n")
            for w in r.warnings:
                sys.stdout.write(f"  warn      {w}\n")
        else:
            rc = 1
            for w in r.warnings:
                sys.stderr.write(f"skillmd-lint: {r.source}: {w}\n")
    return rc


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
