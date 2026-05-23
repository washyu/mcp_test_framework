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
    ret = sig.get("return")
    # Some Python versions return `typing.NoReturn`, others normalise to a
    # form whose `__name__` is "NoReturn"; accept both. The previous
    # `type(None).__class__` middle branch resolved to `type`, which
    # accidentally permitted any class-typed return annotation (e.g. `-> int`).
    assert ret is typing.NoReturn or getattr(ret, "__name__", "") == "NoReturn", (
        f"return annotation must be NoReturn, got {ret!r}"
    )


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


def test_load_config_validation_error_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """version: 99 produces operator-tone schema-version error.

    Phase 23 D-03 (env-pollution audit): cli._load_config mutates
    os.environ["MCPTF_CONFIG_FILE"] (cli.py:299). Without a monkeypatch
    baseline, that mutation persists into later tests -- e.g.
    test_homelab_config.test_config_default_homelab loading this
    version: 99 yaml and tripping the version validator.
    """
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
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
        'version: 2\n'
        'sdet:\n  generated_root: "tests/sdet/_generated"\n'
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
        'version: 2\n'
        'sdet:\n  generated_root: "tests/sdet/_generated"\n'
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


def test_config_init_help_text_no_banned_tokens() -> None:
    """The new --command/--arg help strings must not leak banned tokens."""
    res = _runner().invoke(app, ["config-init", "--help"])
    assert res.exit_code == 0, (res.exit_code, res.stderr, res.stdout)
    assert not BANNED_RE.search(res.stdout), (
        f"banned tokens in config-init --help: {res.stdout!r}"
    )


def test_config_init_fallback_scaffold_no_banned_tokens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The fallback scaffold's header comment must not leak banned tokens."""
    for var in (
        "OLLAMA_BASE_URL", "OLLAMA_MODEL", "OLLAMA_TIMEOUT_SECONDS",
        "MCP_SERVER_COMMAND", "MCP_SERVER_ARGS", "MCP_SERVER_TIMEOUT_SECONDS",
        "JUDGE_TIMEOUT_SECONDS", "TARGET_TOOL_NAME", "MCPTF_CONFIG_FILE",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "out.yaml"
    res = _runner().invoke(
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
    assert out.exists(), "fallback scaffold not written"
    text = out.read_text(encoding="utf-8")
    assert not BANNED_RE.search(text), (
        f"banned tokens in fallback scaffold: {text!r}"
    )


def test_safe_03_no_config_found_fails_loud_with_locked_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase 13 SAFE-03: cwd has no config.yaml, no env var, no --config."""
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
    monkeypatch.chdir(tmp_path)
    runner = _runner()
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 2
    # Verbatim SAFE-03 lead and SAFE-03 detail (docs/ERROR-STYLE.md:46-55).
    assert "no config file found: ./config.yaml" in result.stderr
    assert "the framework refuses to run without a config file" in result.stderr
    assert "destructive ones. you must explicitly opt in" in result.stderr
    assert "config-init -o config.yaml" in result.stderr


def test_phase_31_mcptf_config_file_typo_no_longer_routed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase 31 SHIM-05 D-05 inversion of legacy SAFE-04 env-var branch.

    Pre-Phase-31: a typo'd MCPTF_CONFIG_FILE raised the SAFE-04 env-var
    branch error inside ``cli._load_config``.
    Post-Phase-31: the env-var branch is deleted. With no --config and
    no ./config.yaml, the resolver falls through to the SAFE-03
    no-config-found body regardless of MCPTF_CONFIG_FILE contents.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(tmp_path / "missing.yaml"))
    runner = _runner()
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 2
    # SAFE-03 surface fires; env-var-specific wording is gone.
    assert "no config file found: ./config.yaml" in result.stderr
    assert "config file not found via MCPTF_CONFIG_FILE" not in result.stderr


def test_safe_02_cwd_autodiscovery_picks_up_local_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase 13 SAFE-02: ./config.yaml is auto-discovered when no flag/env."""
    # Write a minimal v2 config (Plan 13-02 will accept this).
    (tmp_path / "config.yaml").write_text(
        "version: 2\n"
        "ollama:\n  base_url: http://127.0.0.1:11434\n  model: qwen3.6:latest\n"
        "mcp_server:\n  command: /bin/true\n  args: []\n"
        'sdet:\n  generated_root: "tests/sdet/_generated"\n'
        "tools: {}\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
    monkeypatch.chdir(tmp_path)
    # We assert resolver discovery via the loader directly (no pytest spawn).
    from mcp_test_framework.cli import _load_config
    cfg, resolved = _load_config(None)  # Plan 13-02 makes version=2 valid.
    assert cfg is not None
    assert resolved is not None  # Phase 27: resolver now returns (cfg, path).


def test_config_init_works_in_empty_dir_with_command_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase 13 (revision): SAFE-03 recovery command must run from
    an unconfigured directory. Without the allow_missing bypass, the
    operator-recommended `config-init -o config.yaml` would itself
    fail SAFE-03 -- self-bricking the recovery UX."""
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "out.yaml"
    runner = _runner()
    # The critical assertion: SAFE-03 did NOT fire. If it had, exit
    # would be 2 AND stderr would name "no config file found".
    result = runner.invoke(
        app,
        ["config-init", "--command", "nonexistent-binary-xyz", "-o", str(out)],
    )
    assert "no config file found: ./config.yaml" not in (result.stderr or "")


def test_list_tools_works_in_empty_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase 13 (revision): list-tools must not SAFE-03 in an empty dir.
    Same rationale as test_config_init_works_in_empty_dir_with_command_override:
    bootstrap-friendly commands return defaults; only `run` fails loud."""
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
    monkeypatch.chdir(tmp_path)
    runner = _runner()
    result = runner.invoke(app, ["list-tools"])
    # SAFE-03 did NOT fire. Downstream MCP handshake may fail (default
    # mcp_server.command may not be on PATH), which is acceptable --
    # what we are pinning is the resolver bypass.
    assert "no config file found: ./config.yaml" not in (result.stderr or "")


def test_run_still_fails_loud_in_empty_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase 13 (revision): regression test pinning that `run` keeps
    SAFE-03 fail-loud even after the allow_missing bypass is added
    to config-init and list-tools."""
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
    monkeypatch.chdir(tmp_path)
    runner = _runner()
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 2
    assert "no config file found: ./config.yaml" in result.stderr


def test_safe_06_v1_config_emits_locked_migration_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase 13 SAFE-06: loading a v1 config exits 2 with the LOCKED
    ERROR-STYLE message body (docs/ERROR-STYLE.md:57-73).

    Phase 23 D-03 (env-pollution audit): cli._load_config mutates
    os.environ["MCPTF_CONFIG_FILE"] directly (cli.py:299) so that the
    in-process pytest session sees the resolved path. monkeypatch.delenv
    here gives MonkeyPatch a baseline to restore on test teardown --
    without it the SUT's mutation persists into later tests, e.g.
    test_homelab_config.test_config_default_homelab loading a stale
    tmp_path/old.yaml at version: 1 and tripping the version validator.
    """
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
    cfg = tmp_path / "old.yaml"
    cfg.write_text(
        "version: 1\n"
        "ollama:\n  base_url: http://x:11434\n  model: m\n"
        "mcp_server:\n  command: /bin/true\n"
        "tools: {}\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    runner = _runner()
    result = runner.invoke(app, ["run", "--config", str(cfg)])
    assert result.exit_code == 2
    assert "config file uses an older format:" in result.stderr
    assert "schema version 2 (opt-in" in result.stderr
    assert "docs/MIGRATION-v1-to-v2.md" in result.stderr
    assert "config-init -o config.yaml.new" in result.stderr


def test_phase_31_v1_config_via_env_var_no_longer_routed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase 31 SHIM-05 D-05 inversion of legacy SAFE-06 env-var route.

    Pre-Phase-31: setting MCPTF_CONFIG_FILE to a v1 config triggered the
    SAFE-06 locked migration message via the env-var entry path.
    Post-Phase-31: the env-var entry path is gone. With no --config and
    no ./config.yaml, the resolver fails SAFE-03 (no config found); the
    v1 config at the env-pointed path is never read.
    """
    cfg = tmp_path / "old.yaml"
    cfg.write_text(
        "version: 1\n"
        "ollama:\n  base_url: http://x:11434\n  model: m\n"
        "mcp_server:\n  command: /bin/true\n"
        "tools: {}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(cfg))
    monkeypatch.chdir(tmp_path)
    runner = _runner()
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 2
    # The env-pointed v1 config is NEVER opened; the resolver falls
    # straight to SAFE-03.
    assert "no config file found: ./config.yaml" in result.stderr
    assert "config file uses an older format:" not in result.stderr


def test_cli_errors_static_call_sites_no_banned_tokens() -> None:
    """AST scan: every _emit_operator_error call's literal args are operator-tone."""
    import ast
    # Walk up from this test file to the repo root (same pattern as
    # test_doc_scrub._repo_root) so the test passes regardless of the
    # cwd pytest is invoked from.
    repo_root = Path(__file__).resolve().parents[3]
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
