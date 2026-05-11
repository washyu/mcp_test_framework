"""Pytest session-level configuration.

Phase 1 ships the black-box `sys.modules` guard. Phase 4 ships the
session-scoped fixtures (mcp_client, judge, target_tool, config, _preflight,
and three rubric fixtures) via `pytest_plugins` registration of
`mcp_test_framework.fixtures` -- the load-bearing one-line seam adopters add
to their own conftest to inherit the framework's fixture set (D-layout-1).
Phase 14: per-tool reporting moved OUT of an in-pytest plugin and INTO the
wrapper (src/mcp_test_framework/_runner.py). The _DISCOVERED_TOOL_NAMES
cache (imported from `mcp_test_framework._runner`) is used ONLY by
pytest_generate_tests for parametrize-time filtering (Phase 13 SAFE-01
allowlist); the wrapper has its own discovery in cli.py for header counts
and state-(a) SKIP rows.
"""

from __future__ import annotations

pytest_plugins = ["mcp_test_framework.fixtures"]

import asyncio  # noqa: E402
import sys  # noqa: E402 -- pytest_plugins must be a top-level statement

import pytest  # noqa: E402

from mcp_test_framework import _runner as _r  # noqa: E402 -- live module attribute, not a snapshot
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
# Cache lives in src/mcp_test_framework/_runner.py after the v1.1 plugin removal in Phase 14 Plan 05.
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

    The wrapper (cli.py) composes SKIP rows for states (a) and (c) at
    render time using Config.tools + its own wrapper-side discovery.
    This site never calls pytest.skip() -- filtering at parametrize
    time avoids the v1.1.1 runtime-SKIP explosion (260508-p0b).

    Single-tool focus is handled via `--config focus-<tool>.yaml`
    (Phase 12 D-03) -- there is no in-process target field anymore.
    """
    if _r._DISCOVERED_TOOL_NAMES is None:
        try:
            _r._set_discovered_tool_names(asyncio.run(_discover_tools(config)))
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
    #   (a) unlisted          -> excluded here; wrapper renders
    #                            "not selected in config" at render time.
    #   (b) listed + skip=False -> included in parametrize (this branch).
    #   (c) listed + skip=True  -> excluded here; wrapper renders
    #                            tool_cfg.skip_reason or "explicit skip in config".
    # Both (a) and (c) drop out of pytest collection -- the v1.1.1 hotfix
    # invariant (no 560 runtime-SKIPPED rows). The wrapper composes the
    # SKIP rows from Config.tools + its own wrapper-side discovery at
    # render time. Phase 14: state lives in production code (_runner module),
    # not the test tree.
    return [
        name for name in _r._DISCOVERED_TOOL_NAMES
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
