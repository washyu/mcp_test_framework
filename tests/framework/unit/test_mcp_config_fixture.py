"""Regression test for the `mcp_config` session fixture's resolution order.

The fixture body resolves through two tiers (post-Phase-27):

  1. ``session.config._mcp_contracts_config`` -- the stash set by
     ``_plugin.pytest_configure`` when ``[tool.pytest.ini_options]
     mcp_config_file = PATH`` is present (library mode) OR when the CLI
     subprocesses pytest with ``-o "mcp_config_file=PATH"`` (CLI mode).
  2. Bare ``Config()`` fallback for tests that bypass the plugin.

Bug repro (pre-fix): the fixture called bare ``Config()`` unconditionally.
``settings_customise_sources`` fell back to ``MCPTF_CONFIG_FILE`` env var
which the post-Phase-27 runner no longer writes, so the YAML never loaded
and ``Config`` validation failed with ``test_code: Field required`` for
every injected contract test parametrize. Surfaced during Phase 30 UAT-1
when the operator ran ``mcp-contracts run --test-code --config config.yaml``
against a tools-populated config.

These tests use ``types.SimpleNamespace`` fakes for ``request.session.config``
so the fixture imports + executes with no live pytest session.
"""
from __future__ import annotations

import types

from mcp_test_framework.config import Config
from mcp_test_framework.fixtures import mcp_config as _mcp_config_fixture
from mcp_test_framework.models import McpServerConfig, OllamaConfig, TestCodeConfig


# Pytest forbids calling fixtures directly (PT012). Unwrap to the bare
# function body so the tests exercise the resolution logic without standing
# up a pytest session.
mcp_config = _mcp_config_fixture._get_wrapped_function()  # type: ignore[attr-defined]


def _fake_request(stashed: Config | None) -> types.SimpleNamespace:
    """Build a minimal `request` whose `.session.config._mcp_contracts_config`
    is either set to ``stashed`` or absent entirely (mirrors the plugin
    silent-no-op path)."""
    session_config = types.SimpleNamespace()
    if stashed is not None:
        session_config._mcp_contracts_config = stashed
    session = types.SimpleNamespace(config=session_config)
    return types.SimpleNamespace(session=session)


def _build_concrete_config() -> Config:
    """Construct a Config without YAML I/O for the stash-hit assertion."""
    return Config(
        ollama=OllamaConfig(),
        mcp_server=McpServerConfig(command="true", args=[]),
        test_code=TestCodeConfig(generated_root="tests/test_code/_generated"),
        tools={},
    )


def test_mcp_config_returns_stashed_config_when_plugin_set_it() -> None:
    """Tier 1: stash present -> fixture returns the stashed instance verbatim."""
    stashed = _build_concrete_config()
    request = _fake_request(stashed)

    result = mcp_config(request)

    assert result is stashed, (
        "mcp_config must return the stashed _mcp_contracts_config instance "
        "(identity check) so the contract test fixtures see the YAML the "
        "plugin already loaded -- not a fresh bare Config() that has no "
        "path source post-Phase-27."
    )


def test_mcp_config_falls_back_to_bare_config_when_no_stash(
    monkeypatch,
) -> None:
    """Tier 2: stash absent -> fixture falls back to bare Config().

    Bare Config() requires `test_code` which we provide via env-var injection
    is NOT supported (settings_customise_sources drops env_settings). The
    fallback path is only reachable when the caller provides config some
    other way -- e.g. framework self-tests that construct their own Config
    via `yaml_file=` and never hit this fixture. We assert the no-stash
    branch is exercised by stubbing Config so this test does not require
    a real YAML on disk.
    """
    request = _fake_request(stashed=None)
    sentinel = _build_concrete_config()

    def _stub_config(*args, **kwargs):  # noqa: ARG001
        return sentinel

    monkeypatch.setattr(
        "mcp_test_framework.fixtures.Config",
        _stub_config,
    )

    result = mcp_config(request)

    assert result is sentinel, (
        "mcp_config must fall back to bare Config() when no stash is present "
        "(legacy compat path for tests bypassing the plugin)."
    )
