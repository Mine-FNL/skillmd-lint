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


def _rule_file_exists(path: str, fm: dict, body: str) -> Iterable[LintFinding]:
    # ``file_exists`` is checked at the file level (we wouldn't be here if
    # the file didn't exist), so this rule is a placeholder.
    return ()


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
]


def lint_text(text: str, path: str | None = None) -> LintResult:
    """Lint SKILL.md content from a string."""

    fm, body = _split_frontmatter(text)
    result = LintResult(path=path or "<text>", looks_like_skill=bool(fm))
    for rule in _RULES:
        for finding in rule(path, fm, body):
            if finding.path is None:
                finding = LintFinding(
                    code=finding.code,
                    severity=finding.severity,
                    message=finding.message,
                    path=path,
                )
            result.findings.append(finding)
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
    text = p.read_text(encoding="utf-8", errors="replace")
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
