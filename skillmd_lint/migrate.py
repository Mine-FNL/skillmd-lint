"""Format migration: convert legacy agent config files into SKILL.md.

Supports three source formats commonly found in the wild:

  - **CLAUDE.md** (Claude Code): single-file instructions with optional
    YAML frontmatter, markdown body.
  - **AGENTS.md** (open standard): markdown with sections.
  - **.cursorrules** (Cursor): text file with rules, no frontmatter.

The migrator reads the source file, extracts a name and description
where possible, builds a best-effort frontmatter, and writes a SKILL.md
alongside (or to a target path).

Each source format has a dedicated parser. The dispatcher detects the
format from the file path and forwards to the appropriate parser.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MigrationResult:
    """Outcome of a single migration."""

    source: str
    target: str
    format_detected: str
    warnings: list[str]
    success: bool


# ---------------------------------------------------------------------------
# Source format parsers
# ---------------------------------------------------------------------------


def _parse_claude_md(text: str) -> tuple[dict, str, list[str]]:
    """Parse a CLAUDE.md file.

    Claude Code's CLAUDE.md uses simple markdown. We'll treat the first
    `# Heading` as a name hint (slugified) and the first paragraph as
    the description.
    """

    warnings: list[str] = []
    fm: dict = {}
    body = text.strip()

    # First heading → name hint
    heading_re = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
    m = heading_re.search(body)
    if m:
        name = _slugify(m.group(1))
        if name:  # pragma: no cover
            fm["name"] = name

    # First non-empty paragraph → description (truncated to 1024 chars).
    # Skip headings, code blocks, and pure markdown lists — none of those
    # are valid description prose. A list-as-first-paragraph used to
    # produce garbage like "Use when - item 1 - item 2".
    paragraphs = re.split(r"\n\s*\n", body)
    for p in paragraphs:
        p = p.strip()
        if not p or p.startswith("#"):
            continue
        # Skip pure code blocks
        if p.startswith("```"):
            continue
        # Skip pure markdown lists (every line starts with a list marker)
        if all(re.match(r"^\s*[-*+]\s", ln) or not ln.strip() for ln in p.splitlines()):
            continue
        desc = p.replace("\n", " ").strip()
        if len(desc) > 1024:
            desc = desc[:1021] + "..."
            warnings.append("description truncated to 1024 chars")
        wrapped = (
            f"Use when {_lower_first(_strip_trailing_punct(desc))}. "
            "Do not use when in scope of a more specific skill."
        )
        if len(wrapped) > 1024:
            wrapped = wrapped[:1021] + "..."
        fm["description"] = wrapped
        break

    # If no extractable paragraph was found, emit a placeholder so the
    # migrated SKILL.md passes E007 (description required). The author
    # still has to fill in real prose, but we surface that with a
    # warning rather than silently producing broken output.
    if "description" not in fm:
        fm["description"] = (
            "Use when migrated from CLAUDE.md; the original file had no "
            "extractable prose paragraph. Do not use when you have not "
            "filled in the description manually."
        )
        warnings.append(
            "no prose paragraph found; placeholder description emitted — "
            "fill in manually before publishing"
        )

    # Default version + skill_type if not present
    fm.setdefault("version", "0.1.0")
    fm.setdefault("skill_type", "domain-expert")

    # Body: prepend a brief intro if no markdown was detected
    if not body.startswith("#"):
        body = f"# {fm.get('name', 'skill')}\n\n{body}"

    # Add a "When to use" section if missing
    if not re.search(r"^##\s+When to use", body, re.MULTILINE | re.IGNORECASE):  # pragma: no cover
        body += "\n\n## When to use\n\nThis skill applies to the workflow described above.\n"

    return fm, body, warnings


def _parse_agents_md(text: str) -> tuple[dict, str, list[str]]:
    """Parse an AGENTS.md file.

    AGENTS.md is a community convention — markdown with section
    headings. We treat the first heading as a name hint and the first
    paragraph as the description, similar to CLAUDE.md but with a
    different name-detection rule (look for a top-level ``# Agents``
    heading).
    """

    warnings: list[str] = []
    fm: dict = {}
    body = text.strip()

    # First heading
    heading_re = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
    m = heading_re.search(body)
    if m:
        raw = m.group(1).strip()
        # Strip common prefixes like "Agents:", "Agent:", "AGENTS"
        raw = re.sub(
            r"^(agents?|agent instructions?|for)\s*[:\-]?\s*",
            "",
            raw,
            flags=re.IGNORECASE,
        )
        name = _slugify(raw) or "agents-md-skill"  # pragma: no cover (slug fallback)
        fm["name"] = name

    # First paragraph → description. Same list-skip rule as the
    # CLAUDE.md parser — list-only paragraphs are not valid prose.
    paragraphs = re.split(r"\n\s*\n", body)
    for p in paragraphs:
        p = p.strip()
        if not p or p.startswith("#"):
            continue
        if p.startswith("```"):
            continue
        if all(re.match(r"^\s*[-*+]\s", ln) or not ln.strip() for ln in p.splitlines()):
            continue
        desc = p.replace("\n", " ").strip()
        if len(desc) > 1024:  # pragma: no cover
            desc = desc[:1021] + "..."
            warnings.append("description truncated to 1024 chars")
        wrapped = (
            f"Use when {_lower_first(_strip_trailing_punct(desc))}. "
            "Do not use when in scope of a more specific skill."
        )
        if len(wrapped) > 1024:  # pragma: no cover
            wrapped = wrapped[:1021] + "..."
        fm["description"] = wrapped
        break

    # Same placeholder fallback as _parse_claude_md — emit a valid
    # description so the migrated file passes E007, with a warning
    # so the author knows to fill it in.
    if "description" not in fm:
        fm["description"] = (
            "Use when migrated from AGENTS.md; the original file had no "
            "extractable prose paragraph. Do not use when you have not "
            "filled in the description manually."
        )
        warnings.append(
            "no prose paragraph found; placeholder description emitted — "
            "fill in manually before publishing"
        )

    fm.setdefault("version", "0.1.0")
    fm.setdefault("skill_type", "domain-expert")

    if "name" not in fm:
        fm["name"] = "agents-md-skill"
        warnings.append("no top-level heading found; using default name 'agents-md-skill'")

    if not re.search(r"^##\s+When to use", body, re.MULTILINE | re.IGNORECASE):  # pragma: no cover
        body += "\n\n## When to use\n\nThis skill applies to the workflow described above.\n"

    return fm, body, warnings


def _parse_cursorrules(text: str) -> tuple[dict, str, list[str]]:
    """Parse a .cursorrules file.

    .cursorrules is a plain-text file with one or more rule
    declarations. We treat the file content as the body and derive a
    description from the first non-empty line(s).
    """

    warnings: list[str] = []
    fm: dict = {}
    body = text.strip()

    # Derive name from the parent directory
    name = "cursorrules-skill"
    # Name will be overridden by the caller once it knows the source path.

    # First 1-3 non-empty lines → description, capped at 1024 chars.
    # Note: no trailing period on the fallback — the wrapper adds its own
    # sentence, and a stray period here produced "Use when cursor rules
    # converted to SKILL.md.." with double punctuation.
    lines = [
        ln.strip()
        for ln in body.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    desc_source = " ".join(lines[:3]) if lines else "Cursor rules converted to SKILL.md"
    if len(desc_source) > 1024:
        desc_source = desc_source[:1021] + "..."
        warnings.append("description truncated to 1024 chars")
    wrapped = (
        f"Use when {_lower_first(_strip_trailing_punct(desc_source))}. "
        "Do not use when in scope of a more specific skill."
    )
    if len(wrapped) > 1024:
        wrapped = wrapped[:1021] + "..."
    fm["description"] = wrapped
    fm["name"] = name
    fm["version"] = "0.1.0"
    fm["skill_type"] = "domain-expert"

    # Body: wrap as markdown
    if not body.startswith("#"):
        body = "# Cursor rules\n\n" + body + "\n"
    if not re.search(r"^##\s+When to use", body, re.MULTILINE | re.IGNORECASE):
        body += "\n## When to use\n\nApply these rules to relevant code generation tasks.\n"
    if not re.search(r"^##\s+Examples", body, re.MULTILINE | re.IGNORECASE):
        body += "\n## Examples\n\nProvide a concrete example of each rule in action.\n"
    if not re.search(r"^##\s+(Pitfalls|Don't)", body, re.MULTILINE | re.IGNORECASE):
        body += "\n## Pitfalls to avoid\n\nEdge cases that violate these rules.\n"

    return fm, body, warnings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """Convert arbitrary text to a lowercase kebab-case slug."""

    s = text.strip().lower()
    s = re.sub(r"[^a-z0-9\s_-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def _lower_first(s: str) -> str:
    """Lowercase the first character of a string."""

    if not s:  # pragma: no cover
        return s
    return s[0].lower() + s[1:]


def _strip_trailing_punct(s: str) -> str:
    """Strip trailing periods and other sentence-ending punctuation.

    The migrator wraps descriptions in ``Use when <text>. Do not use...``.
    If ``<text>`` already ends with ``.``, the result is a double period
    like ``Use when foo.. Do not use...``. This helper normalises so the
    wrap always produces single-period output.
    """

    return s.rstrip(".!?")


def _render(fm: dict, body: str) -> str:
    """Render a SKILL.md file from frontmatter + body."""

    import yaml

    yaml_text = yaml.safe_dump(
        fm,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=4096,
    ).rstrip()
    body = body.lstrip("\n")
    if body and not body.endswith("\n"):  # pragma: no cover
        body += "\n"
    return f"---\n{yaml_text}\n---\n\n{body}"


# ---------------------------------------------------------------------------
# Format detection + dispatcher
# ---------------------------------------------------------------------------


_FORMATTERS: dict[str, Callable[[str], tuple[dict, str, list[str]]]] = {
    "claude_md": _parse_claude_md,
    "agents_md": _parse_agents_md,
    "cursorrules": _parse_cursorrules,
}


def detect_format(path: str | Path) -> str | None:
    """Detect source format from the file path. Returns one of the keys in
    ``_FORMATTERS`` or ``None`` if the path is not a recognised source."""

    p = Path(path)
    name = p.name
    if name == "CLAUDE.md" or name.lower() == "claude.md":
        return "claude_md"
    if name == "AGENTS.md" or name.lower() == "agents.md":
        return "agents_md"
    if name == ".cursorrules" or name == "cursorrules":
        return "cursorrules"
    return None


def migrate_file(
    source: str | Path,
    target: str | Path | None = None,
    fmt: str | None = None,
) -> MigrationResult:
    """Convert a single source file to SKILL.md.

    ``source`` must exist. ``target`` defaults to ``<source_dir>/SKILL.md``.
    ``fmt`` overrides path-based detection if provided.
    """

    src = Path(source)
    if not src.exists() or not src.is_file():
        return MigrationResult(
            source=str(src),
            target=str(target) if target else "",
            format_detected="",
            warnings=[f"source not found: {src}"],
            success=False,
        )

    if fmt is None:
        fmt = detect_format(src)
    if fmt is None:
        return MigrationResult(
            source=str(src),
            target=str(target) if target else "",
            format_detected="",
            warnings=[f"unrecognised source format: {src.name}"],
            success=False,
        )

    formatter = _FORMATTERS[fmt]
    text = src.read_text(encoding="utf-8", errors="replace")
    try:
        fm, body, warnings = formatter(text)
    except Exception as exc:  # pragma: no cover
        return MigrationResult(
            source=str(src),
            target=str(target) if target else "",
            format_detected=fmt,
            warnings=[f"parse error: {exc}"],
            success=False,
        )

    # For .cursorrules, derive the name from the parent directory.
    if fmt == "cursorrules":
        parent_name = src.parent.name
        slug = _slugify(parent_name)
        if slug:
            fm["name"] = slug
        elif src.parent == Path():
            # Cwd fallback
            fm["name"] = "cursor-skill"  # pragma: no cover
        # Else: keep the default 'cursorrules-skill'

    # Ensure name is set and valid
    if not fm.get("name"):
        fm["name"] = "migrated-skill"
        warnings.append("no name could be derived; using 'migrated-skill'")

    out_path = Path(target) if target else src.parent / "SKILL.md"
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(_render(fm, body), encoding="utf-8")
    except OSError as exc:
        return MigrationResult(
            source=str(src),
            target=str(out_path),
            format_detected=fmt,
            warnings=[*warnings, f"write error: {exc}"],
            success=False,
        )

    return MigrationResult(
        source=str(src),
        target=str(out_path),
        format_detected=fmt,
        warnings=warnings,
        success=True,
    )


def migrate_path(source: str | Path) -> list[MigrationResult]:
    """Migrate a file, or all recognised files in a directory."""

    src = Path(source)
    if src.is_file():
        return [migrate_file(src)]
    if src.is_dir():
        results: list[MigrationResult] = []
        for name in ("CLAUDE.md", "AGENTS.md", ".cursorrules"):
            candidate = src / name
            if candidate.exists() and candidate.is_file():
                results.append(migrate_file(candidate))
        return results
    return [
        MigrationResult(
            source=str(src),
            target="",
            format_detected="",
            warnings=[f"path not found: {src}"],
            success=False,
        )
    ]


__all__ = [
    "MigrationResult",
    "detect_format",
    "migrate_file",
    "migrate_path",
]
