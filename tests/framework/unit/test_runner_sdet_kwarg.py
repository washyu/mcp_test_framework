"""Phase 18 D-04 / D-05 + Phase 25 D-07: --test-code plumbing through _runner helpers.

Pins:
- `_build_pytest_args(sdet=True, ...)` SWAPS the discovery path to
  `tests/test_code` (NOT additive; `tests/contract` is absent). The legacy
  `tests/sdet/` path is appended only when that directory contains
  `test_*.py` files (D-07 dual-discovery fallback).
- `_build_pytest_args(sdet=False, ...)` preserves Phase 14/16 default
  byte-identically (no `tests/test_code` ever appears).
- `--with-framework` remains ALWAYS additive on top of whichever
  operator-surface scope is active.
- `--sdet` / `--test-code` literal strings are NEVER appended to the
  returned argv (wrapper-owned flag; matches Phase 16 D-07 / `--explain`
  pattern).
- `run_pytest_subprocess` signature includes `sdet: bool = False` and
  forwards it to `_build_pytest_args(sdet=sdet)`.
"""
from __future__ import annotations

import inspect

import pytest

from mcp_test_framework import _runner
from mcp_test_framework._runner import _build_pytest_args, run_pytest_subprocess


# ---------------------------------------------------------------------------
# _build_pytest_args: discovery-path matrix per D-04 / D-05
# ---------------------------------------------------------------------------


def test_build_pytest_args_sdet_false_returns_contract_scope(tmp_path, monkeypatch) -> None:
    """Default (sdet=False, with_framework=False) -> ['tests/contract', ...]."""
    monkeypatch.chdir(tmp_path)
    args = _build_pytest_args(
        junit_xml=None, pytest_args=[], with_framework=False, sdet=False
    )
    assert args[0] == "tests/contract"
    assert "tests/test_code" not in args
    assert "tests/sdet" not in args


def test_build_pytest_args_sdet_true_swaps_to_test_code_scope(tmp_path, monkeypatch) -> None:
    """--test-code only -> ['tests/test_code']; tests/contract MUST be absent (SWAP, not additive).

    With no legacy tests/sdet/ directory in cwd, the dual-discovery fallback
    is inactive and argv contains only 'tests/test_code'.
    """
    monkeypatch.chdir(tmp_path)
    args = _build_pytest_args(
        junit_xml=None, pytest_args=[], with_framework=False, sdet=True
    )
    assert args[0] == "tests/test_code"
    assert "tests/contract" not in args
    # No legacy tests/sdet/ in cwd -> fallback inactive.
    assert "tests/sdet" not in args  # noqa: sdet-rename-shim


def test_build_pytest_args_sdet_true_with_legacy_dir_appends_legacy(tmp_path, monkeypatch) -> None:
    """D-07: when tests/sdet/ exists AND contains test_*.py, both paths are passed."""
    legacy = tmp_path / "tests" / "sdet"  # noqa: sdet-rename-shim
    legacy.mkdir(parents=True)
    (legacy / "test_demo.py").write_text("# noqa: sdet-rename-shim\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    args = _build_pytest_args(
        junit_xml=None, pytest_args=[], with_framework=False, sdet=True
    )
    assert args[0] == "tests/test_code"
    assert "tests/sdet" in args  # noqa: sdet-rename-shim
    assert args.index("tests/test_code") < args.index("tests/sdet")  # noqa: sdet-rename-shim


def test_build_pytest_args_sdet_true_legacy_dir_empty_is_inactive(tmp_path, monkeypatch) -> None:
    """D-07: empty tests/sdet/ (no test_*.py) does NOT activate the fallback."""
    legacy = tmp_path / "tests" / "sdet"  # noqa: sdet-rename-shim
    legacy.mkdir(parents=True)
    # No test_*.py inside -- only a stray helper file -- fallback stays off.
    (legacy / "helpers.py").write_text("\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    args = _build_pytest_args(
        junit_xml=None, pytest_args=[], with_framework=False, sdet=True
    )
    assert args == ["tests/test_code"]


def test_build_pytest_args_sdet_true_with_framework_additive(tmp_path, monkeypatch) -> None:
    """--test-code --with-framework -> ['tests/test_code', 'tests/framework'] in that order."""
    monkeypatch.chdir(tmp_path)
    args = _build_pytest_args(
        junit_xml=None, pytest_args=[], with_framework=True, sdet=True
    )
    assert "tests/test_code" in args
    assert "tests/framework" in args
    assert args.index("tests/test_code") < args.index("tests/framework")
    assert "tests/contract" not in args


def test_build_pytest_args_sdet_false_with_framework_zero_diff_from_phase16(
    tmp_path, monkeypatch
) -> None:
    """--with-framework alone -> ['tests/contract', 'tests/framework'] (Phase 16 default-path)."""
    monkeypatch.chdir(tmp_path)
    args = _build_pytest_args(
        junit_xml=None, pytest_args=[], with_framework=True, sdet=False
    )
    assert "tests/contract" in args
    assert "tests/framework" in args
    assert args.index("tests/contract") < args.index("tests/framework")
    assert "tests/test_code" not in args
    assert "tests/sdet" not in args  # noqa: sdet-rename-shim


def test_build_pytest_args_sdet_literal_never_in_argv(tmp_path, monkeypatch) -> None:
    """--sdet / --test-code are wrapper-owned; literal strings MUST NOT appear in argv."""
    monkeypatch.chdir(tmp_path)
    args = _build_pytest_args(
        junit_xml=None, pytest_args=[], with_framework=True, sdet=True
    )
    assert "--sdet" not in args  # noqa: sdet-rename-shim
    assert "--test-code" not in args


def test_build_pytest_args_forwarded_args_appended_after_scope(tmp_path, monkeypatch) -> None:
    """Operator passthrough args trail the scope paths (Phase 09 D-01a precedence preserved)."""
    monkeypatch.chdir(tmp_path)
    args = _build_pytest_args(
        junit_xml=None, pytest_args=["-k", "thing"], with_framework=False, sdet=True
    )
    assert args[0] == "tests/test_code"
    assert args[-2:] == ["-k", "thing"]


# ---------------------------------------------------------------------------
# Signature contracts
# ---------------------------------------------------------------------------


def test_build_pytest_args_has_sdet_kwarg_default_false() -> None:
    sig = inspect.signature(_build_pytest_args)
    assert "sdet" in sig.parameters
    assert sig.parameters["sdet"].default is False


def test_run_pytest_subprocess_has_sdet_kwarg_default_false() -> None:
    sig = inspect.signature(run_pytest_subprocess)
    assert "sdet" in sig.parameters
    assert sig.parameters["sdet"].default is False


# ---------------------------------------------------------------------------
# run_pytest_subprocess forwards sdet to _build_pytest_args
# ---------------------------------------------------------------------------


def test_run_pytest_subprocess_forwards_sdet_to_build_args(monkeypatch, tmp_path) -> None:
    """When run_pytest_subprocess is called with sdet=True, the argv handed to
    subprocess.run includes `tests/test_code` and excludes `tests/contract`."""
    from types import SimpleNamespace

    monkeypatch.chdir(tmp_path)
    captured: dict = {}

    def fake_run(argv, **kwargs):
        captured["argv"] = list(argv)
        # In raw mode, no tempfile is expected, no XML write needed.
        return SimpleNamespace(returncode=0, stdout="", stderr="", args=argv)

    monkeypatch.setattr(_runner.subprocess, "run", fake_run)

    rc, tmp, _stdout, _stderr = run_pytest_subprocess(
        junit_xml=None,
        pytest_args=[],
        raw=True,
        with_framework=False,
        sdet=True,
    )
    assert rc == 0
    argv = captured["argv"]
    assert "tests/test_code" in argv
    assert "tests/contract" not in argv
    assert "--sdet" not in argv  # wrapper-owned: never forwarded  # noqa: sdet-rename-shim
    assert "--test-code" not in argv  # wrapper-owned: never forwarded
