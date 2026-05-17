"""Phase 29 Plan 01 unit tests: live TestReport adapter.

Pins Phase 29 D-01 (build ParsedRun at session end via _build_parsed_run_from_reports)
+ D-01a (adapter co-located with parse_junit_xml in _runner.py) + REPORTER-01
(live event-driven path, NOT JUnit XML parsing).

The adapter must produce ParsedRun instances field-equal to parse_junit_xml
when fed the equivalent TestReport sequence. Phase-precedence semantics
(any-fail-wins, setup-skip recognition, teardown-failure promotion to FAIL)
are pinned across >=10 cases here.

Lives under tests/framework/unit/ so it short-circuits the autouse
_preflight session fixture (fixtures.py:_session_needs_preflight). These
are pure-data adapter tests with no MCP/Ollama dependency, matching the
established convention in tests/framework/unit/test_runner_parser.py.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from mcp_test_framework._runner import (
    ParsedRun,
    ToolVerdict,
    _build_parsed_run_from_reports,
    parse_junit_xml,
)


# ---------------------------------------------------------------------------
# TestReport factory helper (NOT a pytest fixture; a plain factory function so
# each test constructs reports inline).
# ---------------------------------------------------------------------------


def _make_report(
    nodeid: str,
    when: str,
    outcome: str,
    duration: float = 0.01,
    longrepr: object = None,
    user_properties: list[tuple[str, object]] | None = None,
) -> pytest.TestReport:
    """Construct a TestReport without running pytest.

    pytest.TestReport.__init__ accepts these kwargs in pytest >=9.0.
    """
    return pytest.TestReport(
        nodeid=nodeid,
        location=("dummy.py", 0, nodeid),
        keywords={},
        outcome=outcome,
        longrepr=longrepr,
        when=when,
        sections=[],
        duration=duration,
        user_properties=user_properties or [],
    )


# ---------------------------------------------------------------------------
# Phase-precedence semantics (Pitfall 1: three phase reports per nodeid)
# ---------------------------------------------------------------------------


def test_three_phase_pass_produces_one_case() -> None:
    """Three reports for one parametrized nodeid all passed -> single case.

    WR-01: bucket.duration mirrors pytest's JUnit writer's default
    `<testcase time>` (call-phase only), so the three-phase run reports
    the call-phase duration (0.01), NOT the setup+call+teardown sum.
    """
    nodeid = "tests/contract/test_x.py::test_y[mytool]"
    reports = [
        _make_report(nodeid, "setup", "passed", duration=0.01),
        _make_report(nodeid, "call", "passed", duration=0.01),
        _make_report(nodeid, "teardown", "passed", duration=0.01),
    ]
    run = _build_parsed_run_from_reports(reports)
    assert run.total_cases == 1
    assert "mytool" in run.per_tool
    bucket = run.per_tool["mytool"]
    assert bucket.case_count == 1
    assert bucket.verdict == "PASS"
    assert bucket.duration == pytest.approx(0.01)


def test_call_failure_produces_fail_verdict() -> None:
    """Call-phase FAIL -> verdict=FAIL with failure_message from longrepr."""
    nodeid = "tests/contract/test_x.py::test_y[mytool]"
    reports = [
        _make_report(nodeid, "setup", "passed"),
        _make_report(nodeid, "call", "failed", longrepr="boom\nstack trace line 2"),
        _make_report(nodeid, "teardown", "passed"),
    ]
    run = _build_parsed_run_from_reports(reports)
    bucket = run.per_tool["mytool"]
    assert bucket.verdict == "FAIL"
    assert bucket.failure_message == "boom"
    assert bucket.failure_body is not None
    assert bucket.failure_body.startswith("boom")


def test_setup_failure_produces_fail_verdict() -> None:
    """Setup FAILED with no call/teardown -> verdict=FAIL (any-fail-wins)."""
    nodeid = "tests/contract/test_x.py::test_y[mytool]"
    reports = [
        _make_report(nodeid, "setup", "failed", longrepr="setup-broke"),
    ]
    run = _build_parsed_run_from_reports(reports)
    bucket = run.per_tool["mytool"]
    assert bucket.verdict == "FAIL"


def test_teardown_failure_promotes_to_fail() -> None:
    """Setup PASS + call PASS + teardown FAIL -> verdict=FAIL (sticky)."""
    nodeid = "tests/contract/test_x.py::test_y[mytool]"
    reports = [
        _make_report(nodeid, "setup", "passed"),
        _make_report(nodeid, "call", "passed"),
        _make_report(nodeid, "teardown", "failed", longrepr="teardown-broke"),
    ]
    run = _build_parsed_run_from_reports(reports)
    bucket = run.per_tool["mytool"]
    assert bucket.verdict == "FAIL"


def test_setup_skipped_produces_skip() -> None:
    """Setup SKIPPED with reason -> verdict=SKIP, skip_reasons populated."""
    nodeid = "tests/contract/test_x.py::test_y[mytool]"
    reports = [
        _make_report(
            nodeid,
            "setup",
            "skipped",
            longrepr=("file.py", 1, "Skipped: fixture missing"),
        ),
    ]
    run = _build_parsed_run_from_reports(reports)
    bucket = run.per_tool["mytool"]
    assert bucket.verdict == "SKIP"
    assert bucket.skip_reasons == ["fixture missing"]


# ---------------------------------------------------------------------------
# Pitfall 4: ToolCallError properties on user_properties (NOT XML <property>)
# ---------------------------------------------------------------------------


def test_user_properties_mcptf_error_code_and_message() -> None:
    """user_properties code+message -> failure_message == '[code] message'."""
    nodeid = "tests/contract/test_x.py::test_y[mytool]"
    reports = [
        _make_report(nodeid, "setup", "passed"),
        _make_report(
            nodeid,
            "call",
            "failed",
            longrepr="raw-failure",
            user_properties=[
                ("mcptf_error_code", "E001"),
                ("mcptf_error_message", "boom"),
            ],
        ),
        _make_report(nodeid, "teardown", "passed"),
    ]
    run = _build_parsed_run_from_reports(reports)
    bucket = run.per_tool["mytool"]
    assert bucket.failure_message == "[E001] boom"


def test_user_properties_message_without_code() -> None:
    """user_properties with only message -> failure_message=='boom' (no brackets)."""
    nodeid = "tests/contract/test_x.py::test_y[mytool]"
    reports = [
        _make_report(nodeid, "setup", "passed"),
        _make_report(
            nodeid,
            "call",
            "failed",
            longrepr="raw-failure",
            user_properties=[("mcptf_error_message", "boom")],
        ),
        _make_report(nodeid, "teardown", "passed"),
    ]
    run = _build_parsed_run_from_reports(reports)
    bucket = run.per_tool["mytool"]
    assert bucket.failure_message == "boom"


# ---------------------------------------------------------------------------
# Scenario fall-through (test_code + legacy sdet shim) — mirror of
# parse_junit_xml:540-563.
# ---------------------------------------------------------------------------


def test_scenario_test_code_fall_through() -> None:
    """tests/test_code nodeid (no [...] suffix) -> synthetic group::row key."""
    nodeid = "tests/test_code/test_lifecycle.py::test_create_then_delete"
    reports = [
        _make_report(nodeid, "setup", "passed"),
        _make_report(nodeid, "call", "passed"),
        _make_report(nodeid, "teardown", "passed"),
    ]
    run = _build_parsed_run_from_reports(reports)
    assert list(run.per_tool.keys()) == ["lifecycle::create_then_delete"]
    bucket = run.per_tool["lifecycle::create_then_delete"]
    assert bucket.verdict == "PASS"


def test_scenario_legacy_sdet_fall_through() -> None:  # noqa: sdet-rename-shim
    """tests/sdet legacy nodeid -> synthetic group::row key (rename shim)."""
    nodeid = "tests/sdet/test_legacy.py::test_foo"  # noqa: sdet-rename-shim
    reports = [
        _make_report(nodeid, "setup", "passed"),
        _make_report(nodeid, "call", "passed"),
        _make_report(nodeid, "teardown", "passed"),
    ]
    run = _build_parsed_run_from_reports(reports)
    assert list(run.per_tool.keys()) == ["legacy::foo"]


# ---------------------------------------------------------------------------
# Totals aggregation across buckets.
# ---------------------------------------------------------------------------


def test_totals_sum_across_buckets() -> None:
    """Mixed PASS/FAIL/SKIP across multiple nodeids -> correct totals."""
    nid_pass = "tests/contract/test_x.py::test_y[tool_pass]"
    nid_fail = "tests/contract/test_x.py::test_y[tool_fail]"
    nid_skip = "tests/contract/test_x.py::test_y[tool_skip]"
    reports = [
        # tool_pass: all pass
        _make_report(nid_pass, "setup", "passed", duration=0.01),
        _make_report(nid_pass, "call", "passed", duration=0.01),
        _make_report(nid_pass, "teardown", "passed", duration=0.01),
        # tool_fail: call failed
        _make_report(nid_fail, "setup", "passed", duration=0.01),
        _make_report(nid_fail, "call", "failed", duration=0.02, longrepr="boom"),
        _make_report(nid_fail, "teardown", "passed", duration=0.01),
        # tool_skip: setup skipped
        _make_report(
            nid_skip,
            "setup",
            "skipped",
            duration=0.01,
            longrepr=("file.py", 1, "Skipped: not needed"),
        ),
    ]
    run = _build_parsed_run_from_reports(reports)
    assert run.total_cases == 3
    assert run.total_failures == 1
    assert run.total_skipped == 1
    # WR-01: bucket.duration is the call-phase duration (matches pytest's
    # JUnit writer default `<testcase time>`), with a setup-skip fallback
    # that sums the available phases when no call report exists.
    # tool_pass: call=0.01 -> 0.01
    # tool_fail: call=0.02 -> 0.02
    # tool_skip: setup-skip fallback (no call) -> 0.01
    # Total: 0.01 + 0.02 + 0.01 = 0.04
    assert run.total_time == pytest.approx(0.04)


# ---------------------------------------------------------------------------
# Field-equal parity with parse_junit_xml on a paired-fixture run.
# ---------------------------------------------------------------------------


def test_field_equal_to_parse_junit_xml(tmp_path: Path) -> None:
    """parse_junit_xml(xml) and _build_parsed_run_from_reports(reports) agree.

    Given a JUnit XML fixture AND a list of TestReport objects representing
    the same logical run, the two adapters produce equal per_tool keys /
    verdicts / failure_messages / case_counts and equal aggregate totals.
    """
    xml_text = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<testsuite name="pytest" tests="2" failures="1" errors="0" '
        'skipped="0" time="0.06">\n'
        '  <testcase classname="tests.contract.test_mcp_tool_contract" '
        'name="test_schema[tool_a]" time="0.03"/>\n'
        '  <testcase classname="tests.contract.test_mcp_tool_contract" '
        'name="test_schema[tool_b]" time="0.03">\n'
        '    <failure message="oops">trace</failure>\n'
        '    <properties>\n'
        '      <property name="mcptf_error_code" value="E001"/>\n'
        '      <property name="mcptf_error_message" value="oops"/>\n'
        '    </properties>\n'
        '  </testcase>\n'
        '</testsuite>\n'
    )
    xml_path = tmp_path / "junit.xml"
    xml_path.write_text(xml_text, encoding="utf-8")

    # Equivalent TestReport sequence for the same logical run.
    nid_a = "tests/contract/test_mcp_tool_contract.py::test_schema[tool_a]"
    nid_b = "tests/contract/test_mcp_tool_contract.py::test_schema[tool_b]"
    reports = [
        _make_report(nid_a, "setup", "passed", duration=0.01),
        _make_report(nid_a, "call", "passed", duration=0.01),
        _make_report(nid_a, "teardown", "passed", duration=0.01),
        _make_report(nid_b, "setup", "passed", duration=0.01),
        _make_report(
            nid_b,
            "call",
            "failed",
            duration=0.01,
            longrepr="trace",
            user_properties=[
                ("mcptf_error_code", "E001"),
                ("mcptf_error_message", "oops"),
            ],
        ),
        _make_report(nid_b, "teardown", "passed", duration=0.01),
    ]

    xml_parsed = parse_junit_xml(xml_path)
    live_parsed = _build_parsed_run_from_reports(reports)

    assert set(xml_parsed.per_tool.keys()) == set(live_parsed.per_tool.keys())
    for tool in xml_parsed.per_tool:
        x = xml_parsed.per_tool[tool]
        live = live_parsed.per_tool[tool]
        assert x.verdict == live.verdict, f"verdict mismatch for {tool}"
        assert x.failure_message == live.failure_message, (
            f"failure_message mismatch for {tool}: "
            f"xml={x.failure_message!r} live={live.failure_message!r}"
        )
        assert x.case_count == live.case_count, f"case_count mismatch for {tool}"
    assert xml_parsed.total_failures == live_parsed.total_failures
    assert xml_parsed.total_cases == live_parsed.total_cases
