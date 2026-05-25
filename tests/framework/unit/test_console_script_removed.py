"""Regression test for SHIM-08: legacy mcp-test-framework console-script
hard-rejects with operator-tone pointer at mcp-contracts."""
from __future__ import annotations

import subprocess
import sys


def test_console_script_removed() -> None:
    """SHIM-08: invoking _deprecated_script.main() exits 2 with operator-tone
    three-part text pointing at mcp-contracts. Verbatim message drift in
    either _deprecated_script.py or this test breaks the assertion."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from mcp_test_framework._deprecated_script import main; main()",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2, (
        f"expected exit 2, got {result.returncode}; "
        f"stdout={result.stdout!r}; stderr={result.stderr!r}"
    )
    # Verbatim three-part text from _deprecated_script.py.
    assert "mcp-test-framework was removed in v1.5" in result.stderr, result.stderr
    assert "mcp-contracts" in result.stderr, result.stderr
    assert "next:" in result.stderr, result.stderr
    assert "[mcp-contracts]" in result.stderr, result.stderr
    # Stdout should be empty (message routes to stderr only).
    assert result.stdout == "", (
        f"stdout should be empty (message routes to stderr); got: {result.stdout!r}"
    )
