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


# ---------------------------------------------------------------------------
# Phase 13 review CR-01/CR-02 regression: IPC handoff from cli.py:_load_config
# to the in-process pytest session's bare Config().
#
# These tests pin the "MCPTF_CONFIG_FILE as path-pointer fallback" channel
# without requiring a live MCP server or pytest.main subprocess.
# ---------------------------------------------------------------------------


def test_cr01_bare_config_picks_up_mcptf_config_file(
    tmp_path,
    monkeypatch,
) -> None:
    """Phase 13 review CR-01: a bare `Config()` (no yaml_file kwarg) must
    read MCPTF_CONFIG_FILE and load the operator's tools block.

    This is the IPC channel `cli.py:_load_config` relies on: after the
    resolver writes the resolved YAML path to the env var, `pytest.main`
    spawns an in-process session where `tests/conftest.py`,
    `fixtures.config`, and `_reporter.pytest_terminal_summary` all
    instantiate bare `Config()`. Without this channel the operator's
    `tools:` allowlist is silently dropped to the default `{}` and every
    discovered tool renders as state-(a) "not selected in config".
    """
    from mcp_test_framework.config import Config

    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(
        "version: 2\n"
        "ollama:\n"
        "  base_url: http://127.0.0.1:11434\n"
        "  model: qwen3.6:latest\n"
        "mcp_server:\n"
        "  command: uvx\n"
        "  args: [homelab-mcp]\n"
        "tools:\n"
        "  list_registered_servers:\n"
        "    skip: false\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(yaml_path))
    # Chdir to a directory WITHOUT a config.yaml so autodiscovery cannot
    # mask a broken env-var fallback.
    monkeypatch.chdir(tmp_path / "..")

    cfg = Config()  # bare -- this is what fixtures/conftest/reporter do
    assert "list_registered_servers" in cfg.tools, (
        "MCPTF_CONFIG_FILE path-pointer fallback failed: bare Config() did "
        "not load the operator's tools block. CR-01/CR-02 regression."
    )
    assert cfg.tools["list_registered_servers"].skip is False
    assert cfg.mcp_server.command == "uvx"


def test_cr01_resolver_writes_mcptf_config_file_env_var(
    tmp_path,
    monkeypatch,
) -> None:
    """Phase 13 review CR-01: `_load_config` must export the resolved
    path to MCPTF_CONFIG_FILE so the pytest-session-spawned Config()
    instances see the same source.

    Exercises the full chain: --config PATH -> _load_config -> env var
    set -> bare Config() in the same process reads it.
    """
    from pathlib import Path

    from mcp_test_framework.cli import _load_config
    from mcp_test_framework.config import Config

    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(
        "version: 2\n"
        "ollama:\n"
        "  base_url: http://127.0.0.1:11434\n"
        "  model: qwen3.6:latest\n"
        "mcp_server:\n"
        "  command: uvx\n"
        "  args: [homelab-mcp]\n"
        "tools:\n"
        "  alpha:\n"
        "    skip: false\n"
        "  beta:\n"
        "    skip: true\n"
        "    skip_reason: 'destructive'\n",
        encoding="utf-8",
    )
    # Clear any pre-existing env var to ensure the resolver writes it.
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
    monkeypatch.chdir(tmp_path)

    resolved_cfg = _load_config(Path(str(yaml_path)))
    assert resolved_cfg is not None
    # Resolver's own Config() must see the tools.
    assert set(resolved_cfg.tools.keys()) == {"alpha", "beta"}

    # The env var must now be set so the pytest-session bare Config()
    # picks up the same file. This is the state-(b) + state-(c) channel.
    import os as _os
    assert _os.environ.get("MCPTF_CONFIG_FILE") == str(yaml_path)

    # Simulate the in-process pytest session by constructing a bare
    # Config() (which is exactly what tests/conftest.py:pytest_generate_tests,
    # fixtures.config, and _reporter.pytest_terminal_summary all do).
    bare_cfg = Config()
    assert set(bare_cfg.tools.keys()) == {"alpha", "beta"}, (
        "bare Config() must inherit MCPTF_CONFIG_FILE from _load_config: "
        "CR-01/CR-02 regression."
    )
    assert bare_cfg.tools["alpha"].skip is False
    assert bare_cfg.tools["beta"].skip is True
    assert bare_cfg.tools["beta"].skip_reason == "destructive"


def test_cr02_reporter_state_c_renders_curated_skip_reason(
    tmp_path,
    monkeypatch,
) -> None:
    """Phase 13 review CR-02: after the resolver sets MCPTF_CONFIG_FILE,
    the reporter's bare `_FwConfig()` must load the operator's tools
    block so state-(c) rows render the curated skip_reason -- not the
    state-(a) "not selected in config" default.

    Exercises `_compose_unparametrized_skips` against the SAME bare
    Config() the reporter site uses (`from mcp_test_framework.config
    import Config as _FwConfig; _fw_cfg = _FwConfig()`).
    """
    from mcp_test_framework import _reporter as _rep
    from mcp_test_framework._reporter import (
        _PER_TOOL,
        _compose_unparametrized_skips,
    )
    from mcp_test_framework.config import Config as _FwConfig

    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(
        "version: 2\n"
        "ollama:\n"
        "  base_url: http://127.0.0.1:11434\n"
        "  model: qwen3.6:latest\n"
        "mcp_server:\n"
        "  command: uvx\n"
        "  args: [homelab-mcp]\n"
        "tools:\n"
        "  dangerous_tool:\n"
        "    skip: true\n"
        "    skip_reason: 'hits production registry'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(yaml_path))
    monkeypatch.chdir(tmp_path)

    _rep._DISCOVERED_TOOL_NAMES = ["dangerous_tool", "untracked_tool"]
    _PER_TOOL.clear()
    try:
        # This is EXACTLY what _reporter.pytest_terminal_summary does.
        fw_cfg = _FwConfig()
        out = _compose_unparametrized_skips(fw_cfg)
    finally:
        _rep._DISCOVERED_TOOL_NAMES = None

    # state-(c) -- operator's curated reason flows through.
    assert out["dangerous_tool"] == "hits production registry", (
        "CR-02 regression: reporter rendered state-(a) for an explicitly "
        f"skipped tool. Got: {out['dangerous_tool']!r}"
    )
    # state-(a) -- unlisted tool still renders "not selected in config".
    assert out["untracked_tool"] == "not selected in config"
