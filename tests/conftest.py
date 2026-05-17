"""No fixture-loading ceremony required.

Phase 27 D-17: the framework's pytest plugin (loaded via
``[project.entry-points.pytest11]``) owns ALL contract-test
parametrization, marker application, black-box guard, and config
loading. The operator's ``tests/conftest.py`` mirror is zero-ceremony --
this file is the framework's own demonstration of the same.

Historical context (deleted Phase 27 Plan 05):
  - The legacy module-level plugin-registration list pointed pytest at
    ``mcp_test_framework.fixtures``; that registration is now picked up
    automatically via the pytest11 entry point declared in
    ``pyproject.toml``.
  - The session-level ``sys.modules`` black-box guard was relocated to
    ``src/mcp_test_framework/_black_box_guard.py`` and is invoked from
    the framework plugin's session-configure hook.
  - The ``_discover_tools`` / ``_resolve_tool_names`` helpers were
    relocated to ``src/mcp_test_framework/_plugin.py:_discover_tools_live``
    plus the inline opt-in allowlist filter in the plugin's session-
    collection hook.
  - The indirect parametrize hook on ``target_tool`` was replaced by the
    plugin's own per-metafunc generator gated on the synthetic-module
    sentinel.
"""
