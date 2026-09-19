"""Tests for the LSP server module."""

from __future__ import annotations


def test_findings_to_diagnostics_empty():
    from skillmd_lint.lsp_server import findings_to_diagnostics

    assert findings_to_diagnostics([], uri="file:///x.md", text="") == []


def test_findings_to_diagnostics_maps_severity():
    from skillmd_lint.lsp_server import findings_to_diagnostics

    findings = [
        {"code": "W008", "severity": "warning", "message": "frontmatter typo"},
        {"code": "E004", "severity": "error", "message": "bad name"},
        {"code": "I001", "severity": "info", "message": "info"},
    ]
    diags = findings_to_diagnostics(findings, uri="file:///x.md", text="")
    # error → LSP severity 1, warning → 2, info → 3
    assert diags[0]["severity"] == 2
    assert diags[1]["severity"] == 1
    assert diags[2]["severity"] == 3
    assert all(d["source"] == "skillmd-lint" for d in diags)
    assert all(d["code"] in ("W008", "E004", "I001") for d in diags)


def test_findings_to_diagnostics_default_warning():
    from skillmd_lint.lsp_server import findings_to_diagnostics

    findings = [{"code": "X001", "severity": "unknown", "message": "x"}]
    diags = findings_to_diagnostics(findings, uri="file:///x.md", text="")
    assert diags[0]["severity"] == 2  # defaults to warning


def test_findings_to_diagnostics_range_shape():
    from skillmd_lint.lsp_server import findings_to_diagnostics

    findings = [{"code": "W001", "severity": "warning", "message": "x"}]
    diags = findings_to_diagnostics(findings, uri="file:///x.md", text="")
    assert "range" in diags[0]
    assert "start" in diags[0]["range"]
    assert "end" in diags[0]["range"]


def test_run_lint_uses_python_api():
    """The internal _run_lint helper uses lint_text, not subprocess."""
    from skillmd_lint.lsp_server import _run_lint

    text = "---\nname: BadName\ndescription: x\n---\nbody"
    findings = _run_lint(text, "<text>")
    codes = {f["code"] for f in findings}
    assert "E004" in codes  # bad name format


def test_make_server_constructs():
    """make_server returns a LanguageServer instance."""
    from skillmd_lint.lsp_server import make_server

    server = make_server()
    # The server is constructed; we don't need to start it for this test.
    assert server is not None


def test_make_server_can_be_constructed_without_crashing():
    """The pygls import + handler registration should not raise."""
    from skillmd_lint.lsp_server import make_server

    # Construct twice — exercises any import-side-effect init
    s1 = make_server()
    s2 = make_server()
    assert s1 is not None
    assert s2 is not None


def test_lsp_server_module_exports():
    """The module's __all__ is well-formed."""
    import skillmd_lint.lsp_server as mod

    for name in mod.__all__:
        assert hasattr(mod, name), f"__all__ lists {name} but it's not on the module"
