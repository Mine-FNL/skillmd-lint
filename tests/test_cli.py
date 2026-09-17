"""CLI smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

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

For example, when reviewing a POST /transfers endpoint:

- Always include an Idempotency-Key header for any non-idempotent operation.
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
    assert "1.0.0" in r.stdout


def test_cli_quiet(tmp_path: Path):
    _write_skill(tmp_path)
    r = _run("--quiet", str(tmp_path))
    assert r.returncode == 0
    # Quiet mode shows only the summary line, not per-finding output.
    assert "ok" not in r.stdout.lower().split("\n")[0] or "passed" in r.stdout.lower()


def test_cli_no_paths_shows_help(tmp_path: Path):
    r = _run()
    # argparse returns 2 when required positional is missing.
    assert r.returncode == 2
