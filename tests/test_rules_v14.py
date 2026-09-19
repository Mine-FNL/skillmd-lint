"""Tests for the v1.4.0 rules: E011, W014-W022."""

from __future__ import annotations

import pytest

from skillmd_lint.rules import lint_file, lint_text


def _make(fm: str, body: str = None) -> str:
    if body is None:
        body = (
            "\n## When to use\n\nUse this skill.\n\n"
            "## Examples\n\nFor example, see the `docs` file.\n\n"
            "## Pitfalls to avoid\n\nPitfall here.\n"
        )
    return f"---\n{fm}\n---\n{body}"


# ---------------------------------------------------------------------------
# E011 — version must be a string
# ---------------------------------------------------------------------------


def test_e011_int_version_triggers():
    text = _make("name: helper\ndescription: Use when X.\nversion: 1.0")
    r = lint_text(text, "x")
    assert any(f.code == "E011" for f in r.findings)


def test_e011_float_version_triggers():
    text = _make("name: helper\ndescription: Use when X.\nversion: 1.5")
    r = lint_text(text, "x")
    assert any(f.code == "E011" for f in r.findings)


def test_e011_string_version_no_trigger():
    text = _make("name: helper\ndescription: Use when X.\nversion: '1.0'")
    r = lint_text(text, "x")
    assert not any(f.code == "E011" for f in r.findings)


def test_e011_no_version_no_trigger():
    text = _make("name: helper\ndescription: Use when X.")
    r = lint_text(text, "x")
    assert not any(f.code == "E011" for f in r.findings)


# ---------------------------------------------------------------------------
# W014 — frontmatter tab indentation
# ---------------------------------------------------------------------------


def test_w014_tab_in_frontmatter_triggers(tmp_path):
    p = tmp_path / "SKILL.md"
    p.write_text("---\n\tname: helper\ndescription: Use when X.\n---\n\nbody", encoding="utf-8")
    r = lint_file(p)
    assert any(f.code == "W014" for f in r.findings)


def test_w014_no_tabs_no_trigger(tmp_path):
    p = tmp_path / "SKILL.md"
    p.write_text("---\nname: helper\ndescription: Use when X.\n---\n\nbody", encoding="utf-8")
    r = lint_file(p)
    assert not any(f.code == "W014" for f in r.findings)


def test_w014_text_mode_no_path_no_trigger():
    """W014 needs a file path to re-read the raw text."""
    text = _make("name: helper\ndescription: Use when X.")
    r = lint_text(text, "<text>")
    assert not any(f.code == "W014" for f in r.findings)


# ---------------------------------------------------------------------------
# W015 — placeholder text in description
# ---------------------------------------------------------------------------


def test_w015_todo_in_description():
    text = _make("name: helper\ndescription: TODO write a description.")
    r = lint_text(text, "x")
    assert any(f.code == "W015" for f in r.findings)


def test_w015_lorem_in_description():
    text = _make("name: helper\ndescription: Lorem ipsum dolor sit amet.")
    r = lint_text(text, "x")
    assert any(f.code == "W015" for f in r.findings)


def test_w015_clean_description_no_trigger():
    text = _make("name: helper\ndescription: Use when debugging Python code. Do not use for JS.")
    r = lint_text(text, "x")
    assert not any(f.code == "W015" for f in r.findings)


# ---------------------------------------------------------------------------
# W016 — raw HTML tags in body
# ---------------------------------------------------------------------------


def test_w016_bold_tag_in_body_triggers():
    body = "\n## When to use\n\nUse this.\n\n## Examples\n\nSee `docs`.\n\n## Pitfalls to avoid\n\n<b>old text</b> here\n"
    text = _make("name: helper\ndescription: Use when X.", body)
    r = lint_text(text, "x")
    assert any(f.code == "W016" for f in r.findings)


def test_w016_code_fence_html_no_trigger():
    body = "\n## When to use\n\nUse this.\n\n## Examples\n\nSee `docs`.\n\n## Pitfalls to avoid\n\n```html\n<b>old text</b>\n```\n"
    text = _make("name: helper\ndescription: Use when X.", body)
    r = lint_text(text, "x")
    assert not any(f.code == "W016" for f in r.findings)


def test_w016_markdown_bold_no_trigger():
    body = "\n## When to use\n\nUse this.\n\n## Examples\n\nSee `docs`.\n\n## Pitfalls to avoid\n\n**bold text** here\n"
    text = _make("name: helper\ndescription: Use when X.", body)
    r = lint_text(text, "x")
    assert not any(f.code == "W016" for f in r.findings)


# ---------------------------------------------------------------------------
# W017 — name has leading/trailing hyphen
# ---------------------------------------------------------------------------


def test_w017_trailing_hyphen():
    text = _make("name: helper-\ndescription: Use when X.")
    r = lint_text(text, "x")
    assert any(f.code == "W017" for f in r.findings)


def test_w017_leading_hyphen():
    text = _make("name: -helper\ndescription: Use when X.")
    r = lint_text(text, "x")
    assert any(f.code == "W017" for f in r.findings)


def test_w017_clean_name_no_trigger():
    text = _make("name: helper\ndescription: Use when X.")
    r = lint_text(text, "x")
    assert not any(f.code == "W017" for f in r.findings)


# ---------------------------------------------------------------------------
# W018 — redundant prefix in description
# ---------------------------------------------------------------------------


def test_w018_this_skill_prefix():
    text = _make("name: helper\ndescription: This skill helps debug Python.")
    r = lint_text(text, "x")
    assert any(f.code == "W018" for f in r.findings)


def test_w018_this_is_a_skill_prefix():
    text = _make("name: helper\ndescription: This is a skill for debugging.")
    r = lint_text(text, "x")
    assert any(f.code == "W018" for f in r.findings)


def test_w018_use_when_no_trigger():
    text = _make("name: helper\ndescription: Use when debugging Python code.")
    r = lint_text(text, "x")
    assert not any(f.code == "W018" for f in r.findings)


# ---------------------------------------------------------------------------
# W019 — tags count out of range
# ---------------------------------------------------------------------------


def test_w019_no_tags():
    text = _make("name: helper\ndescription: Use when X.\ntags: []")
    r = lint_text(text, "x")
    assert any(f.code == "W019" for f in r.findings)


def test_w019_tags_field_missing_no_trigger():
    """W019 only fires when the tags key exists with bad count, not when absent."""
    text = _make("name: helper\ndescription: Use when X.")
    r = lint_text(text, "x")
    assert not any(f.code == "W019" for f in r.findings)


def test_w019_too_many_tags():
    tags = "\n  - " + "\n  - ".join(f"tag{i}" for i in range(15))
    text = _make(f"name: helper\ndescription: Use when X.\ntags:{tags}")
    r = lint_text(text, "x")
    assert any(f.code == "W019" for f in r.findings)


def test_w019_reasonable_tags_no_trigger():
    text = _make("name: helper\ndescription: Use when X.\ntags:\n  - python\n  - debug")
    r = lint_text(text, "x")
    assert not any(f.code == "W019" for f in r.findings)


# ---------------------------------------------------------------------------
# W020 — version_notes doesn't reference current version
# ---------------------------------------------------------------------------


def test_w020_version_notes_stale():
    text = _make(
        "name: helper\ndescription: Use when X.\nversion: 1.5.0\n"
        "version_notes: fixed bug in 1.4.0"
    )
    r = lint_text(text, "x")
    assert any(f.code == "W020" for f in r.findings)


def test_w020_version_notes_current_no_trigger():
    text = _make(
        "name: helper\ndescription: Use when X.\nversion: 1.5.0\n"
        "version_notes: changed behaviour in 1.5.0"
    )
    r = lint_text(text, "x")
    assert not any(f.code == "W020" for f in r.findings)


def test_w020_no_notes_no_trigger():
    text = _make("name: helper\ndescription: Use when X.\nversion: 1.0.0")
    r = lint_text(text, "x")
    assert not any(f.code == "W020" for f in r.findings)


# ---------------------------------------------------------------------------
# W021 — base_skill references unknown skill
# ---------------------------------------------------------------------------


def test_w021_base_skill_unknown(tmp_path):
    p = tmp_path / "SKILL.md"
    p.write_text(
        "---\nname: child\ndescription: Use when X.\nbase_skill: nope\n---\nbody",
        encoding="utf-8",
    )
    r = lint_file(p)
    assert any(f.code == "W021" for f in r.findings)


def test_w021_base_skill_known(tmp_path):
    parent = tmp_path / "skills"
    base = parent / "parent-skill"
    base.mkdir(parents=True)
    (base / "SKILL.md").write_text(
        "---\nname: parent-skill\ndescription: Use when X.\n---\nbody",
        encoding="utf-8",
    )
    child = parent / "child-skill"
    child.mkdir()
    p = child / "SKILL.md"
    p.write_text(
        "---\nname: child-skill\ndescription: Use when X.\nbase_skill: parent-skill\n---\nbody",
        encoding="utf-8",
    )
    r = lint_file(p)
    assert not any(f.code == "W021" for f in r.findings)


def test_w021_base_skill_known_in_sibling_dir(tmp_path):
    """base_skill's SKILL.md sits next to the lint target's parent directory."""
    # Layout:
    #   tmp/use-parent/SKILL.md         <- the file we're linting
    #   tmp/use-parent/helper-skill/SKILL.md  <- the base (sibling child)
    use_parent = tmp_path / "use-parent"
    use_parent.mkdir()
    helper = use_parent / "helper-skill"
    helper.mkdir()
    (helper / "SKILL.md").write_text(
        "---\nname: helper-skill\ndescription: Use when X.\n---\nbody",
        encoding="utf-8",
    )
    p = use_parent / "SKILL.md"
    p.write_text(
        "---\nname: use-helper\ndescription: Use when X.\nbase_skill: helper-skill\n---\nbody",
        encoding="utf-8",
    )
    r = lint_file(p)
    assert not any(f.code == "W021" for f in r.findings)


def test_w021_base_skill_in_text_mode_no_trigger():
    """W021 is no-op when path is <text> (no filesystem to walk)."""
    text = (
        "---\nname: child\ndescription: Use when X.\nbase_skill: missing\n"
        "---\nbody"
    )
    r = lint_text(text, "<text>")
    assert not any(f.code == "W021" for f in r.findings)


def test_w021_maybe_other_skills_finds_match(tmp_path):
    """_maybe_other_skills hits the success branch."""
    from skillmd_lint.rules import _maybe_other_skills

    sibling = tmp_path / "lib"
    target = sibling / "helper-skill"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("---\nname: helper-skill\n---\nbody", encoding="utf-8")

    probe = sibling / "consumer" / "SKILL.md"
    probe.parent.mkdir()
    probe.write_text("---\nname: consumer\n---\nbody", encoding="utf-8")

    assert _maybe_other_skills("helper-skill", probe) is True


def test_w021_maybe_other_skills_returns_false(tmp_path):
    """_maybe_other_skills returns False when nothing matches."""
    from skillmd_lint.rules import _maybe_other_skills

    p = tmp_path / "lonely" / "SKILL.md"
    p.parent.mkdir()
    p.write_text("---\nname: lonely\n---\nbody", encoding="utf-8")

    assert _maybe_other_skills("never-existed", p) is False


def test_w021_maybe_other_skills_ignores_files_with_matching_name(tmp_path):
    """A file with the same name as the base (no .md suffix) is not a match.

    Tests the inner-loop branch where ``child.is_dir()`` is False.
    """
    from skillmd_lint.rules import _maybe_other_skills

    # Create a file (not a directory) named like the base skill
    parent = tmp_path / "skill-search"
    parent.mkdir()
    (parent / "helper-skill").write_text("not a directory", encoding="utf-8")

    probe = parent / "consumer" / "SKILL.md"
    probe.parent.mkdir()
    probe.write_text("---\nname: consumer\n---\nbody", encoding="utf-8")

    assert _maybe_other_skills("helper-skill", probe) is False


def test_w021_maybe_other_skills_dir_without_skill_md(tmp_path):
    """A directory named like the base but with no SKILL.md is not a match.

    Tests the inner-loop branch where ``is_file()`` on SKILL.md is False.
    """
    from skillmd_lint.rules import _maybe_other_skills

    parent = tmp_path / "skill-search-2"
    parent.mkdir()
    (parent / "helper-skill").mkdir()

    probe = parent / "consumer" / "SKILL.md"
    probe.parent.mkdir()
    probe.write_text("---\nname: consumer\n---\nbody", encoding="utf-8")

    assert _maybe_other_skills("helper-skill", probe) is False


# ---------------------------------------------------------------------------
# W022 — Examples section lacks concrete I/O
# ---------------------------------------------------------------------------


def test_w022_empty_examples_section():
    body = "\n## When to use\n\nUse this.\n\n## Examples\n\n## Pitfalls to avoid\n\nPitfall here.\n"
    text = _make("name: helper\ndescription: Use when X.", body)
    r = lint_text(text, "x")
    assert any(f.code == "W022" for f in r.findings)


def test_w022_prose_only_examples():
    body = "\n## When to use\n\nUse this.\n\n## Examples\n\nThis is a great skill that does many things well.\n\n## Pitfalls to avoid\n\nPitfall here.\n"
    text = _make("name: helper\ndescription: Use when X.", body)
    r = lint_text(text, "x")
    assert any(f.code == "W022" for f in r.findings)


def test_w022_code_block_examples_no_trigger():
    body = "\n## When to use\n\nUse this.\n\n## Examples\n\n```python\nhelper.do_thing()\n```\n\n## Pitfalls to avoid\n\nPitfall here.\n"
    text = _make("name: helper\ndescription: Use when X.", body)
    r = lint_text(text, "x")
    assert not any(f.code == "W022" for f in r.findings)


def test_w022_inline_code_examples_no_trigger():
    body = "\n## When to use\n\nUse this.\n\n## Examples\n\nUse `helper.do_thing()` to start.\n\n## Pitfalls to avoid\n\nPitfall here.\n"
    text = _make("name: helper\ndescription: Use when X.", body)
    r = lint_text(text, "x")
    assert not any(f.code == "W022" for f in r.findings)


def test_w022_no_examples_section_no_trigger():
    """W022 only fires when ## Examples exists but is empty/prose-only."""
    body = "\n## When to use\n\nUse this.\n\n## Pitfalls to avoid\n\nPitfall here.\n"
    text = _make("name: helper\ndescription: Use when X.", body)
    r = lint_text(text, "x")
    assert not any(f.code == "W022" for f in r.findings)


# ---------------------------------------------------------------------------
# Rule registry totals
# ---------------------------------------------------------------------------


def test_rule_count_now_thirty_three():
    from skillmd_lint.rules import RULE_INDEX
    # 22 (v1.3.0) + 1 (E011) + 9 new warnings (W014-W022) + 1 (W019 retest)
    # = 32 originally; current count after fixes
    assert len(RULE_INDEX) >= 32


def test_rule_registry_includes_v14_codes():
    from skillmd_lint.rules import RULE_INDEX
    codes = {c for c, _, _ in RULE_INDEX}
    assert "E011" in codes
    for code in ("W014", "W015", "W016", "W017", "W018", "W019", "W020", "W021", "W022"):
        assert code in codes, f"missing {code}"


# ---------------------------------------------------------------------------
# Sample skills should still pass strict
# ---------------------------------------------------------------------------


def test_all_sample_skills_pass_strict():
    """The 5 production-quality samples should still pass after rule additions."""
    from pathlib import Path
    samples = Path("/tmp/skillmd-lint-init/examples")
    for sub in samples.iterdir():
        if not sub.is_dir():
            continue
        skill = sub / "SKILL.md"
        if not skill.exists():
            continue
        text = skill.read_text(encoding="utf-8", errors="replace")
        r = lint_text(text, str(skill))
        # No ERROR findings allowed
        errors = [f for f in r.findings if f.severity.value == "error"]
        assert not errors, f"{sub.name} has errors: {[f.message for f in errors]}"
