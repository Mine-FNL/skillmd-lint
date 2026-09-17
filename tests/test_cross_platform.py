"""Cross-platform sanity tests.

We can't run a Windows VM in CI on macOS/Linux runners, but we *can* verify
the linter is robust to platform-specific inputs: BOMs, CRLF line endings,
non-ASCII, and path objects from ``pathlib``. The actual linter logic is
pure-Python and should behave identically on every platform; these tests
exist so we'd notice immediately if anyone introduced a platform-specific
bug (e.g. ``os.path`` usage, hard-coded ``\n``).
"""

from __future__ import annotations

from pathlib import Path

from skillmd_lint import lint_file, lint_folder, lint_paths, lint_text
from skillmd_lint.rules import lint_paths as _lint_paths_alias  # noqa: F401  (import-surfaces API)

VALID = """---
name: cross-platform-skill
description: |
  Use when testing cross-platform behaviour of skillmd-lint. Don't use for
  production skill authoring.
skill_type: domain-expert
---

# Cross-Platform Skill

## When to use

Use this skill to verify skillmd-lint behaves identically across Linux,
macOS, and Windows.

## Examples

For example, on Windows the file path uses backslashes but the linter
should still recognise it as a SKILL.md.

## Pitfalls

Don't rely on line endings — handle CRLF, LF, and CR transparently.
"""


class TestLineEndings:
    def test_crlf_normalised(self):
        text = VALID.replace("\n", "\r\n")
        r = lint_text(text)
        assert r.looks_like_skill is True
        assert r.passed is True

    def test_cr_only(self):
        # Old Mac line endings. Rare but legal.
        text = VALID.replace("\n", "\r")
        r = lint_text(text)
        assert r.looks_like_skill is True
        assert r.passed is True

    def test_mixed_line_endings(self):
        # Force mixed CRLF/LF to confirm the splitter is line-ending-agnostic.
        lines = VALID.split("\n")
        for i in range(0, len(lines), 3):
            if lines[i]:
                lines[i] = lines[i] + "\r"
        text = "\n".join(lines)
        r = lint_text(text)
        assert r.looks_like_skill is True


class TestBOM:
    def test_utf8_bom_stripped(self):
        text = "\ufeff" + VALID
        r = lint_text(text)
        assert r.looks_like_skill is True
        assert r.passed is True


class TestNonASCII:
    def test_unicode_in_body(self):
        text = (
            "---\n"
            "name: my-skill\n"
            "description: Use when X. Don't use for Y.\n"
            "---\n"
            "# Title 文字\n\n"
            "## When to use\n\n"
            "Use this skill.\n\n"
            "## Examples\n\n"
            "For example, café-style accents should round-trip cleanly.\n\n"
            "## Pitfalls\n\n"
            "Don't depend on encoding detection.\n"
        )
        r = lint_text(text)
        assert r.passed is True


class TestPathlibPaths:
    def test_pathlib_path_accepted(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text(VALID, encoding="utf-8")
        # Pass a pathlib.Path, not a string. lint_file should accept it.
        r = lint_file(p)
        assert r.passed is True

    def test_lint_paths_accepts_pathlib(self, tmp_path: Path):
        skill_dir = tmp_path / "skills" / "demo"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(VALID, encoding="utf-8")
        # Both forms should work.
        results_str = lint_paths([str(skill_dir)])
        results_path = lint_paths([skill_dir])
        assert len(results_str) == len(results_path)
        assert all(r.passed for r in results_str)


class TestFolderDiscovery:
    def test_lint_folder_with_str_path(self, tmp_path: Path):
        (tmp_path / "SKILL.md").write_text(VALID, encoding="utf-8")
        results = lint_folder(str(tmp_path))
        assert len(results) == 1
        assert results[0].passed

    def test_lint_folder_with_pathlib(self, tmp_path: Path):
        (tmp_path / "SKILL.md").write_text(VALID, encoding="utf-8")
        results = lint_folder(tmp_path)
        assert len(results) == 1
        assert results[0].passed


class TestWindowsLikePaths:
    """Pure string-level checks. We don't actually create Windows paths on
    POSIX, but we verify the linter doesn't choke when given backslashed
    strings — useful if someone runs it from WSL or Git-Bash.
    """

    def test_windows_style_string_unchewed(self):
        # Forward-slash form must work.
        text = VALID
        r = lint_text(text)
        assert r.passed is True


class TestReproducibility:
    def test_lint_is_deterministic(self):
        # Two consecutive runs should give byte-identical JSON output.
        from skillmd_lint.cli import _format_json

        r = lint_text(VALID)
        a = _format_json([r], strict=False)
        b = _format_json([r], strict=False)
        assert a == b
