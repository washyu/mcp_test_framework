"""--test-code plumbing through _runner helpers.

Pins:
- `_build_pytest_args(test_code=True, ...)` SWAPS the discovery path to
  `tests/test_code` (NOT additive; `tests/contract` is absent). The
  legacy `tests/sdet/` dual-discovery fallback was removed in v1.5;
  argv now contains only `tests/test_code` regardless of whether
  `tests/sdet/` exists on disk.
- `_build_pytest_args(test_code=False, ...)` preserves the historic
  default byte-identically (no `tests/test_code` ever appears).
- `--with-framework` remains ALWAYS additive on top of whichever
  operator-surface scope is active.
- The wrapper-owned `--test-code` literal never reaches pytest argv.
- `run_pytest_subprocess` signature includes `test_code: bool = False`
  and forwards it to `_build_pytest_args(test_code=test_code)`.
"""
from __future__ import annotations

import inspect

from mcp_test_framework import _runner
from mcp_test_framework._runner import _build_pytest_args, run_pytest_subprocess


# ---------------------------------------------------------------------------
# _build_pytest_args: discovery-path matrix
# ---------------------------------------------------------------------------


def test_build_pytest_args_test_code_false_returns_contract_scope(tmp_path, monkeypatch) -> None:
    """Default (test_code=False, with_framework=False) -> ['tests/contract', ...]."""
    monkeypatch.chdir(tmp_path)
    args = _build_pytest_args(
        junit_xml=None, pytest_args=[], with_framework=False, test_code=False
    )
    assert args[0] == "tests/contract"
    assert "tests/test_code" not in args


def test_build_pytest_args_test_code_true_swaps_to_test_code_scope(tmp_path, monkeypatch) -> None:
    """--test-code only -> ['tests/test_code']; tests/contract MUST be absent (SWAP, not additive)."""
    monkeypatch.chdir(tmp_path)
    args = _build_pytest_args(
        junit_xml=None, pytest_args=[], with_framework=False, test_code=True
    )
    assert args[0] == "tests/test_code"
    assert "tests/contract" not in args


def test_build_pytest_args_test_code_true_with_legacy_dir_does_not_add_it(
    tmp_path, monkeypatch
) -> None:
    """v1.5 single-discovery: the legacy directory's presence does NOT add it to argv."""
    legacy = tmp_path / "tests" / "sdet"
    legacy.mkdir(parents=True)
    (legacy / "test_demo.py").write_text("# stale test file\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    args = _build_pytest_args(
        junit_xml=None, pytest_args=[], with_framework=False, test_code=True
    )
    assert args == ["tests/test_code"]


def test_build_pytest_args_test_code_true_with_framework_additive(
    tmp_path, monkeypatch
) -> None:
    """--test-code --with-framework -> ['tests/test_code', 'tests/framework'] in that order."""
    monkeypatch.chdir(tmp_path)
    args = _build_pytest_args(
        junit_xml=None, pytest_args=[], with_framework=True, test_code=True
    )
    assert "tests/test_code" in args
    assert "tests/framework" in args
    assert args.index("tests/test_code") < args.index("tests/framework")
    assert "tests/contract" not in args


def test_build_pytest_args_test_code_false_with_framework_default_pair(
    tmp_path, monkeypatch
) -> None:
    """--with-framework alone -> ['tests/contract', 'tests/framework']."""
    monkeypatch.chdir(tmp_path)
    args = _build_pytest_args(
        junit_xml=None, pytest_args=[], with_framework=True, test_code=False
    )
    assert "tests/contract" in args
    assert "tests/framework" in args
    assert args.index("tests/contract") < args.index("tests/framework")
    assert "tests/test_code" not in args


def test_build_pytest_args_test_code_literal_never_in_argv(tmp_path, monkeypatch) -> None:
    """--test-code is wrapper-owned; the literal string MUST NOT appear in argv."""
    monkeypatch.chdir(tmp_path)
    args = _build_pytest_args(
        junit_xml=None, pytest_args=[], with_framework=True, test_code=True
    )
    assert "--test-code" not in args


def test_build_pytest_args_forwarded_args_appended_after_scope(tmp_path, monkeypatch) -> None:
    """Operator passthrough args trail the scope paths."""
    monkeypatch.chdir(tmp_path)
    args = _build_pytest_args(
        junit_xml=None, pytest_args=["-k", "thing"], with_framework=False, test_code=True
    )
    assert args[0] == "tests/test_code"
    assert args[-2:] == ["-k", "thing"]


# ---------------------------------------------------------------------------
# Signature contracts
# ---------------------------------------------------------------------------


def test_build_pytest_args_has_test_code_kwarg_default_false() -> None:
    sig = inspect.signature(_build_pytest_args)
    assert "test_code" in sig.parameters
    assert sig.parameters["test_code"].default is False
    # Verify the legacy kwarg name is gone.
    assert "sdet" not in sig.parameters


def test_run_pytest_subprocess_has_test_code_kwarg_default_false() -> None:
    sig = inspect.signature(run_pytest_subprocess)
    assert "test_code" in sig.parameters
    assert sig.parameters["test_code"].default is False
    assert "sdet" not in sig.parameters


# ---------------------------------------------------------------------------
# run_pytest_subprocess forwards test_code to _build_pytest_args
# ---------------------------------------------------------------------------


def test_run_pytest_subprocess_forwards_test_code_to_build_args(monkeypatch, tmp_path) -> None:
    """When run_pytest_subprocess is called with test_code=True, the argv handed to
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
        test_code=True,
    )
    assert rc == 0
    argv = captured["argv"]
    assert "tests/test_code" in argv
    assert "tests/contract" not in argv
    assert "--test-code" not in argv  # wrapper-owned: never forwarded
