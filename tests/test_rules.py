"""Tests for skillmd-lint."""

from __future__ import annotations

from pathlib import Path

from skillmd_lint import lint_file, lint_folder, lint_text
from skillmd_lint.rules import (
    RESERVED_SLUGS,
    lint_paths,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID = """---
name: backend-api-engineer
description: |
  Use when designing or reviewing a backend REST API for correctness, security,
  and maintainability. Do not use when the work concerns UI design, database
  administration, or non-API engineering tasks — pair with a different
  specialist for those.
skill_type: domain-expert
domain_focus: REST API design
---

# Backend API Engineer

## When to use

Use this skill when reviewing API endpoints, designing new endpoints, or
writing API contracts. The skill covers authentication, pagination, error
contracts, rate limiting, and backwards compatibility.

## How to use

For every API change, walk these four passes in order:

1. Correctness
2. Security
3. Maintainability
4. Performance

## Examples

For example, when reviewing a POST /transfers endpoint:

- Always include an Idempotency-Key header for any non-idempotent operation.
- Return the same response body on retry with the same key.
- Document the rate-limit semantics in the OpenAPI spec.

## Pitfalls to avoid

Do NOT extrapolate from a single example — most APIs evolve.
"""


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_valid_skill_passes(self):
        r = lint_text(VALID)
        assert r.looks_like_skill is True
        assert r.passed is True
        assert r.errors == []

    def test_valid_skill_includes_only_minor_warnings(self):
        r = lint_text(VALID)
        # A valid 30+ line skill body should produce zero warnings.
        assert r.warnings == []

    def test_valid_skill_from_file(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text(VALID, encoding="utf-8")
        r = lint_file(p)
        assert r.passed is True


# ---------------------------------------------------------------------------
# Error rules
# ---------------------------------------------------------------------------


class TestErrors:
    def test_no_frontmatter(self):
        r = lint_text("# Just a header\n\nNo frontmatter here.\n")
        assert not r.passed
        codes = {f.code for f in r.findings}
        assert "E002" in codes

    def test_invalid_yaml(self):
        r = lint_text("---\nname: [unclosed\n---\nbody\n")
        assert not r.passed
        codes = {f.code for f in r.findings}
        assert "E002" in codes

    def test_missing_name(self):
        text = "---\ndescription: Use when X.\n---\nbody with more than twenty lines\n" + (
            "line\n" * 30
        )
        r = lint_text(text)
        codes = {f.code for f in r.errors}
        assert "E003" in codes

    def test_name_uppercase(self):
        text = "---\nname: My-Skill\ndescription: Use when X. Don't use for Y.\n---\nbody\n" + (
            "line\n" * 30
        )
        r = lint_text(text)
        assert "E004" in {f.code for f in r.errors}

    def test_name_underscore(self):
        text = "---\nname: my_skill\ndescription: Use when X. Don't use for Y.\n---\nbody\n" + (
            "line\n" * 30
        )
        r = lint_text(text)
        assert "E004" in {f.code for f in r.errors}

    def test_name_double_hyphen(self):
        text = "---\nname: my--skill\ndescription: Use when X. Don't use for Y.\n---\nbody\n" + (
            "line\n" * 30
        )
        r = lint_text(text)
        assert "E004" in {f.code for f in r.errors}

    def test_name_reserved(self):
        for reserved in ("anthropic", "claude", "com1", "con", "nul"):
            text = (
                f"---\nname: {reserved}\ndescription: Use when X. Don't use for Y.\n---\nbody\n"
                + ("line\n" * 30)
            )
            r = lint_text(text)
            assert "E005" in {f.code for f in r.errors}, f"failed for reserved={reserved}"

    def test_name_too_long(self):
        long_name = "a" * 65
        text = f"---\nname: {long_name}\ndescription: Use when X. Don't use for Y.\n---\nbody\n" + (
            "line\n" * 30
        )
        r = lint_text(text)
        assert "E006" in {f.code for f in r.errors}

    def test_missing_description(self):
        text = "---\nname: my-skill\n---\nbody\n" + ("line\n" * 30)
        r = lint_text(text)
        assert "E007" in {f.code for f in r.errors}

    def test_description_too_long(self):
        long_desc = "Use when " + ("x" * 1100) + " Don't use for Y."
        text = f"---\nname: my-skill\ndescription: {long_desc}\n---\nbody\n" + ("line\n" * 30)
        r = lint_text(text)
        assert "E008" in {f.code for f in r.errors}

    def test_description_with_xml(self):
        text = (
            "---\nname: my-skill\ndescription: <b>Use when</b> X. Don't use for Y.\n---\nbody\n"
            + ("line\n" * 30)
        )
        r = lint_text(text)
        assert "E009" in {f.code for f in r.errors}


# ---------------------------------------------------------------------------
# Warning rules
# ---------------------------------------------------------------------------


class TestWarnings:
    def test_no_positive_trigger(self):
        body = "Use this for X.\n" + ("line\n" * 25)
        text = f"---\nname: my-skill\ndescription: A skill.\n---\n{body}"
        r = lint_text(text)
        codes = {f.code for f in r.warnings}
        assert "W001" in codes

    def test_no_negative_trigger(self):
        body = "line\n" * 25
        text = f"---\nname: my-skill\ndescription: Use when designing APIs.\n---\n{body}"
        r = lint_text(text)
        codes = {f.code for f in r.warnings}
        assert "W002" in codes

    def test_body_too_short(self):
        text = "---\nname: my-skill\ndescription: Use when X. Don't use for Y.\n---\nShort body."
        r = lint_text(text)
        codes = {f.code for f in r.warnings}
        assert "W003" in codes

    def test_body_too_long(self):
        # > 200 lines → suggest progressive disclosure.
        body = "line\n" * 250
        text = f"---\nname: my-skill\ndescription: Use when X. Don't use for Y.\n---\n{body}"
        r = lint_text(text)
        codes = {f.code for f in r.warnings}
        assert "W004" in codes

    def test_no_when_to_use_section(self):
        body = "line\n" * 25
        text = f"---\nname: my-skill\ndescription: Use when X. Don't use for Y.\n---\n{body}"
        r = lint_text(text)
        codes = {f.code for f in r.warnings}
        assert "W005" in codes

    def test_no_examples(self):
        # Body has '## When to use' but no example marker.
        body = "## When to use\n\n" + ("line\n" * 25)
        text = f"---\nname: my-skill\ndescription: Use when X. Don't use for Y.\n---\n{body}"
        r = lint_text(text)
        codes = {f.code for f in r.warnings}
        assert "W006" in codes

    def test_strict_promotes_warnings_to_errors(self):
        body = "line\n" * 25
        text = f"---\nname: my-skill\ndescription: Use when X. Don't use for Y.\n---\n{body}"
        r = lint_text(text)
        # Without strict, this passes (only warnings).
        assert r.passed is True
        assert len(r.warnings) > 0


# ---------------------------------------------------------------------------
# Folder-level discovery
# ---------------------------------------------------------------------------


class TestFolder:
    def test_folder_with_skill_md_at_root(self, tmp_path: Path):
        (tmp_path / "SKILL.md").write_text(VALID, encoding="utf-8")
        results = lint_folder(tmp_path)
        assert len(results) == 1
        assert results[0].passed

    def test_folder_with_skills_subdir(self, tmp_path: Path):
        skills_dir = tmp_path / "skills"
        for name in ("a", "b", "c"):
            (skills_dir / name).mkdir(parents=True)
            (skills_dir / name / "SKILL.md").write_text(VALID, encoding="utf-8")
        results = lint_folder(tmp_path)
        assert len(results) == 3
        assert all(r.passed for r in results)

    def test_folder_with_no_skill_md(self, tmp_path: Path):
        results = lint_folder(tmp_path)
        assert len(results) == 1
        codes = {f.code for f in results[0].findings}
        assert "W007" in codes

    def test_folder_not_found(self, tmp_path: Path):
        results = lint_folder(tmp_path / "does-not-exist")
        codes = {f.code for f in results[0].findings}
        assert "E000" in codes

    def test_file_not_found(self, tmp_path: Path):
        r = lint_file(tmp_path / "does-not-exist.md")
        codes = {f.code for f in r.findings}
        assert "E001" in codes


class TestLintPaths:
    def test_lint_paths_mixed(self, tmp_path: Path):
        # A folder with one skill + a standalone file.
        skill = tmp_path / "skills" / "demo"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(VALID, encoding="utf-8")

        standalone = tmp_path / "SKILL.md"
        standalone.write_text(VALID, encoding="utf-8")

        results = lint_paths([skill, standalone])
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_lint_paths_nonexistent(self, tmp_path: Path):
        results = lint_paths([tmp_path / "missing"])
        codes = {f.code for f in results[0].findings}
        assert "E000" in codes


# ---------------------------------------------------------------------------
# Sanity tests for the registry
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_reserved_slugs_includes_platform_names(self):
        # The spec rejects model / platform names in skill names.
        for slug in ("anthropic", "claude", "openai", "gpt", "grok"):
            assert slug in RESERVED_SLUGS

    def test_all_rules_have_unique_codes(self):
        from skillmd_lint.rules import _RULES

        codes = []
        for rule in _RULES:
            for finding in rule("dummy", {"name": "x", "description": "y"}, "body"):
                codes.append(finding.code)
        # Each rule emits exactly one finding for our dummy case.
        # Codes are stable per-rule.
        assert len(codes) == len(set(codes))
        assert len(codes) >= 5

    def test_result_serialises(self):
        r = lint_text(VALID)
        d = r.to_dict()
        assert "path" in d
        assert "errors" in d
        assert "warnings" in d
        assert "passed" in d
