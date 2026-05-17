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
# Phase 13 review CR-01 + Phase 27 D-11: config-source IPC channel.
#
# Pre-Phase-27 the wrapper exported the resolved YAML path to
# MCPTF_CONFIG_FILE so a pytest-session-spawned bare `Config()` would
# inherit it. Phase 27 removes the env-var WRITE; the wrapper now threads
# the resolved path explicitly to the subprocess via
# `pytest -o "mcp_config_file=PATH"` (see _runner.run_pytest_subprocess
# `mcp_config_path` kwarg + the in-subprocess plugin's `pytest_configure`).
# The env-var READ in `_load_config` Branch 2 stays for v1.4 back-compat
# so operators with the legacy env var exported still get their config
# picked up (with a one-time DeprecationWarning emitted by the plugin).
# ---------------------------------------------------------------------------


def test_cr01_bare_config_picks_up_mcptf_config_file(
    tmp_path,
    monkeypatch,
) -> None:
    """Phase 13 review CR-01: a bare `Config()` (no yaml_file kwarg) must
    read MCPTF_CONFIG_FILE and load the operator's tools block.

    This is the IPC channel `cli.py:_load_config` relies on: after the
    resolver writes the resolved YAML path to the env var, the in-process
    pytest session spawned by the wrapper instantiates bare `Config()`
    inside `tests/conftest.py` and `fixtures.config`. Without this channel
    the operator's `tools:` allowlist is silently dropped to the default
    `{}` and every discovered tool renders as state-(a) "not selected in
    config".
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
        'sdet:\n  generated_root: "tests/sdet/_generated"\n'
        "tools:\n"
        "  list_registered_servers:\n"
        "    skip: false\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(yaml_path))
    # Chdir to a directory WITHOUT a config.yaml so autodiscovery cannot
    # mask a broken env-var fallback.
    monkeypatch.chdir(tmp_path / "..")

    cfg = Config()  # bare -- this is what fixtures/conftest do
    assert "list_registered_servers" in cfg.tools, (
        "MCPTF_CONFIG_FILE path-pointer fallback failed: bare Config() did "
        "not load the operator's tools block. CR-01 regression."
    )
    assert cfg.tools["list_registered_servers"].skip is False
    assert cfg.mcp_server.command == "uvx"


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
