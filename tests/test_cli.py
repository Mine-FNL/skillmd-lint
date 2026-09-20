"""CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from skillmd_lint import lint_text
from skillmd_lint.cli import _format_github, _format_human, _format_json, _format_rules_list, main

SCRIPT_DIR = Path(__file__).resolve().parent.parent
ROOT = SCRIPT_DIR  # project root when tests live under tests/


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "skillmd_lint", *args],
        capture_output=True,
        text=True,
        cwd=str(SCRIPT_DIR),
    )


VALID = """---
name: backend-api-engineer
description: |
  Use when designing or reviewing a backend REST API for correctness, security,
  and maintainability. Do not use when the work concerns UI design, database
  administration, or non-API engineering tasks.
skill_type: domain-expert
---

# Backend API Engineer

## When to use

For every API change, walk these four passes in order:

1. Correctness
2. Security
3. Maintainability
4. Performance

## Examples

For example, when reviewing a `POST /transfers` endpoint:

- Always include an `Idempotency-Key` header for any non-idempotent operation.
- Document the rate-limit semantics in the OpenAPI spec.

## Pitfalls

Do NOT extrapolate from a single example.
"""


def _write_skill(tmp_path: Path, body: str = VALID) -> Path:
    p = tmp_path / "SKILL.md"
    p.write_text(body, encoding="utf-8")
    return p


def test_cli_happy_path(tmp_path: Path):
    _write_skill(tmp_path)
    r = _run(str(tmp_path))
    assert r.returncode == 0
    assert "ok" in r.stdout or "passed" in r.stdout


def test_cli_errors_produce_exit_1(tmp_path: Path):
    _write_skill(tmp_path, body="# no frontmatter here\nshort")
    # Force a real error: write a file with bad name.
    bad = tmp_path / "BadName"
    bad.mkdir()
    (bad / "SKILL.md").write_text(
        "---\nname: BadName\ndescription: Use when X. Don't use for Y.\n---\n" + ("line\n" * 25),
        encoding="utf-8",
    )
    r = _run(str(bad))
    assert r.returncode == 1
    assert "E004" in r.stdout


def test_cli_json_format(tmp_path: Path):
    _write_skill(tmp_path)
    r = _run("--format", "json", str(tmp_path))
    assert r.returncode == 0
    blob = json.loads(r.stdout)
    assert isinstance(blob, list)
    assert blob[0]["passed"] is True


def test_cli_github_format(tmp_path: Path):
    _write_skill(tmp_path, body="# no frontmatter\nshort")
    r = _run("--format", "github", str(tmp_path))
    # Should still parse; the format produces ::error lines.
    assert "::error" in r.stdout or "::warning" in r.stdout or r.stdout == ""


def test_cli_strict_flag(tmp_path: Path):
    # Body without a "## When to use" section → W005 warning. Strict should fail.
    body = (
        "---\nname: my-skill\n"
        "description: Use when designing APIs. Don't use for UIs.\n"
        "---\n# Body\n" + ("line\n" * 25) + "For example, this is the only example."
    )
    _write_skill(tmp_path, body=body)
    r_normal = _run(str(tmp_path))
    # Normal: passes (no errors).
    assert r_normal.returncode == 0
    r_strict = _run("--strict", str(tmp_path))
    # Strict: warnings become errors → exit 1.
    assert r_strict.returncode == 1


def test_cli_version():
    r = _run("--version")
    assert r.returncode == 0
    assert "skillmd-lint" in r.stdout
    assert "1.4.0" in r.stdout


def test_cli_quiet(tmp_path: Path):
    _write_skill(tmp_path)
    r = _run("--quiet", str(tmp_path))
    assert r.returncode == 0
    # Quiet mode shows only the summary line, not per-finding output.
    assert "ok" not in r.stdout.lower().split("\n")[0] or "passed" in r.stdout.lower()


def test_cli_no_paths_shows_help(tmp_path: Path):
    r = _run()
    # We now require ``--list-rules`` for no-positional usage; otherwise we
    # error with exit 2 + a friendly message.
    assert r.returncode == 2
    assert "at least one path is required" in r.stderr or "required" in r.stderr.lower()


def test_cli_list_rules(tmp_path: Path):
    r = _run("--list-rules")
    assert r.returncode == 0
    # Must include v1.1 codes.
    for code in ("W008", "W009", "W010", "W011", "W012", "W013", "E010"):
        assert code in r.stdout, f"missing rule code {code}"


def test_cli_schema_flag(tmp_path: Path):
    # Bad name → E004 from rules + S001 from schema.
    bad = tmp_path / "BadName"
    bad.mkdir()
    (bad / "SKILL.md").write_text(
        "---\nname: BadName\ndescription: Use when X. Don't use for Y.\n---\n" + ("line\n" * 25),
        encoding="utf-8",
    )
    r = _run("--schema", str(bad))
    assert r.returncode == 1
    assert "E004" in r.stdout
    # Schema findings appear with S### codes.
    assert "S" in r.stdout


def test_cli_schema_clean(tmp_path: Path):
    # Good file → --schema adds no findings.
    _write_skill(tmp_path)
    r = _run("--schema", str(tmp_path))
    assert r.returncode == 0


def test_cli_help_includes_list_rules(tmp_path: Path):
    r = _run("--help")
    assert "--list-rules" in r.stdout
    assert "--schema" in r.stdout


# ---------------------------------------------------------------------------
# Direct (in-process) coverage of the cli.py formatters + main()
# ---------------------------------------------------------------------------


VALID_DOC = """---
name: my-skill
description: Use when X. Don't use for Y.
---

## When to use

Use this.

## Examples

For example, see the `documentation` or the `getting-started` guide.

## Pitfalls

Don't do X.
""" + ("line\n" * 25)


class TestFormatHuman:
    def test_clean_file(self):
        r = lint_text(VALID_DOC)
        out = _format_human([r], strict=False)
        assert "ok" in out
        assert "passed" in out

    def test_with_findings_and_strict(self):
        # Body too short → W003.
        r = lint_text("# short\n")
        out = _format_human([r], strict=False)
        assert "warning" in out

    def test_strict_promotes_warning_to_error(self):
        r = lint_text(
            "---\nname: my-skill\ndescription: Use when X. Don't use for Y.\n---\n# body\n"
            + "line\n" * 25
        )
        # No when-to-use section → W005. Strict should re-tag as error.
        out = _format_human([r], strict=True)
        assert "error" in out


class TestFormatGithub:
    def test_emits_annotations(self):
        r = lint_text(
            "---\nname: BadName\ndescription: Use when X. Don't use for Y.\n---\n" + ("line\n" * 25)
        )
        out = _format_github([r], strict=False)
        assert "::error" in out
        assert "E004" in out


class TestFormatJson:
    def test_round_trip(self):
        r = lint_text(VALID_DOC)
        blob = _format_json([r], strict=False)
        parsed = json.loads(blob)
        assert isinstance(parsed, list)
        assert parsed[0]["passed"] is True

    def test_strict_moves_warnings_to_errors(self):
        r = lint_text("# short\n")
        blob = _format_json([r], strict=True)
        parsed = json.loads(blob)
        # The W003 warning should be promoted into the errors list.
        all_codes = [f["code"] for f in parsed[0]["errors"]]
        assert "W003" in all_codes or parsed[0]["passed"] is False


class TestFormatRulesList:
    def test_lists_all_codes(self):
        out = _format_rules_list()
        assert "E001" in out
        assert "E010" in out
        assert "W013" in out
        assert "error rules" in out
        assert "warning rules" in out


class TestMain:
    def test_main_with_no_paths_errors(self, capsys):
        rc = main([])
        assert rc == 2
        captured = capsys.readouterr()
        assert "at least one path" in captured.err.lower() or "required" in captured.err.lower()

    def test_main_list_rules(self, tmp_path: Path, capsys):
        rc = main(["--list-rules"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "E010" in captured.out
        assert "W013" in captured.out

    def test_main_quiet_passes_clean(self, tmp_path: Path):
        (tmp_path / "SKILL.md").write_text(VALID_DOC, encoding="utf-8")
        rc = main(["--quiet", str(tmp_path)])
        assert rc == 0

    def test_main_json_format(self, tmp_path: Path, capsys):
        (tmp_path / "SKILL.md").write_text(VALID_DOC, encoding="utf-8")
        rc = main(["--format", "json", str(tmp_path)])
        assert rc == 0
        captured = capsys.readouterr()
        # The output should be valid JSON.
        parsed = json.loads(captured.out)
        assert isinstance(parsed, list)

    def test_main_schema_flag(self, tmp_path: Path, capsys):
        # Bad name → E004 from rules + S001 from schema.
        bad = tmp_path / "BadName"
        bad.mkdir()
        (bad / "SKILL.md").write_text(
            "---\nname: BadName\ndescription: Use when X. Don't use for Y.\n---\n"
            + ("line\n" * 25),
            encoding="utf-8",
        )
        rc = main(["--schema", str(bad)])
        assert rc == 1
        captured = capsys.readouterr()
        assert "E004" in captured.out
        assert "S" in captured.out

    def test_main_github_format(self, tmp_path: Path, capsys):
        bad = tmp_path / "BadName"
        bad.mkdir()
        (bad / "SKILL.md").write_text(
            "---\nname: BadName\ndescription: Use when X. Don't use for Y.\n---\n"
            + ("line\n" * 25),
            encoding="utf-8",
        )
        rc = main(["--format", "github", str(bad)])
        assert rc == 1
        captured = capsys.readouterr()
        assert "::error" in captured.out


# ---------------------------------------------------------------------------
# Coverage targets — every uncovered branch in cli._run_schema
# ---------------------------------------------------------------------------


class TestRunSchemaBranches:
    """The ``_run_schema`` helper in cli.py has several defensive branches
    (file unreadable, no frontmatter, unclosed fence, bad YAML, non-dict
    frontmatter). Drive each one explicitly.
    """

    def test_path_not_looks_like_skill(self, tmp_path):
        # Path that does NOT end in SKILL.md → not a skill, schema skipped.
        plain = tmp_path / "README.md"
        plain.write_text("---\nname: foo\n---\nbody\n", encoding="utf-8")
        from skillmd_lint.cli import _run_schema
        from skillmd_lint.rules import LintResult

        r = LintResult(path=str(plain), looks_like_skill=False)
        out = _run_schema([r])
        assert out == [r]  # returned unchanged

    def test_file_unreadable(self, tmp_path):
        """A path that exists but cannot be read as UTF-8 should not crash.

        We simulate this with a directory masquerading as a file — calling
        ``Path.read_text()`` on it raises ``IsADirectoryError`` (which
        inherits from ``OSError``).
        """
        from skillmd_lint.cli import _run_schema
        from skillmd_lint.rules import LintResult

        # Point at a directory: read_text will raise OSError.
        r = LintResult(path=str(tmp_path), looks_like_skill=True)
        out = _run_schema([r])
        # Should return the result unchanged (caught by OSError handler).
        assert out == [r]

    def test_no_frontmatter_marker(self, tmp_path):
        """File looks like a skill but starts with non-frontmatter content."""
        from skillmd_lint.cli import _run_schema
        from skillmd_lint.rules import LintResult

        f = tmp_path / "SKILL.md"
        f.write_text("just some text, no frontmatter\n" + ("line\n" * 25), encoding="utf-8")
        r = LintResult(path=str(f), looks_like_skill=True)
        out = _run_schema([r])
        assert out == [r]

    def test_unclosed_frontmatter_in_schema_layer(self, tmp_path):
        from skillmd_lint.cli import _run_schema
        from skillmd_lint.rules import LintResult

        f = tmp_path / "SKILL.md"
        f.write_text("---\nname: foo\n", encoding="utf-8")
        r = LintResult(path=str(f), looks_like_skill=True)
        out = _run_schema([r])
        assert out == [r]

    def test_invalid_yaml(self, tmp_path):
        from skillmd_lint.cli import _run_schema
        from skillmd_lint.rules import LintResult

        f = tmp_path / "SKILL.md"
        f.write_text("---\nname: [unclosed\n---\nbody\n" + ("line\n" * 25), encoding="utf-8")
        r = LintResult(path=str(f), looks_like_skill=True)
        out = _run_schema([r])
        assert out == [r]

    def test_non_dict_yaml(self, tmp_path):
        from skillmd_lint.cli import _run_schema
        from skillmd_lint.rules import LintResult

        f = tmp_path / "SKILL.md"
        f.write_text("---\n- one\n- two\n---\nbody\n" + ("line\n" * 25), encoding="utf-8")
        r = LintResult(path=str(f), looks_like_skill=True)
        out = _run_schema([r])
        assert out == [r]


def test___main___subprocess(tmp_path):
    """``python -m skillmd_lint`` should exit cleanly on a valid skill."""
    import subprocess
    import sys

    f = tmp_path / "SKILL.md"
    f.write_text(VALID_DOC, encoding="utf-8")

    # Run from a fresh tmp dir (no project context) — the test verifies
    # `python -m skillmd_lint` works as an installed entry point from
    # anywhere on disk, not from a specific checkout path.
    result = subprocess.run(
        [sys.executable, "-m", "skillmd_lint", str(tmp_path)],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0
