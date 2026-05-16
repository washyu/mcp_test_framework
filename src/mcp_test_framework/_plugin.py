"""mcp_test_framework pytest plugin — entry-point target.

Registered via [project.entry-points.pytest11] in pyproject.toml so pytest
auto-discovers the framework's fixtures and hooks WITHOUT any
`pytest_plugins=[...]` declaration in the operator's conftest (PACK-01 / SC2).

Phase 26 lands the skeleton:
  - Hook signatures (`pytest_configure`, `pytest_collection_modifyitems`,
    `pytest_addoption`) are pre-declared with no-op bodies (D-10).
  - Session-scoped fixtures are re-exported from `mcp_test_framework.fixtures`
    under their renamed `mcp_*` names (D-11/D-15).
  - Six unprefixed deprecation aliases (`config`, `judge`, `target_tool`,
    `rubric_clarity`, `rubric_disambiguation`, `rubric_parameters`) are
    declared here as separate `@pytest.fixture` defs that depend on the
    prefixed fixture and emit a one-time DeprecationWarning per process
    (D-17). All six aliases drop in v1.5 (D-18).

Phase 27 (LIB-01..LIB-08) fills the hook bodies with register()-driven
behavior — contract-test injection, marker auto-application, preflight
gating. This plugin is intentionally framework-primitive: NO SUT-aware
logic, NO homelab-mcp imports, NO opinions about what tools exist
(SEED-022).

Coexistence note: `tests/conftest.py:30-55` also defines `pytest_configure`
for the framework's own `sys.modules` black-box guard. Pytest invokes both
hooks; this plugin's body is purely additive (marker registration only)
and MUST NOT remove or relocate the guard.
"""
from __future__ import annotations

import warnings

import pytest

# Re-export the renamed prefixed fixtures from fixtures.py so the pytest
# auto-discovery surfaces them without the operator needing
# `pytest_plugins=[...]` (PACK-01). Internal fixtures (`_preflight`,
# `_isolated_home`) and the function-scoped `tool_config` are re-exported
# too so the framework's own test suite continues to see them via the
# entry-point load path. The `noqa: F401` markers signal that these
# imports are intentionally side-effect-only — pytest discovers fixtures
# by attribute name on the plugin module.
from mcp_test_framework.fixtures import (  # noqa: F401
    _isolated_home,
    _preflight,
    mcp_client,
    mcp_config,
    mcp_judge,
    mcp_rubric_clarity,
    mcp_rubric_disambiguation,
    mcp_rubric_parameters,
    mcp_target_tool,
    tool_config,
)


# ---------------------------------------------------------------------------
# Hook skeletons (Phase 26 D-10): bodies are intentionally trivial.
# Phase 27 fills register()-driven behavior here without re-touching
# pyproject.toml or the entry-point declaration.
# ---------------------------------------------------------------------------

def pytest_configure(config: pytest.Config) -> None:
    """Register the `mcp_contract` marker.

    Coexists with `tests/conftest.py:pytest_configure` (the framework's own
    black-box `sys.modules` guard). Pytest invokes every loaded plugin's
    `pytest_configure`; ordering follows plugin load order. This hook is
    purely additive — adding an inivalue line is idempotent across reruns.

    Phase 27 will extend this body to invoke registration glue (LIB-04).
    """
    config.addinivalue_line(
        "markers",
        "mcp_contract: framework-injected MCP contract test (Phase 27 LIB-04).",
    )


def pytest_addoption(parser: pytest.Parser) -> None:
    """Reserve the --mcp-* CLI option namespace.

    Phase 26: no options registered yet — only the option group is created
    so Phase 27 can `getgroup("mcp_test_framework")` without duplicate-group
    warnings on first call.
    """
    parser.getgroup("mcp_test_framework", "MCP test framework options")


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Hook slot reserved for Phase 27's contract-test injection.

    Phase 26 body is intentionally empty — locking the hook surface so
    Phase 27 only adds behavior, never declarations.
    """
    # No-op in Phase 26 (D-10).


# ---------------------------------------------------------------------------
# Deprecation aliases (D-17 / Phase 25 D-05 pattern):
#
# Each unprefixed alias is a separate `@pytest.fixture` def that:
#   1. Receives the prefixed fixture as a parameter (DI; no manual lookup).
#   2. Calls `warnings.warn(DeprecationWarning, stacklevel=2)` once per
#      process per alias — the default Python warning filter dedups, so
#      a session-wide use prints exactly one warning per alias.
#   3. Returns the prefixed value unchanged (identity passthrough).
#
# Six aliases drop coherently in v1.5 (D-18) alongside every other Phase 25
# and Phase 26 deprecation shim. Hardcoded deprecation copy per call site
# (no central constant) — Phase 25 D-05.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def config(mcp_config):
    """Deprecated alias for `mcp_config` — removed in v1.5 (Phase 26 D-17)."""
    warnings.warn(
        "the `config` fixture is deprecated since v1.4 and will be removed in v1.5 — "
        "use `mcp_config` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return mcp_config


@pytest.fixture(scope="session")
def judge(mcp_judge):
    """Deprecated alias for `mcp_judge` — removed in v1.5 (Phase 26 D-17)."""
    warnings.warn(
        "the `judge` fixture is deprecated since v1.4 and will be removed in v1.5 — "
        "use `mcp_judge` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return mcp_judge


@pytest.fixture(scope="session")
def target_tool(mcp_target_tool):
    """Deprecated alias for `mcp_target_tool` — removed in v1.5 (Phase 26 D-17)."""
    warnings.warn(
        "the `target_tool` fixture is deprecated since v1.4 and will be removed in v1.5 — "
        "use `mcp_target_tool` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return mcp_target_tool


@pytest.fixture(scope="session")
def rubric_clarity(mcp_rubric_clarity):
    """Deprecated alias for `mcp_rubric_clarity` — removed in v1.5 (Phase 26 D-17)."""
    warnings.warn(
        "the `rubric_clarity` fixture is deprecated since v1.4 and will be removed in v1.5 — "
        "use `mcp_rubric_clarity` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return mcp_rubric_clarity


@pytest.fixture(scope="session")
def rubric_disambiguation(mcp_rubric_disambiguation):
    """Deprecated alias for `mcp_rubric_disambiguation` — removed in v1.5 (Phase 26 D-17)."""
    warnings.warn(
        "the `rubric_disambiguation` fixture is deprecated since v1.4 and will be removed in v1.5 — "
        "use `mcp_rubric_disambiguation` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return mcp_rubric_disambiguation


@pytest.fixture(scope="session")
def rubric_parameters(mcp_rubric_parameters):
    """Deprecated alias for `mcp_rubric_parameters` — removed in v1.5 (Phase 26 D-17)."""
    warnings.warn(
        "the `rubric_parameters` fixture is deprecated since v1.4 and will be removed in v1.5 — "
        "use `mcp_rubric_parameters` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return mcp_rubric_parameters
