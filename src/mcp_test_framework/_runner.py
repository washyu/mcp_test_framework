"""Subprocess pytest dispatch + tempfile JUnit XML capture + exit-code mapping.

Phase 14 contract (cites Phase 14 D-01..D-16 and Phase 09 OUTPUT-01):
  - D-01: pytest runs as a child subprocess via [sys.executable, '-m', 'pytest', ...];
          the in-process pytest entry point is forbidden in the wrapper to
          keep the wrapper process decoupled from pytest's plugin globals.
  - D-02: default mode allocates an internal tempfile JUnit XML; operator
          --junit-xml=PATH is honored via a post-subprocess shutil.copy fan-out
          (NOT via a second pytest --junitxml argument, so the wrapper owns the
          tempfile exclusively for parsing).
  - D-03/D-11: the cli.py:run pre-flight gate (_load_config) is the caller's
          responsibility on BOTH default and --raw paths; this module assumes
          the gate has already fired.
  - D-15: pytest exit code mapping (0->0, 1->1, 2->2, 5->0+"no tests collected"
          warning; other codes pass through). KeyboardInterrupt is NEVER caught
          here -- SIGINT propagates so Typer's standalone_mode emits 130.
  - D-16: if pytest exits without writing the tempfile, callers should invoke
          _dispatch_default_mode_or_error to surface an operator-tone diagnostic.
  - Phase 09 OUTPUT-01 (RUNNER-05 preservation): operator --junit-xml=PATH
          continues to receive a valid JUnit XML.

This module also hosts _build_pytest_args and _emit_operator_error -- they
moved here from cli.py (Phase 14 D-01) to avoid a circular import (cli.py
imports _runner; _runner needs the helpers). cli.py re-exports both symbols
so existing tests that `from mcp_test_framework.cli import _build_pytest_args`
keep working.
"""
from __future__ import annotations

import os  # used by run_pytest_subprocess for child env (PYTHONIOENCODING)
import shutil
import subprocess
import sys
import tempfile
import typing
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import typer

from .rubrics import RUBRIC_IDS


# ===========================================================================
# Helpers promoted from cli.py (Phase 14 D-01 -- avoid circular import)
# ===========================================================================


def _emit_operator_error(
    summary: str,
    detail: list[str],
    next_step: str,
    *,
    exit_code: int = 2,
) -> typing.NoReturn:
    """Render an operator-grade error and exit (citation: docs/ERROR-STYLE.md).

    This function never returns; it raises typer.Exit internally. Callers
    MUST NOT prefix calls with `raise`.

    Format (per docs/ERROR-STYLE.md):
        <one-line summary>
        <blank>
        <detail line 1>
        <detail line 2>
        ...
        <blank>
        next: <action verb> <command-or-instruction>

    Operator terms only -- no spec IDs, no file:line refs, no internal jargon.
    """
    parts: list[str] = [summary, ""]
    parts.extend(detail)
    parts.extend(["", f"next: {next_step}"])
    typer.echo("\n".join(parts), err=True)
    raise typer.Exit(code=exit_code)


def _build_pytest_args(
    junit_xml: Path | None,
    pytest_args: list[str] | None,
    *,
    with_framework: bool = False,
    sdet: bool = False,
) -> list[str]:
    """Translate `--junit-xml=PATH` (Phase 09 D-01b public spelling) into pytest's
    `--junitxml=PATH` (no-dash internal spelling) and assemble the argv passed to
    ``pytest`` (in v1.1 to the in-process entry point; in Phase 14 to the subprocess
    argv after `[sys.executable, '-m', 'pytest']`).

    D-01a precedence: the explicit flag is inserted BEFORE the passthrough
    forwarded args so a later passthrough ``--junitxml=...`` (after ``--``)
    wins under pytest's last-occurrence argparse rule. The helper does NOT
    de-duplicate or validate paths -- pytest's own argument handling is the
    single source of truth.

    Phase 15 D-03: scope is operator-default ``tests/contract`` only;
    ``with_framework=True`` APPENDS ``tests/framework`` (not REPLACE) so
    ``--with-framework`` is a superset matching the pre-split
    ``pytest tests/`` collection.

    Phase 18 D-04 / D-05: ``sdet=True`` SWAPS the operator-surface scope from
    ``tests/contract`` to ``tests/sdet`` (not additive); ``with_framework=True``
    remains ALWAYS additive on top of whichever scope is active. ``--sdet`` is
    wrapper-owned and never reaches pytest's argv (Phase 16 D-07 pattern).
    """
    forwarded = list(pytest_args or [])
    if sdet:
        # Phase 18 D-04: --sdet SWAPS the operator-surface scope (NOT additive).
        args: list[str] = ["tests/sdet"]
    else:
        args = ["tests/contract"]
    if with_framework:
        # Phase 15 + Phase 18 D-05: --with-framework is ALWAYS additive on top
        # of whichever operator-surface scope is active.
        args.append("tests/framework")
    if junit_xml is not None:
        args.append(f"--junitxml={junit_xml}")
    args.extend(forwarded)
    return args


# ===========================================================================
# Exit-code mapping (Phase 14 D-15)
# ===========================================================================


def _map_exit_code(pytest_rc: int) -> tuple[int, str | None]:
    """Phase 14 D-15: pytest 0->0, 1->1, 2->2, 5->0 (with warning).

    Other codes pass through unchanged. Returns (mapped_code, optional_warning).
    SIGINT (130) is never seen here under normal flow -- KeyboardInterrupt is
    not caught by run_pytest_subprocess. The 130 pass-through is defensive
    only (e.g., a subprocess that catches its own SIGINT and exits 130).
    """
    if pytest_rc == 5:
        return (0, "no tests collected")
    return (pytest_rc, None)


# ===========================================================================
# Subprocess dispatch (Phase 14 D-01 / D-02 / D-11 / D-15)
# ===========================================================================


def run_pytest_subprocess(
    *,
    junit_xml: Path | None,
    pytest_args: list[str] | None,
    raw: bool,
    with_framework: bool = False,
    sdet: bool = False,
) -> tuple[int, Path | None, str, str]:
    """Spawn pytest as a child process and return its result.

    Returns:
        (exit_code, tempfile_xml_path_or_None, captured_stdout, captured_stderr)

    Default mode (raw=False):
      - Allocate an internal tempfile XML (suffix='.xml', delete=False).
      - argv = [sys.executable, '-m', 'pytest',
                *_build_pytest_args(None, pytest_args),
                f'--junitxml=<tempfile>']
        NOTE: operator junit_xml is passed as None to _build_pytest_args so
        only ONE --junitxml arg (the wrapper's tempfile) reaches pytest.
        After subprocess completes, if operator junit_xml was supplied, we
        shutil.copy(tempfile, operator_path) so the operator's path is
        populated independently. This avoids relying on pytest's
        last-occurrence rule and gives the wrapper an exclusive tempfile
        to parse.
      - capture_output=True, text=True, check=False.

    Raw mode (raw=True):
      - argv = [sys.executable, '-m', 'pytest',
                *_build_pytest_args(junit_xml, pytest_args)]
        No internal tempfile. No capture (stdout/stderr inherit so operator
        sees raw output live). Operator-supplied --junit-xml=PATH still
        flows through _build_pytest_args (Phase 09 D-01a).
      - check=False.
      - Returns (exit_code, None, "", "") -- caller does not render.

    Does NOT catch KeyboardInterrupt: SIGINT propagates so Typer emits 130
    (Phase 14 D-15 / Phase 04.1 AsyncExitStack contract).
    """
    if raw:
        # D-11: raw mode -- no internal tempfile, no capture.
        inner_args = _build_pytest_args(
            junit_xml, pytest_args, with_framework=with_framework, sdet=sdet
        )
        argv = [sys.executable, "-m", "pytest", *inner_args]
        # Phase 14 gap-closure (GAP 1 from 14-HUMAN-UAT.md): force the child
        # pytest to WRITE utf-8 bytes even on Windows (where the default code
        # page is cp1252 and would otherwise leak bytes like 0x97 -- cp1252
        # em-dash -- into the inherited stdout). The parent's sys.stdout has
        # already been reconfigured to utf-8 by cli.run before reaching here,
        # so the child inherits a utf-8-capable fd.
        child_env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        proc = subprocess.run(argv, check=False, env=child_env)
        return (proc.returncode, None, "", "")

    # Default mode -- allocate an internal tempfile JUnit XML.
    # NamedTemporaryFile is closed immediately; we only want the path.
    # delete=False so the child subprocess can open it for write on Windows.
    handle = tempfile.NamedTemporaryFile(suffix=".xml", delete=False)
    tmp = Path(handle.name)
    handle.close()
    # Remove the empty zero-byte placeholder so a "no XML written" condition
    # (D-16) is detectable via .exists() / size checks after subprocess exits.
    # On Windows the file was created but is empty; pytest will overwrite it
    # with its real JUnit body. If pytest crashes before writing, we want
    # _dispatch_default_mode_or_error to fire.
    try:
        tmp.unlink()
    except OSError:
        pass

    # operator junit_xml is deliberately suppressed inside _build_pytest_args
    # so only the wrapper's tempfile is exposed to pytest as --junitxml.
    inner_args = _build_pytest_args(
        None, pytest_args, with_framework=with_framework, sdet=sdet
    )
    argv = [
        sys.executable,
        "-m",
        "pytest",
        *inner_args,
        f"--junitxml={tmp}",
    ]
    # Phase 14 gap-closure (GAP 1 from 14-HUMAN-UAT.md): two-sided encoding hygiene.
    # - PYTHONIOENCODING in the child env forces pytest to WRITE utf-8 bytes even
    #   on Windows (where the default code page is cp1252 and would otherwise leak
    #   bytes like 0x97 -- cp1252 em-dash -- into the captured stdout, causing the
    #   parent's utf-8 decoder to raise UnicodeDecodeError mid-capture).
    # - errors="replace" on the parent decode is a belt-and-suspenders fallback so
    #   a stray non-utf-8 byte never raises mid-capture -- it is replaced with
    #   U+FFFD and the renderer still gets a complete string to work with.
    child_env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        env=child_env,
    )

    # Fan-out: if operator wanted the XML at PATH, copy from the tempfile.
    if junit_xml is not None and tmp.exists():
        try:
            shutil.copy(str(tmp), str(junit_xml))
        except OSError:
            # Best-effort fan-out; if the copy fails the wrapper still
            # owns the tempfile for parsing. The operator can re-run with
            # an explicit destination they own.
            pass

    return (
        proc.returncode,
        tmp,
        proc.stdout or "",
        proc.stderr or "",
    )


# ===========================================================================
# D-16: domain-shaped error for "pytest exited without producing JUnit XML"
# ===========================================================================


def _dispatch_default_mode_or_error(
    tmp_path: Path | None,
    exit_code: int,
    captured_stderr: str,
) -> None:
    """Phase 14 D-16: if pytest crashed before writing the tempfile, surface
    a domain-shaped error pointing the operator at --debug / --raw for raw
    pytest output.

    Only fires when the tempfile path is missing/empty AND pytest exited
    non-zero -- a clean exit with no XML (e.g., pytest 5 + no XML emission
    on some plugin combos) is mapped by _map_exit_code instead.

    Calls _emit_operator_error which raises typer.Exit(2); never returns
    when fired. Returns None silently when the tempfile is present.
    """
    if tmp_path is not None and tmp_path.exists():
        return
    if exit_code == 0:
        return
    _emit_operator_error(
        summary="pytest exited without producing a JUnit XML",
        detail=[
            "the test runner crashed before writing its results file.",
            "this usually means a collection error or a fixture-setup failure.",
            "",
            "captured stderr (last 20 lines):",
            *captured_stderr.splitlines()[-20:],
        ],
        next_step=(
            "re-run with `--raw` to see pytest's native output, or pass "
            "`--config PATH` to verify config resolution"
        ),
    )


# ===========================================================================
# Phase 14 Plan 02: JUnit XML parser + domain model
# ===========================================================================
#
# Ported from the v1.1 in-pytest reporter plugin (deleted in Plan 14-05)
# adapted to read JUnit XML elements rather than pytest report objects.
# Pins Phase 09 D-03 (any-fail-wins) + D-05 (skip-reason dedup+cap) + Phase 13
# D-12 (locked skip-reason constants). Tests pin both constants verbatim in
# tests/unit/test_runner_parser.py::test_runner_skip_reason_constants_locked.
# ===========================================================================

_SKIP_REASON_CAP: int = 3

# Phase 13 D-12 / SAFE-01: two distinct skip-reason strings for opt-in
# tool selection. Module-level constants so they cannot drift silently.
_REASON_NOT_SELECTED = "not selected in config"        # state (a): unlisted
_REASON_EXPLICIT_DEFAULT = "explicit skip in config"   # state (c): default

# Phase 16 D-03: pre-run "Test plan" multiplier. Pinned by
# tests/framework/unit/test_runner_pre_run_digest.py::test_cases_per_contract_tool_constant_locked
# AND by tests/framework/unit/test_runner_pre_run_digest.py::test_cases_per_contract_tool_matches_actual_parametrize_count
# (which AST-counts test_* funcs in tests/contract/test_mcp_tool_contract.py).
# Sources: 5 schema validators + 4 judge dimensions + 1 output conformance = 10.
CASES_PER_CONTRACT_TOOL: int = 10


def _extract_tool_name(nodeid_or_name: str) -> str | None:
    """Return tool name from `[<tool>]` parametrize suffix, or None.

    Ported from the v1.1 plugin's _extract_tool_name (Phase 09 D-02a). Works on
    both pytest ``report.nodeid`` (``<file>::<test>[<tool>]``) and JUnit XML
    ``<testcase name="test_x[<tool>]">`` -- the bracket grammar is identical.

    rindex picks the LAST ``[...]`` so nested suffixes (defensive against
    future parametrize layering) resolve to the innermost token.
    """
    if "[" not in nodeid_or_name or not nodeid_or_name.endswith("]"):
        return None
    return nodeid_or_name[nodeid_or_name.rindex("[") + 1 : -1]


def _strip_pytest_skipped_prefix(text: str | None) -> str | None:
    """Strip pytest's ``Skipped: `` prefix that wraps operator-supplied
    ``pytest.skip(reason=...)`` strings in ``<skipped message="...">`` attrs.

    Ported from the v1.1 plugin's ``_extract_skip_reason`` prefix-strip half
    (Phase 09 D-05a). Returns ``None`` for ``None`` input so callers can chain
    without adding their own None-guard.
    """
    if text is None:
        return None
    prefix = "Skipped: "
    return text[len(prefix):] if text.startswith(prefix) else text


def _format_skip_reasons(reasons: list[str]) -> str:
    """Phase 09 D-05: dedup + cap at 3 + ``... (N more)``.

    Ported verbatim from the v1.1 plugin's ``_format_skip_reasons``. Callers
    are responsible for de-duplication on insertion (the parser already does
    this); this helper only handles the join + cap rendering.
    """
    if not reasons:
        return ""
    if len(reasons) <= _SKIP_REASON_CAP:
        return "; ".join(reasons)
    head = "; ".join(reasons[:_SKIP_REASON_CAP])
    return f"{head}; ... ({len(reasons) - _SKIP_REASON_CAP} more)"


# ---------------------------------------------------------------------------
# Domain model (consumed by the renderer in Plan 14-03)
# ---------------------------------------------------------------------------
#
# Stdlib dataclasses, no pydantic -- this is an internal seam between the
# parser and the renderer; no I/O validation is needed at this boundary.
# ---------------------------------------------------------------------------


Verdict = Literal["PASS", "FAIL", "SKIP"]


@dataclass
class ToolVerdict:
    """Aggregated per-tool outcome.

    Fields:
      name: the parametrize-id suffix (e.g. "list_registered_servers").
      verdict: PASS / FAIL / SKIP per Phase 09 D-03 (any-fail-wins).
      failure_message: the <failure message="..."> attribute (D-08 surface;
        NOT the long traceback body -- that lives in failure_body and is
        gated to --debug in Plan 14-04).
      failure_body: the <failure>/<error> element text. Reserved for --debug.
      skip_reasons: de-duplicated list after the ``Skipped: `` prefix-strip.
      case_count: total number of <testcase> elements that contributed.
      duration: sum of <testcase time="..."> across this tool's cases.
    """

    name: str
    verdict: Verdict
    failure_message: str | None = None
    failure_body: str | None = None  # XML <failure> body text; --debug only
    skip_reasons: list[str] = field(default_factory=list)
    case_count: int = 0
    duration: float = 0.0


@dataclass
class ParsedRun:
    """Top-level parse result.

    ``per_tool`` is keyed by extracted parametrize-id (Phase 07 ``ids=names``).
    ``total_time`` comes from ``<testsuite time="...">``.
    ``total_cases`` / ``total_failures`` / ``total_skipped`` / ``total_errors``
    come from ``<testsuite>`` attributes (D-08 surface for the summary line).
    """

    per_tool: dict[str, ToolVerdict] = field(default_factory=dict)
    total_time: float = 0.0
    total_cases: int = 0
    total_failures: int = 0
    total_skipped: int = 0
    total_errors: int = 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def parse_junit_xml(xml_path: Path) -> ParsedRun:
    """Parse a pytest JUnit XML file into a ParsedRun domain model.

    Phase 14 D-02/D-05/D-08/D-09. Stdlib ``xml.etree.ElementTree`` only --
    no new runtime dependency.

    Aggregation (Phase 09 D-03 any-fail-wins, ported from the v1.1 plugin):
      1. <testcase> with <failure> or <error> child -> verdict = FAIL (sticky)
      2. else passed (no child elements)            -> verdict = PASS unless
                                                       FAIL already set
      3. else <skipped> child                       -> verdict = SKIP if no
                                                       PASS/FAIL set; record
                                                       de-duplicated reason

    Order-independence: a tool's verdict is the same regardless of XML order
    among its <testcase> elements -- FAIL is sticky; PASS dominates SKIP.

    Raises:
        xml.etree.ElementTree.ParseError on malformed XML (caller catches and
        surfaces via D-16 in the cli.py wrapper).
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Locate the <testsuite> -- root may be <testsuites> wrapping it, or
    # <testsuite> directly. Pytest's writer wraps for multi-suite output
    # (rare) and ships <testsuite> directly for single-session (common).
    if root.tag == "testsuites":
        suites = list(root.iter("testsuite"))
        if not suites:
            return ParsedRun()
        suite = suites[0]  # pytest emits one suite per JUnit XML.
    elif root.tag == "testsuite":
        suite = root
    else:
        return ParsedRun()  # Unknown root -- empty parse.

    run = ParsedRun(
        total_time=float(suite.get("time", "0") or "0"),
        total_cases=int(suite.get("tests", "0") or "0"),
        total_failures=int(suite.get("failures", "0") or "0"),
        total_skipped=int(suite.get("skipped", "0") or "0"),
        total_errors=int(suite.get("errors", "0") or "0"),
    )

    # Transient tracker for per-tool "has any case passed?" state. Used to
    # demote PASS->SKIP when a tool has both kinds of cases and no FAIL.
    # Kept off the dataclass surface so consumers (renderer) never see it.
    _has_pass: dict[str, bool] = {}

    for tc in suite.iter("testcase"):
        name = tc.get("name", "")
        tool = _extract_tool_name(name)
        if tool is None:
            continue  # D-09: testcases without [<tool>] suffix excluded.

        bucket = run.per_tool.setdefault(
            tool, ToolVerdict(name=tool, verdict="PASS")
        )
        bucket.case_count += 1
        try:
            bucket.duration += float(tc.get("time", "0") or "0")
        except (TypeError, ValueError):
            pass  # malformed time -- skip rather than crash.

        failure = tc.find("failure")
        error = tc.find("error")
        skipped = tc.find("skipped")

        if failure is not None or error is not None:
            # D-03 rule 1: any failed/error -> FAIL (sticky).
            bucket.verdict = "FAIL"
            elem = failure if failure is not None else error
            # Phase 18 D-09: ToolCallError-attached JUnit properties (set by
            # tests/sdet/conftest.py:pytest_exception_interact -- see Plan
            # 18-07 Task 2) win over the raw <failure message="..."> attr
            # when present. The third property `mcptf_error_raw` carries the
            # CallToolResult.model_dump_json(indent=2) string and is consumed
            # by the --debug appendix builder via a second XML pass
            # (_extract_tool_call_errors_from_xml). No new ToolVerdict fields
            # are added: the appendix re-parses the XML rather than threading
            # the dump string through the dataclass (Strategy 1).
            props = tc.find("properties")
            prop_msg: str | None = None
            if props is not None:
                code: str | None = None
                msg_field: str | None = None
                for prop in props.iter("property"):
                    n = prop.get("name", "")
                    v = prop.get("value", "")
                    if n == "mcptf_error_code":
                        code = v or None
                    elif n == "mcptf_error_message":
                        msg_field = v
                if msg_field is not None:
                    # D-10: "[code] message" when code present; else bare.
                    prop_msg = f"[{code}] {msg_field}" if code else msg_field

            msg = elem.get("message")
            if prop_msg is not None and bucket.failure_message is None:
                bucket.failure_message = prop_msg
            elif msg and bucket.failure_message is None:
                bucket.failure_message = msg
            body = (elem.text or "").strip()
            if body and bucket.failure_body is None:
                bucket.failure_body = body
            continue

        if skipped is not None:
            # D-03 rule 3: SKIP sticks only if nothing else ever set verdict.
            reason = _strip_pytest_skipped_prefix(skipped.get("message"))
            if reason and reason not in bucket.skip_reasons:
                bucket.skip_reasons.append(reason)
            # Demote to SKIP only when no FAIL set AND no PASS case seen.
            if bucket.verdict != "FAIL" and not _has_pass.get(tool, False):
                bucket.verdict = "SKIP"
            continue

        # No failure / error / skipped child -> PASS case.
        # D-03 rule 2: PASS sets verdict unless FAIL already sticky.
        _has_pass[tool] = True
        if bucket.verdict != "FAIL":
            bucket.verdict = "PASS"

    return run


# ===========================================================================
# Phase 14 Plan 03: Domain UI renderer
# ===========================================================================
#
# Consumes ParsedRun (Plan 14-02) plus a RenderContext (non-XML metadata from
# cli.py:run) and emits the operator-facing header / per-tool rows / summary
# line described in SEED-011 §2 and Phase 14 D-04..D-09.
#
# Architectural shift vs the v1.1 in-pytest plugin: the state-(a)/(c) skip
# composer is now a PURE FUNCTION (_compose_unparametrized_skips_from_config)
# that takes discovered_tools as an argument rather than reading a module
# global off the deleted plugin. The wrapper runs outside the pytest process
# and cannot reach the in-pytest cache; it performs its own discovery call
# before launching the subprocess.
#
# Em-dash U+2014 ("—") appears verbatim in this source file -- locked at
# Phase 09 SC-3 and the v1.1 reporter tests (Plan 14 Plans 02-03 re-pin via
# tests/test_runner_renderer.py).
# ===========================================================================


@dataclass
class RenderContext:
    """Non-XML data the renderer needs.

    Phase 14 D-07: header inputs come from the resolved Config (server cmd,
    judges) and a wrapper-side discovery call (discovered tool list).
    Phase 14 D-09: total_planned_cases is the count of <testcase> elements
    we EXPECT (typically discovered-and-allowed tools * cases per tool);
    today this equals `parsed.total_cases` for the header's "Test plan: N
    contract cases" line, since pytest's collected count IS the plan.
    """

    server_cmd: str
    discovered_tools: list[str] = field(default_factory=list)
    tools_config: dict = field(default_factory=dict)  # name -> ToolConfig
    judges: list[str] = field(default_factory=list)
    total_planned_cases: int = 0


def _compose_unparametrized_skips_from_config(
    discovered_tools: list[str],
    tools_config: dict,
    ran_tools: set[str],
) -> dict[str, str]:
    """Phase 13 D-12/D-13 + Phase 14: state-(a)/(c) SKIP rows the wrapper
    composes outside the pytest process.

    Inputs:
      - discovered_tools: tools the MCP server advertises (from wrapper-side discovery).
      - tools_config: Config.tools (operator allowlist).
      - ran_tools: tools that DID parametrize and produced testcases
        (i.e., the keys of parsed.per_tool). Excluded from this composition;
        the standard per-tool rows path handles them.

    Returns {tool_name: reason} for every discovered tool that did NOT run.

    State (c): tool listed AND tools[name].skip is True
               -> skip_reason or _REASON_EXPLICIT_DEFAULT
    State (a): tool NOT in tools_config (or tools[name].skip is False but
               somehow didn't run -- defensive)
               -> _REASON_NOT_SELECTED

    Architectural shift vs the v1.1 in-pytest composer: this function is
    PURE -- discovered_tools is an argument, not a module global. The
    wrapper rediscovers tools before launching pytest (cli.py:
    _discover_tools_for_run) because the in-pytest cache lives in another
    process.
    """
    result: dict[str, str] = {}
    for name in discovered_tools:
        if name in ran_tools:
            continue
        cfg_entry = tools_config.get(name)
        if cfg_entry is not None and getattr(cfg_entry, "skip", False):
            reason = (getattr(cfg_entry, "skip_reason", "") or "").strip()
            result[name] = reason or _REASON_EXPLICIT_DEFAULT
        else:
            result[name] = _REASON_NOT_SELECTED
    return result


def _compose_pre_run_skip_reasons(
    discovered_tools: list[str],
    tools_config: dict,
) -> dict[str, str]:
    """Phase 16 D-05/D-14: pre-run skip-reason map for `--explain`.

    Pre-run wrapper that exposes ONLY state-(a) unlisted + state-(c) explicit
    skips. State-(b) tools (listed AND skip=False) are running pre-run and
    must NOT appear in the skip-explain output. The post-run composer's
    defensive `skip=False -> _REASON_NOT_SELECTED` fallback is correct for
    post-run (a state-b tool that produced no testcase is anomalous) but
    incorrect pre-run (state-b is the running set).

    Returns: {tool_name: reason_string} for state-(a)/(c) skips only.
    """
    # Compute the running set (state-b: in config AND skip != True), then
    # delegate to the post-run composer with ran_tools=<running>. This filters
    # state-b out via the existing `if name in ran_tools: continue` clause,
    # leaving only state-(a) unlisted + state-(c) explicit-skip entries.
    running: set[str] = {
        name
        for name in discovered_tools
        if name in tools_config and not getattr(tools_config[name], "skip", False)
    }
    return _compose_unparametrized_skips_from_config(
        discovered_tools, tools_config, ran_tools=running
    )


def _compose_judges_from_tool_configs(tools_config: dict) -> list[str]:
    """Phase 16 plan 05: build the digest's `Judges:` union, honoring TOOLCFG-06.

    ToolConfig.judges semantics (locked at models.py:98 + contract gates at
    tests/contract/test_mcp_tool_contract.py:124,154,185):
      - None  (default, unset)      -> run ALL rubrics in RUBRIC_IDS
      - []    (explicit empty list) -> explicit opt-out, run no rubrics on this tool
      - [...] (subset list)         -> run literally these rubrics

    The pre-run digest must reflect what will actually execute. Pre-plan-05,
    cli.py's union loop used `getattr(tool_cfg, "judges", []) or []`, which
    silently collapsed the None default to [] and produced an empty union
    even when every tool was running all three rubrics at runtime.

    Returns: sorted list of rubric IDs that will fire for at least one
    configured tool. Empty list iff every tool explicitly opts out via [].
    """
    judges_set: set[str] = set()
    for tool_cfg in tools_config.values():
        declared = getattr(tool_cfg, "judges", None)
        if declared is None:
            judges_set.update(RUBRIC_IDS)  # TOOLCFG-06: None = run all rubrics
        else:
            judges_set.update(declared)    # [] is a no-op; subset passes through
    return sorted(judges_set)


# ---------------------------------------------------------------------------
# ANSI guard helpers (D-06: codes only when stdout is a TTY)
# ---------------------------------------------------------------------------


def _ansi_enabled(file) -> bool:
    """Phase 14 D-06: ANSI codes only when file is a TTY. Piped output stays plain."""
    return hasattr(file, "isatty") and file.isatty()


def _green(s: str, file) -> str:
    return f"\x1b[32m{s}\x1b[0m" if _ansi_enabled(file) else s


def _red(s: str, file) -> str:
    return f"\x1b[31m{s}\x1b[0m" if _ansi_enabled(file) else s


def _dim(s: str, file) -> str:
    return f"\x1b[2m{s}\x1b[0m" if _ansi_enabled(file) else s


# ---------------------------------------------------------------------------
# Header (SEED-011 §2 mockup -- verbatim shape for v1.2)
# ---------------------------------------------------------------------------


def _render_header(ctx: RenderContext, parsed: ParsedRun, file=None) -> None:
    """SEED-011 §2 mockup -- verbatim shape for v1.2.

    Lines (exact order):
      ========================================
      MCP Test Framework
      ========================================
      MCP server:  {server_cmd}
      Discovered:  {N} tools
      Running:     {R}  ({comma-joined names})
      Skipping:    {S}  (use --explain to list)
      Judges:      {comma-joined}
      Test plan:   {C} contract cases

    `file=None` defaults to sys.stdout resolved at call-time so pytest
    `capsys` capture works (capsys replaces sys.stdout per-test; a
    `file=sys.stdout` default would capture the pre-test stdout at function
    definition time and bypass the fixture).
    """
    if file is None:
        file = sys.stdout
    ran = sorted(parsed.per_tool.keys())
    discovered_n = len(ctx.discovered_tools)
    running_n = len(ran)
    skipping_n = max(0, discovered_n - running_n)
    judges_text = ", ".join(ctx.judges) if ctx.judges else "(none configured)"
    running_text = ", ".join(ran) if ran else "(none)"

    print("=" * 40, file=file)
    print("MCP Test Framework", file=file)
    print("=" * 40, file=file)
    print(f"MCP server:  {ctx.server_cmd}", file=file)
    print(f"Discovered:  {discovered_n} tools", file=file)
    print(f"Running:     {running_n:>2}  ({running_text})", file=file)
    print(f"Skipping:    {skipping_n:>2}  (use --explain to list)", file=file)
    print(f"Judges:      {judges_text}", file=file)
    print(f"Test plan:   {parsed.total_cases} contract cases", file=file)
    print("", file=file)  # blank line before per-tool rows


# ---------------------------------------------------------------------------
# Phase 16 D-01: Pre-run digest — moves SEED-011 §2 header to BEFORE pytest.
# ---------------------------------------------------------------------------


def _render_pre_run_digest(
    ctx: RenderContext,
    with_framework: bool = False,
    explain: bool = False,
    file=None,
) -> None:
    """Phase 16 D-01/D-03/D-04/D-12: pre-run digest emitted before pytest runs.

    Lines (exact order, ≤ 10 total in default mode; up to 11 with with_framework=True):
      ========================================
      MCP Test Framework
      ========================================
      MCP server:  {server_cmd}
      Discovered:  {N} tools
      Running:     {R}  ({comma-joined names, sorted})
      Skipping:    {S}  (use --explain to list)   [hint omitted if explain=True]
      Judges:      {comma-joined, sorted}
      Test plan:   {R * CASES_PER_CONTRACT_TOOL} contract cases
                   + framework self-tests        [only if with_framework=True]
      (blank line)

    `file=None` -> sys.stdout at call-time (capsys-friendly; see _render_header
    docstring for the rationale).

    D-04: two buckets only — Running and Skipping. The Phase 13 state-(a) /
    state-(c) distinction is visible in --explain output, not here.
    D-12: digest height ≤ 10 lines regardless of N (the Skipping list is
    NEVER inline-expanded here — `--explain` is the expansion surface).

    Running list is derived from `ctx.discovered_tools` filtered by
    `ctx.tools_config` (state-b: listed AND not skip:true). This matches
    the runtime selection logic in tests/conftest.py without re-importing it.
    """
    if file is None:
        file = sys.stdout

    discovered_n = len(ctx.discovered_tools)
    # state-b: tool is in tools_config AND tools_config[t].skip is not True.
    # Anything else (state-a unlisted, state-c skip:true) is "skipping".
    running = sorted(
        t
        for t in ctx.discovered_tools
        if t in ctx.tools_config and not getattr(ctx.tools_config[t], "skip", False)
    )
    running_n = len(running)
    skipping_n = max(0, discovered_n - running_n)
    judges_text = ", ".join(ctx.judges) if ctx.judges else "(none configured)"
    running_text = ", ".join(running) if running else "(none)"
    planned_cases = running_n * CASES_PER_CONTRACT_TOOL

    print("=" * 40, file=file)
    print("MCP Test Framework", file=file)
    print("=" * 40, file=file)
    print(f"MCP server:  {ctx.server_cmd}", file=file)
    print(f"Discovered:  {discovered_n} tools", file=file)
    print(f"Running:     {running_n:>2}  ({running_text})", file=file)
    # REVISION: omit "(use --explain to list)" hint when explain=True (the
    # explain block renders right below, so the hint would lie).
    if explain:
        print(f"Skipping:    {skipping_n:>2}", file=file)
    else:
        print(f"Skipping:    {skipping_n:>2}  (use --explain to list)", file=file)
    print(f"Judges:      {judges_text}", file=file)
    print(f"Test plan:   {planned_cases} contract cases", file=file)
    # REVISION: --with-framework suffix emits IMMEDIATELY after Test plan line,
    # BEFORE the trailing blank, as a continuation line. 13-space indent matches
    # the label column width so "+ framework self-tests" visually hangs under
    # the contract-cases value.
    if with_framework:
        print("             + framework self-tests", file=file)
    print("", file=file)  # blank line before next section


def _render_skipped_tools_explain(ctx: RenderContext, file=None) -> None:
    """Phase 16 D-05/D-13: `--explain` expansion of the digest's Skipping hint.

    Lines (alphabetical order):
      Skipping (N):
        <tool>  — <reason>      [N times, sorted alphabetically]
      (blank line)

    Reasons sourced from `_compose_pre_run_skip_reasons` (Phase 14's pure
    composer called with `ran_tools=set()` since pytest hasn't run yet).

    Format invariants (D-13, grep-able at N=70):
      - One tool per line, no wrapping.
      - U+2014 em-dash separator (matches Phase 09 SC-3 / Phase 14 _render_per_tool_rows).
      - Tool name left-justified to width(longest skipped tool name) for visual scan.
      - Output footprint ≤ N+2 lines (header + N tool lines + 1 trailing blank).

    `file=None` -> sys.stdout at call-time (capsys-friendly).
    """
    if file is None:
        file = sys.stdout

    skipped = _compose_pre_run_skip_reasons(ctx.discovered_tools, ctx.tools_config)
    if not skipped:
        # Edge: nothing to explain. Emit a zero-tool header so the operator
        # sees the empty state explicitly rather than silence.
        print("Skipping (0):", file=file)
        print("", file=file)
        return

    name_width = max(len(t) for t in skipped)
    print(f"Skipping ({len(skipped)}):", file=file)
    for tool in sorted(skipped.keys()):
        # U+2014 em-dash; two spaces before + after. Matches the
        # `  ✗ {tag} — {failure_message}` shape in _render_per_tool_rows.
        print(f"  {tool.ljust(name_width)}  — {skipped[tool]}", file=file)
    print("", file=file)


# ---------------------------------------------------------------------------
# Per-tool rows (Phase 09 CD-03 ordering, D-08 reasoning, em-dash separator)
# ---------------------------------------------------------------------------


def _render_per_tool_rows(
    parsed: ParsedRun,
    unparam_skips: dict[str, str],
    file=None,
) -> None:
    """Phase 09 CD-03: FAIL -> SKIP -> PASS, alphabetical within each.
    Phase 14 D-08: FAIL row appends `failure_message` after em-dash.
    Em-dash separator = U+2014 (literal '—'), not ASCII hyphen.
    `file=None` -> sys.stdout at call time (capsys-friendly).
    """
    if file is None:
        file = sys.stdout
    fails = sorted(t for t, v in parsed.per_tool.items() if v.verdict == "FAIL")
    skips_xml = {t for t, v in parsed.per_tool.items() if v.verdict == "SKIP"}
    passes = sorted(t for t, v in parsed.per_tool.items() if v.verdict == "PASS")

    # Union XML-derived SKIPs with state-(a)/(c) composer entries.
    all_skips = sorted(skips_xml | set(unparam_skips.keys()))

    all_names = list(parsed.per_tool.keys()) + list(unparam_skips.keys())
    name_width = max((len(n) for n in all_names), default=0)

    if fails:
        print("failures:", file=file)
        for tool in fails:
            v = parsed.per_tool[tool]
            tag = _red("FAIL", file)
            if v.failure_message:
                # U+2014 em-dash; matches Phase 09 SC-3 (locked separator).
                print(f"  {tool.ljust(name_width)}  ✗ {tag} — {v.failure_message}", file=file)
            else:
                print(f"  {tool.ljust(name_width)}  ✗ {tag}", file=file)

    if all_skips:
        print("skipped:", file=file)
        for tool in all_skips:
            if tool in parsed.per_tool and parsed.per_tool[tool].verdict == "SKIP":
                reasons_text = _format_skip_reasons(parsed.per_tool[tool].skip_reasons)
            else:
                reasons_text = unparam_skips[tool]
            tag = _dim("SKIP", file)
            if reasons_text:
                print(f"  {tool.ljust(name_width)}  – {tag} — {reasons_text}", file=file)
            else:
                print(f"  {tool.ljust(name_width)}  – {tag}", file=file)

    if passes:
        print("passing:", file=file)
        for tool in passes:
            tag = _green("PASS", file)
            print(f"  {tool.ljust(name_width)}  ✓ {tag}", file=file)


# ---------------------------------------------------------------------------
# Summary line
# ---------------------------------------------------------------------------


def _render_summary_line(
    parsed: ParsedRun,
    unparam_skips: dict[str, str],
    file=None,
) -> None:
    """SEED-011 §2: `Result: N PASS / M FAIL  in T.Ts`.

    Skip count includes state-(a)/(c) composer entries so the summary line
    agrees with the per-tool rows (must_haves truth: 'discovered/running/
    skipping counts agree with what the runner actually executes').
    `file=None` -> sys.stdout at call time (capsys-friendly).
    """
    if file is None:
        file = sys.stdout
    n_pass = sum(1 for v in parsed.per_tool.values() if v.verdict == "PASS")
    n_fail = sum(1 for v in parsed.per_tool.values() if v.verdict == "FAIL")
    n_skip = sum(1 for v in parsed.per_tool.values() if v.verdict == "SKIP") + len(unparam_skips)
    skip_segment = f" / {n_skip} SKIP" if n_skip else ""
    print("", file=file)
    print(
        f"Result: {n_pass} PASS / {n_fail} FAIL{skip_segment}  in {parsed.total_time:.1f}s",
        file=file,
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def render_domain_ui(
    parsed: ParsedRun,
    ctx: RenderContext,
    file=None,
) -> None:
    """Top-level renderer. Phase 14 D-04 (batch render) + D-06 (stdlib + ANSI).

    Order: per-tool rows -> summary line. (Header moved pre-run to
    _render_pre_run_digest per Phase 16 D-01.)
    State-(a)/(c) SKIP rows merge with XML-derived SKIPs via
    _compose_unparametrized_skips_from_config.
    `file=None` -> sys.stdout at call time (capsys-friendly).
    """
    if file is None:
        file = sys.stdout
    ran_tools = set(parsed.per_tool.keys())
    unparam_skips = _compose_unparametrized_skips_from_config(
        ctx.discovered_tools, ctx.tools_config, ran_tools
    )
    _render_per_tool_rows(parsed, unparam_skips, file=file)
    _render_summary_line(parsed, unparam_skips, file=file)


# ===========================================================================
# Phase 14 Plan 04: verbosity ladder helpers (D-12 / D-13)
# ===========================================================================
#
# Two orthogonal renderers extending render_domain_ui:
#   - render_summary_only: D-12 `-q` -- prints only the summary line.
#   - render_debug_appendix: D-13 `--debug` -- printed AFTER whatever the
#     default/quiet rung produced. Default UI shape unchanged regardless
#     of --debug (D-13 invariant: each rung adds info; none re-shapes
#     the layer below).
#
# The `--explain` flag is DELIBERATELY ABSENT here (D-14: Phase 16 owns it).
# ===========================================================================


def render_summary_only(
    parsed: ParsedRun,
    ctx: RenderContext,
    file=None,
) -> None:
    """Phase 14 D-12: `-q` / `--quiet` -- summary line only.

    No header, no per-tool rows. Same summary content as render_domain_ui's
    last line, including state-(a)/(c) SKIP count contribution so the
    quiet-mode summary agrees with the default-mode summary.

    `file=None` -> sys.stdout at call time (capsys-friendly), matching
    the other renderers in this module.
    """
    if file is None:
        file = sys.stdout
    ran_tools = set(parsed.per_tool.keys())
    unparam_skips = _compose_unparametrized_skips_from_config(
        ctx.discovered_tools, ctx.tools_config, ran_tools
    )
    _render_summary_line(parsed, unparam_skips, file=file)


def render_debug_appendix(
    captured_stdout: str,
    captured_stderr: str,
    parsed: ParsedRun,
    file=None,
) -> None:
    """Phase 14 D-13: `--debug` -- appended AFTER the domain UI.

    Order (only printed if non-empty):
      --- raw pytest output ---
      {captured_stdout verbatim}
      --- captured stderr ---
      {captured_stderr verbatim}     (only if non-empty)
      --- failure tracebacks ---     (only if any tool has failure_body)
      {tool_name}:
        {failure_body indented by 2 spaces}

    Default UI must be UNCHANGED whether --debug is passed or not (D-13
    invariant: each rung adds info; none re-shapes the layer below).

    The `--- raw pytest output ---` separator string is grep-able
    regression-pin material; do not reword.
    """
    if file is None:
        file = sys.stdout
    print("", file=file)
    print("--- raw pytest output ---", file=file)
    if captured_stdout:
        # Print verbatim -- no transformation. The operator asked for raw.
        print(captured_stdout.rstrip("\n"), file=file)
    else:
        print("(no stdout captured)", file=file)

    if captured_stderr:
        print("", file=file)
        print("--- captured stderr ---", file=file)
        print(captured_stderr.rstrip("\n"), file=file)

    failures_with_bodies = [
        (name, v.failure_body)
        for name, v in parsed.per_tool.items()
        if v.verdict == "FAIL" and v.failure_body
    ]
    if failures_with_bodies:
        print("", file=file)
        print("--- failure tracebacks ---", file=file)
        for name, body in sorted(failures_with_bodies):
            print(f"{name}:", file=file)
            for line in body.splitlines():
                print(f"  {line}", file=file)
            print("", file=file)


# ===========================================================================
# Phase 14 Plan 05: in-pytest discovery cache (migrated from the deleted
# v1.1 reporter plugin).
# ===========================================================================
#
# This cache lives in `_runner` (a real importable module under src/) rather
# than `tests/conftest.py` because `tests/` is NOT a Python package (no
# `tests/__init__.py`). Surviving Phase 13 SAFE-01 allowlist unit tests need
# to patch this cache via a real import path:
#
#     from mcp_test_framework import _runner as _r
#     _r._DISCOVERED_TOOL_NAMES = ["alpha", "beta"]
#
# This cache is SEPARATE from the wrapper-side discovery in
# `cli.py:_discover_tools_for_run`. The TWO-cache architecture is intentional
# for v1.2 (each discovery costs <1s); consolidation is a v1.3 candidate.
# The wrapper cache lives only on the RenderContext; this cache lives at
# module scope because `pytest_generate_tests` in conftest needs to read
# it across multiple parametrize calls within a single pytest session.
# ===========================================================================

_DISCOVERED_TOOL_NAMES: "list[str] | None" = None


def _set_discovered_tool_names(names: list[str]) -> None:
    """Phase 14 Plan 05: helper for `tests/conftest.py:_resolve_tool_names` to
    populate the in-pytest discovery cache without using a `global` declaration
    at the call site. Tests can patch the cache directly via
    `_runner._DISCOVERED_TOOL_NAMES = [...]`."""
    global _DISCOVERED_TOOL_NAMES
    _DISCOVERED_TOOL_NAMES = list(names)
