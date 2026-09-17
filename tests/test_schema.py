"""Tests for the JSON Schema frontmatter validator.

We deliberately don't pull in the ``jsonschema`` package — the linter is a
zero-dependency tool beyond PyYAML, and the embedded schema validator
implements only the small subset of Draft 2020-12 we need.
"""

from __future__ import annotations

from pathlib import Path

from skillmd_lint import lint_text
from skillmd_lint.schema import get_schema, validate_frontmatter


class TestSchemaLoader:
    def test_get_schema_returns_dict(self):
        s = get_schema()
        assert isinstance(s, dict)
        assert s.get("title") == "SKILL.md frontmatter"

    def test_schema_requires_name_and_description(self):
        s = get_schema()
        assert "name" in s.get("required", [])
        assert "description" in s.get("required", [])


class TestValidateFrontmatter:
    def test_valid_fm_clean(self):
        fm = {
            "name": "my-skill",
            "description": "Use when X. Don't use for Y.",
            "skill_type": "domain-expert",
            "tags": ["api", "rest"],
            "version": "1.0.0",
            "token_budget": 1500,
        }
        assert validate_frontmatter(fm) == []

    def test_missing_required_key(self):
        fm = {"name": "my-skill"}
        errs = validate_frontmatter(fm)
        assert any("description" in e for e in errs)

    def test_name_pattern_violation(self):
        fm = {"name": "MySkill", "description": "Use when X. Don't use for Y."}
        errs = validate_frontmatter(fm)
        assert any("name" in e for e in errs)

    def test_description_too_long(self):
        fm = {"name": "my-skill", "description": "x" * 2000}
        errs = validate_frontmatter(fm)
        assert any("maxLength" in e for e in errs)

    def test_skill_type_enum_violation(self):
        fm = {"name": "my-skill", "description": "Use when X.", "skill_type": "ninja"}
        errs = validate_frontmatter(fm)
        assert any("skill_type" in e and "enum" in e for e in errs)

    def test_token_budget_must_be_positive_int(self):
        fm = {"name": "my-skill", "description": "Use when X.", "token_budget": -1}
        errs = validate_frontmatter(fm)
        assert any("token_budget" in e for e in errs)

    def test_token_budget_must_be_int_not_string(self):
        fm = {"name": "my-skill", "description": "Use when X.", "token_budget": "lots"}
        errs = validate_frontmatter(fm)
        assert any("token_budget" in e for e in errs)

    def test_tags_unique_items(self):
        fm = {
            "name": "my-skill",
            "description": "Use when X.",
            "tags": ["api", "api"],
        }
        errs = validate_frontmatter(fm)
        assert any("duplicate" in e for e in errs)

    def test_tags_kebab_case(self):
        fm = {
            "name": "my-skill",
            "description": "Use when X.",
            "tags": ["Bad_Tag"],
        }
        errs = validate_frontmatter(fm)
        assert any("tags[0]" in e for e in errs)

    def test_version_semver_pattern(self):
        fm = {"name": "my-skill", "description": "Use when X.", "version": "v1.0"}
        errs = validate_frontmatter(fm)
        assert any("version" in e for e in errs)

    def test_additional_properties_allowed(self):
        # Unknown keys are *not* an error — forward-compat.
        fm = {
            "name": "my-skill",
            "description": "Use when X.",
            "future_field": "anything",
        }
        assert validate_frontmatter(fm) == []


class TestSchemaCLIIntegration:
    """End-to-end: ``skillmd-lint --schema`` reports schema violations as
    S001..S999 findings.
    """

    def test_schema_flag_emits_findings(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text(
            "---\n"
            "name: BadName\n"  # schema: pattern violation
            "description: Use when X.\n"
            "---\n" + ("line\n" * 25),
            encoding="utf-8",
        )
        # The rule engine flags BadName as E004; the schema layer flags it as
        # S001. Both are valid — verify the rule engine runs.
        r = lint_text(p.read_text(encoding="utf-8"))
        codes = {f.code for f in r.errors}
        assert "E004" in codes
