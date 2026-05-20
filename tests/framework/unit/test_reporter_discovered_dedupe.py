"""Regression test for `pytest_collection_finish` discovered_tools dedupe.

Bug repro (pre-fix): the reporter built `discovered_tools` by iterating
`session.items` and extracting `[<tool>]` parametrize suffixes without
deduping. Each contract test parametrizes over the SAME tool list, so a
50-tool config with 10 contract tests produced a 500-entry list with
each tool name repeated 10 times. The `Discovered: N tools` banner
showed the inflated count and downstream `running` / `skipping` math
iterated duplicates too.

Surfaced during Phase 30 UAT-1 when the operator saw "500 tools" in
the reporter banner against ~50 actual server tools.

This test does NOT drive a subprocess pytest -- it builds a fake
`session` with duplicate-tool nodeids and invokes
`_reporter.pytest_collection_finish` directly, then asserts that the
`_STATE.ctx.discovered_tools` it caches has every tool exactly once.
"""
from __future__ import annotations

import types

import mcp_test_framework._reporter as reporter
from mcp_test_framework.config import Config
from mcp_test_framework.models import McpServerConfig, OllamaConfig, TestCodeConfig


def _build_config_with_tools(tool_names: list[str]) -> Config:
    """Minimal Config with `tools` populated so the reporter scope-gate
    `has_contract_shape_items` accepts the fake items below."""
    from mcp_test_framework.models import ToolConfig

    return Config(
        ollama=OllamaConfig(),
        mcp_server=McpServerConfig(command="true", args=[]),
        test_code=TestCodeConfig(generated_root="tests/test_code/_generated"),
        tools={name: ToolConfig() for name in tool_names},
    )


def _fake_item(nodeid: str) -> types.SimpleNamespace:
    """Minimal pytest.Item stand-in: only `nodeid` is read by the reporter
    on this path."""
    return types.SimpleNamespace(nodeid=nodeid)


def _fake_session(cfg: Config, items: list[types.SimpleNamespace]) -> types.SimpleNamespace:
    """Build a session whose `config._mcp_contracts_config` is the plugin
    stash and whose `items` are the parametrize-shaped fakes."""
    session_config = types.SimpleNamespace(
        _mcp_contracts_config=cfg,
    )
    return types.SimpleNamespace(config=session_config, items=items)


def test_pytest_collection_finish_dedupes_discovered_tools(
    monkeypatch, capsys
) -> None:
    """Per-tool surface: 3 tools × 4 parametrize cases each = 12 items but
    `discovered_tools` must list each tool exactly once."""
    tool_names = ["alpha", "beta", "gamma"]
    cfg = _build_config_with_tools(tool_names)

    # 4 contract cases per tool -> 12 items total, each tool name 4x.
    items = [
        _fake_item(f"<mcp-contracts>::test_{check}[{tool}]")
        for tool in tool_names
        for check in (
            "target_tool_exists",
            "schema_passes_structural_checks",
            "description_min_length",
            "every_parameter_has_description_and_type",
        )
    ]
    session = _fake_session(cfg, items)

    # Force _STATE.enabled so the early-return at the top of
    # pytest_collection_finish does not short-circuit. The renderer call
    # at the end writes to stdout; capsys swallows it.
    state = reporter._ReporterState(enabled=True)
    monkeypatch.setattr(reporter, "_STATE", state)

    reporter.pytest_collection_finish(session)  # type: ignore[arg-type]

    assert state.ctx is not None, (
        "pytest_collection_finish must populate _STATE.ctx when "
        "_mcp_contracts_config is present and items have contract shape."
    )
    discovered = state.ctx.discovered_tools
    assert discovered == sorted(tool_names), (
        f"discovered_tools must be deduped + sorted: expected {sorted(tool_names)!r}, "
        f"got {discovered!r} (len={len(discovered)})"
    )
    # Defensive: the banner reads len(ctx.discovered_tools) -- if the dedupe
    # ever regresses, the count blows up by a factor of (cases-per-tool).
    assert len(discovered) == len(tool_names), (
        f"discovered_tools length must equal unique tool count "
        f"({len(tool_names)}), got {len(discovered)}"
    )
    capsys.readouterr()  # drain the pre-run digest stdout
