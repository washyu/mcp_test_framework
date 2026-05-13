"""Phase 18 D-11: --debug appendix emits ToolCallError dump block.

Pins:
- `_extract_tool_call_errors_from_xml` and `_ToolCallErrorRecord` exist.
- The helper returns one record per testcase carrying mcptf_error_*
  user_properties, reading all three (code, message, raw).
- The helper returns [] when XML lacks ToolCallError-attached testcases
  (D-13 invariant: --debug appendix unchanged when no ToolCallError fires).
- `render_debug_appendix(xml_path=...)` emits the dump block BEFORE the
  `--- raw pytest output ---` lead-in when properties present.
- The dump block carries tool / code / message / raw lines per CONTEXT.md
  lines 123-134 (D-11). Each line of the raw CallToolResult JSON dump is
  indented 2 spaces under the `raw:` label.
- When `mcptf_error_raw` is empty, the dump emits `raw: (none)` (NOT a
  fallback workaround message).
- When `code` is absent / empty, the line reads `code: (none)`.
- When `xml_path` is None or absent, the appendix is byte-identical to the
  Phase 14 baseline (D-13 invariant).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from mcp_test_framework._runner import (
    _extract_tool_call_errors_from_xml,
    _ToolCallErrorRecord,
    parse_junit_xml,
    render_debug_appendix,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_xml(tmp_path: Path, properties_block: str = "") -> Path:
    """Write a synthesized JUnit XML and return its path."""
    body = (
        '<?xml version="1.0"?>'
        '<testsuites>'
        '<testsuite name="pytest" tests="1" failures="1" skipped="0" '
        'errors="0" time="0.1">'
        '<testcase classname="t" name="test_create_vm[create_vm]" time="0.05">'
        '<failure message="raw" type="ToolCallError">tb</failure>'
        f'{properties_block}'
        '</testcase>'
        '</testsuite></testsuites>'
    )
    xml = tmp_path / "synth.xml"
    xml.write_text(body, encoding="utf-8")
    return xml


def _make_xml_no_failure(tmp_path: Path) -> Path:
    """XML with all-pass cases, no ToolCallError, no <properties> block."""
    xml = tmp_path / "pass.xml"
    xml.write_text(
        '<?xml version="1.0"?>'
        '<testsuites>'
        '<testsuite name="pytest" tests="1" failures="0" skipped="0" '
        'errors="0" time="0.05">'
        '<testcase classname="t" name="test_ok[x]" time="0.05"/>'
        '</testsuite></testsuites>',
        encoding="utf-8",
    )
    return xml


# ---------------------------------------------------------------------------
# _extract_tool_call_errors_from_xml
# ---------------------------------------------------------------------------


def test_extract_returns_empty_when_no_properties(tmp_path: Path) -> None:
    """D-13 invariant: appendix unchanged when no ToolCallError fires."""
    xml = _make_xml(tmp_path, properties_block="")
    records = _extract_tool_call_errors_from_xml(xml)
    assert records == []


def test_extract_returns_empty_when_xml_missing(tmp_path: Path) -> None:
    """Missing XML -> [] (no crash)."""
    records = _extract_tool_call_errors_from_xml(tmp_path / "nonexistent.xml")
    assert records == []


def test_extract_returns_empty_when_xml_malformed(tmp_path: Path) -> None:
    """Malformed XML -> [] (no crash)."""
    xml = tmp_path / "broken.xml"
    xml.write_text("not xml at all <<", encoding="utf-8")
    records = _extract_tool_call_errors_from_xml(xml)
    assert records == []


def test_extract_reads_all_three_properties(tmp_path: Path) -> None:
    """D-11: code + message + raw all parsed onto _ToolCallErrorRecord."""
    raw_json = '{\n  "isError": true,\n  "content": []\n}'
    # XML attribute value: " and \n must be escaped via &quot; and &#10;
    raw_attr = raw_json.replace('"', '&quot;').replace('\n', '&#10;')
    xml = _make_xml(
        tmp_path,
        properties_block=(
            '<properties>'
            '<property name="mcptf_error_code" value="VM_NAME_TAKEN"/>'
            '<property name="mcptf_error_message" value="name already in use"/>'
            f'<property name="mcptf_error_raw" value="{raw_attr}"/>'
            '</properties>'
        ),
    )
    records = _extract_tool_call_errors_from_xml(xml)
    assert len(records) == 1
    rec = records[0]
    assert isinstance(rec, _ToolCallErrorRecord)
    assert rec.code == "VM_NAME_TAKEN"
    assert rec.message == "name already in use"
    assert rec.raw == raw_json
    # tool field = the testcase name (Plan 18-07 sets it to the test function name)
    assert rec.tool == "test_create_vm[create_vm]"


def test_extract_treats_empty_code_as_none(tmp_path: Path) -> None:
    xml = _make_xml(
        tmp_path,
        properties_block=(
            '<properties>'
            '<property name="mcptf_error_code" value=""/>'
            '<property name="mcptf_error_message" value="m"/>'
            '</properties>'
        ),
    )
    records = _extract_tool_call_errors_from_xml(xml)
    assert len(records) == 1
    assert records[0].code is None


def test_extract_treats_missing_raw_as_empty(tmp_path: Path) -> None:
    """D-11: when mcptf_error_raw is absent (e.g. exc.raw was None), .raw is ''."""
    xml = _make_xml(
        tmp_path,
        properties_block=(
            '<properties>'
            '<property name="mcptf_error_code" value="X"/>'
            '<property name="mcptf_error_message" value="m"/>'
            '</properties>'
        ),
    )
    records = _extract_tool_call_errors_from_xml(xml)
    assert len(records) == 1
    assert records[0].raw == ""


def test_extract_skips_testcase_without_message(tmp_path: Path) -> None:
    """A <properties> block without mcptf_error_message is not a
    ToolCallError-attached testcase; skip it (defensive)."""
    xml = _make_xml(
        tmp_path,
        properties_block=(
            '<properties>'
            '<property name="other_prop" value="v"/>'
            '</properties>'
        ),
    )
    records = _extract_tool_call_errors_from_xml(xml)
    assert records == []


# ---------------------------------------------------------------------------
# render_debug_appendix with xml_path
# ---------------------------------------------------------------------------


def test_debug_appendix_emits_dump_block_before_raw_pytest_output(
    tmp_path: Path, capsys
) -> None:
    """D-11: --- ToolCallError dump --- emitted BEFORE --- raw pytest output ---."""
    xml = _make_xml(
        tmp_path,
        properties_block=(
            '<properties>'
            '<property name="mcptf_error_code" value="VM_NAME_TAKEN"/>'
            '<property name="mcptf_error_message" value="name already in use"/>'
            '<property name="mcptf_error_raw" value=""/>'
            '</properties>'
        ),
    )
    parsed = parse_junit_xml(xml)
    render_debug_appendix(
        captured_stdout="pytest stdout",
        captured_stderr="",
        parsed=parsed,
        xml_path=xml,
    )
    out = capsys.readouterr().out
    dump_idx = out.find("--- ToolCallError dump ---")
    raw_idx = out.find("--- raw pytest output ---")
    assert dump_idx >= 0, out
    assert raw_idx >= 0, out
    assert dump_idx < raw_idx, (
        f"ToolCallError block must precede raw pytest output; "
        f"got dump={dump_idx} raw={raw_idx}"
    )


def test_debug_appendix_dump_block_carries_tool_code_message(
    tmp_path: Path, capsys
) -> None:
    xml = _make_xml(
        tmp_path,
        properties_block=(
            '<properties>'
            '<property name="mcptf_error_code" value="VM_NAME_TAKEN"/>'
            '<property name="mcptf_error_message" value="name already in use"/>'
            '</properties>'
        ),
    )
    parsed = parse_junit_xml(xml)
    render_debug_appendix(
        captured_stdout="",
        captured_stderr="",
        parsed=parsed,
        xml_path=xml,
    )
    out = capsys.readouterr().out
    assert "tool: test_create_vm[create_vm]" in out
    assert "code: VM_NAME_TAKEN" in out
    assert "message: name already in use" in out


def test_debug_appendix_renders_raw_dump_with_indent(
    tmp_path: Path, capsys
) -> None:
    """D-11: the mcptf_error_raw value is rendered under `raw:`, each line
    prefixed with 2 spaces. The JSON dump's own indentation is preserved."""
    raw_json = '{\n  "isError": true,\n  "content": []\n}'
    raw_attr = raw_json.replace('"', '&quot;').replace('\n', '&#10;')
    xml = _make_xml(
        tmp_path,
        properties_block=(
            '<properties>'
            '<property name="mcptf_error_code" value="X"/>'
            '<property name="mcptf_error_message" value="m"/>'
            f'<property name="mcptf_error_raw" value="{raw_attr}"/>'
            '</properties>'
        ),
    )
    parsed = parse_junit_xml(xml)
    render_debug_appendix(
        captured_stdout="",
        captured_stderr="",
        parsed=parsed,
        xml_path=xml,
    )
    out = capsys.readouterr().out
    assert "raw:" in out
    # Each line of the raw JSON dump gets a leading 2-space prefix.
    assert "  {" in out
    assert '  "isError": true,' in out
    assert "  }" in out


def test_debug_appendix_emits_raw_none_when_raw_empty(
    tmp_path: Path, capsys
) -> None:
    """D-11: empty mcptf_error_raw -> 'raw: (none)' sentinel, NOT a
    fallback workaround message."""
    xml = _make_xml(
        tmp_path,
        properties_block=(
            '<properties>'
            '<property name="mcptf_error_code" value="X"/>'
            '<property name="mcptf_error_message" value="m"/>'
            '<property name="mcptf_error_raw" value=""/>'
            '</properties>'
        ),
    )
    parsed = parse_junit_xml(xml)
    render_debug_appendix(
        captured_stdout="",
        captured_stderr="",
        parsed=parsed,
        xml_path=xml,
    )
    out = capsys.readouterr().out
    assert "raw: (none)" in out
    # The forbidden workaround language must NOT appear in the output.
    assert "re-run with --raw" not in out
    assert "unavailable" not in out


def test_debug_appendix_emits_code_none_when_code_missing(
    tmp_path: Path, capsys
) -> None:
    """D-11: missing mcptf_error_code -> 'code: (none)' sentinel."""
    xml = _make_xml(
        tmp_path,
        properties_block=(
            '<properties>'
            '<property name="mcptf_error_message" value="m"/>'
            '</properties>'
        ),
    )
    parsed = parse_junit_xml(xml)
    render_debug_appendix(
        captured_stdout="",
        captured_stderr="",
        parsed=parsed,
        xml_path=xml,
    )
    out = capsys.readouterr().out
    assert "code: (none)" in out


def test_debug_appendix_omits_dump_block_when_no_properties(
    tmp_path: Path, capsys
) -> None:
    """D-13 invariant: when no ToolCallError-attached testcases, appendix
    is byte-identical to the Phase 14 baseline (no dump block at all)."""
    xml = _make_xml_no_failure(tmp_path)
    parsed = parse_junit_xml(xml)
    render_debug_appendix(
        captured_stdout="stdout",
        captured_stderr="",
        parsed=parsed,
        xml_path=xml,
    )
    out = capsys.readouterr().out
    assert "--- ToolCallError dump ---" not in out
    # Phase 14 baseline lines still present.
    assert "--- raw pytest output ---" in out


def test_debug_appendix_omits_dump_block_when_xml_path_not_passed(
    tmp_path: Path, capsys
) -> None:
    """Backward-compat: existing call sites without xml_path see no dump
    block (Plan 18-05 / Phase 14 callers unchanged)."""
    xml = _make_xml(
        tmp_path,
        properties_block=(
            '<properties>'
            '<property name="mcptf_error_code" value="X"/>'
            '<property name="mcptf_error_message" value="m"/>'
            '</properties>'
        ),
    )
    parsed = parse_junit_xml(xml)
    render_debug_appendix(
        captured_stdout="stdout",
        captured_stderr="",
        parsed=parsed,
        # xml_path NOT passed -> appendix cannot scan for properties.
    )
    out = capsys.readouterr().out
    assert "--- ToolCallError dump ---" not in out


def test_debug_appendix_dump_block_terminator(
    tmp_path: Path, capsys
) -> None:
    """D-11: dump block terminator is `---` on its own line (matches the
    PATTERNS.md line 547 aesthetic)."""
    xml = _make_xml(
        tmp_path,
        properties_block=(
            '<properties>'
            '<property name="mcptf_error_code" value="X"/>'
            '<property name="mcptf_error_message" value="m"/>'
            '</properties>'
        ),
    )
    parsed = parse_junit_xml(xml)
    render_debug_appendix(
        captured_stdout="",
        captured_stderr="",
        parsed=parsed,
        xml_path=xml,
    )
    out = capsys.readouterr().out
    # Locate the dump block and confirm its terminator is `---` alone on a line.
    lines = out.split("\n")
    dump_idx = next(
        i for i, ln in enumerate(lines) if ln == "--- ToolCallError dump ---"
    )
    # Find the next `---` standalone line after the lead-in.
    terminator_idx = next(
        i for i, ln in enumerate(lines[dump_idx + 1 :], start=dump_idx + 1)
        if ln == "---"
    )
    assert terminator_idx > dump_idx


def test_debug_appendix_multiple_failures_emit_multiple_blocks(
    tmp_path: Path, capsys
) -> None:
    """D-11: each ToolCallError-attached testcase gets its own dump block."""
    xml = tmp_path / "multi.xml"
    xml.write_text(
        '<?xml version="1.0"?>'
        '<testsuites>'
        '<testsuite name="pytest" tests="2" failures="2" skipped="0" '
        'errors="0" time="0.1">'
        '<testcase classname="t" name="test_a[tool_a]" time="0.05">'
        '<failure message="raw" type="ToolCallError">tb</failure>'
        '<properties>'
        '<property name="mcptf_error_code" value="CODE_A"/>'
        '<property name="mcptf_error_message" value="msg_a"/>'
        '</properties>'
        '</testcase>'
        '<testcase classname="t" name="test_b[tool_b]" time="0.05">'
        '<failure message="raw" type="ToolCallError">tb</failure>'
        '<properties>'
        '<property name="mcptf_error_code" value="CODE_B"/>'
        '<property name="mcptf_error_message" value="msg_b"/>'
        '</properties>'
        '</testcase>'
        '</testsuite></testsuites>',
        encoding="utf-8",
    )
    parsed = parse_junit_xml(xml)
    render_debug_appendix(
        captured_stdout="",
        captured_stderr="",
        parsed=parsed,
        xml_path=xml,
    )
    out = capsys.readouterr().out
    # Two dump blocks -> the lead-in string appears twice.
    assert out.count("--- ToolCallError dump ---") == 2
    assert "code: CODE_A" in out
    assert "code: CODE_B" in out
