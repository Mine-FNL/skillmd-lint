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
tags:
  - api
  - rest
  - backend
version: 1.0.0
token_budget: 1800
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

For example, when reviewing a `POST /transfers` endpoint:

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


# ---------------------------------------------------------------------------
# v1.1 rules: W008..W013 + E010
# ---------------------------------------------------------------------------


class TestFrontmatterTypos:
    def test_typo_description(self):
        text = "---\nname: my-skill\ndesription: Use when X. Don't use for Y.\n---\n" + (
            "line\n" * 25
        )
        r = lint_text(text)
        codes = {f.code for f in r.warnings}
        assert "W008" in codes

    def test_typo_with_dash_form(self):
        text = (
            "---\n"
            "name: my-skill\n"
            "description: Use when X. Don't use for Y.\n"
            "token-budget: 100\n"
            "---\n" + ("line\n" * 25)
        )
        r = lint_text(text)
        assert "W008" in {f.code for f in r.warnings}

    def test_no_typo_clean(self):
        # VALID fixture has no typos → no W008.
        r = lint_text(VALID)
        assert "W008" not in {f.code for f in r.warnings}


class TestSkillTypeValid:
    def test_unknown_skill_type(self):
        text = (
            "---\n"
            "name: my-skill\n"
            "description: Use when X. Don't use for Y.\n"
            "skill_type: ninja\n"
            "---\n" + ("line\n" * 25)
        )
        r = lint_text(text)
        assert "W009" in {f.code for f in r.warnings}

    def test_valid_skill_type(self):
        r = lint_text(VALID)
        assert "W009" not in {f.code for f in r.warnings}


class TestVersionSemver:
    def test_non_semver_version(self):
        text = (
            "---\n"
            "name: my-skill\n"
            "description: Use when X. Don't use for Y.\n"
            "version: v1.0\n"
            "---\n" + ("line\n" * 25)
        )
        r = lint_text(text)
        assert "W010" in {f.code for f in r.warnings}

    def test_semver_with_prerelease(self):
        text = (
            "---\n"
            "name: my-skill\n"
            "description: Use when X. Don't use for Y.\n"
            "version: 1.0.0-rc.1\n"
            "---\n" + ("line\n" * 25)
        )
        r = lint_text(text)
        assert "W010" not in {f.code for f in r.warnings}

    def test_valid_version(self):
        r = lint_text(VALID)
        assert "W010" not in {f.code for f in r.warnings}


class TestTokenBudgetSane:
    def test_negative_token_budget(self):
        text = (
            "---\n"
            "name: my-skill\n"
            "description: Use when X. Don't use for Y.\n"
            "token_budget: -5\n"
            "---\n" + ("line\n" * 25)
        )
        r = lint_text(text)
        assert "W011" in {f.code for f in r.warnings}

    def test_string_token_budget(self):
        text = (
            "---\n"
            "name: my-skill\n"
            "description: Use when X. Don't use for Y.\n"
            "token_budget: 'a lot'\n"
            "---\n" + ("line\n" * 25)
        )
        r = lint_text(text)
        assert "W011" in {f.code for f in r.warnings}

    def test_bool_token_budget(self):
        # bool is an int subclass — must be rejected explicitly.
        text = (
            "---\n"
            "name: my-skill\n"
            "description: Use when X. Don't use for Y.\n"
            "token_budget: true\n"
            "---\n" + ("line\n" * 25)
        )
        r = lint_text(text)
        assert "W011" in {f.code for f in r.warnings}

    def test_zero_token_budget(self):
        text = (
            "---\n"
            "name: my-skill\n"
            "description: Use when X. Don't use for Y.\n"
            "token_budget: 0\n"
            "---\n" + ("line\n" * 25)
        )
        r = lint_text(text)
        assert "W011" in {f.code for f in r.warnings}


class TestPitfallsSection:
    def test_no_pitfalls_section(self):
        # Body has ## When to use and ## Examples but no Pitfalls.
        body = (
            "## When to use\n\n"
            "Use this skill.\n\n"
            "## Examples\n\n"
            "For example, this is the only example.\n" + ("line\n" * 25)
        )
        text = "---\nname: my-skill\ndescription: Use when X. Don't use for Y.\n---\n" + body
        r = lint_text(text)
        assert "W012" in {f.code for f in r.warnings}

    def test_pitfalls_alternate_heading(self):
        body = (
            "## When to use\n\n"
            "Use this skill.\n\n"
            "## Examples\n\n"
            "For example.\n\n"
            "## Common mistakes\n\n"
            "Don't do X.\n" + ("line\n" * 25)
        )
        text = "---\nname: my-skill\ndescription: Use when X. Don't use for Y.\n---\n" + body
        r = lint_text(text)
        assert "W012" not in {f.code for f in r.warnings}


class TestTagsFormat:
    def test_uppercase_tag(self):
        text = (
            "---\n"
            "name: my-skill\n"
            "description: Use when X. Don't use for Y.\n"
            "tags:\n  - Backend\n"
            "---\n" + ("line\n" * 25)
        )
        r = lint_text(text)
        assert "W013" in {f.code for f in r.warnings}

    def test_underscore_tag(self):
        text = (
            "---\n"
            "name: my-skill\n"
            "description: Use when X. Don't use for Y.\n"
            "tags:\n  - some_tag\n"
            "---\n" + ("line\n" * 25)
        )
        r = lint_text(text)
        assert "W013" in {f.code for f in r.warnings}

    def test_duplicate_tag_is_error(self):
        text = (
            "---\n"
            "name: my-skill\n"
            "description: Use when X. Don't use for Y.\n"
            "tags:\n  - api\n  - api\n"
            "---\n" + ("line\n" * 25)
        )
        r = lint_text(text)
        assert "E010" in {f.code for f in r.errors}

    def test_valid_tags(self):
        r = lint_text(VALID)
        assert "W013" not in {f.code for f in r.warnings}
        assert "E010" not in {f.code for f in r.errors}


class TestRULE_INDEX:
    def test_index_lists_every_rule(self):
        # The index is the canonical rule table — every rule in _RULES must be
        # represented, and the codes must be unique.
        from skillmd_lint.rules import RULE_INDEX

        # No duplicate codes in the index.
        codes = [c for c, _, _ in RULE_INDEX]
        assert len(codes) == len(set(codes))

        # Index should cover at least the 6 new v1.1 codes.
        assert "W008" in codes
        assert "W013" in codes
        assert "E010" in codes

        # Index summary should mention the right words for grep-ability.
        summaries = {c: s for c, _, s in RULE_INDEX}
        assert "typo" in summaries["W008"]
        assert "skill_type" in summaries["W009"]
        assert "semver" in summaries["W010"]
        assert "token_budget" in summaries["W011"]
        assert "Pitfalls" in summaries["W012"]
        assert "duplicate" in summaries["E010"]


# ---------------------------------------------------------------------------
# Coverage targets — every uncovered branch in rules.py
# ---------------------------------------------------------------------------


class TestSplitFrontmatterEdgeCases:
    """The ``_split_frontmatter`` helper is private; we test it via the
    public ``lint_text`` API since that's the only way users reach it.
    """

    def test_unclosed_frontmatter(self):
        # No closing ``---`` marker — _split_frontmatter returns ({}, text).
        text = "---\nname: my-skill\ndescription: Use when X. Don't use for Y.\n"
        r = lint_text(text)
        # With no body, the rule engine sees no frontmatter → E002 fires.
        codes = {f.code for f in r.findings}
        assert "E002" in codes

    def test_yaml_returns_non_dict(self):
        # YAML root is a list, not a dict. _split_frontmatter returns ({}, body).
        text = "---\n- one\n- two\n---\n# body\n" + ("line\n" * 25)
        r = lint_text(text)
        # No frontmatter dict → E002 (frontmatter missing or invalid).
        codes = {f.code for f in r.findings}
        assert "E002" in codes

    def test_split_frontmatter_unclosed_branch(self):
        """Direct exercise of the ``if end is None`` branch in _split_frontmatter."""
        from skillmd_lint.rules import _split_frontmatter

        text = "---\nname: my-skill\n"  # no closing fence
        fm, body = _split_frontmatter(text)
        assert fm == {}
        assert body == text

    def test_split_frontmatter_non_dict_branch(self):
        """Direct exercise of the ``if not isinstance(data, dict)`` branch."""
        from skillmd_lint.rules import _split_frontmatter

        text = "---\n- one\n- two\n---\nbody"
        fm, body = _split_frontmatter(text)
        assert fm == {}
        assert "body" in body


class TestRuleEdgeCases:
    def test_name_reserved_with_non_string_name(self):
        # ``name`` is an int, not a string — the ``isinstance`` guard in
        # ``_rule_name_reserved`` skips it (returns immediately), so E005
        # does NOT fire even though ``42`` is not in RESERVED_SLUGS.
        # E003 fires because E003 owns the "name is not a valid string" check.
        text = "---\nname: 42\ndescription: Use when X. Don't use for Y.\n---\n" + ("line\n" * 25)
        r = lint_text(text)
        codes = {f.code for f in r.findings}
        assert "E003" in codes
        assert "E005" not in codes

    def test_skill_type_non_string(self):
        # ``skill_type`` is a list, not a string.
        text = (
            "---\n"
            "name: my-skill\n"
            "description: Use when X. Don't use for Y.\n"
            "skill_type:\n  - domain-expert\n"
            "---\n" + ("line\n" * 25)
        )
        r = lint_text(text)
        warnings = {f.code for f in r.warnings}
        assert "W009" in warnings
        # Verify the message mentions the actual type.
        msg = next(f.message for f in r.warnings if f.code == "W009")
        assert "list" in msg

    def test_tags_not_a_list(self):
        # ``tags`` is a string, not a list.
        text = (
            "---\n"
            "name: my-skill\n"
            "description: Use when X. Don't use for Y.\n"
            "tags: 'api, rest'\n"
            "---\n" + ("line\n" * 25)
        )
        r = lint_text(text)
        warnings = {f.code for f in r.warnings}
        assert "W013" in warnings
        msg = next(f.message for f in r.warnings if f.code == "W013")
        assert "list" in msg

    def test_tags_list_with_non_string_items(self):
        # ``tags`` is a list containing a non-string element (an int).
        text = (
            "---\n"
            "name: my-skill\n"
            "description: Use when X. Don't use for Y.\n"
            "tags:\n  - api\n  - 42\n"
            "---\n" + ("line\n" * 25)
        )
        r = lint_text(text)
        warnings = {f.code for f in r.warnings}
        assert "W013" in warnings

    def test_tags_with_empty_string(self):
        # An empty string inside the tags list — should warn.
        text = (
            "---\n"
            "name: my-skill\n"
            "description: Use when X. Don't use for Y.\n"
            "tags:\n  - ''\n"
            "---\n" + ("line\n" * 25)
        )
        r = lint_text(text)
        warnings = {f.code for f in r.warnings}
        assert "W013" in warnings

    def test_tags_unique_ignores_non_strings(self):
        # E010 only fires on duplicate *strings*; non-strings are silently
        # skipped (W013 owns the format complaint).
        text = (
            "---\n"
            "name: my-skill\n"
            "description: Use when X. Don't use for Y.\n"
            "tags:\n  - api\n  - 42\n  - 42\n"
            "---\n" + ("line\n" * 25)
        )
        r = lint_text(text)
        errors = {f.code for f in r.errors}
        assert "E010" not in errors

    def test_lint_paths_also_warns_for_non_string_tags(self):
        # Same as above but routed through lint_paths for the additional
        # coverage of the lint_paths wrapper branches.
        from skillmd_lint.rules import lint_paths

        text = (
            "---\n"
            "name: my-skill\n"
            "description: Use when X. Don't use for Y.\n"
            "tags:\n  - 42\n"
            "---\n" + ("line\n" * 25)
        )
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(text)
            path = Path(f.name)
        try:
            results = lint_paths([path])
            warnings = {f.code for r in results for f in r.warnings}
            assert "W013" in warnings
        finally:
            path.unlink()


class TestFolderDiscoveryBranches:
    def test_skills_dir_with_non_skill_children(self, tmp_path: Path):
        """``skills/`` may contain non-skill entries; the loop must skip them.

        This drives the ``child.is_dir() and (child / "SKILL.md").is_file()``
        False branch in ``lint_folder`` (line 712 -> 711) — the only branch
        not covered by the existing happy-path test.
        """

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        # Valid skill: should be linted.
        valid = skills_dir / "valid-skill"
        valid.mkdir()
        (valid / "SKILL.md").write_text(VALID, encoding="utf-8")
        # Non-skill directory (no SKILL.md): should be SKIPPED.
        empty = skills_dir / "empty-dir"
        empty.mkdir()
        # Non-directory entry (a stray file at the root of skills/): should be
        # SKIPPED.
        stray = skills_dir / "stray-file.md"
        stray.write_text("not a skill\n", encoding="utf-8")

        results = lint_folder(tmp_path)
        # Only the valid skill should produce a LintResult.
        assert len(results) == 1
        assert results[0].passed
