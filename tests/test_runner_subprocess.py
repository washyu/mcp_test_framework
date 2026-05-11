"""Phase 14 Plan 01 unit tests: subprocess dispatch, exit-code mapping,
--raw bypass, --junit-xml=PATH preservation.

Pins Phase 14 D-01, D-02, D-03, D-11, D-15, D-16 + RUNNER-01/03/05/06.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from mcp_test_framework._runner import (
    _map_exit_code,
    run_pytest_subprocess,
)
from mcp_test_framework.cli import app


def _invoke(*args: str):
    return CliRunner().invoke(app, list(args))


# ---- _map_exit_code (D-15) ----

def test_map_exit_code_0_passes_through() -> None:
    assert _map_exit_code(0) == (0, None)


def test_map_exit_code_1_passes_through() -> None:
    assert _map_exit_code(1) == (1, None)


def test_map_exit_code_2_passes_through() -> None:
    assert _map_exit_code(2) == (2, None)


def test_map_exit_code_5_maps_to_0_with_warning() -> None:
    # D-15: pytest 5 (no tests collected) -> 0 with warning line.
    mapped, warning = _map_exit_code(5)
    assert mapped == 0
    assert warning == "no tests collected"


def test_map_exit_code_130_passes_through() -> None:
    # SIGINT path -- defensive: KeyboardInterrupt is never caught, but
    # if subprocess somehow returns 130 (e.g., child caught its own SIGINT)
    # the mapping does not mangle the contract.
    assert _map_exit_code(130) == (130, None)


# ---- run_pytest_subprocess argv shape (D-01, D-02, D-11) ----

def _stub_subprocess_run_writing_xml(returncode: int = 0):
    """Build a fake subprocess.run that writes a minimal JUnit XML to the
    last --junitxml=PATH arg in argv before returning."""
    def _fake(argv, **kwargs):
        # Find the LAST --junitxml=... arg (pytest's last-occurrence rule).
        junit_args = [a for a in argv if isinstance(a, str) and a.startswith("--junitxml=")]
        if junit_args:
            path = Path(junit_args[-1].split("=", 1)[1])
            path.write_text(
                '<?xml version="1.0" encoding="utf-8"?>'
                '<testsuites><testsuite name="pytest" tests="0" failures="0" '
                'errors="0" skipped="0" time="0.01"/></testsuites>',
                encoding="utf-8",
            )
        return SimpleNamespace(
            returncode=returncode, stdout="", stderr="", args=argv,
        )
    return _fake


def test_run_pytest_subprocess_invokes_python_dash_m_pytest(monkeypatch) -> None:
    """D-01: must use [sys.executable, '-m', 'pytest', ...], not pytest.main()."""
    captured = {}

    def _fake(argv, **kwargs):
        captured["argv"] = list(argv)
        return _stub_subprocess_run_writing_xml(0)(argv, **kwargs)
    monkeypatch.setattr("mcp_test_framework._runner.subprocess.run", _fake)

    run_pytest_subprocess(junit_xml=None, pytest_args=None, raw=False)

    assert captured["argv"][0] == sys.executable
    assert captured["argv"][1] == "-m"
    assert captured["argv"][2] == "pytest"


def test_run_pytest_subprocess_default_mode_adds_tempfile_junitxml(monkeypatch) -> None:
    """D-02: default mode argv contains exactly one --junitxml=<tempfile>."""
    captured = {}

    def _fake(argv, **kwargs):
        captured["argv"] = list(argv)
        return _stub_subprocess_run_writing_xml(0)(argv, **kwargs)
    monkeypatch.setattr("mcp_test_framework._runner.subprocess.run", _fake)

    run_pytest_subprocess(junit_xml=None, pytest_args=None, raw=False)

    junit_args = [a for a in captured["argv"] if a.startswith("--junitxml=")]
    assert len(junit_args) == 1
    # Path looks tempfile-y -- ends in .xml under the OS temp dir.
    assert junit_args[0].endswith(".xml")


def test_run_pytest_subprocess_raw_mode_no_tempfile_junitxml(monkeypatch) -> None:
    """D-11: raw mode does NOT append a wrapper tempfile."""
    captured = {}

    def _fake(argv, **kwargs):
        captured["argv"] = list(argv)
        return SimpleNamespace(returncode=0, stdout="", stderr="", args=argv)
    monkeypatch.setattr("mcp_test_framework._runner.subprocess.run", _fake)

    run_pytest_subprocess(junit_xml=None, pytest_args=None, raw=True)

    # Only --junitxml=PATH that the operator passed (none here) should appear.
    junit_args = [a for a in captured["argv"] if a.startswith("--junitxml=")]
    assert junit_args == []


def test_run_pytest_subprocess_preserves_operator_junit_xml(monkeypatch, tmp_path) -> None:
    """RUNNER-05: operator --junit-xml=PATH still receives XML after subprocess."""
    operator_path = tmp_path / "operator.xml"
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_run_writing_xml(0),
    )

    rc, tmp_xml, _out, _err = run_pytest_subprocess(
        junit_xml=operator_path, pytest_args=None, raw=False,
    )
    assert rc == 0
    assert operator_path.exists(), (
        "operator --junit-xml=PATH must be populated post-subprocess via shutil.copy"
    )
    # Operator's XML should be the same content as the tempfile the wrapper
    # parses, so the content check is on existence + non-empty.
    assert operator_path.stat().st_size > 0


def test_run_pytest_subprocess_default_mode_exactly_one_junitxml(monkeypatch, tmp_path) -> None:
    """D-02 strict: even when operator passes --junit-xml=PATH, only ONE
    --junitxml=<tempfile> reaches pytest (operator path is post-subprocess copy)."""
    operator_path = tmp_path / "operator.xml"
    captured = {}

    def _fake(argv, **kwargs):
        captured["argv"] = list(argv)
        return _stub_subprocess_run_writing_xml(0)(argv, **kwargs)
    monkeypatch.setattr("mcp_test_framework._runner.subprocess.run", _fake)

    run_pytest_subprocess(junit_xml=operator_path, pytest_args=None, raw=False)

    junit_args = [a for a in captured["argv"] if a.startswith("--junitxml=")]
    assert len(junit_args) == 1, (
        f"expected exactly one --junitxml arg in default mode, got: {junit_args}"
    )
    # And the single arg points at a tempfile, NOT the operator path.
    assert str(operator_path) not in junit_args[0]


# ---- CLI surface (D-03, D-11, RUNNER-03) ----

def test_run_help_lists_raw_flag() -> None:
    """RUNNER-03: --raw is in --help."""
    result = _invoke("run", "--help")
    assert result.exit_code == 0, result.output
    assert "--raw" in result.output


def test_run_help_lists_junit_xml() -> None:
    """RUNNER-05: --junit-xml stays exposed."""
    result = _invoke("run", "--help")
    assert result.exit_code == 0, result.output
    assert "--junit-xml" in result.output


def test_run_help_does_not_list_debug() -> None:
    """Plan 04 adds --debug; Plan 01 must not expose it."""
    result = _invoke("run", "--help")
    assert result.exit_code == 0, result.output
    assert "--debug" not in result.output


def test_run_default_calls_load_config_before_subprocess(monkeypatch, tmp_path) -> None:
    """D-03: _load_config must run before subprocess in default mode.
    Test via SAFE-04: a bad --config path exits 2 with no subprocess call."""
    spy = MagicMock()
    monkeypatch.setattr("mcp_test_framework._runner.subprocess.run", spy)

    result = _invoke("run", "--config", str(tmp_path / "does-not-exist.yaml"))

    assert result.exit_code == 2
    spy.assert_not_called()  # subprocess never spawned -- config gate held.


def test_run_raw_also_calls_load_config_before_subprocess(monkeypatch, tmp_path) -> None:
    """D-11: --raw cannot bypass SAFE-03/04 -- _load_config still runs."""
    spy = MagicMock()
    monkeypatch.setattr("mcp_test_framework._runner.subprocess.run", spy)

    result = _invoke("run", "--raw", "--config", str(tmp_path / "does-not-exist.yaml"))

    assert result.exit_code == 2
    spy.assert_not_called()


def test_run_exit_code_5_maps_to_0(monkeypatch, tmp_path) -> None:
    """D-15: pytest 5 -> 0 with stderr warning."""
    # Need a valid config for _load_config to pass.
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "version: 2\nollama:\n  base_url: http://127.0.0.1:11434\n  model: q\n"
        "mcp_server:\n  command: uvx\n  args: [homelab-mcp]\ntools: {}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_run_writing_xml(5),
    )
    result = _invoke("run", "--config", str(config_path))
    assert result.exit_code == 0  # 5 mapped to 0
    # Warning goes to stderr; CliRunner mixes streams by default.
    combined = (result.output or "") + (result.stderr or "")
    assert "no tests collected" in combined


def test_run_exit_code_1_passes_through(monkeypatch, tmp_path) -> None:
    """D-15: pytest 1 (test failures) -> exit 1."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "version: 2\nollama:\n  base_url: http://127.0.0.1:11434\n  model: q\n"
        "mcp_server:\n  command: uvx\n  args: [homelab-mcp]\ntools: {}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_run_writing_xml(1),
    )
    result = _invoke("run", "--config", str(config_path))
    assert result.exit_code == 1


def test_cli_reexports_helpers_for_backward_compat() -> None:
    """Existing test imports from mcp_test_framework.cli must keep working
    after the helpers move to _runner.py (re-export preserved)."""
    from mcp_test_framework.cli import _build_pytest_args, _emit_operator_error
    assert callable(_build_pytest_args)
    assert callable(_emit_operator_error)
