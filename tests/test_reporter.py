"""Phase 09 verification: --junit-xml flag + per-tool summary plugin.

Unit-level tests (no live MCP server needed):
  - _build_pytest_args translation rules (D-01a, D-01b)
  - --junit-xml is documented in `mcp-test-framework run --help`
  - _extract_tool_name on parametrize-suffix nodeids (D-02a)
  - _extract_skip_reason on pytest skip longrepr tuples (D-05)
  - _format_skip_reasons de-dup + cap rules (D-05)
  - pytest_runtest_logreport verdict aggregation rules (D-03, D-03a)
  - pytest_terminal_summary -q suppression (D-04b)

Live tests (gated behind @live_homelab):
  - End-to-end JUnit XML produced by `mcp-test-framework run --junit-xml=...`
    is well-formed and contains <testcase> entries with [<tool>] suffix in
    `name` attribute (OUTPUT-01 + OUTPUT-02 free-ride per L-01).
  - The per-tool summary section appears in the live run's terminal output
    (OUTPUT-03 always-on per D-04).

Decisions cited: D-01..D-05, CD-03, L-01..L-06 from
.planning/phases/09-junit-xml-output-per-tool-reporting/09-CONTEXT.md.
"""
from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from mcp_test_framework import _reporter
from mcp_test_framework.cli import _build_pytest_args, app


def _invoke(*args: str):
    """CliRunner construction site -- mirrors tests/test_config_init_cli.py:22-25."""
    return CliRunner().invoke(app, list(args))


def _make_report(nodeid, outcome, *, when="call", failed=False, longrepr=None):
    """Construct a minimal duck-typed pytest report for plugin tests.

    SimpleNamespace mirrors the test_tool_config.py pattern (line 14 import).
    Real ``_pytest.reports.TestReport`` carries many more fields, but the
    plugin only reads ``nodeid``, ``outcome``, ``when``, ``failed``, and
    ``longrepr`` -- duck typing is sufficient.
    """
    return SimpleNamespace(
        nodeid=nodeid,
        outcome=outcome,
        when=when,
        failed=failed,
        longrepr=longrepr,
    )


@pytest.fixture(autouse=True)
def _reset_per_tool_buffer():
    """Reset the module-level aggregation dict between tests.

    The plugin uses module-level state (``_PER_TOOL``) intentionally -- pytest
    re-imports the plugin once per session, but our unit tests run many
    aggregation scenarios in the same session, so we reset between cases.
    """
    _reporter._PER_TOOL.clear()
    yield
    _reporter._PER_TOOL.clear()


# ===========================================================================
# Unit-level: _build_pytest_args (D-01a, D-01b)
# ===========================================================================


def test_build_pytest_args_no_flag_no_passthrough() -> None:
    """Default invocation: argv is just ['tests']."""
    assert _build_pytest_args(None, None) == ["tests"]


def test_build_pytest_args_translates_dashed_to_no_dash(tmp_path: Path) -> None:
    """D-01b: public --junit-xml -> internal --junitxml (no-dash)."""
    target = tmp_path / "out.xml"
    result = _build_pytest_args(target, None)
    assert result == ["tests", f"--junitxml={target}"]
    assert not any(arg.startswith("--junit-xml=") for arg in result)


def test_build_pytest_args_passthrough_wins_under_last_occurrence(tmp_path: Path) -> None:
    """D-01a: explicit flag is inserted BEFORE passthrough so a passthrough
    --junitxml=... after `--` wins under pytest's last-occurrence argparse rule.
    """
    explicit = tmp_path / "a.xml"
    passthrough_arg = "--junitxml=passthrough.xml"
    result = _build_pytest_args(explicit, [passthrough_arg])
    assert result.index(f"--junitxml={explicit}") < result.index(passthrough_arg)


def test_build_pytest_args_passthrough_only_no_injection() -> None:
    """When --junit-xml is None, no synthetic --junitxml is injected."""
    result = _build_pytest_args(None, ["-k", "schema"])
    assert result == ["tests", "-k", "schema"]
    assert not any(arg.startswith("--junitxml") for arg in result)


def test_build_pytest_args_explicit_then_other_passthrough(tmp_path: Path) -> None:
    """Non-conflicting passthrough args sit AFTER the synthetic --junitxml."""
    target = tmp_path / "out.xml"
    result = _build_pytest_args(target, ["-v", "-k", "judge"])
    assert result == ["tests", f"--junitxml={target}", "-v", "-k", "judge"]


# ===========================================================================
# Unit-level: --help surface (D-01b spelling discoverability)
# ===========================================================================


def test_run_help_lists_junit_xml() -> None:
    """OUTPUT-01: `mcp-test-framework run --help` documents --junit-xml."""
    result = _invoke("run", "--help")
    assert result.exit_code == 0, result.output
    assert "--junit-xml" in result.output, result.output


# ===========================================================================
# Unit-level: _extract_tool_name (D-02a)
# ===========================================================================


def test_extract_tool_name_simple_suffix() -> None:
    assert (
        _reporter._extract_tool_name("tests/foo.py::test_x[mytool]") == "mytool"
    )


def test_extract_tool_name_no_suffix_returns_none() -> None:
    """D-02a: tests without [<tool>] suffix excluded from per-tool summary."""
    assert _reporter._extract_tool_name("tests/unit/test_pure.py::test_y") is None


def test_extract_tool_name_underscores_preserved() -> None:
    assert (
        _reporter._extract_tool_name("tests/foo.py::test_x[tool_with_underscores]")
        == "tool_with_underscores"
    )


def test_extract_tool_name_arbitrary_chars_in_brackets() -> None:
    """Tool names from Phase 07 are emitted verbatim via ids=names -- any chars
    the MCP server returns must round-trip."""
    assert _reporter._extract_tool_name("a.py::test_x[a-b]") == "a-b"


# ===========================================================================
# Unit-level: _format_skip_reasons (D-05)
# ===========================================================================


def test_format_skip_reasons_empty() -> None:
    assert _reporter._format_skip_reasons([]) == ""


def test_format_skip_reasons_single() -> None:
    assert _reporter._format_skip_reasons(["only reason"]) == "only reason"


def test_format_skip_reasons_two_joined_with_semicolon_space() -> None:
    """D-05: multiple distinct reasons -> '; '-joined."""
    assert _reporter._format_skip_reasons(["A", "B"]) == "A; B"


def test_format_skip_reasons_cap_at_three_distinct() -> None:
    """D-05: cap at 3 distinct, append '; ... (N more)' if more."""
    reasons = ["r1", "r2", "r3", "r4", "r5"]
    assert _reporter._format_skip_reasons(reasons) == "r1; r2; r3; ... (2 more)"


def test_format_skip_reasons_verbatim_no_transform() -> None:
    """D-05a: reasons rendered VERBATIM -- semicolons / quotes preserved."""
    weird = ['has "quotes" inside', "has; semicolon inside"]
    out = _reporter._format_skip_reasons(weird)
    assert 'has "quotes" inside' in out
    assert "has; semicolon inside" in out


# ===========================================================================
# Unit-level: pytest_runtest_logreport verdict aggregation (D-03, D-03a)
# ===========================================================================


def test_aggregation_passed_only_yields_pass() -> None:
    _reporter.pytest_runtest_logreport(_make_report("a.py::t[x]", "passed"))
    assert _reporter._PER_TOOL["x"]["verdict"] == "PASS"


def test_aggregation_failed_then_passed_stays_fail() -> None:
    """D-03 rule 1: any failed/error -> FAIL (sticky)."""
    _reporter.pytest_runtest_logreport(
        _make_report("a.py::t[x]", "failed", failed=True)
    )
    _reporter.pytest_runtest_logreport(_make_report("a.py::t[x]", "passed"))
    assert _reporter._PER_TOOL["x"]["verdict"] == "FAIL"


def test_aggregation_passed_then_failed_becomes_fail() -> None:
    """D-03 rule 1 also wins when failure arrives second."""
    _reporter.pytest_runtest_logreport(_make_report("a.py::t[x]", "passed"))
    _reporter.pytest_runtest_logreport(
        _make_report("a.py::t[x]", "failed", failed=True)
    )
    assert _reporter._PER_TOOL["x"]["verdict"] == "FAIL"


def test_aggregation_setup_error_collapses_to_fail() -> None:
    """D-03a: error outcome (setup-phase failure) collapses to FAIL."""
    _reporter.pytest_runtest_logreport(
        _make_report("a.py::t[x]", "failed", when="setup", failed=True)
    )
    assert _reporter._PER_TOOL["x"]["verdict"] == "FAIL"


def test_aggregation_all_skipped_yields_skip() -> None:
    """D-03 rule 3: all reports skipped -> SKIP."""
    _reporter.pytest_runtest_logreport(
        _make_report(
            "a.py::t[x]", "skipped",
            longrepr=("a.py", 1, "Skipped: r1"),
        )
    )
    assert _reporter._PER_TOOL["x"]["verdict"] == "SKIP"


def test_aggregation_pass_plus_skip_yields_pass() -> None:
    """D-03 rule 2: any passed wins over partial skips."""
    _reporter.pytest_runtest_logreport(_make_report("a.py::t[x]", "passed"))
    _reporter.pytest_runtest_logreport(
        _make_report(
            "a.py::t[x]", "skipped",
            longrepr=("a.py", 1, "Skipped: judge not selected"),
        )
    )
    assert _reporter._PER_TOOL["x"]["verdict"] == "PASS"


def test_aggregation_unit_test_excluded() -> None:
    """D-02a: report without [<tool>] suffix does NOT grow _PER_TOOL."""
    _reporter.pytest_runtest_logreport(
        _make_report("tests/unit/test_pure.py::test_y", "passed")
    )
    assert _reporter._PER_TOOL == {}


def test_skip_reason_dedup_first_seen_order() -> None:
    """D-05: reasons collected in first-seen order, deduplicated."""
    for reason in ["A", "B", "A", "C"]:
        _reporter.pytest_runtest_logreport(
            _make_report(
                "a.py::t[x]", "skipped",
                longrepr=("a.py", 1, f"Skipped: {reason}"),
            )
        )
    assert _reporter._PER_TOOL["x"]["reasons"] == ["A", "B", "C"]


# ===========================================================================
# Unit-level: pytest_terminal_summary -q suppression (D-04b)
# ===========================================================================


class _FakeTerminal:
    """Minimal terminalreporter stub. Captures write_sep/write_line calls."""

    def __init__(self, verbose: int = 0) -> None:
        self.config = SimpleNamespace(option=SimpleNamespace(verbose=verbose))
        self.lines: list[str] = []
        self.seps: list[tuple[str, str | None]] = []

    def write_line(self, line: str, **markup) -> None:
        self.lines.append(line)

    def write_sep(self, sep_char: str, title: str | None = None, **markup) -> None:
        self.seps.append((sep_char, title))


def test_terminal_summary_suppressed_under_quiet() -> None:
    """D-04b: verbose < 0 (i.e. -q) suppresses the per-tool section."""
    _reporter.pytest_runtest_logreport(_make_report("a.py::t[x]", "passed"))
    term = _FakeTerminal(verbose=-1)
    _reporter.pytest_terminal_summary(term, 0, term.config)
    assert term.lines == []
    assert term.seps == []


def test_terminal_summary_emits_at_default_verbose() -> None:
    """D-04: always-on at default verbose level."""
    _reporter.pytest_runtest_logreport(_make_report("a.py::t[x]", "passed"))
    term = _FakeTerminal(verbose=0)
    _reporter.pytest_terminal_summary(term, 0, term.config)
    # Section header was written.
    assert any(title == "per-tool summary" for _sep, title in term.seps)
    # PASS row present.
    assert any("PASS" in line and "x" in line for line in term.lines)


def test_terminal_summary_row_order_fail_skip_pass(tmp_path: Path) -> None:
    """CD-03: FAIL -> SKIP -> PASS, alphabetical within each.

    The grouping header line itself contains the substring "alphabetical"
    three times, so a naive ``out.find("alpha")`` would match inside the
    header rather than the alpha-named FAIL row. We instead filter
    ``term.lines`` down to the actual rendered ROW lines (two-space indent,
    not one of the group headers ``failures:``/``skipped:``/``passing:``,
    not the parenthesized grouping annotation), then assert the tool-name
    order across that filtered row list. This makes the within-FAIL-group
    alphabetical assertion tight: if the alpha row were missing, the test
    would fail because the row sequence would not start with ``alpha``.
    """
    # FAIL: zoo, alpha (intentionally insert in non-alphabetical order to
    # exercise the within-group sort)
    _reporter.pytest_runtest_logreport(
        _make_report("a.py::t[zoo]", "failed", failed=True)
    )
    _reporter.pytest_runtest_logreport(
        _make_report("a.py::t[alpha]", "failed", failed=True)
    )
    # SKIP: gamma
    _reporter.pytest_runtest_logreport(
        _make_report(
            "a.py::t[gamma]", "skipped",
            longrepr=("a.py", 1, "Skipped: reason"),
        )
    )
    # PASS: mango
    _reporter.pytest_runtest_logreport(_make_report("a.py::t[mango]", "passed"))

    term = _FakeTerminal(verbose=0)
    _reporter.pytest_terminal_summary(term, 0, term.config)

    # Row lines: two-space indent (the renderer uses ``  {tool.ljust(...)}``)
    # AND not one of the group-header / grouping-annotation lines. The group
    # headers are emitted WITHOUT leading spaces (``failures:`` etc.), and
    # the grouping annotation line begins with ``(``, so the indent guard
    # alone is sufficient -- but we add an explicit exclusion for safety in
    # case future edits change the header indentation.
    row_lines = [
        ln for ln in term.lines
        if ln.startswith("  ")
        and not ln.lstrip().startswith(("failures:", "skipped:", "passing:", "("))
    ]
    # Extract the tool name from each row (first non-space token).
    row_tools = [ln.split()[0] for ln in row_lines]

    # CD-03 contract: FAIL group first (alphabetical: alpha, zoo),
    # then SKIP group (gamma), then PASS group (mango).
    assert row_tools == ["alpha", "zoo", "gamma", "mango"], (
        f"row order does not match CD-03 grouping/alpha rules; "
        f"row_lines={row_lines!r}"
    )

    # Defense-in-depth: the alpha row must exist as a real FAIL row
    # (substring match on the full line, NOT on the grouping header).
    assert any("alpha" in ln and "FAIL" in ln for ln in row_lines), (
        f"no FAIL row for 'alpha' tool in row_lines={row_lines!r}"
    )


def test_terminal_summary_pass_row_no_reason_suffix() -> None:
    """D-03b: PASS rows have NO ' -- <reason>' / ' - <reason>' suffix."""
    _reporter.pytest_runtest_logreport(_make_report("a.py::t[ok]", "passed"))
    term = _FakeTerminal(verbose=0)
    _reporter.pytest_terminal_summary(term, 0, term.config)
    pass_lines = [line for line in term.lines if "ok" in line and "PASS" in line]
    assert pass_lines, term.lines
    for line in pass_lines:
        assert " - " not in line and " — " not in line, line


def test_terminal_summary_fail_row_no_reason_suffix() -> None:
    """D-03b: FAIL rows have NO reason text on the summary row."""
    _reporter.pytest_runtest_logreport(
        _make_report("a.py::t[bad]", "failed", failed=True)
    )
    term = _FakeTerminal(verbose=0)
    _reporter.pytest_terminal_summary(term, 0, term.config)
    fail_lines = [line for line in term.lines if "bad" in line and "FAIL" in line]
    assert fail_lines, term.lines
    for line in fail_lines:
        assert " - " not in line and " — " not in line, line


def test_terminal_summary_skip_row_with_reason() -> None:
    """D-05 + ROADMAP SC-3: SKIP rows render with reason text using the
    em-dash (`—`, U+2014) separator -- verbatim ROADMAP wording
    `<tool_name>: PASS|FAIL|SKIP — <reason>`. Also asserts that the ASCII
    hyphen form (` SKIP - `) is NOT present, so any future regression to
    ASCII fails this test.
    """
    _reporter.pytest_runtest_logreport(
        _make_report(
            "a.py::t[s]", "skipped",
            longrepr=("a.py", 1, "Skipped: needs upstream fix"),
        )
    )
    term = _FakeTerminal(verbose=0)
    _reporter.pytest_terminal_summary(term, 0, term.config)
    skip_lines = [line for line in term.lines if "s" in line and "SKIP" in line]
    # Em-dash separator with reason text present.
    assert any(
        " SKIP — needs upstream fix" in line for line in skip_lines
    ), f"em-dash SKIP row missing; skip_lines={skip_lines!r}"
    # ASCII hyphen separator MUST NOT be present (regression guard).
    for line in skip_lines:
        assert " SKIP - " not in line, (
            f"ASCII-hyphen SKIP separator detected -- should be em-dash per "
            f"ROADMAP SC-3: {line!r}"
        )


# ===========================================================================
# Live: end-to-end JUnit XML + per-tool summary against real homelab-mcp
# ===========================================================================


def _run_framework_subprocess(
    *args: str,
    cwd: Path,
) -> subprocess.CompletedProcess:
    """Drive `mcp-test-framework run` in a subprocess so the plugin's
    pytest_terminal_summary fires in its OWN pytest session (not nested
    inside the calling test's session, which would skew terminalreporter
    state).

    Mirrors tests/test_tool_config.py's subprocess.run([sys.executable,
    "-m", ...]) pattern. Uses the installed console-script via
    ``uv run mcp-test-framework`` to exercise the actual entry point.
    """
    return subprocess.run(
        [
            "uv",
            "run",
            "mcp-test-framework",
            "run",
            *args,
            "--",
            "-m",
            "live_homelab",
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.live_homelab
def test_junit_xml_emitted_and_well_formed(tmp_path: Path) -> None:
    """OUTPUT-01: --junit-xml=PATH writes a well-formed XML file.

    Drives a real `mcp-test-framework run --junit-xml=<path> -- -m live_homelab`
    subprocess and parses the resulting XML via xml.etree.ElementTree.

    Why subprocess: pytest_terminal_summary needs its own pytest session;
    nesting CliRunner.invoke inside this test would conflate report streams.
    """
    repo_root = Path(__file__).parent.parent
    target = tmp_path / "results.xml"

    proc = _run_framework_subprocess(f"--junit-xml={target}", cwd=repo_root)

    # The subprocess exit code mirrors pytest's exit code -- non-zero is
    # acceptable here because Phase 08 retained an upstream-blocked failure
    # (suggest_deployments disambiguation rubric). What we care about is
    # that the XML file was produced.
    assert target.exists(), (
        f"JUnit XML not produced at {target}. "
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )

    # Parse for well-formedness. ElementTree.parse raises on malformed XML.
    tree = ET.parse(target)
    root = tree.getroot()

    # pytest emits <testsuites> as the root for multi-suite output, or
    # <testsuite> for a single suite. Accept either per CD-01 (pytest defaults).
    assert root.tag in {"testsuites", "testsuite"}, root.tag


@pytest.mark.live_homelab
def test_junit_xml_testcase_names_carry_tool_suffix(tmp_path: Path) -> None:
    """OUTPUT-02 (ROADMAP SC-2): <testcase> name attributes carry the
    `[<tool_name>]` SUFFIX -- name BOTH contains `[` AND ends with `]`.

    L-01: parametrize IDs from Phase 07 free-ride into pytest's JUnit
    reporter natively. Phase 09 verifies the contract; no Phase 09 code
    produces this -- we just check pytest's defaults still emit it.

    Tightness rationale: a previous version of this assertion checked only
    ``"[" in name``, which would pass on a name like ``test_x[a]something``
    that violates the ROADMAP SC-2 SUFFIX contract. We now require BOTH
    ``"[" in name`` AND ``name.endswith("]")`` -- matching the parsing rule
    in ``_extract_tool_name`` (09-02 PLAN line ~206).
    """
    repo_root = Path(__file__).parent.parent
    target = tmp_path / "results.xml"

    proc = _run_framework_subprocess(f"--junit-xml={target}", cwd=repo_root)
    assert target.exists(), (
        f"JUnit XML not produced. "
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )

    tree = ET.parse(target)
    root = tree.getroot()
    # Find every <testcase> element regardless of nesting depth.
    testcases = list(root.iter("testcase"))
    # ROADMAP SC-2 SUFFIX contract: name has `[` AND ends with `]`.
    names_with_suffix = [
        tc.get("name", "")
        for tc in testcases
        if "[" in tc.get("name", "") and tc.get("name", "").endswith("]")
    ]
    assert names_with_suffix, (
        "No <testcase> with `[<tool>]` SUFFIX found (name must contain `[` "
        "AND end with `]`). Phase 07 IDs not flowing into JUnit XML, or "
        "the SUFFIX contract from ROADMAP SC-2 is violated. "
        f"All testcase names: {[tc.get('name', '') for tc in testcases]!r}\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )


@pytest.mark.live_homelab
def test_per_tool_summary_section_always_on() -> None:
    """OUTPUT-03 + D-04: terminal output of `mcp-test-framework run` contains
    a `per-tool summary` section by default.
    """
    repo_root = Path(__file__).parent.parent

    proc = _run_framework_subprocess(cwd=repo_root)

    # The section header is emitted via terminalreporter.write_sep with
    # title="per-tool summary" -- pytest renders the title between '=' chars.
    assert "per-tool summary" in proc.stdout, (
        f"per-tool summary section missing from terminal output.\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )

    # CD-03: grouping header line is present.
    assert "grouping:" in proc.stdout, (
        f"per-tool summary grouping header missing.\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
