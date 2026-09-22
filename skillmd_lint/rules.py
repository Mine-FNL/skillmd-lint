"""Core rule engine: parse, classify, evaluate the SKILL.md spec."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import yaml

# Reserved slugs from the SKILL.md spec — collisions would shadow filesystem
# paths or platform reserved names. Matches skill_factory/safety.py.
RESERVED_SLUGS: frozenset[str] = frozenset(
    {
        "",
        ".",
        "..",
        "~",
        "con",
        "prn",
        "aux",
        "nul",
        "com1",
        "com2",
        "com3",
        "com4",
        "com5",
        "com6",
        "com7",
        "com8",
        "com9",
        "lpt1",
        "lpt2",
        "lpt3",
        "lpt4",
        "lpt5",
        "lpt6",
        "lpt7",
        "lpt8",
        "lpt9",
        # The open spec additionally rejects reserved model / platform names.
        "anthropic",
        "claude",
        "openai",
        "gpt",
        "grok",
    }
)

# Spec limits.
MAX_NAME_LEN = 64
MAX_DESC_LEN = 1024
MIN_BODY_LINES = 20
RECOMMENDED_BODY_LINES = 200  # beyond this, suggest progressive disclosure

# Valid skill name: lowercase kebab-case.
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Phrases that signal a positive trigger in the description.
POSITIVE_TRIGGER_PHRASES = (
    "use when",
    "use this",
    "use this skill",
    "when ",
    "whenever",
    "for ",
    "trigger",
    "applies when",
    "if the user",
    "whenever you need",
)

# Phrases that signal a negative trigger ("do not use when…").
NEGATIVE_TRIGGER_PHRASES = (
    "do not use",
    "don't use",
    "not for",
    "do not apply",
    "not appropriate",
    "not applicable",
    "skip when",
)

# Common frontmatter typos. Mapped to the canonical key.
FRONTMATTER_TYPO_MAP: dict[str, str] = {
    "desription": "description",
    "desc": "description",
    "descriptions": "description",
    "nme": "name",
    "naem": "name",
    "skill_type": "skill_type",  # canonical, included for clarity
    "type": "skill_type",
    "kind": "skill_type",
    "tokkens": "tokens",
    "tokn_budget": "token_budget",
    "token-budget": "token_budget",
    "tagss": "tags",
    "tag": "tags",
    "entites": "entities",
    "entity": "entities",
    "domian": "domain",
    "doamin": "domain",
}

# Recognised frontmatter keys (kept loose: unknown keys are not flagged).
RECOGNISED_FRONTMATTER_KEYS: frozenset[str] = frozenset(
    {
        "name",
        "description",
        "skill_type",
        "domain_focus",
        "tags",
        "entities",
        "base_skill",
        "version",
        "version_notes",
        "token_budget",
        "tone",
        "model",
        "references",
    }
)

VALID_SKILL_TYPES: frozenset[str] = frozenset({"domain-expert", "specialist", "workflow", "hybrid"})


class LintSeverity(str, Enum):
    """Severity of a lint finding."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class LintFinding:
    """A single rule violation."""

    code: str
    severity: LintSeverity
    message: str
    path: str | None = None  # set by the runner, not by the rule itself

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "path": self.path,
        }


@dataclass
class LintResult:
    """Lint outcome for a single file."""

    path: str
    findings: list[LintFinding] = field(default_factory=list)
    # Whether the file looks like a valid SKILL.md at all (has a name).
    looks_like_skill: bool = False

    @property
    def errors(self) -> list[LintFinding]:
        return [f for f in self.findings if f.severity == LintSeverity.ERROR]

    @property
    def warnings(self) -> list[LintFinding]:
        return [f for f in self.findings if f.severity == LintSeverity.WARNING]

    @property
    def passed(self) -> bool:
        """A file passes when it has no errors. Warnings are non-fatal."""

        return len(self.errors) == 0 and self.looks_like_skill

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "looks_like_skill": self.looks_like_skill,
            "passed": self.passed,
            "errors": [f.to_dict() for f in self.errors],
            "warnings": [f.to_dict() for f in self.warnings],
        }


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Split a SKILL.md into (frontmatter dict, body).

    Returns ``({}, text)`` if the frontmatter is missing or unparseable. Mirrors
    the helper in skill_factory/frontmatter.py so the behaviour matches.
    """

    stripped = text.lstrip("﻿")
    if not stripped.startswith("---"):
        return {}, text
    lines = stripped.splitlines()
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    fm_block = "\n".join(lines[1:end])
    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    try:
        data = yaml.safe_load(fm_block) or {}
    except yaml.YAMLError:
        return {}, body
    if not isinstance(data, dict):
        return {}, body
    return data, body


def _has_xml_tags(s: str) -> bool:
    """Return True if ``s`` contains XML/HTML tag-like sequences."""

    return bool(re.search(r"<[a-zA-Z][^>]*>", s))


# ---------------------------------------------------------------------------
# Individual rules
# ---------------------------------------------------------------------------


def _rule_frontmatter(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    if not fm:
        yield LintFinding(
            code="E002",
            severity=LintSeverity.ERROR,
            message=(
                "frontmatter is missing or invalid; SKILL.md must start with "
                "a YAML frontmatter block delimited by `---` markers"
            ),
        )
        return


def _rule_name_present(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    name = fm.get("name")
    if not name or not isinstance(name, str) or not name.strip():
        yield LintFinding(
            code="E003",
            severity=LintSeverity.ERROR,
            message="`name` is missing or empty",
        )


def _rule_name_format(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    name = fm.get("name", "")
    if not isinstance(name, str) or not name:
        return
    if not NAME_RE.match(name):
        yield LintFinding(
            code="E004",
            severity=LintSeverity.ERROR,
            message=(
                f"name '{name}' must be lowercase kebab-case "
                "(letters, digits, single hyphens; no leading/trailing/double "
                "hyphens; no underscores or uppercase letters)"
            ),
        )


def _rule_name_reserved(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    name = fm.get("name", "")
    if not isinstance(name, str):
        return
    if name in RESERVED_SLUGS:
        yield LintFinding(
            code="E005",
            severity=LintSeverity.ERROR,
            message=(
                f"name '{name}' collides with a reserved word (Windows device "
                "names, the open SKILL.md reserved list, or filesystem specials)"
            ),
        )


def _rule_name_length(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    name = fm.get("name", "")
    if not isinstance(name, str) or not name:
        return
    if len(name) > MAX_NAME_LEN:
        yield LintFinding(
            code="E006",
            severity=LintSeverity.ERROR,
            message=(f"name is {len(name)} chars; spec limit is {MAX_NAME_LEN}"),
        )


def _rule_description_present(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    desc = fm.get("description")
    if not desc or not isinstance(desc, str) or not desc.strip():
        yield LintFinding(
            code="E007",
            severity=LintSeverity.ERROR,
            message="`description` is missing or empty",
        )


def _rule_description_length(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    desc = fm.get("description", "")
    if not isinstance(desc, str) or not desc:
        return
    if len(desc) > MAX_DESC_LEN:
        yield LintFinding(
            code="E008",
            severity=LintSeverity.ERROR,
            message=(f"description is {len(desc)} chars; spec limit is {MAX_DESC_LEN}"),
        )


def _rule_description_xml(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    desc = fm.get("description", "")
    if isinstance(desc, str) and _has_xml_tags(desc):
        yield LintFinding(
            code="E009",
            severity=LintSeverity.ERROR,
            message="description contains XML tags; spec forbids them",
        )


def _rule_description_positive_trigger(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    desc = (fm.get("description") or "").lower()
    if not desc:
        return
    if not any(phrase in desc for phrase in POSITIVE_TRIGGER_PHRASES):
        yield LintFinding(
            code="W001",
            severity=LintSeverity.WARNING,
            message=(
                "description has no positive trigger phrase (e.g. 'use when', "
                "'whenever', 'for ...'). The agent uses these to decide whether "
                "to load the skill."
            ),
        )


def _rule_description_negative_trigger(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    desc = (fm.get("description") or "").lower()
    if not desc:
        return
    if not any(phrase in desc for phrase in NEGATIVE_TRIGGER_PHRASES):
        yield LintFinding(
            code="W002",
            severity=LintSeverity.WARNING,
            message=(
                "description has no negative trigger ('do not use when…', "
                "'not for…'). Negative triggers reduce over-firing."
            ),
        )


def _rule_body_length(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    lines = body.splitlines()
    n = len(lines)
    if n < MIN_BODY_LINES:
        yield LintFinding(
            code="W003",
            severity=LintSeverity.WARNING,
            message=(f"body has {n} lines; spec recommends at least {MIN_BODY_LINES}"),
        )
    elif n > RECOMMENDED_BODY_LINES:
        yield LintFinding(
            code="W004",
            severity=LintSeverity.WARNING,
            message=(
                f"body has {n} lines; >{RECOMMENDED_BODY_LINES} suggests "
                "progressive disclosure (move detail into references/)"
            ),
        )


def _rule_when_to_use_section(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    body_low = body.lower()
    if not any(
        marker in body_low for marker in ("## when to use", "## usage", "## when", "## how to use")
    ):
        yield LintFinding(
            code="W005",
            severity=LintSeverity.WARNING,
            message=(
                "no '## When to use' (or equivalent) section in the body — "
                "readers can't quickly find the activation conditions"
            ),
        )


def _rule_has_examples(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    body_low = body.lower()
    if not any(marker in body_low for marker in ("example", "e.g.", "for example", "for instance")):
        yield LintFinding(
            code="W006",
            severity=LintSeverity.WARNING,
            message=(
                "body has no concrete examples; skills with examples are "
                "significantly more reliable in practice"
            ),
        )


# ---------------------------------------------------------------------------
# v1.1 rules
# ---------------------------------------------------------------------------


SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?$")
TAG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _rule_frontmatter_typos(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    """W008: detect common frontmatter-key typos (desription, desc, nme, …)."""

    if not fm:
        return
    for key in list(fm.keys()):
        suggestion = FRONTMATTER_TYPO_MAP.get(key)
        if not suggestion or suggestion == key:
            continue
        yield LintFinding(
            code="W008",
            severity=LintSeverity.WARNING,
            message=(f"frontmatter key '{key}' looks like a typo; did you mean '{suggestion}'?"),
        )


def _rule_skill_type_valid(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    """W009: `skill_type`, if present, must be a recognised value."""

    st = fm.get("skill_type")
    if st is None or st == "":
        return
    if not isinstance(st, str):
        yield LintFinding(
            code="W009",
            severity=LintSeverity.WARNING,
            message=(
                f"`skill_type` must be a string; got {type(st).__name__}. "
                f"Valid values: {sorted(VALID_SKILL_TYPES)}"
            ),
        )
        return
    if st not in VALID_SKILL_TYPES:
        yield LintFinding(
            code="W009",
            severity=LintSeverity.WARNING,
            message=(
                f"`skill_type` '{st}' is not a recognised value; expected one of "
                f"{sorted(VALID_SKILL_TYPES)}"
            ),
        )


def _rule_version_semver(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    """W010: `version`, if present, must be valid semver (X.Y.Z[-prerelease])."""

    ver = fm.get("version")
    if ver is None or ver == "":
        return
    if not isinstance(ver, str) or not SEMVER_RE.match(ver):
        yield LintFinding(
            code="W010",
            severity=LintSeverity.WARNING,
            message=(
                f"`version` '{ver}' is not valid semver (expected e.g. '1.0.0' or '1.0.0-rc.1')"
            ),
        )


def _rule_token_budget_sane(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    """W011: `token_budget`, if present, must be a positive integer."""

    tb = fm.get("token_budget")
    if tb is None:
        return
    # bool is a subclass of int — reject it explicitly so True/False don't slip through.
    if isinstance(tb, bool) or not isinstance(tb, int) or tb <= 0:
        yield LintFinding(
            code="W011",
            severity=LintSeverity.WARNING,
            message=(f"`token_budget` must be a positive integer; got {tb!r}"),
        )


def _rule_pitfalls_section(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    """W012: body should have a '## Pitfalls to avoid' (or equivalent) section."""

    body_low = body.lower()
    if not any(
        marker in body_low
        for marker in (
            "## pitfalls",
            "## gotchas",
            "## common mistakes",
            "## what to avoid",
        )
    ):
        yield LintFinding(
            code="W012",
            severity=LintSeverity.WARNING,
            message=(
                "no '## Pitfalls to avoid' (or equivalent) section; documenting "
                "common mistakes sharply improves skill reliability"
            ),
        )


def _rule_tags_format(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    """W013: every tag should be lowercase kebab-case (a-z, 0-9, single hyphen)."""

    tags = fm.get("tags")
    if tags is None:
        return
    if not isinstance(tags, list):
        yield LintFinding(
            code="W013",
            severity=LintSeverity.WARNING,
            message=(f"`tags` must be a list; got {type(tags).__name__}"),
        )
        return
    seen: set[str] = set()
    for tag in tags:
        if not isinstance(tag, str):
            yield LintFinding(
                code="W013",
                severity=LintSeverity.WARNING,
                message=(f"tag must be a string; got {type(tag).__name__}: {tag!r}"),
            )
            continue
        if tag in seen:
            # Duplicates get the E010 code; the format rule stays clean.
            continue
        seen.add(tag)
        if not tag:
            yield LintFinding(
                code="W013",
                severity=LintSeverity.WARNING,
                message="tag must be non-empty",
            )
            continue
        if not TAG_RE.match(tag):
            yield LintFinding(
                code="W013",
                severity=LintSeverity.WARNING,
                message=(
                    f"tag '{tag}' must be lowercase kebab-case (letters, digits, "
                    "single hyphens; no underscores, spaces, or uppercase)"
                ),
            )


def _rule_tags_unique(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    """E010: tags list must not contain duplicates."""

    tags = fm.get("tags")
    if not isinstance(tags, list):
        return
    seen: set[str] = set()
    for tag in tags:
        if not isinstance(tag, str):
            continue
        if tag in seen:
            yield LintFinding(
                code="E010",
                severity=LintSeverity.ERROR,
                message=f"duplicate tag: '{tag}'",
            )
        else:
            seen.add(tag)


# ---------------------------------------------------------------------------
# New rules added in v1.4.0 — closes the rule-count gap with agnix.
# ---------------------------------------------------------------------------


def _rule_version_type(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    """E011: version must be a string, not an int or float.

    Semver is text-shaped: "1.2.3-rc.1" can't be expressed as a number.
    Some teams accidentally type `version: 1.0` and YAML coerces it
    to int, which then sorts wrong and breaks semver-aware tooling.
    """

    v = fm.get("version")
    if v is None:
        return
    if not isinstance(v, str):
        yield LintFinding(
            code="E011",
            severity=LintSeverity.ERROR,
            message=(
                f"`version` must be a string with quotes around it (got {type(v).__name__}: {v!r})"
            ),
        )


def _rule_frontmatter_indentation(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    """W014: frontmatter must use spaces, not tabs.

    YAML forbids tabs for indentation. Some editors silently
    convert; some YAML parsers accept them anyway. skillmd-lint
    flags them so the inconsistency is caught before the file
    hits a stricter parser downstream.
    """

    # Re-derive the raw frontmatter to inspect indentation. We can
    # check the original text via the path argument when linting
    # from a file; for in-text mode, this is a best-effort fallback.
    # The CLI ensures the path is set when linting a file.
    if path == "<text>" or not path:
        return
    try:
        p = Path(path)
        raw = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    # Find the frontmatter block
    if not raw.lstrip("\ufeff").startswith("---"):  # pragma: no cover
        return
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":  # pragma: no cover
        return
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:  # pragma: no cover
        return
    for i, line in enumerate(lines[1:end], start=1):
        if "\t" in line:
            yield LintFinding(
                code="W014",
                severity=LintSeverity.WARNING,
                message=(f"frontmatter line {i} uses tab indentation; YAML requires spaces"),
            )
            return  # report once


def _rule_placeholder_text(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    """W015: description must not contain placeholder text.

    Detects 'TODO', 'FIXME', 'lorem ipsum', 'placeholder', '...'
    in the description — signs of a skill shipped before the
    author filled in the prose.
    """

    desc = fm.get("description")
    if not isinstance(desc, str):
        return
    placeholders = ("todo", "fixme", "xxx", "lorem", "placeholder", "tbd", "fill in")
    desc_lower = desc.lower()
    for ph in placeholders:
        if ph in desc_lower:
            yield LintFinding(
                code="W015",
                severity=LintSeverity.WARNING,
                message=f"description contains placeholder text ('{ph}')",
            )
            return


def _rule_body_html_tags(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    """W016: body should not contain raw HTML tags.

    SKILL.md is rendered as Markdown. HTML tags inside the body
    render unpredictably across runtimes. Use the Markdown
    equivalent (`**bold**` not `<b>bold</b>`).
    """

    # Skip code fences — tags inside ``` blocks are intentional
    stripped_lines: list[str] = []
    in_fence = False
    for line in body.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            stripped_lines.append(line)
    text = "\n".join(stripped_lines)
    # Match the most common raw-HTML anti-patterns
    import re

    html_re = re.compile(
        r"<\s*(b|strong|i|em|u|br|hr|div|span|p)\b[^>]*>",
        re.IGNORECASE,
    )
    if html_re.search(text):
        yield LintFinding(
            code="W016",
            severity=LintSeverity.WARNING,
            message=(
                "body contains raw HTML tags; prefer Markdown equivalents (`**bold**`, `*italic*`)"
            ),
        )


def _rule_name_trailing_hyphen(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    """W017: name must not start or end with a hyphen."""

    name = fm.get("name")
    if not isinstance(name, str):
        return
    if name.startswith("-") or name.endswith("-"):
        yield LintFinding(
            code="W017",
            severity=LintSeverity.WARNING,
            message=f"`name` has leading or trailing hyphen: '{name}'",
        )


def _rule_description_redundant_prefix(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    """W018: description should not start with "this skill" / "this is".

    The agent already knows it's a skill. Starting the description
    with 'this skill ...' wastes the trigger slot.
    """

    desc = fm.get("description")
    if not isinstance(desc, str):
        return
    stripped = desc.lstrip().lower()
    redundant_prefixes = (
        "this skill ",
        "this is a skill ",
        "this is an ",
        "the skill ",
    )
    for prefix in redundant_prefixes:
        if stripped.startswith(prefix):
            yield LintFinding(
                code="W018",
                severity=LintSeverity.WARNING,
                message=(
                    f"description starts with '{prefix.rstrip()}' — "
                    f"the agent already knows it's a skill; lead with the trigger"
                ),
            )
            return


def _rule_tags_count(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    """W019: tags list should have between 1 and 10 entries.

    0 tags means the skill won't be discoverable by topic; >10
    means the author is hedging — usually a sign the skill's
    scope is unclear.
    """

    tags = fm.get("tags")
    if tags is None:
        return
    if not isinstance(tags, list):
        return
    if len(tags) == 0:
        yield LintFinding(
            code="W019",
            severity=LintSeverity.WARNING,
            message="`tags` is empty; add at least one topic tag for discoverability",
        )
    elif len(tags) > 10:
        yield LintFinding(
            code="W019",
            severity=LintSeverity.WARNING,
            message=(
                f"`tags` has {len(tags)} entries; consider tightening "
                f"to the most relevant 5 or fewer"
            ),
        )


def _rule_version_consistency(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    """W020: if version_notes is present, it should mention the version.

    Useful for finding stale changelog entries where the author
    bumped version but forgot to update version_notes.
    """

    version = fm.get("version")
    notes = fm.get("version_notes")
    if not isinstance(version, str) or not isinstance(notes, str):
        return
    if version in notes:
        return
    yield LintFinding(
        code="W020",
        severity=LintSeverity.WARNING,
        message=(f"`version_notes` does not mention version {version!r} — is the changelog stale?"),
    )


def _rule_referenced_skill_exists(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    """W021: base_skill must reference an existing skill name.

    Flags typos and references to skills that have been renamed
    or removed. Folder-mode only; in-text mode requires knowing
    the parent folder.
    """

    base = fm.get("base_skill")
    if not isinstance(base, str):
        return
    if path == "<text>" or not path:  # pragma: no cover
        return
    p = Path(path)
    # Walk up to the skills/ folder; if we find it, check for the base.
    parent = p.parent
    candidate: Path | None = None
    for _ in range(4):
        if (parent / "skills" / base / "SKILL.md").is_file():  # pragma: no cover
            candidate = parent / "skills" / base
            break
        if (parent / base / "SKILL.md").is_file():
            candidate = parent / base
            break
        parent = parent.parent
        if parent == parent.parent:  # pragma: no cover
            break
    if candidate is None and not _maybe_other_skills(base, p):
        yield LintFinding(
            code="W021",
            severity=LintSeverity.WARNING,
            message=f"`base_skill` references '{base}' but no matching SKILL.md found nearby",
        )


def _maybe_other_skills(name: str, p: Path) -> bool:
    """Best-effort: did we find the referenced skill somewhere reasonable?"""

    # Search the filesystem for a folder named ``name`` that contains
    # a SKILL.md, within a reasonable depth up the tree.
    parent = p.parent
    for _ in range(4):
        if not parent.exists():  # pragma: no cover
            return False
        try:
            for child in parent.iterdir():
                if child.is_dir() and child.name == name and (child / "SKILL.md").is_file():
                    return True
        except OSError:  # pragma: no cover
            return False
        parent = parent.parent
    return False  # pragma: no cover


def _rule_examples_have_io(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    """W022: examples should show input/output pairs.

    A "## Examples" section with prose but no concrete user/skill
    dialog is not actionable. Catch the common case where the
    section exists but has no quoted/indented code block or
    user-prompt example.
    """

    import re

    if not re.search(r"^##\s+Examples", body, re.MULTILINE | re.IGNORECASE):
        return
    # Find the section body
    lines = body.splitlines()
    in_section = False
    section_body: list[str] = []
    for line in lines:
        if re.match(r"^##\s+Examples", line, re.IGNORECASE):
            in_section = True
            continue
        if in_section:
            if re.match(r"^##\s+", line):
                break
            section_body.append(line)
    text = "\n".join(section_body).strip()
    if not text:
        yield LintFinding(
            code="W022",
            severity=LintSeverity.WARNING,
            message="`## Examples` section is empty",
        )
        return
    # Look for code fences, indented blocks, inline code, or quoted dialog
    has_io = (
        "```" in text
        or "`" in text  # any inline `code` formatting counts
        or re.search(r"^\s{4}", text, re.MULTILINE) is not None
        or re.search(r"(?im)^user:", text) is not None
        or re.search(r'(?im)^"', text) is not None
    )
    if not has_io:
        yield LintFinding(
            code="W022",
            severity=LintSeverity.WARNING,
            message=(
                "`## Examples` has prose but no concrete "
                "input/output example (no code block, indented "
                "block, or 'user:' prompt)"
            ),
        )


# ---------------------------------------------------------------------------
# Unicode spoofing (W023)
# ---------------------------------------------------------------------------


# Unicode bidi/format controls + zero-width characters that are commonly
# used in phishing/scoping attacks against humans reading text.
# - U+202A..U+202E, U+2066..U+2069: bidi embedding/override/isolate
# - U+200B, U+200C, U+200D, U+FEFF: zero-width space / joiners / BOM
#
# Zero-width joiners (U+200D) are legitimately used in emoji sequences
# like 👨‍👩‍👧‍👦 — flagging those would create noise. We accept them
# in `body` (where emoji live) but flag them in `name` and
# `description` where they have no legitimate use.
_UNICODE_SPOOF_RANGES: tuple[tuple[int, int, str], ...] = (
    (0x202A, 0x202E, "bidi-override"),  # LRE/RLE/PDF/LRO/RLO
    (0x2066, 0x2069, "bidi-isolate"),  # LRI/RLI/FSI/PDI
)


def _rule_unicode_spoofing(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    """W023: frontmatter must not contain Unicode bidi/zero-width chars.

    Bidi override (U+202E etc.) and zero-width joiners (U+200B/D) in
    a skill's ``name`` or ``description`` can be used to make the
    rendered text appear to say one thing while the underlying bytes
    mean another — a classic supply-chain-attack vector for AI skill
    descriptions. We flag the dangerous controls in frontmatter
    fields, plus zero-width chars (U+200B, U+200C, U+FEFF) which
    have no legitimate use in frontmatter prose. Zero-width joiners
    are allowed in the body because emoji sequences like
    👨‍👩‍👧‍👦 depend on them.
    """

    " ".join(str(v) for v in fm.values() if isinstance(v, (str, int, float)))

    # Check frontmatter for bidi controls + zero-width chars
    def _flag(field_name: str, value: object) -> Iterable[LintFinding]:
        if not isinstance(value, str):
            return
        for start, end, kind in _UNICODE_SPOOF_RANGES:
            for ch in value:
                cp = ord(ch)
                if start <= cp <= end:
                    yield LintFinding(
                        code="W023",
                        severity=LintSeverity.WARNING,
                        message=(
                            f"{field_name} contains Unicode bidi control "
                            f"(U+{cp:04X}, {kind}); this can be used to spoof "
                            "rendered text"
                        ),
                    )
                    return  # one finding per field is enough
        for ch in value:
            cp = ord(ch)
            if cp in (0x200B, 0x200C, 0xFEFF):
                yield LintFinding(
                    code="W023",
                    severity=LintSeverity.WARNING,
                    message=(
                        f"{field_name} contains invisible Unicode "
                        f"character (U+{cp:04X}); this can hide "
                        "malicious content in plain-looking text"
                    ),
                )
                return

    for field_name in ("name", "description"):
        if field_name in fm:
            yield from _flag(f"`{field_name}`", fm[field_name])

    # tags are list-valued
    tags = fm.get("tags")
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, str):
                for start, end, kind in _UNICODE_SPOOF_RANGES:
                    if any(start <= ord(ch) <= end for ch in tag):
                        yield LintFinding(
                            code="W023",
                            severity=LintSeverity.WARNING,
                            message=(
                                f"`tags` contains Unicode bidi control "
                                f"({kind}); this can spoof rendered tag lists"
                            ),
                        )
                        return


# ---------------------------------------------------------------------------
# Rule registry
# ---------------------------------------------------------------------------

_RULES = [
    _rule_frontmatter,
    _rule_name_present,
    _rule_name_format,
    _rule_name_reserved,
    _rule_name_length,
    _rule_description_present,
    _rule_description_length,
    _rule_description_xml,
    _rule_description_positive_trigger,
    _rule_description_negative_trigger,
    _rule_body_length,
    _rule_when_to_use_section,
    _rule_has_examples,
    _rule_frontmatter_typos,
    _rule_skill_type_valid,
    _rule_version_semver,
    _rule_token_budget_sane,
    _rule_pitfalls_section,
    _rule_tags_format,
    _rule_tags_unique,
    _rule_version_type,
    _rule_frontmatter_indentation,
    _rule_placeholder_text,
    _rule_body_html_tags,
    _rule_name_trailing_hyphen,
    _rule_description_redundant_prefix,
    _rule_tags_count,
    _rule_version_consistency,
    _rule_referenced_skill_exists,
    _rule_examples_have_io,
    _rule_unicode_spoofing,
]


# Public list of all (code, severity, summary) for the CLI --list output and for
# docs generation. Kept in sync with ``_RULES`` above.
RULE_INDEX: list[tuple[str, str, str]] = [
    ("E001", "error", "SKILL.md file not found at folder root"),
    ("E002", "error", "frontmatter is missing or not valid YAML"),
    ("E003", "error", "`name` missing or empty"),
    ("E004", "error", "`name` not lowercase kebab-case"),
    ("E005", "error", "`name` collides with a reserved word"),
    ("E006", "error", "`name` exceeds 64 characters"),
    ("E007", "error", "`description` missing or empty"),
    ("E008", "error", "`description` exceeds 1024 characters"),
    ("E009", "error", "`description` contains XML tags"),
    ("E010", "error", "`tags` list contains duplicates"),
    ("E011", "error", "`version` is not a string"),
    ("W001", "warning", "description missing positive trigger phrase"),
    ("W002", "warning", "description missing negative trigger"),
    ("W003", "warning", "body has fewer than 20 lines"),
    ("W004", "warning", "body exceeds 200 lines"),
    ("W005", "warning", "no `## When to use` section in body"),
    ("W006", "warning", "no concrete examples in body"),
    ("W007", "warning", "skills/ subfolder has no `SKILL.md`"),
    ("W008", "warning", "frontmatter key looks like a typo"),
    ("W009", "warning", "`skill_type` is not a recognised value"),
    ("W010", "warning", "`version` is not valid semver"),
    ("W011", "warning", "`token_budget` is not a positive integer"),
    ("W012", "warning", "no `## Pitfalls to avoid` section in body"),
    ("W013", "warning", "tag is not lowercase kebab-case"),
    ("W014", "warning", "frontmatter uses tab indentation"),
    ("W015", "warning", "description contains placeholder text"),
    ("W016", "warning", "body contains raw HTML tags"),
    ("W017", "warning", "`name` has leading or trailing hyphen"),
    ("W018", "warning", "description starts with redundant prefix"),
    ("W019", "warning", "`tags` count is outside the 1-10 range"),
    ("W020", "warning", "`version_notes` doesn't reference current version"),
    ("W021", "warning", "`base_skill` references unknown skill"),
    ("W022", "warning", "`## Examples` lacks concrete input/output"),
    (
        "W023",
        "warning",
        "frontmatter contains Unicode bidi or zero-width characters (spoofing risk)",
    ),
]


def lint_text(text: str, path: str | None = None) -> LintResult:
    """Lint SKILL.md content from a string."""

    fm, body = _split_frontmatter(text)
    result = LintResult(path=path or "<text>", looks_like_skill=bool(fm))
    for rule in _RULES:
        for finding in rule(path, fm, body):
            # Findings from rules never carry a path; we attach the
            # file/folder path the linter was invoked with. (``finding.path
            # or path`` keeps the contract alive in case a future rule sets
            # its own path on a per-finding basis.)
            result.findings.append(
                LintFinding(
                    code=finding.code,
                    severity=finding.severity,
                    message=finding.message,
                    path=finding.path or path,
                )
            )
    return result


def lint_file(path: str | Path) -> LintResult:
    """Lint a single SKILL.md file."""

    p = Path(path)
    if not p.exists():
        result = LintResult(path=str(p))
        result.findings.append(
            LintFinding(
                code="E001",
                severity=LintSeverity.ERROR,
                message=f"file not found: {p}",
                path=str(p),
            )
        )
        return result
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        result = LintResult(path=str(p), looks_like_skill=True)
        result.findings.append(
            LintFinding(
                code="E001",
                severity=LintSeverity.ERROR,
                message=f"cannot read {p}: {exc}",
                path=str(p),
            )
        )
        return result
    return lint_text(text, path=str(p))


def lint_folder(path: str | Path) -> list[LintResult]:
    """Lint a folder; returns a LintResult per SKILL.md found + a folder result.

    If the folder itself contains a SKILL.md at the root, that file is linted.
    If the folder contains a ``skills/`` subdirectory, every immediate child
    of that subdirectory with a SKILL.md is linted.

    Always includes a folder-level result so the CLI can report folder
    discovery even when no SKILL.md is present.
    """

    root = Path(path)
    if not root.exists() or not root.is_dir():
        return [
            LintResult(
                path=str(root),
                findings=[
                    LintFinding(
                        code="E000",
                        severity=LintSeverity.ERROR,
                        message=f"folder not found: {root}",
                        path=str(root),
                    ),
                ],
            )
        ]

    candidates: list[Path] = []
    if (root / "SKILL.md").is_file():
        candidates.append(root / "SKILL.md")

    skills_dir = root / "skills"
    if skills_dir.is_dir():
        for child in sorted(skills_dir.iterdir()):
            if child.is_dir() and (child / "SKILL.md").is_file():
                candidates.append(child / "SKILL.md")

    if not candidates:
        return [
            LintResult(
                path=str(root),
                findings=[
                    LintFinding(
                        code="W007",
                        severity=LintSeverity.WARNING,
                        message=(
                            f"no SKILL.md found at {root} or under {root}/skills/; nothing to lint"
                        ),
                        path=str(root),
                    ),
                ],
            )
        ]

    return [lint_file(c) for c in candidates]


def lint_paths(paths: Iterable[str | Path]) -> list[LintResult]:
    """Lint a sequence of paths (files or folders)."""

    results: list[LintResult] = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            results.extend(lint_folder(path))
        elif path.is_file():
            results.append(lint_file(path))
        else:
            results.append(
                LintResult(
                    path=str(path),
                    findings=[
                        LintFinding(
                            code="E000",
                            severity=LintSeverity.ERROR,
                            message=f"path not found: {path}",
                            path=str(path),
                        ),
                    ],
                )
            )
    return results
