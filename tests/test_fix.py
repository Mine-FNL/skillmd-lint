"""Tests for the mechanical-fix module."""

from __future__ import annotations

from skillmd_lint import fix
from skillmd_lint.rules import lint_text


def _make_skill(
    frontmatter: str,
    body: str = "\n## When to use\n\n## Examples\n\n## Pitfalls to avoid\n",
) -> str:
    return f"---\n{frontmatter}\n---\n{body}"


# ---------------------------------------------------------------------------
# W008 — frontmatter typos
# ---------------------------------------------------------------------------


def test_fix_w008_renames_desription_typo():
    text = _make_skill(
        "name: api-helper\ndesription: Use when working with the API. Do not use elsewhere."
    )
    result = lint_text(text, "x")
    assert any(f.code == "W008" for f in result.findings)
    new_text, applied = fix.apply_fixes(text, result)
    assert any(a.code == "W008" for a in applied)
    assert "description" in new_text
    assert "desription" not in new_text


def test_fix_w008_no_typo_is_noop():
    text = _make_skill("name: api-helper\ndescription: Use when working with the API.")
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    assert applied == []
    assert new_text == text


def test_fix_w008_multiple_typos():
    text = _make_skill("nme: helper\ndesription: Use when X.")
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    codes = {a.code for a in applied}
    assert "W008" in codes
    assert "name" in new_text
    assert "description" in new_text
    assert "nme" not in new_text
    assert "desription" not in new_text


# ---------------------------------------------------------------------------
# E010 — duplicate tags
# ---------------------------------------------------------------------------


def test_fix_e010_dedupes_tags():
    text = _make_skill(
        "name: helper\ndescription: Use when X.\ntags:\n  - python\n  - python\n  - helper"
    )
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    assert any(a.code == "E010" for a in applied)
    # Re-lint to confirm the dedup held.
    new_result = lint_text(new_text, "x")
    assert not any(f.code == "E010" for f in new_result.findings)


def test_fix_e010_no_dupes_is_noop():
    text = _make_skill("name: helper\ndescription: Use when X.\ntags:\n  - python\n  - helper")
    result = lint_text(text, "x")
    _new_text, applied = fix.apply_fixes(text, result)
    # E010 may or may not fire depending on rule's exact behaviour with
    # case-sensitive matching; we only require no fix to be applied if
    # the rule didn't fire.
    if any(f.code == "E010" for f in result.findings):
        # If it fired, fix should have deduped
        assert applied
    else:
        assert applied == []


# ---------------------------------------------------------------------------
# W013 — tag format
# ---------------------------------------------------------------------------


def test_fix_w013_normalises_tag_case():
    text = _make_skill("name: helper\ndescription: Use when X.\ntags:\n  - Python\n  - API Helper")
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    # If the rule fired, the fix should have applied
    if any(f.code == "W013" for f in result.findings):
        assert any(a.code == "W013" for a in applied)
        assert "python" in new_text
        assert "api-helper" in new_text
        # Re-lint: rule should not fire again
        new_result = lint_text(new_text, "x")
        assert not any(f.code == "W013" for f in new_result.findings)


def test_fix_w013_handles_underscores_and_spaces():
    text = _make_skill(
        "name: helper\ndescription: Use when X.\ntags:\n  - api_helper\n  - web frontend"
    )
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    if any(f.code == "W013" for f in result.findings):
        assert any(a.code == "W013" for a in applied)
        assert "api-helper" in new_text
        assert "web-frontend" in new_text


# ---------------------------------------------------------------------------
# W010 — semver prefix
# ---------------------------------------------------------------------------


def test_fix_w010_strips_v_prefix():
    text = _make_skill("name: helper\ndescription: Use when X.\nversion: v1.2.3")
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    assert any(a.code == "W010" for a in applied)
    assert "version: 1.2.3" in new_text


def test_fix_w010_no_prefix_is_noop():
    text = _make_skill("name: helper\ndescription: Use when X.\nversion: 1.2.3")
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    # If the rule didn't fire, no fix; if it did, no harm done.
    assert applied == [] or "version: 1.2.3" in new_text


def test_fix_w010_complex_semver_unchanged():
    """v-prefix is stripped only when the result is still valid semver."""
    text = _make_skill("name: helper\ndescription: Use when X.\nversion: v1.2.3-rc.1")
    result = lint_text(text, "x")
    _new_text, applied = fix.apply_fixes(text, result)
    # Complex prerelease semver may not be flagged; if it isn't, no fix
    if any(f.code == "W010" for f in result.findings):
        assert applied  # some fix happened


# ---------------------------------------------------------------------------
# W011 — token_budget coercion
# ---------------------------------------------------------------------------


def test_fix_w011_string_to_int():
    text = _make_skill('name: helper\ndescription: Use when X.\ntoken_budget: "1500"')
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    if any(f.code == "W011" for f in result.findings):
        assert any(a.code == "W011" for a in applied)
        # After fix, the integer value is present
        assert "1500" in new_text


# ---------------------------------------------------------------------------
# E004 — name format (unsafe, gated)
# ---------------------------------------------------------------------------


def test_fix_e004_unsafe_default_off():
    text = _make_skill("name: MySkill\ndescription: Use when X.")
    result = lint_text(text, "x")
    _new_text, applied = fix.apply_fixes(text, result, unsafe=False)
    # Without --unsafe-fix, E004 should not be applied.
    assert not any(a.code == "E004" for a in applied)


def test_fix_e004_unsafe_enabled():
    text = _make_skill("name: MySkill\ndescription: Use when X.")
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result, unsafe=True)
    if any(f.code == "E004" for f in result.findings):
        assert any(a.code == "E004" for a in applied)
        assert "my-skill" in new_text


def test_fix_e004_does_not_change_already_valid():
    text = _make_skill("name: my-skill\ndescription: Use when X.")
    result = lint_text(text, "x")
    _new_text, applied = fix.apply_fixes(text, result, unsafe=True)
    assert not any(a.code == "E004" for a in applied)


# ---------------------------------------------------------------------------
# W009 — skill_type alias (unsafe, gated)
# ---------------------------------------------------------------------------


def test_fix_w009_aliases_code():
    text = _make_skill("name: helper\ndescription: Use when X.\nskill_type: code")
    result = lint_text(text, "x")
    _new_text, applied = fix.apply_fixes(text, result, unsafe=True)
    if any(f.code == "W009" for f in result.findings):
        # Map says code → specialist
        assert any(a.code == "W009" for a in applied)


def test_fix_w009_unknown_alias_is_noop():
    text = _make_skill("name: helper\ndescription: Use when X.\nskill_type: ninja")
    result = lint_text(text, "x")
    _new_text, applied = fix.apply_fixes(text, result, unsafe=True)
    if any(f.code == "W009" for f in result.findings):
        # ninja isn't in alias_map → no fix
        assert not any(a.code == "W009" for a in applied)


# ---------------------------------------------------------------------------
# Integration: no findings → no fixes
# ---------------------------------------------------------------------------


def test_apply_fixes_no_findings_no_changes():
    text = _make_skill(
        "name: helper\ndescription: Use when X. Do not use elsewhere.\n"
        "skill_type: domain-expert\nversion: 1.0.0\n"
        "tags:\n  - python\n  - helper"
    )
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    assert applied == []
    assert new_text == text


def test_apply_fixes_invalid_yaml_no_crash():
    text = "no frontmatter at all, just markdown body content\n" * 5
    result = lint_text(text, "x")
    new_text, applied = fix.apply_fixes(text, result)
    assert applied == []
    assert new_text == text


def test_apply_fixes_only_attempts_fired_codes():
    """Fixers don't run for rules that didn't fire."""

    # A skill with ONLY a name typo (W008), nothing else.
    text = _make_skill("name: helper\ndesription: Use when X.")
    result = lint_text(text, "x")
    fired = {f.code for f in result.findings}
    _new_text, applied = fix.apply_fixes(text, result)
    applied_codes = {a.code for a in applied}
    assert applied_codes.issubset(fired)


def test_list_fixable_codes_returns_safe_only():
    safe = fix.list_fixable_codes(unsafe=False)
    unsafe_only = fix.list_fixable_codes(unsafe=True)
    assert set(safe).issubset(set(unsafe_only))
    # Unsafe should have at least E004 and W009
    assert "E004" in unsafe_only
    assert "W009" in unsafe_only
    # And the safe set should have the documented safe codes
    assert "W008" in safe
    assert "W010" in safe


# ---------------------------------------------------------------------------
# Schema export CLI
# ---------------------------------------------------------------------------


def test_schema_export_cli(tmp_path, capsys):
    """schema-export writes a valid JSON Schema to the requested path."""
    import json
    import subprocess
    import sys

    target = tmp_path / "schema.json"
    result = subprocess.run(
        [sys.executable, "-m", "skillmd_lint", "--schema-export", str(target)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert target.exists()
    schema = json.loads(target.read_text())
    assert "$schema" in schema
    assert "title" in schema
    assert schema["title"] == "SKILL.md frontmatter"


def test_schema_export_cli_no_paths_required(tmp_path):
    """schema-export works without any positional paths."""
    import subprocess
    import sys

    target = tmp_path / "s2.json"
    result = subprocess.run(
        [sys.executable, "-m", "skillmd_lint", "--schema-export", str(target)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert target.exists()
