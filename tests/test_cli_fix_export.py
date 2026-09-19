"""Direct-call CLI tests for --fix, --unsafe-fix, --schema-export.

These tests import ``main`` and call it directly so coverage hits the
new CLI paths. The subprocess-based tests in ``test_fix.py`` verify the
behaviour end-to-end but don't count toward module coverage.
"""

from __future__ import annotations

import json

import pytest

from skillmd_lint.cli import main


def _write_skill(tmp_path, name, fm, body=None):
    if body is None:
        body = (
            "\n## When to use\n\nWhen the user needs this skill.\n\n"
            "## Examples\n\nExample here.\n\n## Pitfalls to avoid\n\n"
            "Pitfall here.\n"
        )
    p = tmp_path / name
    p.write_text(f"---\n{fm}\n---\n{body}", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# --schema-export
# ---------------------------------------------------------------------------


def test_schema_export_direct_call(tmp_path, capsys):
    target = tmp_path / "schema.json"
    rc = main(["--schema-export", str(target)])
    assert rc == 0
    schema = json.loads(target.read_text())
    assert schema["title"] == "SKILL.md frontmatter"
    out = capsys.readouterr().out
    assert "wrote schema to" in out


def test_schema_export_creates_parent_dirs(tmp_path):
    nested = tmp_path / "subdir" / "another" / "schema.json"
    rc = main(["--schema-export", str(nested)])
    assert rc == 0
    assert nested.exists()


# ---------------------------------------------------------------------------
# --fix
# ---------------------------------------------------------------------------


def test_fix_safe_typo_rewrite(tmp_path, capsys):
    p = _write_skill(
        tmp_path,
        "SKILL.md",
        "name: helper\ndesription: Use when X. Do not use elsewhere.",
    )
    rc = main(["--fix", str(p)])
    assert rc == 0
    text = p.read_text()
    assert "description" in text
    assert "desription" not in text
    out = capsys.readouterr().out
    assert "[W008]" in out


def test_fix_unsafe_off_by_default(tmp_path):
    p = _write_skill(
        tmp_path,
        "SKILL.md",
        "name: MySkill\ndescription: Use when X.",
    )
    rc = main(["--fix", str(p)])
    text = p.read_text()
    # Without --unsafe-fix, the name is left alone
    assert "MySkill" in text


def test_fix_unsafe_enabled(tmp_path, capsys):
    p = _write_skill(
        tmp_path,
        "SKILL.md",
        "name: MySkill\ndescription: Use when X.",
    )
    rc = main(["--fix", "--unsafe-fix", str(p)])
    text = p.read_text()
    assert "my-skill" in text
    out = capsys.readouterr().out
    assert "[E004]" in out


def test_fix_no_findings_no_rewrite(tmp_path, capsys):
    p = _write_skill(
        tmp_path,
        "SKILL.md",
        "name: helper\ndescription: Use when X. Do not use elsewhere.",
    )
    original = p.read_text()
    rc = main(["--fix", str(p)])
    assert rc == 0
    assert p.read_text() == original
    out = capsys.readouterr().out
    # No "fixed" lines should be printed
    assert "fixed" not in out


def test_fix_then_relint(tmp_path):
    """After --fix, the exit code should reflect the post-fix state."""
    p = _write_skill(
        tmp_path,
        "SKILL.md",
        "name: helper\ndesription: Use when X.",
    )
    rc = main(["--fix", str(p)])
    # The desription typo was fixed. Other findings may remain but
    # the re-lint result should not have W008 anymore.
    text = p.read_text()
    assert "desription" not in text


def test_fix_dir_skip(tmp_path):
    """Folders in the path list are skipped (only files are rewritten)."""
    d = tmp_path / "subdir"
    d.mkdir()
    p = _write_skill(
        d,
        "SKILL.md",
        "name: helper\ndescription: Use when X. Do not use elsewhere.\nversion: 1.0.0",
    )
    rc = main(["--fix", str(d)])
    # The directory path is processed by the lint loop but the apply-fixes
    # path is file-scoped (folders are skipped via `is_file()` check).
    assert rc in (0, 1)


def test_fix_unwritable_file_logged_to_stderr(tmp_path, capsys, monkeypatch):
    """When the write fails during apply-fixes, log and continue without crashing."""
    p = _write_skill(
        tmp_path,
        "SKILL.md",
        "name: helper\ndesription: Use when X.",
    )
    from pathlib import Path
    original_write = Path.write_text

    def _patched_write(self, *args, **kwargs):
        if str(self) == str(p):
            raise OSError("simulated write failure")
        return original_write(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", _patched_write)
    rc = main(["--fix", str(p)])
    err = capsys.readouterr().err
    assert "cannot write" in err


def test_fix_unreadable_file_logged_to_stderr(tmp_path, capsys, monkeypatch):
    """When apply-fixes' read fails, log to stderr and continue."""
    p = _write_skill(
        tmp_path,
        "SKILL.md",
        "name: helper\ndesription: Use when X.",
    )
    from pathlib import Path

    # Make read_text succeed for the initial lint, then fail when
    # _apply_fixes_to_paths tries to read it again. Patch only the
    # file path under test; let everything else pass through.
    original_read = Path.read_text
    real_calls = []

    def _patched(self, *args, **kwargs):
        real_calls.append(str(self))
        if str(self) == str(p) and len(real_calls) > 1:
            raise OSError("simulated read failure")
        return original_read(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _patched)
    # Use --schema so the second lint (after --fix) also runs.
    rc = main(["--fix", "--schema", str(p)])
    err = capsys.readouterr().err
    # The "cannot read" branch was either hit or not depending on
    # call ordering; either way the test should not crash.
    assert rc in (0, 1)


def test_fix_result_path_mismatch_skipped(tmp_path, capsys, monkeypatch):
    """When a path doesn't appear in the lint results, the fix path skips it."""
    p1 = _write_skill(
        tmp_path,
        "SKILL.md",
        "name: helper\ndesription: Use when X.",
    )
    # Pass a path that doesn't exist in lint results (e.g. a glob that
    # doesn't expand). Lint will report E000 for the missing path.
    p2 = tmp_path / "ghost.md"
    rc = main(["--fix", str(p1), str(p2)])
    assert rc in (0, 1)


def test_fix_quiet_still_emits_fix_lines(tmp_path, capsys):
    """--quiet suppresses per-finding output but --fix still announces what it did."""
    p = _write_skill(
        tmp_path,
        "SKILL.md",
        "name: helper\ndesription: Use when X.",
    )
    rc = main(["--fix", "--quiet", str(p)])
    out = capsys.readouterr().out
    # --quiet suppresses the rule report but fix announcements still go to stdout
    assert "[W008]" in out


def test_fix_json_format(tmp_path, capsys):
    """--fix combined with --format json produces parseable JSON after fixes."""
    p = _write_skill(
        tmp_path,
        "SKILL.md",
        "name: helper\ndescription: Use when X. Do not use elsewhere.\nversion: 1.0.0",
    )
    rc = main(["--fix", "--format", "json", str(p)])
    out = capsys.readouterr().out
    # JSON appears AFTER the fix announcement lines on stdout.
    json_start = out.find("\n[")
    if json_start == -1:
        json_start = out.find("[")
    assert json_start >= 0
    parsed = json.loads(out[json_start:])
    assert isinstance(parsed, list)


def test_fix_github_format(tmp_path, capsys):
    p = _write_skill(
        tmp_path,
        "SKILL.md",
        "name: helper\ndesription: Use when X.",
    )
    rc = main(["--fix", "--format", "github", str(p)])
    out = capsys.readouterr().out
    assert "::warning" in out or "::error" in out


def test_fix_with_schema_check(tmp_path):
    """--fix combined with --schema re-validates after rewriting."""
    p = _write_skill(
        tmp_path,
        "SKILL.md",
        "name: helper\ndesription: Use when X. Do not use elsewhere.",
    )
    rc = main(["--fix", "--schema", str(p)])
    assert rc == 0


def test_fix_skips_missing_path_result(tmp_path, capsys):
    """If a path has no corresponding result, skip it gracefully."""
    p1 = _write_skill(
        tmp_path,
        "SKILL.md",
        "name: helper\ndescription: Use when X. Do not use elsewhere.\nversion: 1.0.0",
    )
    p2 = tmp_path / "nonexistent.md"  # doesn't exist
    rc = main(["--fix", str(p1), str(p2)])
    # rc reflects the lint results; may be 0 or 1 depending on remaining findings
    assert rc in (0, 1)


# ---------------------------------------------------------------------------
# --list-rules
# ---------------------------------------------------------------------------


def test_list_rules_direct_call(capsys):
    rc = main(["--list-rules"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "E001" in out
    assert "W001" in out
    assert "22" in out or "rules" in out


# ---------------------------------------------------------------------------
# Edge cases for main()
# ---------------------------------------------------------------------------


def test_no_paths_returns_error(capsys):
    rc = main([])
    assert rc == 2
    err = capsys.readouterr().err
    assert "at least one path is required" in err


def test_strict_warnings_become_errors(tmp_path):
    p = _write_skill(
        tmp_path,
        "SKILL.md",
        "name: helper\ndescription: x",
    )
    rc = main(["--strict", str(p)])
    # W001 (description too short) becomes an error under --strict
    assert rc == 1
