"""Pytest session-level configuration.

Phase 1 ships the black-box `sys.modules` guard. Phase 4 ships the
session-scoped fixtures (mcp_client, judge, target_tool, config, _preflight,
and three rubric fixtures) via `pytest_plugins` registration of
`mcp_test_framework.fixtures` -- the load-bearing one-line seam adopters add
to their own conftest to inherit the framework's fixture set (D-layout-1).
"""

from __future__ import annotations

pytest_plugins = ["mcp_test_framework.fixtures"]

import sys  # noqa: E402 -- pytest_plugins must be a top-level statement


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
