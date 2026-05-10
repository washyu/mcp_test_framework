"""PERSONA-02 / D-05..D-09 coverage for `list-tools` UX changes."""
from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from mcp_test_framework.cli import (
    _format_param_signature,
    _format_tools_text,
)


class _StubTool:
    """Minimal Tool stand-in: name + description + inputSchema."""
    def __init__(
        self,
        name: str,
        description: str | None = None,
        inputSchema: dict | None = None,
        outputSchema: dict | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.inputSchema = inputSchema
        self.outputSchema = outputSchema


# --- _format_param_signature ---

def test_param_signature_no_inputschema() -> None:
    assert _format_param_signature(_StubTool("x")) == "()"


def test_param_signature_empty_properties() -> None:
    assert _format_param_signature(_StubTool("x", inputSchema={"properties": {}})) == "()"


def test_param_signature_required_only() -> None:
    sig = _format_param_signature(_StubTool("x", inputSchema={
        "properties": {"host": {"type": "string"}},
        "required": ["host"],
    }))
    assert sig == "(host: str)"


def test_param_signature_optional_only() -> None:
    sig = _format_param_signature(_StubTool("x", inputSchema={
        "properties": {"timeout": {"type": "integer", "default": 30}},
    }))
    assert sig == "(*, timeout: int = 30)"


def test_param_signature_mixed() -> None:
    sig = _format_param_signature(_StubTool("x", inputSchema={
        "properties": {
            "host": {"type": "string"},
            "timeout": {"type": "integer", "default": 30},
        },
        "required": ["host"],
    }))
    assert sig == "(host: str, *, timeout: int = 30)"


def test_param_signature_required_order_preserved() -> None:
    sig = _format_param_signature(_StubTool("x", inputSchema={
        "properties": {"a": {"type": "string"}, "b": {"type": "integer"}},
        "required": ["b", "a"],
    }))
    assert sig == "(b: int, a: str)"


def test_param_signature_kwargs_sorted_alphabetically() -> None:
    sig = _format_param_signature(_StubTool("x", inputSchema={
        "properties": {
            "z_opt": {"type": "string", "default": "z"},
            "a_opt": {"type": "integer", "default": 1},
        },
    }))
    assert sig.index("a_opt") < sig.index("z_opt")


def test_param_signature_unknown_type_falls_back_to_any() -> None:
    sig = _format_param_signature(_StubTool("x", inputSchema={
        "properties": {"weird": {}},
        "required": ["weird"],
    }))
    assert "Any" in sig


def test_param_signature_default_value_repr() -> None:
    """Defaults render via repr so strings stay quoted."""
    sig = _format_param_signature(_StubTool("x", inputSchema={
        "properties": {"q": {"type": "string", "default": "hello"}},
    }))
    assert "= 'hello'" in sig


# --- _format_tools_text default + --full ---

def _stub_tools() -> list[_StubTool]:
    return [
        _StubTool("alpha", description="Read alpha records.",
                  inputSchema={"properties": {"q": {"type": "string", "description": "Search query."}}, "required": ["q"]}),
        _StubTool("beta",  description="Write to beta. Use with caution.",
                  inputSchema={"properties": {}}),
        _StubTool("gamma", description=None),
    ]


def test_default_render_has_signature() -> None:
    out = _format_tools_text(_stub_tools())
    assert "alpha(q: str)" in out
    assert "beta()" in out
    assert "gamma()" in out


def test_default_render_truncates_description() -> None:
    long_desc = "word " * 200
    out = _format_tools_text([_StubTool("x", description=long_desc)])
    line_with_desc = next(l for l in out.splitlines() if "word" in l)
    assert "..." in line_with_desc or len(line_with_desc) < 200


def test_full_render_includes_param_descriptions() -> None:
    out = _format_tools_text(_stub_tools(), full=True)
    assert "Search query." in out
    assert "parameters:" in out


def test_full_render_wraps_description() -> None:
    out = _format_tools_text([_StubTool("x", description="A " * 300)], full=True)
    assert out.count("\n") > 1


def test_name_filter_case_insensitive_substring() -> None:
    out = _format_tools_text(_stub_tools(), name_filter="ALP")
    assert "alpha" in out
    assert "beta" not in out
    assert "gamma" not in out


def test_name_filter_zero_match_message() -> None:
    out = _format_tools_text(_stub_tools(), name_filter="zzz")
    assert "no tools matched filter 'zzz'" in out
    assert "server has 3 tools total" in out


def test_empty_tools_no_filter() -> None:
    assert _format_tools_text([]) == "(no tools registered on the server)"


def test_alphabetical_sort_preserved() -> None:
    out = _format_tools_text([_StubTool("zeta"), _StubTool("alpha"), _StubTool("mu")])
    a, m, z = out.index("alpha"), out.index("mu"), out.index("zeta")
    assert a < m < z


# --- CLI-level orthogonality (D-07) ---

def test_json_full_orthogonal(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`list-tools --json --full` MUST equal `list-tools --json` byte-for-byte.

    Rationale (D-07): --json is the machine-readable format, --full is a
    verbosity flag for the human-readable path. JSON output is already
    complete by definition; --full is a no-op under --json.
    """
    from mcp_test_framework import cli as cli_mod

    # Build a deterministic 2-tool set; monkeypatch _list_tools_async so the
    # command does not try to spawn an MCP server.
    fake_tools = [
        _StubTool(
            "alpha",
            description="Read alpha records.",
            inputSchema={
                "properties": {"q": {"type": "string", "description": "Search query."}},
                "required": ["q"],
            },
        ),
        _StubTool("beta", description="Write to beta.", inputSchema={"properties": {}}),
    ]

    async def _fake_list_tools_async(cfg):  # noqa: ARG001
        return fake_tools

    monkeypatch.setattr(cli_mod, "_list_tools_async", _fake_list_tools_async)

    # Minimal config that loads without .env
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        'ollama:\n'
        '  base_url: "http://127.0.0.1:11434"\n'
        '  model: "qwen3.6:latest"\n'
        '  timeout_seconds: 120\n'
        'mcp_server:\n'
        '  command: "uvx"\n'
        '  args: ["x"]\n'
        '  timeout_seconds: 30\n'
        'judge_timeout_seconds: 120\n'
        'version: 2\n'
        'tools: {}\n',
        encoding="utf-8",
    )
    for var in (
        "OLLAMA_BASE_URL", "OLLAMA_MODEL", "OLLAMA_TIMEOUT_SECONDS",
        "MCP_SERVER_COMMAND", "MCP_SERVER_ARGS", "MCP_SERVER_TIMEOUT_SECONDS",
        "JUDGE_TIMEOUT_SECONDS", "TARGET_TOOL_NAME", "MCPTF_CONFIG_FILE",
    ):
        monkeypatch.delenv(var, raising=False)

    runner = CliRunner()
    res_json = runner.invoke(cli_mod.app, ["list-tools", "--config", str(cfg_path), "--json"])
    res_json_full = runner.invoke(
        cli_mod.app, ["list-tools", "--config", str(cfg_path), "--json", "--full"]
    )

    assert res_json.exit_code == 0, res_json.output
    assert res_json_full.exit_code == 0, res_json_full.output
    # Output must be byte-identical (D-07: --full is verbosity for the
    # human-readable path; --json is already full).
    assert res_json.stdout == res_json_full.stdout
    # Sanity: the output is parseable JSON and contains both tools.
    parsed = json.loads(res_json.stdout)
    names = [t["name"] for t in parsed]
    assert "alpha" in names and "beta" in names
