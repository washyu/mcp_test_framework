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
    """--sdet appears in `run --help` (parallel to Phase 16 --explain)."""
    result = _invoke("run", "--help")
    assert result.exit_code == 0, result.output
    assert "--sdet" in result.output


def test_run_help_sdet_mentions_composition_with_with_framework() -> None:
    """The --sdet help text documents composition with --with-framework (D-05)."""
    result = _invoke("run", "--help")
    assert result.exit_code == 0, result.output
    # Verbatim from CONTEXT.md (the pattern doc): the help text mentions
    # composing with --with-framework, --raw, --debug, -q, and --explain.
    assert "--with-framework" in result.output
    assert "tests/sdet" in result.output


# ---------------------------------------------------------------------------
# --raw branch: sdet=sdet flows into subprocess argv
# ---------------------------------------------------------------------------


def test_run_raw_sdet_argv_has_tests_sdet(tmp_path, monkeypatch) -> None:
    """`run --sdet --raw` -> subprocess argv contains tests/sdet, not tests/contract."""
    cfg_path = _make_valid_config(tmp_path)
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(cfg_path))
    captured: dict = {}
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_capturing_argv(captured),
    )
    result = _invoke("run", "--raw", "--sdet", "--config", str(cfg_path))
    # Exit code is the stubbed subprocess returncode (0).
    assert result.exit_code == 0, result.output
    argv = captured.get("argv", [])
    assert "tests/sdet" in argv, argv
    assert "tests/contract" not in argv, argv
    # D-07: --sdet literal must never reach pytest's argv.
    assert "--sdet" not in argv, argv


def test_run_raw_sdet_with_framework_argv_has_both(tmp_path, monkeypatch) -> None:
    """`run --sdet --with-framework --raw` -> argv has tests/sdet AND tests/framework."""
    cfg_path = _make_valid_config(tmp_path)
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(cfg_path))
    captured: dict = {}
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_capturing_argv(captured),
    )
    result = _invoke(
        "run", "--raw", "--sdet", "--with-framework", "--config", str(cfg_path)
    )
    assert result.exit_code == 0, result.output
    argv = captured.get("argv", [])
    assert "tests/sdet" in argv, argv
    assert "tests/framework" in argv, argv
    assert "tests/contract" not in argv, argv
    assert "--sdet" not in argv, argv


def test_run_raw_no_sdet_argv_has_tests_contract(tmp_path, monkeypatch) -> None:
    """`run --raw` (no --sdet) -> argv has tests/contract; tests/sdet absent.

    Phase 16 default-path zero-diff guard.
    """
    cfg_path = _make_valid_config(tmp_path)
    monkeypatch.setenv("MCPTF_CONFIG_FILE", str(cfg_path))
    captured: dict = {}
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_capturing_argv(captured),
    )
    result = _invoke("run", "--raw", "--config", str(cfg_path))
    assert result.exit_code == 0, result.output
    argv = captured.get("argv", [])
    assert "tests/contract" in argv, argv
    assert "tests/sdet" not in argv, argv
