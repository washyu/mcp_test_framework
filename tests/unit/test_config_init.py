"""Self-contained-scaffold coverage for Phase 12 CLEAN-05 + D-01/D-02/D-03."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from mcp_test_framework.cli import _format_tools_yaml_scaffold
from mcp_test_framework.config import Config


class _StubTool:
    """Minimal stand-in for mcp.types.Tool -- only `name` is read by the scaffold."""

    def __init__(self, name: str) -> None:
        self.name = name


def _scaffold(tool_names: list[str]) -> str:
    return _format_tools_yaml_scaffold([_StubTool(n) for n in tool_names])


def _parse(yaml_text: str) -> dict[str, Any]:
    data = yaml.safe_load(yaml_text)
    assert isinstance(data, dict)
    return data


def test_scaffold_has_top_level_ollama() -> None:
    data = _parse(_scaffold(["a"]))
    assert "ollama" in data
    o = data["ollama"]
    assert "base_url" in o and "model" in o and "timeout_seconds" in o


def test_scaffold_has_top_level_mcp_server() -> None:
    data = _parse(_scaffold(["a"]))
    assert "mcp_server" in data
    s = data["mcp_server"]
    assert "command" in s and "args" in s and "timeout_seconds" in s


def test_scaffold_has_top_level_judge_timeout() -> None:
    data = _parse(_scaffold(["a"]))
    assert isinstance(data["judge_timeout_seconds"], int)


def test_scaffold_has_version_1() -> None:
    """D-01: v1-header / v2-style content. Phase 12 keeps version: 1."""
    data = _parse(_scaffold(["a"]))
    assert data["version"] == 1


def test_scaffold_no_target_block() -> None:
    """D-03: target.tool_name is leaving -- never emit `target:`."""
    data = _parse(_scaffold(["a"]))
    assert "target" not in data


def test_scaffold_tools_all_skip_true() -> None:
    """D-02: every discovered tool gets skip: true with the curated reason."""
    data = _parse(_scaffold(["alpha", "beta", "gamma"]))
    tools = data["tools"]
    assert set(tools) == {"alpha", "beta", "gamma"}
    for name, entry in tools.items():
        assert entry["skip"] is True, name
        assert entry["skip_reason"] == "review and remove skip to enable", name


def test_scaffold_empty_tool_list_returns_empty_mapping() -> None:
    text = _scaffold([])
    assert "tools:\n  {}\n" in text or "tools: {}\n" in text
    data = yaml.safe_load(text)
    assert data["tools"] == {}, (
        f"empty scaffold must yield an empty mapping, got {data['tools']!r}"
    )


def test_scaffold_loadable_via_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLEAN-05 acceptance: the scaffold loads via Config() with no .env present."""
    for var in (
        "OLLAMA_BASE_URL", "OLLAMA_MODEL", "OLLAMA_TIMEOUT_SECONDS",
        "MCP_SERVER_COMMAND", "MCP_SERVER_ARGS", "MCP_SERVER_TIMEOUT_SECONDS",
        "JUDGE_TIMEOUT_SECONDS", "TARGET_TOOL_NAME", "MCPTF_CONFIG_FILE",
    ):
        monkeypatch.delenv(var, raising=False)
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(_scaffold(["alpha", "beta"]), encoding="utf-8")
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(cfg_path))

    cfg = Config()
    assert cfg.version == 1
    assert cfg.mcp_server.command == "uvx"
    assert "11434" in str(cfg.ollama.base_url)


def test_scaffold_no_banned_tokens() -> None:
    import re
    text = _scaffold(["alpha", "beta"])
    banned = [
        r"\bPhase \d", r"\bPlan \d-\d", r"\bTOOLCFG-\d", r"\bISOL-\d",
        r"\bCD-\d", r"\bD-\d{2}", r"\b\d{6}-[a-z0-9]{3}",
        r"src/[\w/.]+\.py:\d+",
    ]
    for p in banned:
        assert not re.search(p, text), f"banned pattern {p!r} in scaffold output"


def test_scaffold_sorted_alphabetically() -> None:
    """Preserve the v1.1 D-list-4 sort contract."""
    text = _scaffold(["zeta", "alpha", "mu"])
    a = text.index("alpha:")
    m = text.index("mu:")
    z = text.index("zeta:")
    assert a < m < z


def test_scaffold_yaml_key_quotes_unsafe_names() -> None:
    """Defensive: tool names containing YAML control chars are JSON-quoted."""
    from mcp_test_framework.cli import _yaml_key
    assert _yaml_key("alpha") == "alpha"
    assert _yaml_key("alpha_beta") == "alpha_beta"
    assert _yaml_key("alpha:beta").startswith('"')
    assert _yaml_key("alpha\nbeta").startswith('"')
