"""SAFE-01 allowlist filter + MCPTF_CONFIG_FILE IPC channel regression tests.

Covers:
  - The opt-in allowlist filter (Phase 13 SAFE-01) -- the filter logic
    that used to live in ``tests/conftest.py:_resolve_tool_names`` is now
    inlined in ``src/mcp_test_framework/_plugin.py:pytest_collection`` as
    a generator expression over ``cfg.tools.items()``. These tests pin
    the contract (skip:true excluded, empty tools means zero selection)
    against the new in-plugin filter shape rather than the deleted
    conftest helper.
  - The MCPTF_CONFIG_FILE IPC handoff (Phase 13 CR-01 / Phase 27 D-11)
    -- bare ``Config()`` must read the env var so the in-subprocess
    pytest session inherits the operator's tools allowlist when the
    legacy back-compat path is used.

The state-(a)/(c) composer + locked constants tests that previously
lived alongside these are covered by tests/test_runner_renderer.py and
tests/test_runner_parser.py respectively.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_discovery_cache():
    """Reset the legacy discovery cache so tests stay independent.

    The cache in ``mcp_test_framework._runner._DISCOVERED_TOOL_NAMES``
    is a residual seam from the v1.1 in-pytest discovery pathway. The
    Phase 27 plugin path discovers tools live inside ``pytest_collection``
    and does not consult this cache, but other framework tests still
    prime it, so the autouse reset keeps test ordering deterministic.
    """
    from mcp_test_framework import _runner as _r
    _r._DISCOVERED_TOOL_NAMES = None
    yield
    _r._DISCOVERED_TOOL_NAMES = None


# ---------------------------------------------------------------------------
# SAFE-01 allowlist filter (now inlined in _plugin.py:pytest_collection)
#
# Helper mirrors the plugin's one-liner so the contract is testable in
# isolation without spawning pytest or the MCP server. Keep this shape
# in sync with the generator expression in ``pytest_collection``:
#
#     allowed = sorted(
#         name for name, tcfg in cfg.tools.items() if not tcfg.skip
#     )
# ---------------------------------------------------------------------------


def _allowed_tools(cfg) -> list[str]:
    """Verbatim mirror of the plugin's opt-in allowlist filter."""
    return sorted(name for name, tcfg in cfg.tools.items() if not tcfg.skip)


def test_safe_01_allowlist_includes_listed_unskipped() -> None:
    """SAFE-01 state (b): listed + skip=False -> included."""
    from mcp_test_framework.models import ToolConfig

    class _FakeConfig:
        tools = {"tool_a": ToolConfig(), "tool_b": ToolConfig()}

    assert _allowed_tools(_FakeConfig()) == ["tool_a", "tool_b"]


def test_safe_01_allowlist_excludes_unlisted_and_skipped() -> None:
    """SAFE-01 states (a) and (c): unlisted + skipped both excluded.

    State (a) is enforced by the plugin's intersection step (discovered
    AND allowed); this filter alone only enforces state (c) since
    unlisted tools never appear in ``cfg.tools`` to begin with.
    """
    from mcp_test_framework.models import ToolConfig

    class _FakeConfig:
        tools = {
            "tool_a": ToolConfig(skip=True, skip_reason="dangerous"),
            # tool_b is unlisted -> state (a); not present in cfg.tools.
        }

    assert _allowed_tools(_FakeConfig()) == []


def test_safe_01_empty_tools_means_zero_selection() -> None:
    """``tools: {}`` -> every discovered tool drops out (plugin no-inject)."""

    class _FakeConfig:
        tools = {}

    assert _allowed_tools(_FakeConfig()) == []


# ---------------------------------------------------------------------------
# Phase 13 review CR-01 + Phase 27 D-11 + Phase 31 SHIM-05 D-05:
# config-source IPC channel.
#
# Pre-Phase-27 the wrapper exported the resolved YAML path to
# MCPTF_CONFIG_FILE so a pytest-session-spawned bare `Config()` would
# inherit it. Phase 27 removed the env-var WRITE; the wrapper threaded
# the resolved path via `pytest -o "mcp_config_file=PATH"` instead.
# Phase 31 SHIM-05 removes the env-var READ too: the env var is now inert
# as a value source. Bare `Config()` no longer picks up an env-pointed
# YAML; the in-subprocess plugin reads the path from the
# `mcp_config_file` ini override and constructs `Config(yaml_file=PATH)`
# explicitly.
# ---------------------------------------------------------------------------


def test_phase_31_bare_config_does_not_pick_up_mcptf_config_file(
    tmp_path,
    monkeypatch,
) -> None:
    """Phase 31 SHIM-05 D-05 inversion of legacy CR-01.

    Pre-Phase-31: bare `Config()` would consult MCPTF_CONFIG_FILE as a
    path-pointer fallback inside ``settings_customise_sources``.
    Post-Phase-31: the fallback is deleted. The env var is inert as a
    value source. Bare ``Config()`` falls through to model defaults
    regardless of what MCPTF_CONFIG_FILE points at.
    """
    from mcp_test_framework.config import Config
    from mcp_test_framework.models import TestCodeConfig

    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(
        "version: 2\n"
        "ollama:\n"
        "  base_url: http://127.0.0.1:11434\n"
        "  model: qwen3.6:latest\n"
        "mcp_server:\n"
        "  command: uvx\n"
        "  args: [homelab-mcp]\n"
        'sdet:\n  generated_root: "tests/sdet/_generated"\n'
        "tools:\n"
        "  list_registered_servers:\n"
        "    skip: false\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(yaml_path))
    # Chdir away from any config.yaml so autodiscovery cannot mask the
    # env-var fallback we expect to be GONE.
    monkeypatch.chdir(tmp_path / "..")

    # Use the test_code stub since TestCodeConfig is required.
    cfg = Config(test_code=TestCodeConfig(generated_root="tests/sdet/_generated"))
    assert "list_registered_servers" not in cfg.tools, (
        "MCPTF_CONFIG_FILE env-var fallback still wired: bare Config() "
        "leaked the env-pointed tools block (Phase 31 SHIM-05 D-05 "
        "regression)."
    )
    # Defaults survive: mcp_server.command is the model default, not uvx.
    assert cfg.mcp_server.command != "uvx"


def test_resolver_returns_resolved_path_and_does_not_write_env_var(
    tmp_path,
    monkeypatch,
) -> None:
    """Phase 27 D-11: `_load_config` returns `(Config, resolved_path)` and
    does NOT write MCPTF_CONFIG_FILE.

    Pre-Phase-27 behavior: the resolver exported MCPTF_CONFIG_FILE so a
    bare `Config()` spawned inside pytest would inherit the path. That
    write was the env-var-precedence footgun: a stale value left by an
    earlier run could silently override an explicit --config. Phase 27
    removes the write; the wrapper now threads the resolved path
    explicitly to the subprocess pytest via `-o "mcp_config_file=PATH"`
    (see _runner.run_pytest_subprocess(mcp_config_path=...)) so the
    in-subprocess plugin's pytest_configure reads it through the same
    ini key library-mode operators set in
    [tool.pytest.ini_options].

    This test pins the two new invariants:
      1. The resolver returns a 2-tuple (Config, Path).
      2. The resolver does NOT mutate os.environ["MCPTF_CONFIG_FILE"].
    """
    from pathlib import Path

    from mcp_test_framework.cli import _load_config

    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(
        "version: 2\n"
        "ollama:\n"
        "  base_url: http://127.0.0.1:11434\n"
        "  model: qwen3.6:latest\n"
        "mcp_server:\n"
        "  command: uvx\n"
        "  args: [homelab-mcp]\n"
        'sdet:\n  generated_root: "tests/sdet/_generated"\n'
        "tools:\n"
        "  alpha:\n"
        "    skip: false\n"
        "  beta:\n"
        "    skip: true\n"
        "    skip_reason: 'destructive'\n",
        encoding="utf-8",
    )
    # Clear any pre-existing env var so we can assert the resolver does NOT
    # write one (i.e., absence post-resolution = no write).
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
    monkeypatch.chdir(tmp_path)

    cfg, resolved = _load_config(Path(str(yaml_path)))
    assert cfg is not None
    # Resolver's own Config() must see the tools.
    assert set(cfg.tools.keys()) == {"alpha", "beta"}
    assert cfg.tools["alpha"].skip is False
    assert cfg.tools["beta"].skip is True
    assert cfg.tools["beta"].skip_reason == "destructive"

    # New tuple-return contract.
    assert resolved == Path(str(yaml_path))

    # The env var MUST NOT be set by the resolver. The wrapper now passes
    # the resolved path explicitly to the subprocess via `-o`; an env-var
    # write would re-introduce the precedence-ambiguity footgun this plan
    # closes.
    import os as _os
    assert _os.environ.get("MCPTF_CONFIG_FILE") is None
