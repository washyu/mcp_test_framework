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


def test_scaffold_has_version_2() -> None:
    """Phase 13 D-08: v2 schema header. Plan 13-02 wires the validator
    to accept this value; Plan 13-01 owns the scaffold emit."""
    data = _parse(_scaffold(["a"]))
    assert data["version"] == 2


def test_config_init_scaffold_emits_version_2() -> None:
    """Phase 13 SAFE-06 / D-08: the regenerated scaffold targets v2.

    The scaffold body MUST contain `version: 2\\n` and MUST NOT contain
    the literal `version: 1\\n` -- after the v1->v2 flip, the SAFE-06
    migration error tells operators to regenerate the scaffold to get v2,
    so a stale v1 in the emit would brick the recovery UX.
    """
    text = _scaffold(["alpha"])
    assert "version: 2\n" in text
    assert "version: 1\n" not in text


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
    """CLEAN-05 acceptance: the scaffold loads via Config(yaml_file=...).

    Phase 13 D-06: MCPTF_CONFIG_FILE is no longer a Config() source; the
    resolver in cli.py passes the resolved path as an explicit kwarg.
    """
    for var in (
        "OLLAMA_BASE_URL", "OLLAMA_MODEL", "OLLAMA_TIMEOUT_SECONDS",
        "MCP_SERVER_COMMAND", "MCP_SERVER_ARGS", "MCP_SERVER_TIMEOUT_SECONDS",
        "JUDGE_TIMEOUT_SECONDS", "TARGET_TOOL_NAME", "MCPTF_CONFIG_FILE",
    ):
        monkeypatch.delenv(var, raising=False)
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(_scaffold(["alpha", "beta"]), encoding="utf-8")

    cfg = Config(yaml_file=str(cfg_path))
    assert cfg.version == 2
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


# ---------------------------------------------------------------------------
# Plan 12-08: --command/--arg flags + fallback scaffold on launch failure.
# UAT gap 2 PRIMARY (override flags) + SECONDARY (fallback scaffold).
# ---------------------------------------------------------------------------


_SPEC_ENV_VARS = (
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "OLLAMA_TIMEOUT_SECONDS",
    "MCP_SERVER_COMMAND",
    "MCP_SERVER_ARGS",
    "MCP_SERVER_TIMEOUT_SECONDS",
    "JUDGE_TIMEOUT_SECONDS",
    "TARGET_TOOL_NAME",
    "MCPTF_CONFIG_FILE",
)


def _clear_spec_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _SPEC_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_config_init_command_arg_flags_override_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--command/--arg reach _list_tools_async via init kwargs (highest precedence).

    The proxy: when launch fails because the bogus command isn't on PATH, the
    operator-tone error quotes both the command and the args. If those values
    appear in stderr, the flags reached cfg.mcp_server.command/args.
    """
    from typer.testing import CliRunner

    from mcp_test_framework.cli import app

    _clear_spec_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "out.yaml"
    res = CliRunner().invoke(
        app,
        [
            "config-init",
            "--command",
            "nonexistent-binary-xyz",
            "--arg",
            "first",
            "--arg",
            "second",
            "-o",
            str(out),
        ],
    )
    assert res.exit_code == 2, (res.exit_code, res.stderr, res.stdout)
    err = res.stderr
    assert "nonexistent-binary-xyz" in err, (
        f"--command value did not reach the operator-tone error; stderr={err!r}"
    )
    assert "first" in err, (
        f"--arg first did not reach the operator-tone error; stderr={err!r}"
    )
    assert "second" in err, (
        f"--arg second did not reach the operator-tone error; stderr={err!r}"
    )


def test_config_init_fallback_scaffold_written_on_launch_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When --output is given AND launch fails, write a fallback scaffold shell."""
    from typer.testing import CliRunner

    from mcp_test_framework.cli import app

    _clear_spec_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "out.yaml"
    res = CliRunner().invoke(
        app,
        [
            "config-init",
            "--command",
            "nonexistent-binary-xyz",
            "-o",
            str(out),
        ],
    )
    assert res.exit_code == 2
    assert out.exists(), (
        "fallback scaffold was not written -- operator's recovery path is "
        "still 'hand-write a config from scratch' (UAT gap 2 SECONDARY)"
    )
    text = out.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert isinstance(data, dict)
    assert {
        "ollama",
        "mcp_server",
        "judge_timeout_seconds",
        "version",
        "tools",
    }.issubset(data.keys()), (
        f"fallback scaffold missing top-level blocks: keys={set(data)!r}"
    )
    tools = data["tools"]
    assert tools == {} or tools == [], (
        f"fallback scaffold tools block must be empty, got {tools!r}"
    )
    assert "mcp_server.command" in text, (
        "fallback scaffold header must name `mcp_server.command` so the "
        "operator knows which field to fix before re-running config-init"
    )


def test_config_init_fallback_scaffold_header_documents_defaults_limitation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CONCERN #2 disposition lock: header acknowledges --command/--arg overrides
    are NOT propagated into the fallback scaffold's mcp_server block."""
    from typer.testing import CliRunner

    from mcp_test_framework.cli import app

    _clear_spec_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "out.yaml"
    res = CliRunner().invoke(
        app,
        [
            "config-init",
            "--command",
            "nonexistent-binary-xyz",
            "--arg",
            "abc",
            "-o",
            str(out),
        ],
    )
    assert res.exit_code == 2
    assert out.exists()
    text = out.read_text(encoding="utf-8").lower()
    acceptable = (
        "shows the framework default",
        "if you intended",
        "edit those lines",
        "substitute",
    )
    assert any(phrase in text for phrase in acceptable), (
        "fallback scaffold header doesn't acknowledge that --command/--arg "
        "overrides aren't propagated; operator who passed custom flags will "
        "be confused. Header must include one of: "
        f"{acceptable!r}"
    )


def test_config_init_fallback_scaffold_not_written_in_stdout_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No --output => no fallback file. stdout-mode recovery is moot."""
    from typer.testing import CliRunner

    from mcp_test_framework.cli import app

    _clear_spec_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    res = CliRunner().invoke(
        app,
        ["config-init", "--command", "nonexistent-binary-xyz"],
    )
    assert res.exit_code == 2
    assert not (tmp_path / "config.yaml").exists(), (
        "stdout-mode launch failure must not silently write config.yaml in cwd"
    )


def test_config_init_success_path_unchanged_when_command_resolvable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Sanity: when launch succeeds, the populated scaffold path is byte-identical."""
    from typer.testing import CliRunner

    import mcp_test_framework.cli as cli_module
    from mcp_test_framework.cli import app

    _clear_spec_env(monkeypatch)
    monkeypatch.chdir(tmp_path)

    async def _fake_list_tools_async(cfg):  # type: ignore[no-untyped-def]
        return [_StubTool("alpha"), _StubTool("beta")]

    monkeypatch.setattr(cli_module, "_list_tools_async", _fake_list_tools_async)

    out = tmp_path / "ok.yaml"
    res = CliRunner().invoke(
        app,
        ["config-init", "--command", "python", "-o", str(out)],
    )
    assert res.exit_code == 0, (res.exit_code, res.stderr, res.stdout)
    assert out.exists()
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert "tools" in data
    tools = data["tools"]
    assert "alpha" in tools and "beta" in tools, (
        f"success path lost tool entries: {tools!r}"
    )
    for name in ("alpha", "beta"):
        assert tools[name]["skip"] is True, name
