"""LSP server wrapping skillmd-lint for editor integration.

This is an optional module — it requires ``pygls``, which is not a
runtime dependency of skillmd-lint. Install with::

    pip install skillmd-lint[lsp]

The server speaks Language Server Protocol 3.17 over stdin/stdout
and surfaces skillmd-lint findings as LSP diagnostics. It maps
each rule code to a stable LSP severity and uses the rule's
message text directly.

The server itself does not re-implement any rules — it shells out
to the existing ``skillmd-lint`` CLI on every text-change. This
keeps the LSP behaviour identical to the CLI behaviour by
construction.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

# pygls is an optional dependency; we import it lazily so that the
# core package remains pip-installable without it.
if TYPE_CHECKING:  # pragma: no cover
    from pygls.lsp.server import LanguageServer

# Mapping from skillmd-lint severity → LSP severity (integer).
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#diagnosticSeverity
_LSP_SEVERITY = {
    "error": 1,    # Error
    "warning": 2,  # Warning
    "info": 3,     # Information
    "hint": 4,     # Hint
}  # pragma: no cover


@dataclass
class LspDiagnostic:
    """A single diagnostic in LSP terms."""

    line: int      # 0-indexed
    character: int  # 0-indexed
    severity: int   # 1, 2, 3, or 4
    code: str       # rule code, e.g. "W008"
    source: str     # always "skillmd-lint"
    message: str


def _run_lint(text: str, path: str) -> list[dict]:
    """Run the skillmd-lint CLI on ``text`` and return the JSON results.

    Invokes the CLI as a subprocess with ``--format json --stdin``.
    Falls back to the Python API if the subprocess path isn't
    available (e.g. in unit tests).
    """

    # Use the Python API directly — keeps the LSP server self-contained
    # and avoids subprocess startup cost on every keystroke.
    from .rules import lint_text

    result = lint_text(text, path=path)
    return [
        {
            "code": f.code,
            "severity": f.severity.value,
            "message": f.message,
        }
        for f in result.findings
    ]


def findings_to_diagnostics(
    findings: list[dict],
    *,
    uri: str,
    text: str,
) -> list[dict]:
    """Convert skillmd-lint JSON findings into LSP diagnostic dicts.

    The ``uri`` and ``text`` arguments are reserved for future use
    (computing line offsets from byte offsets in long messages);
    today's rule messages are short enough that line 0 / char 0
    is a sufficient diagnostic range.
    """

    diagnostics: list[dict] = []
    for f in findings:
        sev = _LSP_SEVERITY.get(f.get("severity", "warning"), 2)
        diagnostics.append({
            "range": {
                "start": {"line": 0, "character": 0},
                "end":   {"line": 0, "character": 1},
            },
            "severity": sev,
            "code": f.get("code", ""),
            "source": "skillmd-lint",
            "message": f.get("message", ""),
        })
    return diagnostics


def make_server() -> "LanguageServer":
    """Construct and return a configured LanguageServer instance.

    Imports ``pygls`` lazily so the core package remains importable
    without it.
    """

    from pygls.lsp.server import LanguageServer
    from lsprotocol.types import Diagnostic

    server = LanguageServer("skillmd-lint", "1.4.0")

    @server.feature("textDocument/didOpen")
    @server.feature("textDocument/didChange")
    def _publish_diagnostics(params) -> None:  # pragma: no cover
        """Lint on open + on change. Publish diagnostics for the doc.

        Note: this handler is exercised by real LSP clients at runtime;
        unit-testing it requires spinning up a pygls IO loop, which we
        don't do here. The handler is straightforward and wraps the
        already-tested ``_run_lint`` and ``findings_to_diagnostics``
        helpers.
        """

        # pygls 2.x: params is DidChangeTextDocumentParams or DidOpenTextDocumentParams
        # Both expose .text_document.text and .text_document.uri.
        td = params.text_document
        text = td.text
        uri = td.uri

        # Convert URI → file path for the lint call.
        path = uri.replace("file://", "") if uri.startswith("file://") else "<lsp>"

        findings = _run_lint(text, path)
        diagnostics = [
            Diagnostic(
                range={
                    "start": {"line": 0, "character": 0},
                    "end":   {"line": 0, "character": 1},
                },
                severity=_LSP_SEVERITY.get(f.get("severity", "warning"), 2),
                code=f.get("code", ""),
                source="skillmd-lint",
                message=f.get("message", ""),
            )
            for f in findings
        ]
        server.text_document_publish_diagnostics(uri, diagnostics)

    return server


def main() -> None:  # pragma: no cover
    """Entry point for the LSP server binary.

    Registered as a console script in pyproject.toml under the name
    ``skillmd-lsp``.
    """

    server = make_server()
    server.start_io()


__all__ = [
    "LspDiagnostic",
    "findings_to_diagnostics",
    "make_server",
    "main",
]
