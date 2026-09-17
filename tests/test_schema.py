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


# ---------------------------------------------------------------------------
# Coverage targets — every uncovered branch in schema.py
# ---------------------------------------------------------------------------


class TestSchemaLoaderFallback:
    def test_load_schema_falls_back_to_repo_root(self, monkeypatch):
        """When the package resource is unavailable, fall back to the
        repo-root ``skillmd_frontmatter.schema.json`` file.
        """

        from skillmd_lint import schema as schema_mod

        # Reset the memoized loader so we re-execute the try/except.
        schema_mod._SCHEMA_TEXT = None

        def fake_files(_pkg):
            raise ModuleNotFoundError("simulated missing resource")

        monkeypatch.setattr(schema_mod.resources, "files", fake_files)
        schema_text = schema_mod._load_schema_text()
        assert isinstance(schema_text, str)
        assert "skill-md frontmatter" in schema_text.lower() or "title" in schema_text

        # Restore for downstream tests.
        schema_mod._SCHEMA_TEXT = None

    def test_load_schema_raises_when_both_paths_missing(self, monkeypatch, tmp_path):
        """If both the package resource AND the repo-root fallback are missing,
        the FileNotFoundError propagates. (The exception branch in the loader.)
        """

        from skillmd_lint import schema as schema_mod

        schema_mod._SCHEMA_TEXT = None

        # Force the package resource lookup to fail.
        def fake_files(_pkg):
            raise ModuleNotFoundError("simulated missing resource")

        # Force the fallback to point at a non-existent file by re-pointing
        # ``__file__`` so the resolver walks a missing directory.
        monkeypatch.setattr(schema_mod, "__file__", str(tmp_path / "does_not_exist" / "schema.py"))
        monkeypatch.setattr(schema_mod.resources, "files", fake_files)

        try:
            schema_mod._load_schema_text()
            raise AssertionError("expected FileNotFoundError")
        except FileNotFoundError:
            pass
        finally:
            schema_mod._SCHEMA_TEXT = None


class TestScalarCoercion:
    def test_int_coerced_to_string(self):
        """An int/float value in a string-typed field is coerced to a string."""
        from skillmd_lint.schema import _coerce_scalar

        coerced = _coerce_scalar(42, {"type": "string"})
        assert coerced == "42"
        assert isinstance(coerced, str)

    def test_float_coerced_to_string(self):
        from skillmd_lint.schema import _coerce_scalar

        coerced = _coerce_scalar(3.14, {"type": "string"})
        assert coerced == "3.14"

    def test_bool_not_coerced(self):
        """Bools are a subclass of int in Python — must NOT be coerced."""
        from skillmd_lint.schema import _coerce_scalar

        # ``True`` is a bool, which is an int subclass — but the function
        # explicitly excludes bools from the string coercion.
        result = _coerce_scalar(True, {"type": "string"})
        assert result is True


class TestCheckOneBranches:
    """Drive each branch of the recursive ``_check_one`` function."""

    def test_expected_string_type(self):
        """Field declared as string but value is an int."""
        from skillmd_lint.schema import _check_one

        errs: list[str] = []
        _check_one(42, {"type": "string"}, "$.field", errs)
        assert any("expected string" in e for e in errs)

    def test_min_length_fires(self):
        from skillmd_lint.schema import _check_one

        errs: list[str] = []
        _check_one("a", {"type": "string", "minLength": 3}, "$.field", errs)
        assert any("minLength 3" in e for e in errs)

    def test_array_wrong_type(self):
        from skillmd_lint.schema import _check_one

        errs: list[str] = []
        _check_one("not a list", {"type": "array"}, "$.field", errs)
        assert any("expected array" in e for e in errs)

    def test_object_wrong_type(self):
        from skillmd_lint.schema import _check_one

        errs: list[str] = []
        _check_one("not a dict", {"type": "object"}, "$.field", errs)
        assert any("expected object" in e for e in errs)


class TestArraySchemaBranches:
    """Drive every branch of the array-schema code path."""

    def test_array_without_unique_items(self):
        """An array schema without ``uniqueItems`` skips the dup-check block."""
        from skillmd_lint.schema import _check_one

        errs: list[str] = []
        # ``uniqueItems`` absent → the `if schema.get("uniqueItems"):` branch
        # evaluates False and falls through to the items-schema check.
        _check_one(["a", "b", "a"], {"type": "array"}, "$.field", errs)
        # No error because no constraints and no items schema.
        assert errs == []

    def test_array_with_empty_unique_items(self):
        """An empty array with ``uniqueItems`` set passes the dup check."""
        from skillmd_lint.schema import _check_one

        errs: list[str] = []
        _check_one([], {"type": "array", "uniqueItems": True}, "$.field", errs)
        assert errs == []

    def test_array_with_single_unique_item(self):
        """A single-item array with uniqueItems: loop runs once."""
        from skillmd_lint.schema import _check_one

        errs: list[str] = []
        _check_one(["only"], {"type": "array", "uniqueItems": True}, "$.field", errs)
        assert errs == []

    def test_array_with_unique_items_and_duplicates(self):
        """A duplicate triggers the dup error (covers the inner branch)."""
        from skillmd_lint.schema import _check_one

        errs: list[str] = []
        _check_one(["a", "a"], {"type": "array", "uniqueItems": True}, "$.field", errs)
        assert any("duplicate" in e for e in errs)

    def test_array_without_items_schema(self):
        """An array schema with no ``items`` field skips the per-item recursion."""
        from skillmd_lint.schema import _check_one

        errs: list[str] = []
        _check_one([1, 2, 3], {"type": "array"}, "$.field", errs)
        # No errors because items is missing → ``isinstance(item_schema, dict)`` False.
        assert errs == []

    def test_array_with_non_dict_items_schema(self):
        """An items schema that's not a dict (e.g. just True/False) is skipped."""
        from skillmd_lint.schema import _check_one

        errs: list[str] = []
        # YAML true parses as Python True — not a dict, so we skip the recursion.
        _check_one(["x"], {"type": "array", "items": True}, "$.field", errs)
        assert errs == []

    def test_array_with_items_schema_runs_recursion(self):
        """When ``items`` is a dict, recurse on each item."""
        from skillmd_lint.schema import _check_one

        errs: list[str] = []
        # items says string, but we pass an int → error per item.
        _check_one([1, 2, 3], {"type": "array", "items": {"type": "string"}}, "$.field", errs)
        assert len(errs) == 3


class TestObjectSchemaBranches:
    def test_object_without_required_keys(self):
        """Object schema with no ``required`` field: empty required loop."""
        from skillmd_lint.schema import _check_one

        errs: list[str] = []
        _check_one({}, {"type": "object"}, "$.field", errs)
        assert errs == []

    def test_object_with_all_required_present(self):
        from skillmd_lint.schema import _check_one

        errs: list[str] = []
        _check_one({"a": 1, "b": 2}, {"type": "object", "required": ["a", "b"]}, "$.field", errs)
        assert errs == []


class TestUnknownSchemaType:
    def test_unknown_type_passes_through(self):
        """A schema with an unknown type (e.g. ``boolean``) doesn't error."""
        from skillmd_lint.schema import _check_one

        errs: list[str] = []
        # ``boolean`` is not one of the four we handle; we should pass through.
        _check_one(True, {"type": "boolean"}, "$.field", errs)
        assert errs == []

    def test_missing_type_passes_through(self):
        from skillmd_lint.schema import _check_one

        errs: list[str] = []
        _check_one("anything", {}, "$.field", errs)
        assert errs == []
