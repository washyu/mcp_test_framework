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

import os  # noqa: F401  -- reserved for future env-passthrough hooks
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
    """
    forwarded = list(pytest_args or [])
    args: list[str] = ["tests"]
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
        inner_args = _build_pytest_args(junit_xml, pytest_args)
        argv = [sys.executable, "-m", "pytest", *inner_args]
        proc = subprocess.run(argv, check=False)
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
    inner_args = _build_pytest_args(None, pytest_args)
    argv = [
        sys.executable,
        "-m",
        "pytest",
        *inner_args,
        f"--junitxml={tmp}",
    ]
    proc = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
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
# Ported from the v1.1 plugin (`_reporter.py` -- to be deleted in Plan 14-05)
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
            msg = elem.get("message")
            if msg and bucket.failure_message is None:
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
