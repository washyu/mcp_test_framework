"""Phase 18 D-04 / D-05: --sdet plumbing through _runner helpers.

Pins:
- `_build_pytest_args(sdet=True, ...)` SWAPS the discovery path to `tests/sdet`
  (NOT additive; `tests/contract` is absent).
- `_build_pytest_args(sdet=False, ...)` preserves Phase 14/16 default
  byte-identically (no `tests/sdet` ever appears).
- `--with-framework` remains ALWAYS additive on top of whichever
  operator-surface scope is active.
- `--sdet` literal string is NEVER appended to the returned argv
  (wrapper-owned flag; matches Phase 16 D-07 / `--explain` pattern).
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


def test_build_pytest_args_sdet_false_returns_contract_scope() -> None:
    """Default (sdet=False, with_framework=False) -> ['tests/contract', ...]."""
    args = _build_pytest_args(
        junit_xml=None, pytest_args=[], with_framework=False, sdet=False
    )
    assert args[0] == "tests/contract"
    assert "tests/sdet" not in args


def test_build_pytest_args_sdet_true_swaps_to_sdet_scope() -> None:
    """--sdet only -> ['tests/sdet']; tests/contract MUST be absent (SWAP, not additive)."""
    args = _build_pytest_args(
        junit_xml=None, pytest_args=[], with_framework=False, sdet=True
    )
    assert args[0] == "tests/sdet"
    assert "tests/contract" not in args


def test_build_pytest_args_sdet_true_with_framework_additive() -> None:
    """--sdet --with-framework -> ['tests/sdet', 'tests/framework'] in that order."""
    args = _build_pytest_args(
        junit_xml=None, pytest_args=[], with_framework=True, sdet=True
    )
    assert "tests/sdet" in args
    assert "tests/framework" in args
    assert args.index("tests/sdet") < args.index("tests/framework")
    assert "tests/contract" not in args


def test_build_pytest_args_sdet_false_with_framework_zero_diff_from_phase16() -> None:
    """--with-framework alone -> ['tests/contract', 'tests/framework'] (Phase 16 default-path)."""
    args = _build_pytest_args(
        junit_xml=None, pytest_args=[], with_framework=True, sdet=False
    )
    assert "tests/contract" in args
    assert "tests/framework" in args
    assert args.index("tests/contract") < args.index("tests/framework")
    assert "tests/sdet" not in args


def test_build_pytest_args_sdet_literal_never_in_argv() -> None:
    """--sdet is wrapper-owned; the literal string MUST NOT appear in argv (D-07 inherit)."""
    args = _build_pytest_args(
        junit_xml=None, pytest_args=[], with_framework=True, sdet=True
    )
    assert "--sdet" not in args


def test_build_pytest_args_forwarded_args_appended_after_scope() -> None:
    """Operator passthrough args trail the scope paths (Phase 09 D-01a precedence preserved)."""
    args = _build_pytest_args(
        junit_xml=None, pytest_args=["-k", "thing"], with_framework=False, sdet=True
    )
    assert args[0] == "tests/sdet"
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


def test_run_pytest_subprocess_forwards_sdet_to_build_args(monkeypatch) -> None:
    """When run_pytest_subprocess is called with sdet=True, the argv handed to
    subprocess.run includes `tests/sdet` and excludes `tests/contract`."""
    from types import SimpleNamespace

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
    assert "tests/sdet" in argv
    assert "tests/contract" not in argv
    assert "--sdet" not in argv  # wrapper-owned: never forwarded
