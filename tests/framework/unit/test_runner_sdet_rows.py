"""Phase 19: regression pins for the SDET-classname parse branch and the
scenario-block rendering in _render_per_tool_rows.

Tests synthesize JUnit XML strings, write them to tmp_path, and run them
through parse_junit_xml -> ParsedRun -> _render_per_tool_rows. Pure unit
tests; no pytest subprocess, no live MCP.
"""
from __future__ import annotations

import io
import re
import textwrap
from pathlib import Path

import pytest

from mcp_test_framework._runner import (
    ParsedRun,
    ToolVerdict,
    _render_per_tool_rows,
    parse_junit_xml,
)


def _write_xml(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "junit.xml"
    path.write_text(textwrap.dedent(body))
    return path


# ---------------------------------------------------------------------------
# Task 1: parse_junit_xml SDET classname fall-through (8 RED -> GREEN tests)
# ---------------------------------------------------------------------------


def test_sdet_pass_emits_synthetic_key(tmp_path):
    path = _write_xml(
        tmp_path,
        """\
        <?xml version="1.0" encoding="utf-8"?>
        <testsuites><testsuite name="pytest" tests="1" failures="0" errors="0" skipped="0">
          <testcase classname="tests.sdet.test_proxmox_vm_lifecycle" name="test_create_returns_pending_vm" time="0.5"/>
        </testsuite></testsuites>
        """,
    )
    parsed = parse_junit_xml(path)
    key = "proxmox_vm_lifecycle::create_returns_pending_vm"
    assert key in parsed.per_tool
    assert parsed.per_tool[key].verdict == "PASS"


def test_sdet_fail_carries_em_dash_message(tmp_path):
    path = _write_xml(
        tmp_path,
        """\
        <?xml version="1.0" encoding="utf-8"?>
        <testsuites><testsuite name="pytest" tests="1" failures="1" errors="0" skipped="0">
          <testcase classname="tests.sdet.test_proxmox_vm_lifecycle" name="test_create_returns_pending_vm">
            <properties>
              <property name="mcptf_error_code" value="E_SUBTREE"/>
              <property name="mcptf_error_message" value="vmid not found"/>
            </properties>
            <failure message="boom">trace</failure>
          </testcase>
        </testsuite></testsuites>
        """,
    )
    parsed = parse_junit_xml(path)
    key = "proxmox_vm_lifecycle::create_returns_pending_vm"
    assert parsed.per_tool[key].verdict == "FAIL"
    assert parsed.per_tool[key].failure_message == "[E_SUBTREE] vmid not found"


def test_sdet_skip_carries_reason(tmp_path):
    path = _write_xml(
        tmp_path,
        """\
        <?xml version="1.0" encoding="utf-8"?>
        <testsuites><testsuite name="pytest" tests="1" failures="0" errors="0" skipped="1">
          <testcase classname="tests.sdet.test_proxmox_vm_lifecycle" name="test_create_returns_pending_vm">
            <skipped message="Skipped: requires homelab" type="pytest.skip"/>
          </testcase>
        </testsuite></testsuites>
        """,
    )
    parsed = parse_junit_xml(path)
    key = "proxmox_vm_lifecycle::create_returns_pending_vm"
    assert parsed.per_tool[key].verdict == "SKIP"
    assert "requires homelab" in parsed.per_tool[key].skip_reasons


def test_contract_parametrize_still_works(tmp_path):
    path = _write_xml(
        tmp_path,
        """\
        <?xml version="1.0" encoding="utf-8"?>
        <testsuites><testsuite name="pytest" tests="1" failures="0" errors="0" skipped="0">
          <testcase classname="tests.contract.test_mcp_tool_contract" name="test_x[list_tools]"/>
        </testsuite></testsuites>
        """,
    )
    parsed = parse_junit_xml(path)
    assert "list_tools" in parsed.per_tool
    assert "::" not in "list_tools"


def test_classname_outside_tests_sdet_still_dropped(tmp_path):
    path = _write_xml(
        tmp_path,
        """\
        <?xml version="1.0" encoding="utf-8"?>
        <testsuites><testsuite name="pytest" tests="1" failures="0" errors="0" skipped="0">
          <testcase classname="tests.framework.unit.test_runner_parser" name="test_x"/>
        </testsuite></testsuites>
        """,
    )
    parsed = parse_junit_xml(path)
    assert parsed.per_tool == {}


def test_sdet_classname_with_alt_prefix_still_works(tmp_path):
    path = _write_xml(
        tmp_path,
        """\
        <?xml version="1.0" encoding="utf-8"?>
        <testsuites><testsuite name="pytest" tests="1" failures="0" errors="0" skipped="0">
          <testcase classname="tests.sdet.test_other_scenario" name="test_step_one"/>
        </testsuite></testsuites>
        """,
    )
    parsed = parse_junit_xml(path)
    assert "other_scenario::step_one" in parsed.per_tool


def test_multiple_sdet_tests_same_module_grouped_distinctly(tmp_path):
    path = _write_xml(
        tmp_path,
        """\
        <?xml version="1.0" encoding="utf-8"?>
        <testsuites><testsuite name="pytest" tests="2" failures="0" errors="0" skipped="0">
          <testcase classname="tests.sdet.test_proxmox_vm_lifecycle" name="test_create_returns_pending_vm"/>
          <testcase classname="tests.sdet.test_proxmox_vm_lifecycle" name="test_modify_accepts_cpu_increase"/>
        </testsuite></testsuites>
        """,
    )
    parsed = parse_junit_xml(path)
    assert "proxmox_vm_lifecycle::create_returns_pending_vm" in parsed.per_tool
    assert "proxmox_vm_lifecycle::modify_accepts_cpu_increase" in parsed.per_tool


def test_sdet_testcase_with_brackets_uses_bracket_path(tmp_path):
    # Defensive: if an SDET test ever gets parametrized, the bracket
    # extraction wins (legacy precedence).
    path = _write_xml(
        tmp_path,
        """\
        <?xml version="1.0" encoding="utf-8"?>
        <testsuites><testsuite name="pytest" tests="1" failures="0" errors="0" skipped="0">
          <testcase classname="tests.sdet.test_x" name="test_y[foo]"/>
        </testsuite></testsuites>
        """,
    )
    parsed = parse_junit_xml(path)
    assert "foo" in parsed.per_tool
    assert "::" not in next(iter(parsed.per_tool.keys()))


# ---------------------------------------------------------------------------
# Task 2: _render_per_tool_rows scenario block (9 RED -> GREEN tests)
# ---------------------------------------------------------------------------


def _strip_ansi(s: str) -> str:
    """Strip ANSI color codes for portable assertion."""
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


def test_render_scenario_block_pass():
    parsed = ParsedRun(total_cases=1, total_failures=0, total_skipped=0, total_errors=0)
    parsed.per_tool["proxmox_vm_lifecycle::create_returns_pending_vm"] = ToolVerdict(
        name="proxmox_vm_lifecycle::create_returns_pending_vm", verdict="PASS"
    )
    buf = io.StringIO()
    _render_per_tool_rows(parsed, {}, file=buf)
    lines = buf.getvalue().splitlines()
    plain = [_strip_ansi(ln) for ln in lines]
    # Group header on its own line (no trailing colon).
    assert "proxmox_vm_lifecycle" in plain
    # Indented row: two-space indent + glyph + space + row_label; NO "PASS" word.
    assert "  ✓ create_returns_pending_vm" in plain


def test_render_scenario_block_multi_row_alphabetical_within_group():
    parsed = ParsedRun(total_cases=3, total_failures=0, total_skipped=0, total_errors=0)
    for name in ["test_c", "test_a", "test_b"]:
        key = f"proxmox_vm_lifecycle::{name.removeprefix('test_')}"
        parsed.per_tool[key] = ToolVerdict(name=key, verdict="PASS")
    buf = io.StringIO()
    _render_per_tool_rows(parsed, {}, file=buf)
    plain = [_strip_ansi(ln) for ln in buf.getvalue().splitlines()]
    # Group header appears once.
    assert plain.count("proxmox_vm_lifecycle") == 1
    # All three row labels present.
    assert "  ✓ a" in plain
    assert "  ✓ b" in plain
    assert "  ✓ c" in plain
    # Alphabetical order: find group header position, then a < b < c.
    group_idx = plain.index("proxmox_vm_lifecycle")
    row_lines = plain[group_idx + 1 : group_idx + 4]
    assert row_lines == ["  ✓ a", "  ✓ b", "  ✓ c"]


def test_render_scenario_block_fail_with_em_dash():
    parsed = ParsedRun(total_cases=1, total_failures=1, total_skipped=0, total_errors=0)
    key = "proxmox_vm_lifecycle::create_returns_pending_vm"
    parsed.per_tool[key] = ToolVerdict(
        name=key, verdict="FAIL", failure_message="[E_X] boom"
    )
    buf = io.StringIO()
    _render_per_tool_rows(parsed, {}, file=buf)
    plain = [_strip_ansi(ln) for ln in buf.getvalue().splitlines()]
    # FAIL row: glyph + row_label + em-dash (U+2014) + message; NO "FAIL" word.
    fail_lines = [ln for ln in plain if ln.startswith("  ✗ ")]
    assert len(fail_lines) == 1
    assert "create_returns_pending_vm" in fail_lines[0]
    assert "—" in fail_lines[0]  # em-dash U+2014
    assert "[E_X] boom" in fail_lines[0]


def test_render_scenario_block_skip_with_reason():
    parsed = ParsedRun(total_cases=1, total_failures=0, total_skipped=1, total_errors=0)
    key = "proxmox_vm_lifecycle::create_returns_pending_vm"
    parsed.per_tool[key] = ToolVerdict(
        name=key, verdict="SKIP", skip_reasons=["requires homelab"]
    )
    buf = io.StringIO()
    _render_per_tool_rows(parsed, {}, file=buf)
    plain = [_strip_ansi(ln) for ln in buf.getvalue().splitlines()]
    # SKIP row: en-dash (U+2013) glyph + row_label + em-dash + reason; NO "SKIP" word.
    skip_lines = [ln for ln in plain if ln.startswith("  – ")]
    assert len(skip_lines) == 1
    assert "create_returns_pending_vm" in skip_lines[0]
    assert "requires homelab" in skip_lines[0]


def test_render_mixed_contract_and_scenario():
    parsed = ParsedRun(total_cases=2, total_failures=0, total_skipped=0, total_errors=0)
    # Contract tool (no ::).
    parsed.per_tool["list_tools"] = ToolVerdict(name="list_tools", verdict="PASS")
    # Scenario tool (with ::).
    key = "proxmox_vm_lifecycle::create_returns_pending_vm"
    parsed.per_tool[key] = ToolVerdict(name=key, verdict="PASS")
    buf = io.StringIO()
    _render_per_tool_rows(parsed, {}, file=buf)
    plain = [_strip_ansi(ln) for ln in buf.getvalue().splitlines()]
    output = buf.getvalue()
    plain_output = _strip_ansi(output)
    # Contract section has "passing:" header.
    assert "passing:" in plain_output
    # Scenario group header present.
    assert "proxmox_vm_lifecycle" in plain
    # Contract row uses ljust alignment (has "PASS" word from tag).
    assert any("list_tools" in ln and "PASS" in _strip_ansi(ln) for ln in plain)
    # Scenario row has no "PASS" word.
    scenario_rows = [ln for ln in plain if "create_returns_pending_vm" in ln]
    assert len(scenario_rows) == 1
    assert "PASS" not in scenario_rows[0]


def test_scenario_keys_excluded_from_name_width():
    """A very long scenario key must NOT widen the contract row's ljust."""
    parsed = ParsedRun(total_cases=2, total_failures=0, total_skipped=0, total_errors=0)
    # Short contract tool name.
    parsed.per_tool["short"] = ToolVerdict(name="short", verdict="PASS")
    # Long scenario key — should not affect contract row alignment.
    long_key = "grp::a_very_long_row_label_that_should_not_widen_contract_alignment"
    parsed.per_tool[long_key] = ToolVerdict(name=long_key, verdict="PASS")

    buf = io.StringIO()
    _render_per_tool_rows(parsed, {}, file=buf)
    plain_output = _strip_ansi(buf.getvalue())

    # The contract tool row should be indented by name_width = len("short") = 5
    # not by len(long_key) = 65.
    # Find the contract tool row.
    contract_lines = [ln for ln in plain_output.splitlines() if "short" in ln and "PASS" in ln]
    assert len(contract_lines) == 1
    # "short" ljust(5) = "short" (no extra spaces for ljust padding).
    # The total ljust should be exactly len("short") = 5.
    ln = contract_lines[0]
    # "  short  ✓ PASS" -- name_width=5, short.ljust(5)="short"
    assert ln.startswith("  short  ")


def test_groups_sorted_alphabetically():
    parsed = ParsedRun(total_cases=2, total_failures=0, total_skipped=0, total_errors=0)
    parsed.per_tool["proxmox_vm_lifecycle::create"] = ToolVerdict(
        name="proxmox_vm_lifecycle::create", verdict="PASS"
    )
    parsed.per_tool["ansible_playbook_deploy::run"] = ToolVerdict(
        name="ansible_playbook_deploy::run", verdict="PASS"
    )
    buf = io.StringIO()
    _render_per_tool_rows(parsed, {}, file=buf)
    plain = [_strip_ansi(ln) for ln in buf.getvalue().splitlines()]
    # ansible_* should appear BEFORE proxmox_* alphabetically.
    ansible_idx = next(i for i, ln in enumerate(plain) if ln == "ansible_playbook_deploy")
    proxmox_idx = next(i for i, ln in enumerate(plain) if ln == "proxmox_vm_lifecycle")
    assert ansible_idx < proxmox_idx


def test_scenario_block_empty_if_no_scenarios():
    """No scenario keys -> output byte-identical to pre-Phase-19 contract-only behavior."""
    parsed = ParsedRun(total_cases=1, total_failures=0, total_skipped=0, total_errors=0)
    parsed.per_tool["list_tools"] = ToolVerdict(name="list_tools", verdict="PASS")
    buf = io.StringIO()
    _render_per_tool_rows(parsed, {}, file=buf)
    output = _strip_ansi(buf.getvalue())
    # No group headers (no lines without leading space or "passing:"/"failures:"/"skipped:").
    # No extra blank lines or group-style output.
    assert "passing:" in output
    # No scenario-style lines (bare identifier without leading space).
    lines = output.splitlines()
    # The only non-indented, non-section-header line in the output should be absent.
    non_section = [ln for ln in lines if ln and not ln.startswith("  ") and ln not in ("passing:", "failures:", "skipped:")]
    assert non_section == [], f"Unexpected non-section lines: {non_section}"


def test_render_scenario_block_fixture_error_cascade(tmp_path):
    # Synthesize the pattern pytest emits when a module-scope fixture
    # fails: one testcase carries <error>, subsequent testcases under
    # the same classname carry <skipped> with the fixture-failure
    # reason. Phase 19 dogfood (D-01 fail-loud) produces exactly this
    # shape when Proxmox is unreachable.
    path = _write_xml(
        tmp_path,
        """\
        <?xml version="1.0" encoding="utf-8"?>
        <testsuites><testsuite name="pytest" tests="3" failures="0" errors="1" skipped="2">
          <testcase classname="tests.sdet.test_proxmox_vm_lifecycle" name="test_create_returns_pending_vm">
            <error message="fixture proxmox_vm_lifecycle setup failed">trace</error>
          </testcase>
          <testcase classname="tests.sdet.test_proxmox_vm_lifecycle" name="test_modify_accepts_cpu_increase">
            <skipped message="fixture proxmox_vm_lifecycle failed" type="pytest.skip"/>
          </testcase>
          <testcase classname="tests.sdet.test_proxmox_vm_lifecycle" name="test_delete_returns_ok">
            <skipped message="fixture proxmox_vm_lifecycle failed" type="pytest.skip"/>
          </testcase>
        </testsuite></testsuites>
        """,
    )
    parsed = parse_junit_xml(path)
    # First cascaded test -> FAIL; remaining -> SKIP. All grouped under
    # the scenario classname.
    assert parsed.per_tool["proxmox_vm_lifecycle::create_returns_pending_vm"].verdict == "FAIL"
    assert parsed.per_tool["proxmox_vm_lifecycle::modify_accepts_cpu_increase"].verdict == "SKIP"
    assert parsed.per_tool["proxmox_vm_lifecycle::delete_returns_ok"].verdict == "SKIP"

    buf = io.StringIO()
    _render_per_tool_rows(parsed, {}, file=buf)
    plain = [_strip_ansi(ln) for ln in buf.getvalue().splitlines()]
    # Group header on its own line, then 1 FAIL + 2 SKIP under it,
    # alphabetical by row_label (create_, delete_, modify_).
    assert "proxmox_vm_lifecycle" in plain
    # FAIL row carries em-dash + error text.
    fail_rows = [ln for ln in plain if ln.startswith("  ✗ ")]
    assert len(fail_rows) == 1
    assert "create_returns_pending_vm" in fail_rows[0]
    assert "—" in fail_rows[0]  # em-dash separator
    # Two SKIP rows.
    skip_rows = [ln for ln in plain if ln.startswith("  – ")]
    assert len(skip_rows) == 2
    skip_labels = " ".join(skip_rows)
    assert "modify_accepts_cpu_increase" in skip_labels
    assert "delete_returns_ok" in skip_labels
