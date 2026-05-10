"""Phase 13 SAFE-01 reporter regression tests (unit-only).

These tests pin the opt-in allowlist semantics in `tests/conftest.py:_resolve_tool_names`
and the state-a/state-c skip-row composition in `src/mcp_test_framework/_reporter.py`.

Decisions cited (from .planning/phases/13-config-safety-opt-in-tool-selection/13-CONTEXT.md):
  - D-12: two distinct reason strings, module-level constants in _reporter.py
  - D-13: empty/unset `tools:` -> zero selection (every discovered tool renders as state (a))

Why a separate file under tests/unit/: the existing reporter tests live at
``tests/test_reporter.py`` which would trigger the session-level _preflight
gate (Ollama + MCP server reachability). Phase 13 tests are pure-data and
must run on any developer's box without a live homelab-mcp.

The new tests live HERE (tests/unit/test_reporter.py) so they skip preflight
via fixtures._session_needs_preflight (which short-circuits when every
collected test is under tests/unit/).
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Task 1: allowlist filter in tests/conftest.py:_resolve_tool_names
# ---------------------------------------------------------------------------


def test_safe_01_allowlist_includes_listed_unskipped() -> None:
    """Phase 13 SAFE-01 state (b): listed + skip=False -> included."""
    from mcp_test_framework.models import ToolConfig
    from tests.conftest import _resolve_tool_names

    class _FakeConfig:
        class _Tgt:
            tool_name = None
        target = _Tgt()
        tools = {"tool_a": ToolConfig(), "tool_b": ToolConfig()}
        mcp_server = None  # not reached because _DISCOVERED_TOOL_NAMES is primed

    from mcp_test_framework import _reporter as _rep
    _rep._DISCOVERED_TOOL_NAMES = ["tool_a", "tool_b", "tool_c"]
    try:
        assert _resolve_tool_names(_FakeConfig()) == ["tool_a", "tool_b"]
    finally:
        _rep._DISCOVERED_TOOL_NAMES = None


def test_safe_01_allowlist_excludes_unlisted_and_skipped() -> None:
    """Phase 13 SAFE-01 states (a) and (c): unlisted + skipped both excluded."""
    from mcp_test_framework.models import ToolConfig
    from tests.conftest import _resolve_tool_names

    class _FakeConfig:
        class _Tgt:
            tool_name = None
        target = _Tgt()
        tools = {
            "tool_a": ToolConfig(skip=True, skip_reason="dangerous"),
            # tool_b is unlisted -> state (a) -> excluded
        }

    from mcp_test_framework import _reporter as _rep
    _rep._DISCOVERED_TOOL_NAMES = ["tool_a", "tool_b"]
    try:
        assert _resolve_tool_names(_FakeConfig()) == []
    finally:
        _rep._DISCOVERED_TOOL_NAMES = None


def test_safe_01_empty_tools_means_zero_selection() -> None:
    """Phase 13 D-13: tools: {} -> every discovered tool drops out."""
    from tests.conftest import _resolve_tool_names

    class _FakeConfig:
        class _Tgt:
            tool_name = None
        target = _Tgt()
        tools = {}

    from mcp_test_framework import _reporter as _rep
    _rep._DISCOVERED_TOOL_NAMES = ["x", "y", "z"]
    try:
        assert _resolve_tool_names(_FakeConfig()) == []
    finally:
        _rep._DISCOVERED_TOOL_NAMES = None


# ---------------------------------------------------------------------------
# Task 2: reporter composition of state-a/state-c SKIP rows
# ---------------------------------------------------------------------------


def test_safe_01_reporter_constants_locked() -> None:
    """Phase 13 D-12: the two reason strings cannot drift silently."""
    from mcp_test_framework._reporter import (
        _REASON_EXPLICIT_DEFAULT,
        _REASON_NOT_SELECTED,
    )
    assert _REASON_NOT_SELECTED == "not selected in config"
    assert _REASON_EXPLICIT_DEFAULT == "explicit skip in config"


def test_safe_01_compose_state_a_for_unlisted_tool() -> None:
    """Phase 13 D-12 state (a): unlisted discovered tool -> not selected."""
    from mcp_test_framework import _reporter as _rep
    from mcp_test_framework._reporter import (
        _PER_TOOL,
        _compose_unparametrized_skips,
    )
    _rep._DISCOVERED_TOOL_NAMES = ["tool_a", "tool_b"]
    _PER_TOOL.clear()  # parametrize ran nothing.
    class _Cfg:
        tools: dict = {}
    try:
        out = _compose_unparametrized_skips(_Cfg())
    finally:
        _rep._DISCOVERED_TOOL_NAMES = None
    assert out == {
        "tool_a": "not selected in config",
        "tool_b": "not selected in config",
    }


def test_safe_01_compose_state_c_with_curated_reason() -> None:
    """Phase 13 D-12 state (c) with non-empty skip_reason -> echoed."""
    from mcp_test_framework import _reporter as _rep
    from mcp_test_framework._reporter import (
        _PER_TOOL,
        _compose_unparametrized_skips,
    )
    from mcp_test_framework.models import ToolConfig
    _rep._DISCOVERED_TOOL_NAMES = ["dangerous_tool"]
    _PER_TOOL.clear()

    class _Cfg:
        tools = {"dangerous_tool": ToolConfig(skip=True, skip_reason="hits prod")}

    try:
        out = _compose_unparametrized_skips(_Cfg())
    finally:
        _rep._DISCOVERED_TOOL_NAMES = None
    assert out == {"dangerous_tool": "hits prod"}


def test_safe_01_compose_state_c_default_when_skip_reason_empty() -> None:
    """Phase 13 D-12 state (c) fallback: empty skip_reason -> default.

    ToolConfig's model_validator forbids skip=True + empty skip_reason at
    construction time (TOOLCFG-07). The "legal-but-unhelpful empty" case
    happens when YAML-loaded reason is whitespace that ToolConfig's
    validator would reject; we construct via model_construct() to bypass
    the validator and simulate that edge.
    """
    from mcp_test_framework import _reporter as _rep
    from mcp_test_framework._reporter import (
        _PER_TOOL,
        _REASON_EXPLICIT_DEFAULT,
        _compose_unparametrized_skips,
    )
    from mcp_test_framework.models import ToolConfig
    _rep._DISCOVERED_TOOL_NAMES = ["x"]
    _PER_TOOL.clear()
    tcfg = ToolConfig.model_construct(skip=True, skip_reason="   ")

    class _Cfg:
        tools = {"x": tcfg}

    try:
        out = _compose_unparametrized_skips(_Cfg())
    finally:
        _rep._DISCOVERED_TOOL_NAMES = None
    assert out == {"x": _REASON_EXPLICIT_DEFAULT}


def test_safe_01_compose_no_op_when_discovery_never_ran() -> None:
    """Phase 13 D-12: returns {} when _DISCOVERED_TOOL_NAMES is None.

    Pure-unit-test runs never trigger pytest_generate_tests and the cache
    stays None. The composition step must be a no-op in that case so the
    terminal-summary path doesn't crash.
    """
    from mcp_test_framework import _reporter as _rep
    from mcp_test_framework._reporter import (
        _PER_TOOL,
        _compose_unparametrized_skips,
    )
    _rep._DISCOVERED_TOOL_NAMES = None
    _PER_TOOL.clear()

    class _Cfg:
        tools = {"x": object()}

    assert _compose_unparametrized_skips(_Cfg()) == {}
