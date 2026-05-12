"""Phase 14 Plan 03 unit tests: domain UI renderer.

Pins Phase 14 D-04..D-09, RUNNER-02 must_haves, em-dash U+2014, CD-03 row
ordering, no-pytest-framing invariant.

Test file lives at tests/test_runner_renderer.py per Plan 14-03 spec; the
pure-data nature of these tests (no MCP/Ollama dependency, capsys-only) is
similar to tests/unit/test_runner_parser.py. We follow the plan's stated
path -- tests/conftest.py preflight gate is bypassed when pytest is invoked
with `-p no:cacheprovider` or via direct file targeting in CI, but the
standard mechanism documented at fixtures._session_needs_preflight is to
keep pure-data tests under tests/unit/. We honor the plan literally here;
if preflight blocks collection on a given machine, run with:
    uv run pytest tests/test_runner_renderer.py --no-header -p no:cacheprovider
or move the file to tests/unit/ post-hoc (a Rule 1 deviation that the
parser plan already documented).
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from mcp_test_framework._runner import (
    ParsedRun,
    RenderContext,
    ToolVerdict,
    _compose_unparametrized_skips_from_config,
    _render_header,
    _render_per_tool_rows,
    _render_summary_line,
    parse_junit_xml,
    render_domain_ui,
)


_FIXTURES = Path(__file__).parent / "fixtures"


def _basic_ctx(discovered=None, tools_config=None, judges=None) -> RenderContext:
    return RenderContext(
        server_cmd="uvx homelab-mcp",
        discovered_tools=discovered or [],
        tools_config=tools_config or {},
        judges=judges or [],
        total_planned_cases=0,
    )


# ---------------------------------------------------------------------------
# Header (D-07 + SEED-011 §2 mockup)
# ---------------------------------------------------------------------------


def test_render_header_includes_required_fields(capsys) -> None:
    parsed = parse_junit_xml(_FIXTURES / "junit-all-pass.xml")
    ctx = _basic_ctx(
        discovered=["alpha", "beta", "gamma"],
        judges=["clarity", "parameters"],
    )
    _render_header(ctx, parsed)
    out = capsys.readouterr().out
    assert "MCP Test Framework" in out
    assert "MCP server:" in out
    assert "uvx homelab-mcp" in out
    assert "Discovered:" in out
    assert "Running:" in out
    assert "Skipping:" in out
    assert "Judges:" in out
    assert "Test plan:" in out
    assert "clarity" in out
    assert "parameters" in out


def test_header_skipping_count_excludes_running_tools(capsys) -> None:
    parsed = parse_junit_xml(_FIXTURES / "junit-all-pass.xml")
    # 5 discovered, 3 running (from fixture) -> Skipping: 2
    ctx = _basic_ctx(discovered=["alpha", "beta", "gamma", "extra1", "extra2"])
    _render_header(ctx, parsed)
    out = capsys.readouterr().out
    assert "Discovered:  5 tools" in out
    assert "Running:      3" in out  # right-justified width 2
    assert "Skipping:     2" in out


def test_header_explain_forward_reference_hint(capsys) -> None:
    """Phase 14 D-14: the literal "use --explain to list" hint stays in Phase 14
    even though the flag itself ships in Phase 16."""
    parsed = parse_junit_xml(_FIXTURES / "junit-all-pass.xml")
    ctx = _basic_ctx(discovered=["alpha", "beta", "gamma", "extra1"])
    _render_header(ctx, parsed)
    out = capsys.readouterr().out
    assert "use --explain to list" in out


# ---------------------------------------------------------------------------
# Per-tool rows (CD-03 ordering, D-08 reasoning, em-dash separator)
# ---------------------------------------------------------------------------


def test_render_rows_fail_skip_pass_alphabetical(capsys) -> None:
    """Phase 09 CD-03: FAIL -> SKIP -> PASS, alphabetical within each."""
    parsed = parse_junit_xml(_FIXTURES / "junit-mixed.xml")
    _render_per_tool_rows(parsed, unparam_skips={})
    out = capsys.readouterr().out
    lines = out.splitlines()

    # Find positions of section headers.
    fail_idx = next(i for i, l in enumerate(lines) if "failures:" in l)
    skip_idx = next(i for i, l in enumerate(lines) if "skipped:" in l)
    pass_idx = next(i for i, l in enumerate(lines) if "passing:" in l)

    assert fail_idx < skip_idx < pass_idx, (
        f"Section ordering broken: fail={fail_idx} skip={skip_idx} pass={pass_idx}"
    )
    # Within the passing section, alpha must precede mango (alphabetical).
    alpha_idx = next(i for i, l in enumerate(lines) if "alpha" in l and i > pass_idx)
    mango_idx = next(i for i, l in enumerate(lines) if "mango" in l and i > pass_idx)
    assert alpha_idx < mango_idx


def test_render_fail_row_includes_failure_message(capsys) -> None:
    """D-08: <failure message='...'> surfaces in the row."""
    parsed = parse_junit_xml(_FIXTURES / "junit-one-fail-with-reasoning.xml")
    _render_per_tool_rows(parsed, unparam_skips={})
    out = capsys.readouterr().out
    assert "parameters 3/5: 'unclear param name'" in out


def test_render_skip_row_uses_em_dash_separator(capsys) -> None:
    """Em-dash U+2014, NOT ASCII hyphen. Locked at Phase 09 SC-3 + _reporter.py:275."""
    parsed = parse_junit_xml(_FIXTURES / "junit-all-skip.xml")
    _render_per_tool_rows(parsed, unparam_skips={})
    out = capsys.readouterr().out
    # The em-dash MUST appear somewhere in the SKIP rows.
    assert "—" in out, "U+2014 em-dash missing from SKIP rows"
    assert out.count("—") >= 4  # one per skipped row (4 skipped fixture rows).


def test_render_no_pytest_framing_in_default_output(capsys) -> None:
    """RUNNER-02 must_have: no pytest framing leaks in default mode."""
    parsed = parse_junit_xml(_FIXTURES / "junit-mixed.xml")
    ctx = _basic_ctx(
        discovered=["alpha", "gamma", "mango", "zoo"],
        judges=["clarity"],
    )
    render_domain_ui(parsed, ctx)
    out = capsys.readouterr().out
    assert "test session starts" not in out
    assert "rootdir:" not in out
    # `[<param>]` suffix sometimes appears as `test_x[alpha]` in pytest output;
    # the renderer surfaces tool names WITHOUT the `[...]` brackets.
    assert "[alpha]" not in out
    assert "[zoo]" not in out
    # The bare tool names DO appear (this is intentional).
    assert "alpha" in out
    assert "zoo" in out


# ---------------------------------------------------------------------------
# State-(a)/(c) composition (Phase 13 D-12 + Phase 14)
# ---------------------------------------------------------------------------


def test_state_a_unlisted_renders_not_selected() -> None:
    """Discovered tool NOT in tools_config -> state-(a) 'not selected in config'."""
    result = _compose_unparametrized_skips_from_config(
        discovered_tools=["alpha", "untracked"],
        tools_config={},
        ran_tools=set(),
    )
    assert result == {
        "alpha": "not selected in config",
        "untracked": "not selected in config",
    }


def test_state_c_listed_with_skip_renders_curated_reason() -> None:
    """Listed with skip=True + non-empty skip_reason -> state-(c) curated text."""
    fake_tcfg = SimpleNamespace(skip=True, skip_reason="hits production registry")
    result = _compose_unparametrized_skips_from_config(
        discovered_tools=["dangerous_tool"],
        tools_config={"dangerous_tool": fake_tcfg},
        ran_tools=set(),
    )
    assert result == {"dangerous_tool": "hits production registry"}


def test_state_c_default_when_skip_reason_empty() -> None:
    """Listed with skip=True + empty skip_reason -> default fallback."""
    fake_tcfg = SimpleNamespace(skip=True, skip_reason="")
    result = _compose_unparametrized_skips_from_config(
        discovered_tools=["x"],
        tools_config={"x": fake_tcfg},
        ran_tools=set(),
    )
    assert result == {"x": "explicit skip in config"}


def test_ran_tools_excluded_from_composition() -> None:
    """Tools that produced parsed.per_tool entries are NOT re-composed as SKIP."""
    fake_tcfg = SimpleNamespace(skip=False, skip_reason="")
    result = _compose_unparametrized_skips_from_config(
        discovered_tools=["ran", "skipped"],
        tools_config={"ran": fake_tcfg},
        ran_tools={"ran"},
    )
    assert "ran" not in result
    assert result["skipped"] == "not selected in config"


# ---------------------------------------------------------------------------
# Summary line
# ---------------------------------------------------------------------------


def test_summary_line_includes_skip_count_when_skips_present(capsys) -> None:
    parsed = parse_junit_xml(_FIXTURES / "junit-mixed.xml")
    _render_summary_line(parsed, unparam_skips={})
    out = capsys.readouterr().out
    # mixed fixture: 2 PASS (alpha, mango), 1 FAIL (zoo), 1 SKIP (gamma), time=8.34
    assert "Result: 2 PASS / 1 FAIL / 1 SKIP" in out
    assert "in 8.3s" in out


def test_summary_line_omits_skip_when_zero(capsys) -> None:
    parsed = parse_junit_xml(_FIXTURES / "junit-all-pass.xml")
    _render_summary_line(parsed, unparam_skips={})
    out = capsys.readouterr().out
    assert "Result: 3 PASS / 0 FAIL" in out
    assert "SKIP" not in out  # no skip segment when zero


def test_summary_line_includes_unparam_skips(capsys) -> None:
    """State-(a)/(c) SKIP rows must count toward the summary's SKIP total."""
    parsed = parse_junit_xml(_FIXTURES / "junit-all-pass.xml")  # 3 PASS, 0 FAIL, 0 SKIP
    _render_summary_line(
        parsed,
        unparam_skips={"extra1": "not selected in config", "extra2": "not selected in config"},
    )
    out = capsys.readouterr().out
    assert "Result: 3 PASS / 0 FAIL / 2 SKIP" in out


# ---------------------------------------------------------------------------
# ANSI guard (D-06)
# ---------------------------------------------------------------------------


def test_no_ansi_codes_when_not_tty(capsys) -> None:
    """D-06: ANSI guarded by sys.stdout.isatty() -- capsys is not a TTY."""
    parsed = parse_junit_xml(_FIXTURES / "junit-all-pass.xml")
    ctx = _basic_ctx(discovered=["alpha", "beta", "gamma"])
    render_domain_ui(parsed, ctx)
    out = capsys.readouterr().out
    assert "\x1b[" not in out  # no ANSI escape sequences


# ---------------------------------------------------------------------------
# Integration: full render_domain_ui orchestration
# ---------------------------------------------------------------------------


def test_render_domain_ui_full_flow(capsys) -> None:
    parsed = parse_junit_xml(_FIXTURES / "junit-mixed.xml")
    ctx = _basic_ctx(
        discovered=["alpha", "gamma", "mango", "zoo", "unlisted"],
        judges=["clarity"],
    )
    render_domain_ui(parsed, ctx)
    out = capsys.readouterr().out
    # Phase 16 D-01: render_domain_ui no longer emits the banner / labels;
    # the digest moved pre-run. Assert the banner is GONE here.
    assert "MCP Test Framework" not in out
    assert "=" * 40 not in out  # banner string absent
    # Per-tool rows
    assert "failures:" in out
    assert "skipped:" in out
    assert "passing:" in out
    # State-(a) unlisted tool surfaces as SKIP
    assert "unlisted" in out
    assert "not selected in config" in out
    # Summary
    assert "Result:" in out
