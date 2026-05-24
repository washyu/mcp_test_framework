"""Regression test for DEF-04-03-B: mcp_client fixture teardown must NOT raise.

Two tests in this file:

1. `test_mcp_client_teardown_completes_cleanly` — INNER, async, marked
   live_homelab. Exercises the full mcp_client fixture lifecycle (one
   list_tools() call) and lets the session-scoped fixture's teardown run.
   The body assertion is trivial; the REAL test is whether the fixture's
   teardown emits a `RuntimeError: Attempted to exit cancel scope...`.
   Default addopts skip it; opt in with `-m live_homelab`.

2. `test_mcp_client_teardown_no_cancel_scope_error` — OUTER, sync,
   UNMARKED. Spawns a child `pytest` subprocess targeting the inner test
   above with `-m live_homelab`, captures stdout+stderr, and asserts:
     - Output does NOT contain "Attempted to exit cancel scope" (the
       Pitfall-1 marker — 5 occurrences in 04-03-RUN.txt before the fix).
     - Child exit code is 0 (CONTEXT D-06: exit-code-zero is acceptance).
     - Returncode 2 is treated as preflight-skip (`_preflight` calls
       `pytest.exit(returncode=2)` when env is not configured).

Skipped cleanly when uvx or config.yaml are absent — running this on a
laptop without homelab-mcp / Ollama set up will not fail.

Why both halves: the inner test alone passes (it's a normal pytest test);
the outer subprocess test is the structural assertion that the FIXTURE'S
TEARDOWN didn't emit the Pitfall-1 ERROR. pytest treats teardown errors
as separate from test failures, so a `1 passed, 1 error` run still has
exit code != 0 — exactly the bug we're regressing against.

Black-box-safe: no `import homelab_mcp` anywhere (project rule, sys.modules
guard in tests/conftest.py would catch it anyway).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from mcp_test_framework.mcp_client import McpTestClient

# tests/smoke/test_mcp_client_teardown_regression.py is two levels under repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]


# Inner test: marked live_homelab so it runs only when the live env is configured
# (default `addopts` in pyproject.toml excludes live_homelab + live_ollama). The
# decorators are applied directly to the function rather than via a module-level
# `pytestmark = [...]` block because the OUTER subprocess test in this same module
# is sync/unmarked — module-level pytestmark would incorrectly mark both.
@pytest.mark.live_homelab
@pytest.mark.asyncio(loop_scope="session")
async def test_mcp_client_teardown_completes_cleanly(
    mcp_client: McpTestClient,
) -> None:
    """Exercise full mcp_client lifecycle. Teardown happens at session end.

    Body assertion is trivial; the structural assertion (no cancel-scope
    error at teardown) is verified by the OUTER subprocess test below.
    """
    tools = await mcp_client.list_tools()
    assert tools, "expected at least one tool from homelab-mcp"


# Outer test — unmarked; runs by default; skips cleanly when env not configured.
def test_mcp_client_teardown_no_cancel_scope_error() -> None:
    """DEF-04-03-B regression: child pytest run must exit 0 and have NO cancel-scope error.

    Spawns a child `pytest` subprocess invoking the inner test above with
    `-m live_homelab`, captures combined stdout+stderr, and asserts the
    Pitfall-1 marker string is absent and the exit code is 0.

    Skip semantics:
      - Skip if `uvx` is not on PATH (cannot run homelab-mcp).
      - Skip if `config.yaml` is absent at repo root (the child pytest
        needs an explicit `mcp_config_file` ini override to find it).
      - Skip if child returncode is 2 (preflight gated the run; not a
        regression — `_preflight` is the source of truth for env readiness).
    """
    if shutil.which("uvx") is None:
        pytest.skip("uvx not on PATH — cannot exercise the live MCP lifecycle")
    config_file = _REPO_ROOT / "config.yaml"
    if not config_file.exists():
        pytest.skip("config.yaml absent at repo root — skip live regression")

    # v1.5: thread the config via `-o mcp_config_file=PATH` (the same
    # IPC channel the CLI wrapper uses end-to-end).
    env = {**os.environ}
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "tests/smoke/test_mcp_client_teardown_regression.py::test_mcp_client_teardown_completes_cleanly",
            "-m", "live_homelab",
            "-x",
            "--tb=short",
            "-p", "no:cacheprovider",
            "-o", f"mcp_config_file={config_file}",
        ],
        cwd=str(_REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    output = (result.stdout or "") + (result.stderr or "")

    # Primary structural assertion — Pitfall 1 marker MUST be absent.
    assert "Attempted to exit cancel scope" not in output, (
        f"DEF-04-03-B regression: cancel-scope error in child run.\n"
        f"exit={result.returncode}\n--- output (last 2000 chars) ---\n{output[-2000:]}"
    )

    # Preflight skip path — not a regression, just env not ready.
    if result.returncode == 2:
        pytest.skip(f"child preflight skipped (returncode=2): {output[-500:]}")

    # CONTEXT D-06 acceptance: exit-code-zero, not just "tests passed".
    assert result.returncode == 0, (
        f"child pytest exited {result.returncode} (expected 0).\n"
        f"--- output (last 2000 chars) ---\n{output[-2000:]}"
    )
