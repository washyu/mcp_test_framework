"""Pytest session-level configuration.

Phase 1 ships the black-box `sys.modules` guard. Phase 4 ships the
session-scoped fixtures (mcp_client, judge, target_tool, config, _preflight,
and three rubric fixtures) via `pytest_plugins` registration of
`mcp_test_framework.fixtures` -- the load-bearing one-line seam adopters add
to their own conftest to inherit the framework's fixture set (D-layout-1).
Phase 9 ships the per-tool summary reporter (OUTPUT-03) as a sibling
plugin (``mcp_test_framework._reporter``) registered alongside ``fixtures``
in the same ``pytest_plugins`` seam.
"""

from __future__ import annotations

pytest_plugins = ["mcp_test_framework.fixtures", "mcp_test_framework._reporter"]

import asyncio  # noqa: E402
import sys  # noqa: E402 -- pytest_plugins must be a top-level statement

import pytest  # noqa: E402

from mcp_test_framework import _reporter as _rep  # noqa: E402
from mcp_test_framework.config import Config  # noqa: E402
from mcp_test_framework.mcp_client import McpTestClient  # noqa: E402


def pytest_configure(config) -> None:
    """Fail-fast if anything importable from homelab_mcp leaks into the test process.

    Belt-and-suspenders for ruff TID251 (which does not recursively cover
    submodule imports -- see 01-RESEARCH Pitfall 4 + the comment block in
    pyproject.toml above the [tool.ruff.lint.flake8-tidy-imports.banned-api]
    table).

    The lint rule catches `import homelab_mcp` and `from homelab_mcp import X`
    at static-analysis time, but it does NOT catch `from homelab_mcp.client
    import X` (ruff issue #1614). This runtime check closes that gap by
    inspecting sys.modules at the start of the test session: if anyone
    successfully imported a submodule of homelab_mcp before pytest_configure
    fires, we abort the session with a loud RuntimeError.
    """
    leaked = [
        name
        for name in sys.modules
        if name == "homelab_mcp" or name.startswith("homelab_mcp.")
    ]
    if leaked:
        raise RuntimeError(
            f"Black-box rule violated: homelab_mcp modules in sys.modules "
            f"at test start: {leaked}. The framework must drive homelab-mcp "
            f"via stdio_client only -- never import."
        )


# ---------------------------------------------------------------------------
# Phase 07 -- Tool discovery hook (pytest_generate_tests)
#
# Third spawn site (after _preflight in fixtures.py and mcp_client._owner_task).
# This site MUST NOT open-code stdio_client(...) -- McpTestClient.__aenter__ is
# already isolation-aware as of Phase 06 D-16 (it builds its own per-instance
# tempdir + _build_isolated_env env block). Re-using __aenter__ inherits the
# isolation contract for free; ISOL-03 hash-equality test in tests/test_isolation.py
# remains the regression guard.
#
# Cache lives on the _reporter module (Phase 13 revision iteration 1):
#   - tests/conftest.py is the WRITER of _reporter._DISCOVERED_TOOL_NAMES
#   - _reporter._compose_unparametrized_skips is the READER at terminal-summary
# Single-direction dependency: production exports state, tests read. The
# reporter never imports from tests/, pre-empting Phase 15's tests/contract
# vs tests/framework split.
# ---------------------------------------------------------------------------


async def _discover_tools(config: Config) -> list[str]:
    """Brief MCP handshake -> list_tools -> tool names. Mirrors fixtures.py:142-148.

    Reuses McpTestClient.__aenter__ (Phase 06 D-16) so the spawned subprocess
    receives _build_isolated_env(<per-instance tempdir>) -- Phase 06 ISOL-02/04/07
    contract preserved at this third spawn site (Phase 07 D-11).
    """
    async with McpTestClient(
        config.mcp_server.command,
        config.mcp_server.args,
        config.mcp_server.timeout_seconds,
    ) as client:
        tools = await client.list_tools()
    return [t.name for t in tools]


def _resolve_tool_names(config: Config) -> list[str]:
    """Resolve the parametrize tool-name list under SAFE-01 opt-in semantics.

    States:
      (a) discovered but unlisted in config.tools         -> excluded
      (b) listed with skip=False                          -> included
      (c) listed with skip=True                           -> excluded

    The reporter composes SKIP rows for states (a) and (c) at
    terminal-summary time using Config.tools + _DISCOVERED_TOOL_NAMES.
    This site never calls pytest.skip() -- filtering at parametrize
    time avoids the v1.1.1 runtime-SKIP explosion (260508-p0b).

    Single-tool focus continues to live in the explicit-target
    short-circuit below (config.target.tool_name); Plan 13-04 of
    Phase 13 removes that field and the short-circuit together.
    """
    explicit = config.target.tool_name
    if explicit:
        return [explicit]
    if _rep._DISCOVERED_TOOL_NAMES is None:
        try:
            _rep._DISCOVERED_TOOL_NAMES = asyncio.run(_discover_tools(config))
        except Exception as exc:  # noqa: BLE001 -- mirrors _preflight failure-mode parity
            # Match _preflight failure shape (fixtures.py:149-154) for exit-code parity.
            # See 07-RESEARCH §Pitfall 5.
            msg = (
                f"Tool discovery via {config.mcp_server.command!r} failed: "
                f"{exc.__class__.__name__}: {exc}"
            )
            # Quick-task 260507-j6i: enrich the cryptic "MCP server command not
            # on PATH" FileNotFoundError with a hint pointing users at
            # MCPTF_CONFIG_FILE / config.example.yaml. Keep in sync with
            # src/mcp_test_framework/fixtures.py:_preflight (same hint string).
            if isinstance(exc, FileNotFoundError) and str(exc).startswith(
                "MCP server command not on PATH:"
            ):
                msg += (
                    f"\n\nHint: {config.mcp_server.command!r} was not found on PATH. "
                    "If you intended to use a different command, point "
                    "MCPTF_CONFIG_FILE at a config.yaml that defines "
                    "mcp_server.command (e.g. `command: uvx, args: [homelab-mcp]`). "
                    "The repo ships `config.example.yaml` you can copy and edit."
                )
            pytest.exit(msg, returncode=2)
    # Phase 13 D-13 / SAFE-01: opt-in allowlist semantics. Three states:
    #   (a) unlisted          -> excluded here; reporter renders
    #                            "not selected in config" at terminal summary.
    #   (b) listed + skip=False -> included in parametrize (this branch).
    #   (c) listed + skip=True  -> excluded here; reporter renders
    #                            tool_cfg.skip_reason or "explicit skip in config".
    # Both (a) and (c) drop out of pytest collection -- the v1.1.1 hotfix
    # invariant (no 560 runtime-SKIPPED rows). The reporter composes the
    # SKIP rows from Config.tools + _reporter._DISCOVERED_TOOL_NAMES at
    # terminal-summary time. Revision iteration 1: state lives in
    # production (_reporter), not the test tree.
    return [
        name for name in _rep._DISCOVERED_TOOL_NAMES
        if name in config.tools and not config.tools[name].skip
    ]


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Inject indirect parametrize on `target_tool` for tests that request it.

    Discovery happens lazily -- first test function that needs target_tool
    triggers the (cached) one-shot subprocess spawn. McpTestClient.__aenter__
    uses _build_isolated_env (Phase 06 D-16) so this spawn cannot leak state
    to ~/.homelab_mcp/ (ISOL-03 contract preserved).
    """
    if "target_tool" not in metafunc.fixturenames:
        return
    config = Config()
    names = _resolve_tool_names(config)
    metafunc.parametrize("target_tool", names, indirect=True, ids=names)
