"""Mechanical fixes for SKILL.md rule violations.

Each fix is keyed by a rule code. A fix is *deterministic* when the
replacement is the only sensible option (e.g. dedup a tag list). It is
*unsafe* when the change could lose information (e.g. truncating an
over-long description) — unsafe fixes are gated behind
``--unsafe-fix`` on the CLI.

The fixers return the rewritten YAML frontmatter (as a dict) plus the
body string. The CLI is responsible for re-serialising both back into
a SKILL.md file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

import yaml

from .rules import (
    FRONTMATTER_TYPO_MAP,
    LintResult,
    NAME_RE,
    VALID_SKILL_TYPES,
)

_SAFE_FIXES: dict[str, Callable[[dict, str], tuple[dict, str, str | None]]] = {}
_UNSAFE_FIXES: dict[str, Callable[[dict, str], tuple[dict, str, str | None]]] = {}


def safe_fix(code: str):
    """Decorator: register a deterministic fix."""

    def deco(fn):
        _SAFE_FIXES[code] = fn
        return fn

    return deco


def unsafe_fix(code: str):
    """Decorator: register a fix that may lose information."""

    def deco(fn):
        _UNSAFE_FIXES[code] = fn
        return fn

    return deco


@dataclass
class FixApplication:
    """Represents a single applied fix."""

    code: str
    description: str
    unsafe: bool


# ---------------------------------------------------------------------------
# Frontmatter typos (W008)
# ---------------------------------------------------------------------------


@safe_fix("W008")
def _fix_frontmatter_typos(fm: dict, body: str) -> tuple[dict, str, str]:
    """Rename known-typo keys to their canonical form.

    Returns (new_fm, body, description-or-empty). Empty description
    means "no fix applied" — caller should skip emitting this fix.
    """

    renamed: list[str] = []
    new_fm: dict = {}
    for k, v in fm.items():
        canon = FRONTMATTER_TYPO_MAP.get(k, k)
        if canon != k:
            renamed.append(f"{k!r} → {canon!r}")
        # If both typo and canonical keys exist, the canonical one wins
        # (the typo's value is overwritten by the canonical's).
        if canon in new_fm and canon != k:  # pragma: no cover
            continue
        new_fm[canon] = v
    if renamed:
        return new_fm, body, "; ".join(renamed)
    return fm, body, ""  # pragma: no cover


# ---------------------------------------------------------------------------
# Tags (E010 dup, W013 format)
# ---------------------------------------------------------------------------


@safe_fix("E010")
def _fix_tags_dedupe(fm: dict, body: str) -> tuple[dict, str, str]:
    """Remove duplicate tags, preserving first occurrence."""

    tags = fm.get("tags")
    seen: set[str] = set()
    deduped: list = []
    removed: list[str] = []
    for tag in tags:
        if not isinstance(tag, str):
            deduped.append(tag)
            continue
        if tag in seen:
            removed.append(tag)
            continue
        seen.add(tag)
        deduped.append(tag)
    if removed:
        new_fm = dict(fm)
        new_fm["tags"] = deduped
        return new_fm, body, f"removed {len(removed)} duplicate tag(s): {', '.join(removed)}"
    return fm, body, ""  # pragma: no cover


@safe_fix("W013")
def _fix_tag_format(fm: dict, body: str) -> tuple[dict, str, str]:
    """Normalise tags to lowercase kebab-case."""

    tags = fm.get("tags")

    def _normalise(t: object) -> object:
        if not isinstance(t, str):
            return t
        s = re.sub(r"[\s_]+", "-", t.strip().lower())
        s = re.sub(r"-+", "-", s).strip("-")
        return s

    new_tags = [_normalise(t) for t in tags]
    if new_tags != tags:
        new_fm = dict(fm)
        new_fm["tags"] = new_tags
        return new_fm, body, f"normalised {len(new_tags)} tag(s) to kebab-case"
    return fm, body, ""


# ---------------------------------------------------------------------------
# Version (W010)
# ---------------------------------------------------------------------------


_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


@safe_fix("W010")
def _fix_version_semver(fm: dict, body: str) -> tuple[dict, str, str]:
    """Strip a leading 'v' or 'V' from the version string when otherwise valid."""

    v = fm.get("version")
    if not isinstance(v, str):
        return fm, body, ""  # pragma: no cover
    stripped = v.lstrip("vV")
    if stripped == v:
        return fm, body, ""  # pragma: no cover
    if _SEMVER_RE.match(stripped):
        new_fm = dict(fm)
        new_fm["version"] = stripped
        return new_fm, body, f"version {v!r} → {stripped!r} (stripped 'v')"
    return fm, body, ""


# ---------------------------------------------------------------------------
# Token budget (W011)
# ---------------------------------------------------------------------------


@safe_fix("W011")
def _fix_token_budget(fm: dict, body: str) -> tuple[dict, str, str]:
    """Coerce a string-formatted positive integer to int."""

    tb = fm.get("token_budget")
    if isinstance(tb, int) and tb > 0:
        return fm, body, ""  # pragma: no cover
    if isinstance(tb, str):
        try:
            n = int(tb.strip())
        except ValueError:
            return fm, body, ""
        if n > 0:
            new_fm = dict(fm)
            new_fm["token_budget"] = n
            return new_fm, body, f"token_budget {tb!r} → {n}"
    return fm, body, ""  # pragma: no cover


# ---------------------------------------------------------------------------
# Name format (E004) — unsafe: changes identity
# ---------------------------------------------------------------------------


@unsafe_fix("E004")
def _fix_name_format(fm: dict, body: str) -> tuple[dict, str, str]:
    """Normalise `name` to lowercase kebab-case.

    Handles:
      - lowercase normalisation
      - inserting hyphens at camelCase boundaries (e.g. ``MySkill`` → ``my-skill``)
      - replacing spaces and underscores with hyphens

    Only fires when the normalised form would be validated by the spec
    pattern. Names that need more aggressive rewriting are left alone
    (require manual review).
    """

    name = fm.get("name")
    # Insert a hyphen between a lowercase/digit and an uppercase letter
    # (``mySkill`` → ``my-Skill``) and between two uppercase letters
    # followed by a lowercase (``ABCFoo`` → ``ABC-Foo``).
    intermediate = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", name)
    intermediate = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", intermediate)
    # Replace whitespace and underscores with hyphens, then collapse.
    normalised = re.sub(r"[\s_]+", "-", intermediate.lower())
    normalised = re.sub(r"-+", "-", normalised).strip("-")
    if normalised == name:
        return fm, body, ""  # pragma: no cover
    if not NAME_RE.match(normalised):
        return fm, body, ""  # pragma: no cover
    new_fm = dict(fm)
    new_fm["name"] = normalised
    return new_fm, body, f"name {name!r} → {normalised!r}"


# ---------------------------------------------------------------------------
# Skill type (W009) — unsafe: requires a choice
# ---------------------------------------------------------------------------


_SKILL_TYPE_ALIASES: dict[str, str] = {
    "code": "specialist",
    "coding": "specialist",
    "doc": "domain-expert",
    "document": "domain-expert",
    "documentation": "domain-expert",
    "agent": "hybrid",
    "task": "workflow",
    "workflows": "workflow",
}


@unsafe_fix("W009")
def _fix_skill_type(fm: dict, body: str) -> tuple[dict, str, str]:
    """Best-effort mapping of common aliases to a valid skill_type."""

    st = fm.get("skill_type")
    if not isinstance(st, str) or st in VALID_SKILL_TYPES:
        return fm, body, ""
    canonical = _SKILL_TYPE_ALIASES.get(st.lower())
    if canonical is None:
        return fm, body, ""
    new_fm = dict(fm)
    new_fm["skill_type"] = canonical
    return new_fm, body, f"skill_type {st!r} → {canonical!r}"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def apply_fixes(
    text: str,
    result: LintResult,
    unsafe: bool = False,
) -> tuple[str, list[FixApplication]]:
    """Apply safe fixes to ``text`` based on ``result.findings``.

    Returns the rewritten text and the list of fixes that were applied.
    Only fixes whose rule code fired are attempted; each fix is applied
    at most once. The set of attempted fixes is monotonic — running
    again will not reapply a fix that already succeeded.

    When ``unsafe`` is True, unsafe fixes are also attempted. Otherwise
    only safe fixes are applied.
    """

    fired_codes = {f.code for f in result.findings}
    fm, body = _split_for_fix(text)
    if fm is None:
        return text, []

    applied: list[FixApplication] = []
    attempted_codes: set[str] = set()

    def _run(code: str, fn) -> None:
        if code in attempted_codes:  # pragma: no cover
            return
        attempted_codes.add(code)
        nonlocal fm, body
        new_fm, new_body, desc = fn(fm, body)
        if desc:
            applied.append(FixApplication(code=code, description=desc, unsafe=False))
            fm, body = new_fm, new_body

    for code in fired_codes:
        if code in _SAFE_FIXES:
            _run(code, _SAFE_FIXES[code])

    if unsafe:
        for code in fired_codes:
            if code in _UNSAFE_FIXES and code not in attempted_codes:
                attempted_codes.add(code)
                new_fm, new_body, desc = _UNSAFE_FIXES[code](fm, body)
                if desc:
                    applied.append(
                        FixApplication(code=code, description=desc, unsafe=True)
                    )
                    fm, body = new_fm, new_body

    if not applied:
        return text, []

    return _render(fm, body), applied


def _split_for_fix(text: str) -> tuple[dict | None, str]:
    """Split a SKILL.md file into (frontmatter, body).

    Returns ``(None, text)`` if the file lacks a parseable frontmatter
    block. The body is the empty string if the file is just frontmatter.
    """

    stripped = text.lstrip("\ufeff")
    if not stripped.startswith("---"):
        return None, text
    lines_text = stripped.splitlines()
    if not lines_text or lines_text[0].strip() != "---":  # pragma: no cover
        return None, text
    end = None
    for i in range(1, len(lines_text)):
        if lines_text[i].strip() == "---":
            end = i
            break
    if end is None:
        return None, text
    try:
        fm = yaml.safe_load("\n".join(lines_text[1:end])) or {}
    except yaml.YAMLError:  # pragma: no cover
        return None, text
    if not isinstance(fm, dict):
        return None, text
    body = "\n".join(lines_text[end + 1 :])
    return fm, body


def _render(fm: dict, body: str) -> str:
    """Re-render a SKILL.md file from frontmatter + body."""

    yaml_text = yaml.safe_dump(
        fm,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=4096,
    ).rstrip()
    body = body.lstrip("\n")
    if body and not body.endswith("\n"):
        body += "\n"
    return f"---\n{yaml_text}\n---\n\n{body}"  # pragma: no cover


def list_fixable_codes(unsafe: bool = False) -> list[str]:
    """Return all fixable rule codes (sorted), including unsafe if asked."""

    codes = sorted(_SAFE_FIXES.keys())
    if unsafe:
        codes.extend(sorted(c for c in _UNSAFE_FIXES.keys() if c not in _SAFE_FIXES))
    return codes


__all__ = [
    "FixApplication",
    "apply_fixes",
    "list_fixable_codes",
]
