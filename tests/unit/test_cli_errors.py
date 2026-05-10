"""Operator-tone error coverage for Phase 12 PERSONA-03.

Asserts:
- _emit_operator_error format matches docs/ERROR-STYLE.md (summary + blank +
  detail + blank + next:)
- _load_config errors operator-tone with `next:` lines and no banned tokens
- (Task 1b adds: config-init refuse-to-overwrite, config-init FileNotFoundError,
  list-tools MCP-spawn failure)
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from mcp_test_framework.cli import (
    _emit_operator_error,
    app,
)


BANNED_RE = re.compile(
    r"\b(Phase \d|Plan \d-\d|TOOLCFG-\d|ISOL-\d|OUTPUT-\d|D-\d{2}|"
    r"\d{6}-[a-z0-9]{3}|src/[\w/.]+\.py:\d+)"
)


def _runner() -> CliRunner:
    return CliRunner()


def test_emit_operator_error_format(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(typer.Exit) as ei:
        _emit_operator_error(
            summary="thing broke",
            detail=["line one", "line two"],
            next_step="run something to fix it",
        )
    assert ei.value.exit_code == 2
    err = capsys.readouterr().err
    expected_lines = [
        "thing broke",
        "",
        "line one",
        "line two",
        "",
        "next: run something to fix it",
    ]
    assert err.strip("\n").splitlines() == expected_lines


def test_emit_operator_error_custom_exit_code() -> None:
    with pytest.raises(typer.Exit) as ei:
        _emit_operator_error(
            summary="fail", detail=["x"], next_step="y", exit_code=130
        )
    assert ei.value.exit_code == 130


def test_emit_operator_error_returns_no_return_annotation() -> None:
    """Sanity: helper signature must be NoReturn so call sites without `raise`
    are typecheck-correct."""
    import typing
    sig = typing.get_type_hints(_emit_operator_error)
    # Some Python versions use `typing.NoReturn`, others normalise to `NoReturn`
    assert sig.get("return") in (typing.NoReturn, type(None).__class__) or \
           getattr(sig.get("return"), "__name__", "") == "NoReturn"


def test_load_config_path_not_found(tmp_path: Path) -> None:
    """--config /no/such/file emits operator-tone error, exit 2."""
    bogus = tmp_path / "no_such_config.yaml"
    res = _runner().invoke(app, ["list-tools", "--config", str(bogus)])
    assert res.exit_code == 2
    err = res.stderr
    assert "config file not found:" in err
    assert "next: " in err
    assert "config-init" in err
    assert not BANNED_RE.search(err), f"banned tokens in error: {err!r}"


def test_load_config_validation_error_version(tmp_path: Path) -> None:
    """version: 99 produces operator-tone schema-version error."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        'ollama:\n'
        '  base_url: "http://127.0.0.1:11434"\n'
        '  model: "qwen3.6:latest"\n'
        '  timeout_seconds: 120\n'
        'mcp_server:\n'
        '  command: "uvx"\n'
        '  args: ["x"]\n'
        '  timeout_seconds: 30\n'
        'judge_timeout_seconds: 120\n'
        'version: 99\n'
        'tools: {}\n',
        encoding="utf-8",
    )
    res = _runner().invoke(app, ["list-tools", "--config", str(cfg)])
    assert res.exit_code == 2
    err = res.stderr
    assert "schema version" in err or "older format" in err or "unsupported" in err
    assert "next: " in err
    assert "validation error for Config" not in err  # pydantic raw leak
    assert "value_error" not in err  # pydantic v1 internal jargon
    assert "Value error" not in err  # pydantic v2 internal jargon
    assert "Assertion failed" not in err  # pydantic v2 assert-style jargon
    assert not BANNED_RE.search(err), f"banned tokens in error: {err!r}"


def test_cli_module_has_emit_helper() -> None:
    """Sanity: helper is importable from the module."""
    from mcp_test_framework.cli import _emit_operator_error
    assert callable(_emit_operator_error)


def test_config_init_refuse_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "exists.yaml"
    target.write_text("# existing\n", encoding="utf-8")
    res = _runner().invoke(app, ["config-init", "-o", str(target)])
    assert res.exit_code == 2
    err = res.stderr
    assert "refusing to overwrite" in err
    assert "next: " in err
    assert "--force" in err
    assert not BANNED_RE.search(err)


def test_list_tools_mcp_spawn_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """list-tools handles 'command not on PATH' as an operator-tone error, not a stack trace."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        'ollama:\n'
        '  base_url: "http://127.0.0.1:11434"\n'
        '  model: "qwen3.6:latest"\n'
        '  timeout_seconds: 120\n'
        'mcp_server:\n'
        '  command: "definitely_not_on_path_xyz"\n'
        '  args: []\n'
        '  timeout_seconds: 5\n'
        'judge_timeout_seconds: 120\n'
        'version: 1\n'
        'tools: {}\n',
        encoding="utf-8",
    )
    for var in (
        "OLLAMA_BASE_URL", "OLLAMA_MODEL", "OLLAMA_TIMEOUT_SECONDS",
        "MCP_SERVER_COMMAND", "MCP_SERVER_ARGS", "MCP_SERVER_TIMEOUT_SECONDS",
        "JUDGE_TIMEOUT_SECONDS", "TARGET_TOOL_NAME", "MCPTF_CONFIG_FILE",
    ):
        monkeypatch.delenv(var, raising=False)
    res = _runner().invoke(app, ["list-tools", "--config", str(cfg)])
    assert res.exit_code == 2
    err = res.stderr
    assert "MCP server" in err
    assert "next: " in err
    assert "Traceback" not in err
    assert not BANNED_RE.search(err), f"banned tokens in error: {err!r}"


def test_config_init_mcp_spawn_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """config-init also rewrites MCP-spawn failures to operator-tone."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        'ollama:\n'
        '  base_url: "http://127.0.0.1:11434"\n'
        '  model: "qwen3.6:latest"\n'
        '  timeout_seconds: 120\n'
        'mcp_server:\n'
        '  command: "definitely_not_on_path_xyz"\n'
        '  args: []\n'
        '  timeout_seconds: 5\n'
        'judge_timeout_seconds: 120\n'
        'version: 1\n'
        'tools: {}\n',
        encoding="utf-8",
    )
    for var in (
        "OLLAMA_BASE_URL", "OLLAMA_MODEL", "OLLAMA_TIMEOUT_SECONDS",
        "MCP_SERVER_COMMAND", "MCP_SERVER_ARGS", "MCP_SERVER_TIMEOUT_SECONDS",
        "JUDGE_TIMEOUT_SECONDS", "TARGET_TOOL_NAME", "MCPTF_CONFIG_FILE",
    ):
        monkeypatch.delenv(var, raising=False)
    out = tmp_path / "out.yaml"
    res = _runner().invoke(
        app, ["config-init", "--config", str(cfg), "-o", str(out)]
    )
    assert res.exit_code == 2
    err = res.stderr
    assert "MCP server" in err
    assert "next: " in err
    assert "Traceback" not in err
    assert not BANNED_RE.search(err), f"banned tokens in error: {err!r}"


def test_cli_errors_static_call_sites_no_banned_tokens() -> None:
    """AST scan: every _emit_operator_error call's literal args are operator-tone."""
    import ast
    # Walk up from this test file to the repo root (same pattern as
    # test_doc_scrub._repo_root) so the test passes regardless of the
    # cwd pytest is invoked from.
    repo_root = Path(__file__).resolve().parents[2]
    src = (repo_root / "src" / "mcp_test_framework" / "cli.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "_emit_operator_error"):
            for kw in (node.keywords or []):
                for s in ast.walk(kw.value):
                    if isinstance(s, ast.Constant) and isinstance(s.value, str):
                        assert not BANNED_RE.search(s.value), (
                            f"banned token in keyword {kw.arg!r}: {s.value!r}"
                        )
