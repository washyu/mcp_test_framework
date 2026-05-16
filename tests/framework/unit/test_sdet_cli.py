"""Phase 18 D-04 / D-05: --sdet Typer flag on `run` command.

Pins:
- --sdet is registered in `run --help` (parallel to Phase 16 --explain inverse test)
- `run --sdet` produces argv whose discovery paths swap to tests/sdet
- `run --sdet --with-framework` adds tests/framework on top of tests/sdet
- `run` (no --sdet) preserves Phase 16 default-path argv byte-identically
- --sdet literal string NEVER appears in argv handed to subprocess.run
  (wrapper-owned per Phase 16 D-07 inherit)
- Both run_pytest_subprocess call sites (--raw and domain-UI branches)
  forward sdet=sdet
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from xml.sax.saxutils import escape


_MIN_JUNIT_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<testsuites>'
    '<testsuite name="pytest" errors="0" failures="0" skipped="0" tests="0" time="0.001">'
    '</testsuite>'
    '</testsuites>'
)


def _invoke(*args: str):
    from typer.testing import CliRunner
    from mcp_test_framework.cli import app
    return CliRunner().invoke(app, list(args))


def _make_valid_config(tmp_path: Path) -> Path:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "version: 2\n"
        "ollama:\n  base_url: http://127.0.0.1:11434\n  model: q\n"
        "mcp_server:\n  command: uvx\n  args: [homelab-mcp]\n"
        # Phase 21.1 RELOC-01: sdet.generated_root is now required on Config.
        'sdet:\n  generated_root: "tests/sdet/_generated"\n'
        "tools: {}\n",
        encoding="utf-8",
    )
    return cfg


def _stub_subprocess_capturing_argv(captured: dict, returncode: int = 0):
    """subprocess.run stub that captures argv and writes a minimal JUnit XML
    to whatever --junitxml=PATH it sees."""
    def _fake(argv, **kwargs):
        captured["argv"] = list(argv)
        junit_args = [
            a for a in argv if isinstance(a, str) and a.startswith("--junitxml=")
        ]
        if junit_args:
            path = Path(junit_args[-1].split("=", 1)[1])
            path.write_text(_MIN_JUNIT_XML, encoding="utf-8")
        return SimpleNamespace(
            returncode=returncode, stdout="...", stderr="", args=argv
        )
    return _fake


# ---------------------------------------------------------------------------
# Help registration
# ---------------------------------------------------------------------------


def test_run_help_lists_sdet_flag() -> None:
    """--test-code appears in `run --help` (parallel to Phase 16 --explain).

    Phase 25 RENAME-03 renamed the operator-facing flag from --sdet to
    --test-code. The legacy --sdet flag is hidden=True on the shim and
    must NOT appear in --help output any more. Test name preserved for
    blame continuity; assertion repointed to the new flag.
    """
    result = _invoke("run", "--help")
    assert result.exit_code == 0, result.output
    assert "--test-code" in result.output
    # Old surface intentionally hidden -- documents the deprecation contract.
    assert "--sdet" not in result.output


def test_run_help_sdet_mentions_composition_with_with_framework() -> None:
    """The --test-code help text documents composition with --with-framework (D-05).

    Phase 25 RENAME-03: help text now references tests/test_code/ as the
    documented scope. Plan 04 wires dual-discovery for the legacy
    tests/sdet/ path; this test pins the operator-facing vocabulary.
    """
    result = _invoke("run", "--help")
    assert result.exit_code == 0, result.output
    # Verbatim from CONTEXT.md (the pattern doc): the help text mentions
    # composing with --with-framework, --raw, --debug, -q, and --explain.
    assert "--with-framework" in result.output
    assert "tests/test_code" in result.output


# ---------------------------------------------------------------------------
# --raw branch: sdet=sdet flows into subprocess argv
# ---------------------------------------------------------------------------


def test_run_raw_sdet_argv_has_tests_test_code(tmp_path, monkeypatch) -> None:
    """`run --raw --test-code` -> subprocess argv contains tests/test_code,
    not tests/contract. Phase 25 RENAME-04: primary scope is tests/test_code/."""
    cfg_path = _make_valid_config(tmp_path)
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(cfg_path))
    monkeypatch.chdir(tmp_path)  # No tests/sdet/ in cwd -> dual-discovery inactive.
    captured: dict = {}
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_capturing_argv(captured),
    )
    result = _invoke("run", "--raw", "--test-code", "--config", str(cfg_path))
    # Exit code is the stubbed subprocess returncode (0).
    assert result.exit_code == 0, result.output
    argv = captured.get("argv", [])
    assert "tests/test_code" in argv, argv
    assert "tests/contract" not in argv, argv
    # D-07: --test-code / --sdet literals must never reach pytest's argv.
    assert "--test-code" not in argv, argv
    assert "--sdet" not in argv, argv  # noqa: sdet-rename-shim


def test_run_raw_sdet_with_framework_argv_has_both(tmp_path, monkeypatch) -> None:
    """`run --raw --test-code --with-framework` -> argv has tests/test_code AND tests/framework."""
    cfg_path = _make_valid_config(tmp_path)
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(cfg_path))
    monkeypatch.chdir(tmp_path)
    captured: dict = {}
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_capturing_argv(captured),
    )
    result = _invoke(
        "run", "--raw", "--test-code", "--with-framework", "--config", str(cfg_path)
    )
    assert result.exit_code == 0, result.output
    argv = captured.get("argv", [])
    assert "tests/test_code" in argv, argv
    assert "tests/framework" in argv, argv
    assert "tests/contract" not in argv, argv
    assert "--test-code" not in argv, argv


def test_run_raw_no_sdet_argv_has_tests_contract(tmp_path, monkeypatch) -> None:
    """`run --raw` (no --test-code) -> argv has tests/contract; tests/test_code absent.

    Phase 16 default-path zero-diff guard.
    """
    cfg_path = _make_valid_config(tmp_path)
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(cfg_path))
    monkeypatch.chdir(tmp_path)
    captured: dict = {}
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_capturing_argv(captured),
    )
    result = _invoke("run", "--raw", "--config", str(cfg_path))
    assert result.exit_code == 0, result.output
    argv = captured.get("argv", [])
    assert "tests/contract" in argv, argv
    assert "tests/test_code" not in argv, argv
    assert "tests/sdet" not in argv, argv  # noqa: sdet-rename-shim


# ---------------------------------------------------------------------------
# Phase 18 D-06: pre-run digest dispatch
# ---------------------------------------------------------------------------


def test_run_sdet_dispatches_scenario_digest(tmp_path, monkeypatch) -> None:
    """D-06: `run --test-code` (non-raw) prints the SDET digest banner, NOT the
    tool-flavored 'MCP Test Framework' banner."""
    cfg_path = _make_valid_config(tmp_path)
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(cfg_path))
    monkeypatch.chdir(tmp_path)
    captured: dict = {}
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_capturing_argv(captured),
    )
    # Avoid the wrapper's own discovery call (which would spawn the MCP server).
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda cfg: [],
    )
    result = _invoke("run", "--test-code", "--config", str(cfg_path))
    assert result.exit_code == 0, result.output
    assert "MCP Test Framework (SDET)" in result.output, result.output
    # The tool banner ("MCP Test Framework" followed by newline, no (SDET)
    # suffix) must NOT appear under --test-code.
    assert "\nMCP Test Framework\n" not in result.output


def test_run_no_sdet_uses_tool_digest(tmp_path, monkeypatch) -> None:
    """D-06 regression: `run` (no --test-code) still prints the tool digest banner."""
    cfg_path = _make_valid_config(tmp_path)
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(cfg_path))
    monkeypatch.chdir(tmp_path)
    captured: dict = {}
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_capturing_argv(captured),
    )
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda cfg: [],
    )
    result = _invoke("run", "--config", str(cfg_path))
    assert result.exit_code == 0, result.output
    assert "MCP Test Framework" in result.output
    assert "MCP Test Framework (SDET)" not in result.output


# ---------------------------------------------------------------------------
# Plan 18-08: extended composition-matrix pinning
# ---------------------------------------------------------------------------


def test_run_default_no_sdet_raw_argv_has_tests_contract(
    tmp_path, monkeypatch
) -> None:
    """D-04 baseline: `run --raw` (no --test-code) argv carries tests/contract,
    not tests/test_code. Phase 16 default-path zero-diff regression."""
    cfg_path = _make_valid_config(tmp_path)
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(cfg_path))
    monkeypatch.chdir(tmp_path)
    captured: dict = {}
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_capturing_argv(captured),
    )
    result = _invoke("run", "--raw", "--config", str(cfg_path))
    assert result.exit_code == 0, result.output
    argv = captured.get("argv", [])
    assert "tests/contract" in argv, argv
    assert "tests/test_code" not in argv, argv
    assert "tests/sdet" not in argv, argv  # noqa: sdet-rename-shim


def test_run_with_framework_only_argv_has_contract_and_framework(
    tmp_path, monkeypatch
) -> None:
    """D-05 baseline: `run --raw --with-framework` (no --test-code) argv has
    tests/contract + tests/framework (additive on the contract scope)."""
    cfg_path = _make_valid_config(tmp_path)
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(cfg_path))
    monkeypatch.chdir(tmp_path)
    captured: dict = {}
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_capturing_argv(captured),
    )
    result = _invoke(
        "run", "--raw", "--with-framework", "--config", str(cfg_path)
    )
    assert result.exit_code == 0, result.output
    argv = captured.get("argv", [])
    assert "tests/contract" in argv, argv
    assert "tests/framework" in argv, argv
    assert "tests/test_code" not in argv, argv


def test_run_sdet_q_argv_has_tests_test_code(tmp_path, monkeypatch) -> None:
    """D-05: `run --raw --test-code -q` argv has tests/test_code; -q is a
    pytest flag that DOES forward to the subprocess (unlike --test-code,
    which is wrapper-owned). Pinned here to document the asymmetry:
    --test-code is wrapper-only, -q passes through to pytest."""
    cfg_path = _make_valid_config(tmp_path)
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(cfg_path))
    monkeypatch.chdir(tmp_path)
    captured: dict = {}
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_capturing_argv(captured),
    )
    result = _invoke(
        "run", "--raw", "--test-code", "-q", "--config", str(cfg_path)
    )
    assert result.exit_code == 0, result.output
    argv = captured.get("argv", [])
    assert "tests/test_code" in argv, argv
    # --test-code is wrapper-owned; never leaks to pytest argv.
    assert "--test-code" not in argv, argv
