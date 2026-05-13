"""Unit tests for tests/sdet/conftest.py:pytest_exception_interact (D-09 + D-11).

Pins the strict-ToolCallError behavior of the SDET-only conftest hook:
  - D-09: stash (.code, .message) onto report.user_properties.
  - D-11: stash CallToolResult.model_dump_json(indent=2) onto report.user_properties
    so the --debug appendix can render the raw block.

The hook is module-level in tests/sdet/conftest.py and only enriches
ToolCallError. Other exceptions (AssertionError, RuntimeError, etc.) pass
through untouched -- generic exception enrichment is a v1.4 candidate.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.types import CallToolResult, TextContent

from mcp_test_framework.sdet import ToolCallError


# --- Helpers --------------------------------------------------------------


def _load_sdet_conftest():
    """Load tests/sdet/conftest.py as a module via importlib.

    We can't `import tests.sdet.conftest` directly because pytest plugin
    machinery owns conftest loading. importlib.util gives a clean handle to
    the module's symbols for unit-testing the hook in isolation.
    """
    path = Path(__file__).resolve().parents[3] / "tests" / "sdet" / "conftest.py"
    spec = importlib.util.spec_from_file_location("sdet_conftest_under_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_call(exc: BaseException | None):
    """Build a fake `call` object with the .excinfo.value attribute pytest uses."""
    if exc is None:
        return SimpleNamespace(excinfo=None)
    excinfo = SimpleNamespace(value=exc)
    return SimpleNamespace(excinfo=excinfo)


def _make_report():
    """Build a fake `report` with a mutable user_properties list."""
    return SimpleNamespace(user_properties=[])


def _make_raw_call_tool_result(*, is_error: bool = True, structured: dict | None = None, text: str = "boom"):
    return CallToolResult(
        isError=is_error,
        content=[TextContent(type="text", text=text)],
        structuredContent=structured,
    )


# --- Tests ----------------------------------------------------------------


def test_hook_is_module_level():
    """The hook function must be importable as a top-level attribute."""
    mod = _load_sdet_conftest()
    assert callable(getattr(mod, "pytest_exception_interact", None)), (
        "tests/sdet/conftest.py must define a module-level "
        "pytest_exception_interact function"
    )


def test_hook_appends_three_properties_for_tool_call_error():
    """D-09 + D-11: three properties, in order: code, message, raw."""
    mod = _load_sdet_conftest()
    raw = _make_raw_call_tool_result(
        structured={"code": "VM_X", "message": "boom"},
        text='{"code": "VM_X", "message": "boom"}',
    )
    exc = ToolCallError(tool="x", code="VM_X", message="boom", raw=raw)
    report = _make_report()

    mod.pytest_exception_interact(node=None, call=_make_call(exc), report=report)

    keys = [k for (k, _) in report.user_properties]
    assert keys == ["mcptf_error_code", "mcptf_error_message", "mcptf_error_raw"], (
        f"expected three properties in code/message/raw order, got: {keys}"
    )
    values = dict(report.user_properties)
    assert values["mcptf_error_code"] == "VM_X"
    assert values["mcptf_error_message"] == "boom"


def test_hook_emits_empty_string_when_code_is_none():
    """JUnit XML attribute values are strings; None becomes ''."""
    mod = _load_sdet_conftest()
    raw = _make_raw_call_tool_result()
    exc = ToolCallError(tool="x", code=None, message="boom", raw=raw)
    report = _make_report()

    mod.pytest_exception_interact(node=None, call=_make_call(exc), report=report)

    values = dict(report.user_properties)
    assert values["mcptf_error_code"] == "", (
        "code=None must coerce to empty string (not None, not 'None')"
    )


def test_hook_emits_empty_raw_when_raw_attribute_missing():
    """When exc.raw is None the mcptf_error_raw value is empty string."""
    mod = _load_sdet_conftest()
    # Bypass ToolCallError __init__ to set raw=None (the dataclass-style
    # constructor takes a real CallToolResult; raw=None is a defensive
    # path the hook must still survive).
    exc = ToolCallError.__new__(ToolCallError)
    exc.tool = "x"
    exc.code = None
    exc.message = "boom"
    exc.raw = None  # type: ignore[assignment]
    report = _make_report()

    mod.pytest_exception_interact(node=None, call=_make_call(exc), report=report)

    values = dict(report.user_properties)
    assert values["mcptf_error_raw"] == "", (
        "raw=None must produce empty string, not 'null' / 'None'"
    )


def test_hook_serializes_call_tool_result_as_json_dict():
    """D-11 round-trip: mcptf_error_raw is json.loads-parseable and carries
    the CallToolResult schema keys (isError / content / structuredContent)."""
    mod = _load_sdet_conftest()
    raw = _make_raw_call_tool_result(
        structured={"code": "X", "message": "Y"},
        text="boom",
    )
    exc = ToolCallError(tool="x", code="X", message="Y", raw=raw)
    report = _make_report()

    mod.pytest_exception_interact(node=None, call=_make_call(exc), report=report)

    values = dict(report.user_properties)
    raw_dump = values["mcptf_error_raw"]
    parsed = json.loads(raw_dump)
    assert "isError" in parsed
    assert "content" in parsed
    assert "structuredContent" in parsed
    assert parsed["isError"] is True
    assert parsed["structuredContent"] == {"code": "X", "message": "Y"}


def test_hook_uses_indented_json_form():
    """D-11: model_dump_json(indent=2) so renderer can splice without reflowing."""
    mod = _load_sdet_conftest()
    raw = _make_raw_call_tool_result(structured={"code": "X", "message": "Y"})
    exc = ToolCallError(tool="x", code="X", message="Y", raw=raw)
    report = _make_report()

    mod.pytest_exception_interact(node=None, call=_make_call(exc), report=report)

    values = dict(report.user_properties)
    raw_dump = values["mcptf_error_raw"]
    # Indent=2 form has newlines and leading spaces; flat dump has neither.
    assert "\n" in raw_dump, "expected indented JSON (newlines present)"
    assert "  " in raw_dump, "expected indented JSON (two-space indent present)"


def test_hook_noop_when_call_excinfo_is_none():
    """No exception -> no user_properties mutation."""
    mod = _load_sdet_conftest()
    report = _make_report()
    mod.pytest_exception_interact(node=None, call=_make_call(None), report=report)
    assert report.user_properties == []


def test_hook_strict_ignores_non_tool_call_error():
    """D-09 strict: ONLY ToolCallError is enriched. AssertionError passes through."""
    mod = _load_sdet_conftest()
    report = _make_report()
    mod.pytest_exception_interact(
        node=None, call=_make_call(AssertionError("nope")), report=report
    )
    assert report.user_properties == []


def test_hook_strict_ignores_runtime_error():
    """Same strict gate for RuntimeError -- generic enrichment is a v1.4 candidate."""
    mod = _load_sdet_conftest()
    report = _make_report()
    mod.pytest_exception_interact(
        node=None, call=_make_call(RuntimeError("kaboom")), report=report
    )
    assert report.user_properties == []
