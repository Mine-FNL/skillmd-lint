"""End-to-end smoke test for the LSP server.

This test starts the actual ``skillmd_lint.lsp_server`` module as a
subprocess and exchanges real LSP JSON-RPC messages over stdin/stdout.
The point is to catch install-side bugs that the helper-function tests
in :mod:`test_lsp_server` cannot detect — most notably, a venv where
``pygls`` is missing would make the server crash on first message.

The test is skipped automatically when ``pygls`` is not installed in
the current environment (e.g. when ``pip install skillmd-lint[lsp]``
has not been run). CI installs ``.[dev]`` + ``.[lsp]`` so the test
runs by default; if you forget the ``[lsp]`` extra, this test is
the canary that fails first.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time

import pytest

# pygls is the LSP runtime; not a hard dep of skillmd-lint itself.
pygls = pytest.importorskip(
    "pygls", reason="pygls not installed (run `pip install skillmd-lint[lsp]`)"
)

INITIALIZE_REQUEST = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "processId": None,
        "rootUri": None,
        "capabilities": {},
    },
}

INITIALIZED_NOTIFICATION = {
    "jsonrpc": "2.0",
    "method": "initialized",
    "params": {},
}


def _encode_lsp_message(payload: dict) -> bytes:
    body = json.dumps(payload).encode("utf-8")
    return b"Content-Length: %d\r\n\r\n%s" % (len(body), body)


def _read_lsp_message(stream, deadline: float) -> dict | None:
    """Read one LSP message from ``stream`` before ``deadline``.

    Returns the parsed JSON payload, or ``None`` if EOF/deadline.
    """
    # Read headers
    buf = b""
    while b"\r\n\r\n" not in buf:
        if time.time() > deadline:
            return None
        chunk = stream.read(1)
        if not chunk:
            return None
        buf += chunk
    headers, body_start = buf.split(b"\r\n\r\n", 1)
    cl = 0
    for line in headers.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            cl = int(line.split(b":", 1)[1].strip())
    body = body_start
    while len(body) < cl:
        if time.time() > deadline:
            return None
        chunk = stream.read(cl - len(body))
        if not chunk:
            return None
        body += chunk
    return json.loads(body)


def _spawn_server() -> subprocess.Popen:
    """Spawn the LSP server module as a subprocess.

    Uses ``python -m`` so the test works regardless of whether
    ``skillmd-lsp`` is on PATH (e.g. in a fresh venv where it isn't
    installed yet).
    """
    return subprocess.Popen(
        [sys.executable, "-m", "skillmd_lint.lsp_server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )


def test_lsp_server_initializes_and_responds():
    """Start the LSP server, send initialize, get a server-capabilities response."""
    proc = _spawn_server()
    try:
        # Send initialize
        proc.stdin.write(_encode_lsp_message(INITIALIZE_REQUEST))
        proc.stdin.flush()

        # Read the initialize response (within 5s)
        deadline = time.time() + 5.0
        resp = _read_lsp_message(proc.stdout, deadline)
        assert resp is not None, "LSP server did not respond to initialize within 5s"

        # Validate shape
        assert resp.get("jsonrpc") == "2.0", f"not a JSON-RPC 2.0 response: {resp}"
        assert resp.get("id") == 1, f"response id mismatch: {resp}"
        assert "result" in resp, f"initialize response missing 'result': {resp}"
        result = resp["result"]
        assert "capabilities" in result, f"initialize result missing capabilities: {result}"
        # serverInfo should identify us (pygls fills this from LanguageServer("skillmd-lint", ...))
        server_info = result.get("serverInfo", {})
        assert server_info.get("name") == "skillmd-lint", (
            f"unexpected serverInfo.name: {server_info!r}"
        )
    finally:
        try:
            proc.stdin.write(
    _encode_lsp_message({"jsonrpc": "2.0", "id": 99, "method": "shutdown"})
)
            proc.stdin.flush()
            proc.stdin.write(_encode_lsp_message({"jsonrpc": "2.0", "method": "exit"}))
            proc.stdin.flush()
        except Exception:
            pass
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_lsp_server_does_not_crash_on_malformed_json():
    """Sending an invalid JSON-RPC message must not crash the server.

    LSP clients occasionally send partial frames during reconnect.
    The server should log + continue, not die.
    """
    proc = _spawn_server()
    try:
        # Send garbage that's NOT a valid JSON-RPC frame
        proc.stdin.write(b"this is not a valid LSP frame\r\n\r\n")
        proc.stdin.flush()

        # Now send a valid initialize; it must still work
        proc.stdin.write(_encode_lsp_message(INITIALIZE_REQUEST))
        proc.stdin.flush()

        deadline = time.time() + 5.0
        resp = _read_lsp_message(proc.stdout, deadline)
        assert resp is not None, "server crashed after malformed frame"
        assert resp.get("id") == 1, f"did not get initialize response: {resp}"
    finally:
        try:
            proc.stdin.write(
    _encode_lsp_message({"jsonrpc": "2.0", "id": 99, "method": "shutdown"})
)
            proc.stdin.flush()
            proc.stdin.write(_encode_lsp_message({"jsonrpc": "2.0", "method": "exit"}))
            proc.stdin.flush()
        except Exception:
            pass
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_lsp_server_handles_partial_headers():
    """Sending headers split across writes must not break the server.

    Real LSP clients do this when streaming; the server must reassemble.
    """
    proc = _spawn_server()
    try:
        body = json.dumps(INITIALIZE_REQUEST).encode("utf-8")
        # Write header in two halves
        proc.stdin.write(b"Content-Length: %d\r\n" % len(body))
        proc.stdin.write(b"\r\n")
        proc.stdin.flush()
        proc.stdin.write(body)
        proc.stdin.flush()

        deadline = time.time() + 5.0
        resp = _read_lsp_message(proc.stdout, deadline)
        assert resp is not None, "server could not reassemble split headers"
        assert resp.get("id") == 1, f"unexpected response: {resp}"
    finally:
        try:
            proc.stdin.write(
    _encode_lsp_message({"jsonrpc": "2.0", "id": 99, "method": "shutdown"})
)
            proc.stdin.flush()
            proc.stdin.write(_encode_lsp_message({"jsonrpc": "2.0", "method": "exit"}))
            proc.stdin.flush()
        except Exception:
            pass
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
