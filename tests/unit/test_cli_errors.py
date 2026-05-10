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
    return CliRunner(mix_stderr=False)


def test_emit_operator_error_format(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as ei:
        _emit_operator_error(
            summary="thing broke",
            detail=["line one", "line two"],
            next_step="run something to fix it",
        )
    assert ei.value.code == 2
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
    with pytest.raises(SystemExit) as ei:
        _emit_operator_error(
            summary="fail", detail=["x"], next_step="y", exit_code=130
        )
    assert ei.value.code == 130


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
    assert "value_error" not in err  # pydantic internal jargon
    assert not BANNED_RE.search(err), f"banned tokens in error: {err!r}"


def test_cli_module_has_emit_helper() -> None:
    """Sanity: helper is importable from the module."""
    from mcp_test_framework.cli import _emit_operator_error
    assert callable(_emit_operator_error)
