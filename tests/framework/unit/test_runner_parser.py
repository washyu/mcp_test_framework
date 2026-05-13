"""Phase 14 Plan 02 unit tests: JUnit XML parser + ported aggregation helpers.

Pins Phase 14 D-02/D-05/D-08/D-09 + Phase 09 D-03 (any-fail-wins) +
Phase 13 D-12 (locked skip-reason constants).

Lives under tests/unit/ (not tests/) so it short-circuits the autouse
`_preflight` session fixture (fixtures.py:_session_needs_preflight). These
are pure-data XML round-trip tests with no MCP/Ollama dependency, matching
the established convention in tests/unit/test_reporter.py.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from mcp_test_framework._runner import (
    ParsedRun,
    ToolVerdict,
    _REASON_EXPLICIT_DEFAULT,
    _REASON_NOT_SELECTED,
    _SKIP_REASON_CAP,
    _extract_tool_name,
    _format_skip_reasons,
    _strip_pytest_skipped_prefix,
    parse_junit_xml,
)


# tests/unit/test_runner_parser.py -> tests/unit -> tests -> fixtures
_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Locked constants (Phase 13 D-12) -- regression pins, do NOT reword.
# ---------------------------------------------------------------------------


def test_runner_skip_reason_constants_locked() -> None:
    """Phase 13 D-12: two reason strings must not drift silently."""
    assert _REASON_NOT_SELECTED == "not selected in config"
    assert _REASON_EXPLICIT_DEFAULT == "explicit skip in config"


def test_skip_reason_cap_locked_at_3() -> None:
    """Phase 09 D-05: dedup + cap stays at 3."""
    assert _SKIP_REASON_CAP == 3


# ---------------------------------------------------------------------------
# _extract_tool_name (Phase 09 D-02a)
# ---------------------------------------------------------------------------


def test_extract_tool_name_returns_suffix() -> None:
    assert _extract_tool_name("test_schema[alpha]") == "alpha"


def test_extract_tool_name_returns_none_without_brackets() -> None:
    assert _extract_tool_name("test_unit_no_param") is None


def test_extract_tool_name_handles_nested_brackets() -> None:
    """rindex picks the LAST [...] -- defensive against future parametrize layering."""
    assert _extract_tool_name("test_x[outer][inner]") == "inner"


# ---------------------------------------------------------------------------
# _strip_pytest_skipped_prefix
# ---------------------------------------------------------------------------


def test_strip_prefix_strips_pytest_prefix() -> None:
    assert (
        _strip_pytest_skipped_prefix("Skipped: not selected in config")
        == "not selected in config"
    )


def test_strip_prefix_passes_through_without_prefix() -> None:
    assert _strip_pytest_skipped_prefix("no prefix here") == "no prefix here"


def test_strip_prefix_none_returns_none() -> None:
    assert _strip_pytest_skipped_prefix(None) is None


# ---------------------------------------------------------------------------
# _format_skip_reasons (Phase 09 D-05 dedup + cap)
# ---------------------------------------------------------------------------


def test_format_skip_reasons_empty() -> None:
    assert _format_skip_reasons([]) == ""


def test_format_skip_reasons_under_cap_joins_with_semicolon() -> None:
    assert _format_skip_reasons(["a", "b"]) == "a; b"


def test_format_skip_reasons_over_cap_emits_more_marker() -> None:
    """Cap at 3 + '... (N more)'."""
    out = _format_skip_reasons(["a", "b", "c", "d", "e"])
    assert out == "a; b; c; ... (2 more)"


# ---------------------------------------------------------------------------
# parse_junit_xml -- fixture round-trips
# ---------------------------------------------------------------------------


def test_parse_all_pass_fixture() -> None:
    run = parse_junit_xml(_FIXTURES / "junit-all-pass.xml")
    assert isinstance(run, ParsedRun)
    assert set(run.per_tool.keys()) == {"alpha", "beta", "gamma"}
    for tool in run.per_tool.values():
        assert isinstance(tool, ToolVerdict)
        assert tool.verdict == "PASS", f"{tool.name}: {tool.verdict}"
        assert tool.failure_message is None
        assert tool.skip_reasons == []
    assert run.total_time == pytest.approx(2.45)
    assert run.total_cases == 3
    assert run.total_failures == 0


def test_parse_one_fail_extracts_message_not_body() -> None:
    """D-08: <failure message='...'> attribute is the renderer surface.
    Body text is captured separately for --debug only."""
    run = parse_junit_xml(_FIXTURES / "junit-one-fail-with-reasoning.xml")
    beta = run.per_tool["beta"]
    assert beta.verdict == "FAIL"
    assert beta.failure_message == "parameters 3/5: 'unclear param name'"
    assert beta.failure_body is not None  # body captured for --debug
    assert "AssertionError" in beta.failure_body
    alpha = run.per_tool["alpha"]
    assert alpha.verdict == "PASS"
    assert alpha.failure_message is None


def test_parse_all_skip_strips_pytest_prefix() -> None:
    run = parse_junit_xml(_FIXTURES / "junit-all-skip.xml")
    assert set(run.per_tool.keys()) == {
        "delete_thing",
        "reboot_host",
        "wipe_disk",
        "stop_service",
    }
    for tool in run.per_tool.values():
        assert tool.verdict == "SKIP"
        assert len(tool.skip_reasons) == 1
    # Phase 13 D-12 verbatim strings appear in the parsed model
    # (the renderer downstream will surface them in the per-tool rows).
    reasons = {r for t in run.per_tool.values() for r in t.skip_reasons}
    assert _REASON_NOT_SELECTED in reasons
    assert _REASON_EXPLICIT_DEFAULT in reasons
    assert "hits production registry" in reasons


def test_parse_mixed_aggregation_matches_expected_verdicts() -> None:
    run = parse_junit_xml(_FIXTURES / "junit-mixed.xml")
    assert run.per_tool["alpha"].verdict == "PASS"
    assert run.per_tool["gamma"].verdict == "SKIP"
    assert run.per_tool["mango"].verdict == "PASS"
    assert run.per_tool["zoo"].verdict == "FAIL"


def test_parse_mixed_excludes_unparametrized_testcase() -> None:
    """D-09: testcases without `[<tool>]` suffix do NOT appear in per_tool."""
    run = parse_junit_xml(_FIXTURES / "junit-mixed.xml")
    assert "test_unit_no_param" not in run.per_tool
    assert set(run.per_tool.keys()) == {"alpha", "gamma", "mango", "zoo"}


def test_parse_mixed_total_counts_from_testsuite_attrs() -> None:
    """Summary line inputs come from <testsuite> attributes."""
    run = parse_junit_xml(_FIXTURES / "junit-mixed.xml")
    assert run.total_cases == 5
    assert run.total_failures == 1
    assert run.total_skipped == 1
    assert run.total_time == pytest.approx(8.34)


def test_parse_mixed_zoo_failure_captures_message() -> None:
    """The <failure message='...'> attribute surfaces independently from body."""
    run = parse_junit_xml(_FIXTURES / "junit-mixed.xml")
    zoo = run.per_tool["zoo"]
    assert zoo.failure_message == "parameters 3/5: 'unclear'"


def test_parse_mixed_gamma_skip_reason_stripped() -> None:
    """SKIP rows preserve the operator-supplied reason after prefix-strip."""
    run = parse_junit_xml(_FIXTURES / "junit-mixed.xml")
    gamma = run.per_tool["gamma"]
    assert gamma.skip_reasons == ["not selected in config"]


def test_parse_returns_parsedrun_with_duration_per_tool() -> None:
    """Per-tool duration sums the <testcase time='...'> attribute."""
    run = parse_junit_xml(_FIXTURES / "junit-all-pass.xml")
    assert run.per_tool["alpha"].duration == pytest.approx(0.80)
    assert run.per_tool["beta"].duration == pytest.approx(0.81)
    assert run.per_tool["gamma"].duration == pytest.approx(0.84)


# ---------------------------------------------------------------------------
# Synthesized: any-fail-wins across multiple testcases for the same tool
# ---------------------------------------------------------------------------


def test_any_fail_wins_when_failure_and_pass_share_tool(tmp_path: Path) -> None:
    """Phase 09 D-03 rule 1: FAIL is sticky across multiple cases per tool."""
    xml = tmp_path / "synth.xml"
    xml.write_text(
        '<?xml version="1.0"?>'
        '<testsuites>'
        '<testsuite name="pytest" tests="2" failures="1" skipped="0" errors="0" time="0.1">'
        '<testcase classname="t" name="test_a[foo]" time="0.05"/>'
        '<testcase classname="t" name="test_b[foo]" time="0.05">'
        '<failure message="boom">body</failure>'
        '</testcase>'
        '</testsuite></testsuites>',
        encoding="utf-8",
    )
    run = parse_junit_xml(xml)
    assert run.per_tool["foo"].verdict == "FAIL"
    assert run.per_tool["foo"].failure_message == "boom"


def test_any_fail_wins_with_pass_after_failure_in_xml_order(tmp_path: Path) -> None:
    """Order-independence: FAIL sticks even when the failed case is FIRST."""
    xml = tmp_path / "synth.xml"
    xml.write_text(
        '<?xml version="1.0"?>'
        '<testsuites>'
        '<testsuite name="pytest" tests="2" failures="1" skipped="0" errors="0" time="0.1">'
        '<testcase classname="t" name="test_a[bar]" time="0.05">'
        '<failure message="first">b</failure>'
        '</testcase>'
        '<testcase classname="t" name="test_b[bar]" time="0.05"/>'
        '</testsuite></testsuites>',
        encoding="utf-8",
    )
    run = parse_junit_xml(xml)
    assert run.per_tool["bar"].verdict == "FAIL"


def test_pass_dominates_skip_for_same_tool(tmp_path: Path) -> None:
    """If any case for a tool PASSES and another SKIPS, verdict is PASS
    (D-03 rule 2: PASS over SKIP when no FAIL)."""
    xml = tmp_path / "synth.xml"
    xml.write_text(
        '<?xml version="1.0"?>'
        '<testsuites>'
        '<testsuite name="pytest" tests="2" failures="0" skipped="1" errors="0" time="0.1">'
        '<testcase classname="t" name="test_a[baz]" time="0.05"/>'
        '<testcase classname="t" name="test_b[baz]" time="0.05">'
        '<skipped message="Skipped: pre-req missing" type="pytest.skip"/>'
        '</testcase>'
        '</testsuite></testsuites>',
        encoding="utf-8",
    )
    run = parse_junit_xml(xml)
    assert run.per_tool["baz"].verdict == "PASS"


def test_error_child_counts_as_failure(tmp_path: Path) -> None:
    """D-03a: <error> (collection/fixture errors) collapse into FAIL."""
    xml = tmp_path / "synth.xml"
    xml.write_text(
        '<?xml version="1.0"?>'
        '<testsuites>'
        '<testsuite name="pytest" tests="1" failures="0" skipped="0" errors="1" time="0.05">'
        '<testcase classname="t" name="test_x[qux]" time="0.05">'
        '<error message="setup error">trace</error>'
        '</testcase>'
        '</testsuite></testsuites>',
        encoding="utf-8",
    )
    run = parse_junit_xml(xml)
    assert run.per_tool["qux"].verdict == "FAIL"
    assert run.per_tool["qux"].failure_message == "setup error"


# ---------------------------------------------------------------------------
# Phase 18 D-09 / D-10: mcptf_error_* user_property hookup
# ---------------------------------------------------------------------------
#
# Plan 18-07's pytest_exception_interact attaches three user_properties to
# the JUnit XML <testcase>:
#   - mcptf_error_code    (str | None)
#   - mcptf_error_message (str)
#   - mcptf_error_raw     (str -- CallToolResult JSON dump; renderer-side)
#
# parse_junit_xml only reads code/message; it must compose
# failure_message = "[code] message" when code is present, bare message
# otherwise. Absence of the <properties> block preserves Phase 16 behavior.
# ---------------------------------------------------------------------------


def test_parser_uses_mcptf_error_properties_over_raw_failure_message(
    tmp_path: Path,
) -> None:
    """D-09: when mcptf_error_message present, it wins over <failure message=...>.
    D-10: when mcptf_error_code present, format is '[code] message'."""
    xml = tmp_path / "synth.xml"
    xml.write_text(
        '<?xml version="1.0"?>'
        '<testsuites>'
        '<testsuite name="pytest" tests="1" failures="1" skipped="0" errors="0" time="0.1">'
        '<testcase classname="t" name="test_x[create_vm]" time="0.05">'
        '<failure message="raw_msg" type="ToolCallError">tb</failure>'
        '<properties>'
        '<property name="mcptf_error_code" value="VM_NAME_TAKEN"/>'
        '<property name="mcptf_error_message" value="name already in use"/>'
        '</properties>'
        '</testcase>'
        '</testsuite></testsuites>',
        encoding="utf-8",
    )
    run = parse_junit_xml(xml)
    assert run.per_tool["create_vm"].verdict == "FAIL"
    assert (
        run.per_tool["create_vm"].failure_message
        == "[VM_NAME_TAKEN] name already in use"
    )


def test_parser_falls_back_to_failure_message_when_no_properties_block(
    tmp_path: Path,
) -> None:
    """D-09 regression guard (Phase 16): absence of <properties> preserves the
    raw <failure message="..."> extraction byte-identically."""
    xml = tmp_path / "synth.xml"
    xml.write_text(
        '<?xml version="1.0"?>'
        '<testsuites>'
        '<testsuite name="pytest" tests="1" failures="1" skipped="0" errors="0" time="0.1">'
        '<testcase classname="t" name="test_x[plain]" time="0.05">'
        '<failure message="raw_msg">tb</failure>'
        '</testcase>'
        '</testsuite></testsuites>',
        encoding="utf-8",
    )
    run = parse_junit_xml(xml)
    assert run.per_tool["plain"].failure_message == "raw_msg"


def test_parser_emits_bare_message_when_code_property_absent(tmp_path: Path) -> None:
    """D-10: mcptf_error_message without mcptf_error_code -> bare message
    (no brackets, no leading space)."""
    xml = tmp_path / "synth.xml"
    xml.write_text(
        '<?xml version="1.0"?>'
        '<testsuites>'
        '<testsuite name="pytest" tests="1" failures="1" skipped="0" errors="0" time="0.1">'
        '<testcase classname="t" name="test_x[bare]" time="0.05">'
        '<failure message="raw_msg">tb</failure>'
        '<properties>'
        '<property name="mcptf_error_message" value="name already in use"/>'
        '</properties>'
        '</testcase>'
        '</testsuite></testsuites>',
        encoding="utf-8",
    )
    run = parse_junit_xml(xml)
    assert run.per_tool["bare"].failure_message == "name already in use"


def test_parser_falls_back_when_code_present_but_message_absent(
    tmp_path: Path,
) -> None:
    """D-10: code alone is insufficient -- must have message. Falls back to
    <failure message=...> extraction when mcptf_error_message is missing."""
    xml = tmp_path / "synth.xml"
    xml.write_text(
        '<?xml version="1.0"?>'
        '<testsuites>'
        '<testsuite name="pytest" tests="1" failures="1" skipped="0" errors="0" time="0.1">'
        '<testcase classname="t" name="test_x[code_only]" time="0.05">'
        '<failure message="raw_msg">tb</failure>'
        '<properties>'
        '<property name="mcptf_error_code" value="VM_NAME_TAKEN"/>'
        '</properties>'
        '</testcase>'
        '</testsuite></testsuites>',
        encoding="utf-8",
    )
    run = parse_junit_xml(xml)
    assert run.per_tool["code_only"].failure_message == "raw_msg"


def test_parser_treats_empty_string_code_as_none(tmp_path: Path) -> None:
    """D-09: mcptf_error_code value='' is treated as None (code missing).
    The message is rendered bare (no '[] message' with empty brackets)."""
    xml = tmp_path / "synth.xml"
    xml.write_text(
        '<?xml version="1.0"?>'
        '<testsuites>'
        '<testsuite name="pytest" tests="1" failures="1" skipped="0" errors="0" time="0.1">'
        '<testcase classname="t" name="test_x[empty_code]" time="0.05">'
        '<failure message="raw_msg">tb</failure>'
        '<properties>'
        '<property name="mcptf_error_code" value=""/>'
        '<property name="mcptf_error_message" value="name already in use"/>'
        '</properties>'
        '</testcase>'
        '</testsuite></testsuites>',
        encoding="utf-8",
    )
    run = parse_junit_xml(xml)
    assert run.per_tool["empty_code"].failure_message == "name already in use"


def test_parser_preserves_failure_body_when_properties_present(
    tmp_path: Path,
) -> None:
    """D-09 invariant: only the message-extraction branch changes; the
    failure_body (<failure>.text) extraction is preserved byte-identically."""
    xml = tmp_path / "synth.xml"
    xml.write_text(
        '<?xml version="1.0"?>'
        '<testsuites>'
        '<testsuite name="pytest" tests="1" failures="1" skipped="0" errors="0" time="0.1">'
        '<testcase classname="t" name="test_x[body]" time="0.05">'
        '<failure message="raw_msg">traceback body text</failure>'
        '<properties>'
        '<property name="mcptf_error_code" value="X"/>'
        '<property name="mcptf_error_message" value="m"/>'
        '</properties>'
        '</testcase>'
        '</testsuite></testsuites>',
        encoding="utf-8",
    )
    run = parse_junit_xml(xml)
    assert run.per_tool["body"].failure_body == "traceback body text"
    assert run.per_tool["body"].failure_message == "[X] m"
