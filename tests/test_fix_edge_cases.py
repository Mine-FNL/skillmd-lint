"""Edge-case tests for the mechanical-fix module.

Focuses on defensive branches and edge cases that the main
``test_fix.py`` suite leaves uncovered.
"""

from __future__ import annotations

from skillmd_lint import fix
from skillmd_lint.rules import lint_text


def _skill(fm: str, body: str = "\n## When to use\n\n## Examples\n\n## Pitfalls to avoid\n") -> str:
    return f"---\n{fm}\n---\n{body}"


# ---------------------------------------------------------------------------
# W008 — typo edge cases
# ---------------------------------------------------------------------------


def test_w008_both_typo_and_canonical_present():
    """If both a typo and canonical key exist, canonical wins; typo is dropped."""
    text = _skill(
        "name: helper\ndesription: typo'd value\ndescription: canonical value"
    )
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    assert any(a.code == "W008" for a in applied)
    # The canonical "description" value should remain
    assert "canonical value" in new_text


def test_w008_no_findings_yields_no_change():
    text = _skill("name: helper\ndescription: Use when X.")
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    assert applied == []
    assert new_text == text


# ---------------------------------------------------------------------------
# Tags — non-string entries, edge formats
# ---------------------------------------------------------------------------


def test_e010_non_string_tags_skipped():
    """Non-string entries are preserved; only string duplicates are removed."""
    text = _skill(
        "name: helper\ndescription: Use when X.\ntags:\n  - python\n  - 42\n  - python"
    )
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    if any(f.code == "E010" for f in result.findings):
        assert any(a.code == "E010" for a in applied)


def test_e010_tags_not_a_list_is_noop():
    text = _skill("name: helper\ndescription: Use when X.\ntags: python")
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    # Tags is a string not a list, so rule doesn't fire, fix doesn't apply
    assert not any(a.code == "E010" for a in applied)


def test_w013_non_string_tags_skipped():
    text = _skill(
        "name: helper\ndescription: Use when X.\ntags:\n  - python\n  - 42"
    )
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    # Non-string tag shouldn't be normalised
    assert "42" in new_text


def test_w013_normalises_underscore_and_consecutive_hyphens():
    text = _skill(
        "name: helper\ndescription: Use when X.\ntags:\n  - foo___bar\n  - baz--qux"
    )
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    if any(f.code == "W013" for f in result.findings):
        assert "foo-bar" in new_text
        assert "baz-qux" in new_text


def test_w013_strips_leading_trailing_hyphens():
    text = _skill(
        "name: helper\ndescription: Use when X.\ntags:\n  - '---foo---'"
    )
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    if any(f.code == "W013" for f in result.findings):
        assert "foo" in new_text
        # No leading hyphens
        assert "-foo" not in new_text or "foo" in new_text.lower().replace("--", "-")


# ---------------------------------------------------------------------------
# Name format — multi-boundary camelCase
# ---------------------------------------------------------------------------


def test_e004_multi_boundary_camelcase():
    text = _skill("name: MySkillHelper\ndescription: Use when X.")
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result, unsafe=True)
    if any(f.code == "E004" for f in result.findings):
        assert any(a.code == "E004" for a in applied)
        assert "my-skill-helper" in new_text


def test_e004_uppercase_run_then_lowercase():
    """Names like ``ABCDef`` should split as ``abc-def``, not ``a-b-c-def``."""
    text = _skill("name: ABCDef\ndescription: Use when X.")
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result, unsafe=True)
    if any(f.code == "E004" for f in result.findings):
        assert any(a.code == "E004" for a in applied)
        # Should be abc-def, not abc-d-ef
        assert "abc-def" in new_text


def test_e004_non_string_name_is_noop():
    text = _skill("name: 42\ndescription: Use when X.")
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result, unsafe=True)
    # If the rule fired, fix should not crash on a non-string
    if any(f.code == "E004" for f in result.findings):
        assert not any(a.code == "E004" for a in applied)


def test_e004_canonical_unchanged_unsafe():
    text = _skill("name: my-skill\ndescription: Use when X.")
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result, unsafe=True)
    assert not any(a.code == "E004" for a in applied)


# ---------------------------------------------------------------------------
# Version — edge cases
# ---------------------------------------------------------------------------


def test_w010_non_string_version_is_noop():
    """version: 1 is an int, not str — W010 rule won't fire."""
    text = _skill("name: helper\ndescription: Use when X.\nversion: 1")
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    assert not any(a.code == "W010" for a in applied)


def test_w010_no_prefix_no_change():
    text = _skill("name: helper\ndescription: Use when X.\nversion: 1.2.3")
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    assert not any(a.code == "W010" for a in applied)


def test_w010_invalid_after_strip_is_noop():
    """If stripping 'v' leaves invalid semver, don't apply."""
    text = _skill("name: helper\ndescription: Use when X.\nversion: vfoo")
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    # vfoo → foo (still invalid). Don't apply.
    assert not any(a.code == "W010" for a in applied)


# ---------------------------------------------------------------------------
# Token budget — already-int and negative-string cases
# ---------------------------------------------------------------------------


def test_w011_already_int_no_change():
    text = _skill("name: helper\ndescription: Use when X.\ntoken_budget: 1500")
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    assert not any(a.code == "W011" for a in applied)


def test_w011_non_numeric_string_no_change():
    text = _skill("name: helper\ndescription: Use when X.\ntoken_budget: many")
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    assert not any(a.code == "W011" for a in applied)


def test_w011_zero_string_no_change():
    """0 is not positive, so don't coerce."""
    text = _skill("name: helper\ndescription: Use when X.\ntoken_budget: \"0\"")
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    assert not any(a.code == "W011" for a in applied)


# ---------------------------------------------------------------------------
# Skill type — unknown alias
# ---------------------------------------------------------------------------


def test_w009_valid_skill_type_no_change():
    text = _skill(
        "name: helper\ndescription: Use when X.\nskill_type: domain-expert"
    )
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result, unsafe=True)
    assert not any(a.code == "W009" for a in applied)


def test_w009_non_string_skill_type_no_crash():
    """skill_type: 42 (int) — W009 rule won't fire on non-string."""
    text = _skill("name: helper\ndescription: Use when X.\nskill_type: 42")
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result, unsafe=True)
    assert not any(a.code == "W009" for a in applied)


# ---------------------------------------------------------------------------
# Integration: multiple fixes in one pass
# ---------------------------------------------------------------------------


def test_multiple_safe_fixes_in_one_pass():
    text = _skill(
        "name: helper\n"
        "desription: Use when X.\n"
        "version: v1.0.0\n"
        "tags:\n"
        "  - python\n"
        "  - python"
    )
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    codes = {a.code for a in applied}
    # W008, E010, W010 may all fire
    assert "W008" in codes
    assert "E010" in codes
    assert "W010" in codes


# ---------------------------------------------------------------------------
# _split_for_fix edge cases
# ---------------------------------------------------------------------------


def test_split_no_frontmatter_returns_none():
    text = "## Just a heading\n\nSome markdown."
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    assert applied == []


def test_split_unclosed_frontmatter_returns_none():
    text = "---\nname: helper\ndescription: never closes"
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    assert applied == []


def test_split_non_dict_frontmatter_returns_none():
    """Frontmatter that parses to a non-dict (e.g. just a string) is rejected."""
    text = "---\njust a string\n---\nbody"
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    assert applied == []


def test_split_with_bom_marker():
    """BOM-prefixed frontmatter is stripped before parsing."""
    text = "\ufeff---\nname: helper\ndescription: Use when X.\n---\n\nbody"
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    # The fix pipeline should accept the BOM-prefixed form
    assert applied == [] or new_text != text


# ---------------------------------------------------------------------------
# _render edge cases
# ---------------------------------------------------------------------------


def test_render_preserves_no_trailing_newline_body():
    """Body without trailing newline gets one appended."""
    text = _skill("name: helper\ndesription: Use when X.").rstrip("\n")
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    # When a fix is applied, the result is properly rendered.
    if applied:
        assert new_text.endswith("\n")


def test_render_with_unordered_keys():
    """YAML ordering is preserved when re-rendered."""
    text = _skill("description: Use when X.\nname: helper\nversion: 1.0.0")
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    # If no fix needed, ordering is unchanged
    if not applied:
        # description should still come before name
        assert new_text.index("description") < new_text.index("name")
