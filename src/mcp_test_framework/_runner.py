"""Subprocess pytest dispatch + tempfile JUnit XML capture + exit-code mapping.

Runner contract:
  - pytest runs as a child subprocess via ``[sys.executable, '-m', 'pytest', ...]``.
    The in-process pytest entry point is forbidden in the wrapper to keep the
    wrapper process decoupled from pytest's plugin globals.
  - Default mode allocates an internal tempfile JUnit XML; an operator-supplied
    ``--junit-xml=PATH`` is honored via a post-subprocess ``shutil.copy`` fan-out
    (not via a second ``pytest --junitxml`` argument, so the wrapper owns the
    tempfile exclusively for parsing).
  - The ``cli.py:run`` pre-flight gate (``_load_config``) is the caller's
    responsibility on both default and ``--raw`` paths; this module assumes
    the gate has already fired.
  - Pytest exit code mapping: ``0 -> 0``, ``1 -> 1``, ``2 -> 2``,
    ``5 -> 0 + "no tests collected" warning``; other codes pass through.
    ``KeyboardInterrupt`` is NEVER caught here -- SIGINT propagates so
    Typer's ``standalone_mode`` emits 130.
  - If pytest exits without writing the tempfile, callers should invoke
    ``_dispatch_default_mode_or_error`` to surface an operator-tone diagnostic.
  - Operator ``--junit-xml=PATH`` continues to receive a valid JUnit XML.

This module also hosts ``_build_pytest_args`` and ``_emit_operator_error`` --
they were moved here from ``cli.py`` to avoid a circular import (``cli.py``
imports ``_runner``; ``_runner`` needs the helpers). ``cli.py`` re-exports both
symbols so existing tests that ``from mcp_test_framework.cli import
_build_pytest_args`` keep working.
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

import pytest
import typer

from .rubrics import RUBRIC_IDS


# ===========================================================================
# Helpers promoted from cli.py (kept here to avoid a circular import)
# ===========================================================================


def _emit_operator_error(
    summary: str,
    detail: list[str],
    next_step: str,
    *,
    exit_code: int = 2,
) -> typing.NoReturn:
    """Render an operator-grade error and exit (see docs/ERROR-STYLE.md).

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
    sdet: bool = False,  # noqa: sdet-rename-shim
    mcp_config_path: Path | None = None,
) -> list[str]:
    """Translate the public ``--junit-xml=PATH`` spelling into pytest's
    ``--junitxml=PATH`` (no-dash internal spelling) and assemble the argv
    passed to ``pytest`` (in the subprocess argv after
    ``[sys.executable, '-m', 'pytest']``).

    Precedence: the explicit flag is inserted BEFORE the passthrough forwarded
    args so a later passthrough ``--junitxml=...`` (after ``--``) wins under
    pytest's last-occurrence argparse rule. The helper does NOT de-duplicate
    or validate paths -- pytest's own argument handling is the single source
    of truth.

    Scope rules:
      - Operator-default scope is ``tests/contract`` only.
      - ``with_framework=True`` APPENDS ``tests/framework`` (not REPLACE) so
        ``--with-framework`` is a superset matching the pre-split
        ``pytest tests/`` collection.
      - ``sdet=True`` (operator-facing flag is ``--test-code``) SWAPS the  # noqa: sdet-rename-shim
        operator-surface scope from ``tests/contract`` to ``tests/test_code``
        (not additive). Dual-discovery: the legacy ``tests/sdet/`` path is  # noqa: sdet-rename-shim
        retained as a fallback for v1.4 only (removed in v1.5); if
        it exists AND contains ``test_*.py`` files, both paths are passed
        to pytest. The session-once ``DeprecationWarning`` is fired from
        ``tests/test_code/conftest.py`` when items collect from the legacy
        path. ``with_framework=True`` remains ALWAYS additive on top of
        whichever scope is active. The wrapper-owned ``--test-code`` /
        ``--sdet`` flags never reach pytest's argv.  # noqa: sdet-rename-shim

    Config-path threading:
      - ``mcp_config_path`` (when set) is forwarded to the subprocess pytest
        via two argv elements ``[\"-o\", f\"mcp_config_file={path}\"]``.
        Pytest's ``-o key=value`` mechanism overrides ini values at runtime;
        the in-subprocess plugin's ``pytest_configure`` reads
        ``mcp_config_file`` via ``config.getini`` and constructs
        ``Config(yaml_file=path)``. This is the same code path the operator's
        ``[tool.pytest.ini_options] mcp_config_file = PATH`` drives in
        library mode -- one config-resolution mechanism end-to-end across
        CLI and library modes (no env-var write).
    """  # noqa: sdet-rename-shim
    forwarded = list(pytest_args or [])
    if sdet:  # noqa: sdet-rename-shim
        # --test-code SWAPS the operator-surface scope (NOT additive).
        # Dual-discovery: tests/test_code/ is the v1.4 primary path; the
        # legacy fallback path is kept for one milestone.  # noqa: sdet-rename-shim
        # The session-once DeprecationWarning fires from
        # tests/test_code/conftest.py when items collect from the legacy path.
        args: list[str] = ["tests/test_code"]
        legacy_sdet_dir = Path("tests/sdet")  # noqa: sdet-rename-shim
        if legacy_sdet_dir.is_dir() and any(legacy_sdet_dir.glob("test_*.py")):  # noqa: sdet-rename-shim
            args.append("tests/sdet")  # noqa: sdet-rename-shim
    else:
        args = ["tests/contract"]
    if with_framework:
        # --with-framework is ALWAYS additive on top of whichever
        # operator-surface scope is active.
        args.append("tests/framework")
    if junit_xml is not None:
        args.append(f"--junitxml={junit_xml}")
    args.extend(forwarded)
    if mcp_config_path is not None:
        # Pass the resolved config path to the in-subprocess plugin via
        # pytest's `-o key=value` runtime ini override. Two separate argv
        # elements -- subprocess.run takes a list, no shell interpretation,
        # no quoting concerns. The subprocess plugin's `pytest_configure`
        # reads `mcp_config_file` via `config.getini` and constructs
        # `Config(yaml_file=path)`. Same mechanism the operator's
        # `[tool.pytest.ini_options]` drives in library mode -- one
        # config-resolution route end-to-end.
        args.extend(["-o", f"mcp_config_file={mcp_config_path}"])
    return args


# ===========================================================================
# Exit-code mapping
# ===========================================================================


def _map_exit_code(pytest_rc: int) -> tuple[int, str | None]:
    """Map pytest's exit codes: ``0 -> 0``, ``1 -> 1``, ``2 -> 2``,
    ``5 -> 0 (with "no tests collected" warning)``.

    Other codes pass through unchanged. Returns ``(mapped_code, optional_warning)``.
    SIGINT (130) is never seen here under normal flow -- ``KeyboardInterrupt``
    is not caught by ``run_pytest_subprocess``. The 130 pass-through is
    defensive only (e.g., a subprocess that catches its own SIGINT and exits 130).
    """
    if pytest_rc == 5:
        return (0, "no tests collected")
    return (pytest_rc, None)


# ===========================================================================
# Subprocess dispatch
# ===========================================================================


def run_pytest_subprocess(
    *,
    junit_xml: Path | None,
    pytest_args: list[str] | None,
    raw: bool,
    with_framework: bool = False,
    sdet: bool = False,  # noqa: sdet-rename-shim
    mcp_config_path: Path | None = None,
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
        flows through _build_pytest_args.
      - check=False.
      - Returns (exit_code, None, "", "") -- caller does not render.

    Config-path threading:
      ``mcp_config_path`` (when set) is forwarded through
      ``_build_pytest_args`` so the subprocess pytest's argv carries
      ``-o "mcp_config_file=PATH"``. This is the CLI-side mirror of the
      operator's library-mode ``[tool.pytest.ini_options] mcp_config_file =
      PATH`` -- a single config-resolution mechanism end-to-end across CLI
      and library modes (no env-var write at any layer).

    Does NOT catch KeyboardInterrupt: SIGINT propagates so Typer emits 130
    (AsyncExitStack teardown contract).
    """
    if raw:
        # Raw mode -- no internal tempfile, no capture.
        inner_args = _build_pytest_args(
            junit_xml,
            pytest_args,
            with_framework=with_framework,
            sdet=sdet,  # noqa: sdet-rename-shim
            mcp_config_path=mcp_config_path,
        )
        argv = [sys.executable, "-m", "pytest", *inner_args]
        # Force the child pytest to WRITE utf-8 bytes even on Windows (where
        # the default code page is cp1252 and would otherwise leak bytes like
        # 0x97 -- cp1252 em-dash -- into the inherited stdout). The parent's
        # sys.stdout has already been reconfigured to utf-8 by cli.run before
        # reaching here, so the child inherits a utf-8-capable fd.
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
    # is detectable via .exists() / size checks after subprocess exits.
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
        None,
        pytest_args,
        with_framework=with_framework,
        sdet=sdet,  # noqa: sdet-rename-shim
        mcp_config_path=mcp_config_path,
    )
    argv = [
        sys.executable,
        "-m",
        "pytest",
        *inner_args,
        f"--junitxml={tmp}",
    ]
    # Two-sided encoding hygiene:
    # - PYTHONIOENCODING in the child env forces pytest to WRITE utf-8 bytes
    #   even on Windows (where the default code page is cp1252 and would
    #   otherwise leak bytes like 0x97 -- cp1252 em-dash -- into the captured
    #   stdout, causing the parent's utf-8 decoder to raise UnicodeDecodeError
    #   mid-capture).
    # - errors="replace" on the parent decode is a belt-and-suspenders fallback
    #   so a stray non-utf-8 byte never raises mid-capture -- it is replaced
    #   with U+FFFD and the renderer still gets a complete string to work with.
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
# Domain-shaped error for "pytest exited without producing JUnit XML"
# ===========================================================================


def _dispatch_default_mode_or_error(
    tmp_path: Path | None,
    exit_code: int,
    captured_stderr: str,
) -> None:
    """If pytest crashed before writing the tempfile, surface a domain-shaped
    error pointing the operator at ``--debug`` / ``--raw`` for raw pytest output.

    Only fires when the tempfile path is missing/empty AND pytest exited
    non-zero -- a clean exit with no XML (e.g., pytest 5 + no XML emission
    on some plugin combos) is mapped by ``_map_exit_code`` instead.

    Calls ``_emit_operator_error`` which raises ``typer.Exit(2)``; never
    returns when fired. Returns ``None`` silently when the tempfile is present.
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
# JUnit XML parser + domain model
# ===========================================================================
#
# Adapted from the legacy in-pytest reporter plugin to read JUnit XML elements
# rather than pytest report objects. Implements any-fail-wins aggregation plus
# the skip-reason dedup+cap at 3 with a trailing ``... (N more)`` suffix.
# Locked skip-reason constants below are pinned verbatim by
# tests/framework/unit/test_runner_parser.py::test_runner_skip_reason_constants_locked
# -- keep in sync if you edit them.
# ===========================================================================

_SKIP_REASON_CAP: int = 3

# Locked skip-reason constants for opt-in tool selection. Module-level
# constants so they cannot drift silently. Tests pin both verbatim.
_REASON_NOT_SELECTED = "not selected in config"        # state (a): unlisted
_REASON_EXPLICIT_DEFAULT = "explicit skip in config"   # state (c): default

# Pre-run "Test plan" multiplier. Pinned by
# tests/framework/unit/test_runner_pre_run_digest.py::test_cases_per_contract_tool_constant_locked
# AND by tests/framework/unit/test_runner_pre_run_digest.py::test_cases_per_contract_tool_matches_actual_parametrize_count
# (which AST-counts test_* funcs in tests/contract/test_mcp_tool_contract.py).
# Sources: 5 schema validators + 4 judge dimensions + 1 output conformance = 10.
CASES_PER_CONTRACT_TOOL: int = 10


def _extract_tool_name(nodeid_or_name: str) -> str | None:
    """Return tool name from ``[<tool>]`` parametrize suffix, or None.

    Works on both pytest ``report.nodeid`` (``<file>::<test>[<tool>]``) and
    JUnit XML ``<testcase name="test_x[<tool>]">`` -- the bracket grammar is
    identical.

    ``rindex`` picks the LAST ``[...]`` so nested suffixes (defensive against
    future parametrize layering) resolve to the innermost token.
    """
    if "[" not in nodeid_or_name or not nodeid_or_name.endswith("]"):
        return None
    return nodeid_or_name[nodeid_or_name.rindex("[") + 1 : -1]


def _strip_pytest_skipped_prefix(text: str | None) -> str | None:
    """Strip pytest's ``Skipped: `` prefix that wraps operator-supplied
    ``pytest.skip(reason=...)`` strings in ``<skipped message="...">`` attrs.

    Returns ``None`` for ``None`` input so callers can chain without adding
    their own None-guard.
    """
    if text is None:
        return None
    prefix = "Skipped: "
    return text[len(prefix):] if text.startswith(prefix) else text


def _format_skip_reasons(reasons: list[str]) -> str:
    """Dedup + cap at 3 + trailing ``... (N more)``.

    Callers are responsible for de-duplication on insertion (the parser
    already does this); this helper only handles the join + cap rendering.
    """
    if not reasons:
        return ""
    if len(reasons) <= _SKIP_REASON_CAP:
        return "; ".join(reasons)
    head = "; ".join(reasons[:_SKIP_REASON_CAP])
    return f"{head}; ... ({len(reasons) - _SKIP_REASON_CAP} more)"


# ---------------------------------------------------------------------------
# Domain model (consumed by the renderer)
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
      verdict: PASS / FAIL / SKIP under the any-fail-wins rule.
      failure_message: the ``<failure message="...">`` attribute (operator
        surface; NOT the long traceback body -- that lives in failure_body
        and is gated to ``--debug``).
      failure_body: the ``<failure>``/``<error>`` element text. Reserved
        for ``--debug``.
      skip_reasons: de-duplicated list after the ``Skipped: `` prefix-strip.
      case_count: total number of ``<testcase>`` elements that contributed.
      duration: sum of ``<testcase time="...">`` across this tool's cases.
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

    ``per_tool`` is keyed by extracted parametrize-id.
    ``total_time`` comes from ``<testsuite time="...">``.
    ``total_cases`` / ``total_failures`` / ``total_skipped`` / ``total_errors``
    come from ``<testsuite>`` attributes (operator surface for the summary line).
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
    """Parse a pytest JUnit XML file into a ``ParsedRun`` domain model.

    Stdlib ``xml.etree.ElementTree`` only -- no new runtime dependency.

    Aggregation (any-fail-wins):
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
        surfaces via ``_dispatch_default_mode_or_error`` in the cli.py wrapper).
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
            # test-code-scope fall-through: testcases under tests/test_code/
            # are hand-authored (no parametrize bracket). The legacy
            # tests/sdet/ path is also discovered during the v1.4 dual-  # noqa: sdet-rename-shim
            # discovery window; classnames from both prefixes share the
            # same synthetic bucket shape. Group by the classname's
            # trailing module name
            # with `test_` stripped; use the test function name (also
            # `test_` stripped) as the row label. Synthetic key shape
            # `<group>::<row_label>` keeps the parser->renderer dataclass
            # surface frozen (no new ToolVerdict fields).
            classname = tc.get("classname", "")
            if (
                classname.startswith("tests.test_code.test_")
                or classname.startswith("tests.sdet.test_")  # noqa: sdet-rename-shim
            ):
                group = classname.rsplit(".", 1)[-1].removeprefix("test_")
                row_label = name.removeprefix("test_")
                tool = f"{group}::{row_label}"
            else:
                continue  # legacy: testcases without [<tool>] suffix excluded.

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
            # Any failed/error -> FAIL (sticky).
            bucket.verdict = "FAIL"
            elem = failure if failure is not None else error
            # ToolCallError-attached JUnit properties (set by
            # tests/test_code/conftest.py:pytest_exception_interact) win over the
            # raw <failure message="..."> attr when present. The third
            # property `mcptf_error_raw` carries the
            # CallToolResult.model_dump_json(indent=2) string and is consumed
            # by the --debug appendix builder via a second XML pass
            # (_extract_tool_call_errors_from_xml). No new ToolVerdict fields
            # are added: the appendix re-parses the XML rather than threading
            # the dump string through the dataclass.
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
                    # "[code] message" when code present; else bare.
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
            # SKIP sticks only if nothing else ever set verdict.
            reason = _strip_pytest_skipped_prefix(skipped.get("message"))
            if reason and reason not in bucket.skip_reasons:
                bucket.skip_reasons.append(reason)
            # Demote to SKIP only when no FAIL set AND no PASS case seen.
            if bucket.verdict != "FAIL" and not _has_pass.get(tool, False):
                bucket.verdict = "SKIP"
            continue

        # No failure / error / skipped child -> PASS case.
        # PASS sets verdict unless FAIL already sticky.
        _has_pass[tool] = True
        if bucket.verdict != "FAIL":
            bucket.verdict = "PASS"

    return run


def _classname_from_nodeid(nodeid: str) -> str:
    """Derive a JUnit-style classname from a pytest report.nodeid.

    pytest's ``TestReport`` does not carry the JUnit ``classname`` directly,
    but the same information is encoded in ``report.nodeid``. Strip the
    ``::<test_func>[<param>]`` tail, drop the ``.py`` suffix, and replace
    path separators with ``.``.

    Example:
        ``tests/test_code/test_lifecycle.py::test_create`` ->
        ``tests.test_code.test_lifecycle``.

    Used by ``_build_parsed_run_from_reports`` to apply the scenario
    fall-through branch (live event-driven path) symmetrically with
    ``parse_junit_xml``'s reading of ``<testcase classname="...">``.
    """
    head = nodeid.split("::", 1)[0]  # file path part, before any ::
    if head.endswith(".py"):
        head = head[:-3]
    return head.replace("\\", "/").replace("/", ".")


# Live event-driven adapter colocated with parse_junit_xml. Produces an
# identical-shape ParsedRun from the accumulator the reporter plugin
# maintains in pytest_runtest_logreport.
def _build_parsed_run_from_reports(reports: list[pytest.TestReport]) -> ParsedRun:
    """Build a ParsedRun from accumulated TestReport objects (live event-driven path).

    Companion to ``parse_junit_xml``: same output dataclass, same renderer
    contract, different input source. Where the JUnit parser consumes one
    ``<testcase>`` element per test, this adapter consumes pytest's
    ``TestReport`` events (three phases per test: ``setup``, ``call``,
    ``teardown``) and buckets them by ``report.nodeid`` BEFORE aggregating
    (Pitfall 1: a naive per-event loop counts each test 3x or overwrites
    a call-phase FAIL with a later teardown-phase PASS).

    Aggregation (any-fail-wins; mirror of parse_junit_xml docstring rules):
      1. Any phase report with ``failed=True`` -> verdict = FAIL (sticky).
         ``failure_message`` is sourced from ``user_properties`` keys
         ``mcptf_error_code`` + ``mcptf_error_message`` when present
         (formatted as ``"[code] message"`` to byte-match parse_junit_xml
         line 605), else from the first line of the failing report's
         ``longrepr``. ``failure_body`` carries the full ``longrepr`` text.
      2. Else any phase report with ``skipped=True`` (setup or call) ->
         verdict = SKIP if no PASS/FAIL already set; ``skip_reasons``
         records the deduplicated, prefix-stripped reason (the
         ``pytest.skip(reason=...)`` longrepr is a 3-tuple
         ``(file, lineno, "Skipped: reason")``; the ``Skipped: `` prefix
         is stripped via ``_strip_pytest_skipped_prefix``).
      3. Else all phases passed -> verdict = PASS (unless FAIL already
         sticky).

    Order-independence: a tool's verdict is the same regardless of the
    order in which reports arrive -- FAIL is sticky; PASS dominates SKIP
    (matching parse_junit_xml's ``_has_pass`` book-keeping).

    Scenario fall-through: nodeids without a ``[<tool>]`` parametrize
    suffix produce a synthetic bucket key ``"<group>::<row_label>"`` when
    the classname (derived from the nodeid file path) starts with
    ``tests.test_code.test_`` OR ``tests.sdet.test_`` (legacy dual-
    discovery window). Mirrors parse_junit_xml lines 540-563 verbatim so
    the renderer sees identical bucket shapes across both input paths.
    (noqa: sdet-rename-shim covers the legacy classname-prefix mention.)

    Pitfall 4 (ToolCallError on user_properties): scenario tests
    set ``mcptf_error_code`` / ``mcptf_error_message`` /
    ``mcptf_error_raw`` via ``record_property`` (from
    ``tests/test_code/conftest.py:pytest_exception_interact``). The JUnit
    path reads these from ``<property>`` children; the live path reads
    them from ``report.user_properties`` (a list of ``(name, value)``
    tuples). The ``failure_message`` text MUST be byte-identical across
    both adapters so renderer tests remain valid.

    Args:
        reports: All ``TestReport`` events accumulated during a pytest
            session (every test contributes one report per phase).

    Returns:
        ``ParsedRun`` -- field-equal to ``parse_junit_xml`` output for
        the same logical run (verified by paired-fixture parity test in
        ``tests/framework/unit/test_runner_reports_adapter.py``).
    """
    # Bucket by nodeid first (Pitfall 1). One bucket == one test, regardless
    # of how many phase events were emitted for it.
    by_nodeid: dict[str, dict[str, pytest.TestReport]] = {}
    for r in reports:
        by_nodeid.setdefault(r.nodeid, {})[r.when] = r

    run = ParsedRun()

    # Transient per-tool "any case passed?" tracker -- matches parse_junit_xml's
    # _has_pass book-keeping so SKIP cannot demote PASS within the same tool.
    _has_pass: dict[str, bool] = {}

    for nodeid, phases in by_nodeid.items():
        tool = _extract_tool_name(nodeid)
        if tool is None:
            # Scenario fall-through: mirror parse_junit_xml:540-563 verbatim.
            # tests/test_code/ are hand-authored (no parametrize bracket);
            # tests/sdet/ is the v1.4 dual-discovery legacy path. Both share  # noqa: sdet-rename-shim
            # the same synthetic bucket shape so the renderer's per-tool
            # block stays input-agnostic.
            classname = _classname_from_nodeid(nodeid)
            if (
                classname.startswith("tests.test_code.test_")
                or classname.startswith("tests.sdet.test_")  # noqa: sdet-rename-shim
            ):
                group = classname.rsplit(".", 1)[-1].removeprefix("test_")
                func = nodeid.rsplit("::", 1)[-1]
                if "[" in func:
                    func = func[: func.index("[")]
                row_label = func.removeprefix("test_")
                tool = f"{group}::{row_label}"
            else:
                continue  # legacy: nodeids without [<tool>] suffix excluded.

        bucket = run.per_tool.setdefault(
            tool, ToolVerdict(name=tool, verdict="PASS")
        )
        bucket.case_count += 1
        # Sum durations across all phase events for this nodeid (matches
        # JUnit <testcase time="..."> which is the consolidated test time).
        bucket.duration += sum(
            float(getattr(r, "duration", 0.0) or 0.0) for r in phases.values()
        )

        setup = phases.get("setup")
        call = phases.get("call")
        teardown = phases.get("teardown")

        # Any-fail-wins (Pattern 3 precedence). Call dominates the failing
        # report selection when present; setup/teardown promote to FAIL too.
        any_failed = next(
            (r for r in (call, setup, teardown) if r is not None and r.failed),
            None,
        )
        if any_failed is not None:
            bucket.verdict = "FAIL"
            # Read mcptf_error_code / mcptf_error_message from user_properties
            # (Pitfall 4). The formatting -- "[code] message" when code
            # present, else bare message -- is byte-identical to
            # parse_junit_xml line 605 so renderer tests remain valid.
            code: str | None = None
            msg_field: str | None = None
            for name, value in (any_failed.user_properties or []):
                if name == "mcptf_error_code":
                    if isinstance(value, str):
                        code = value or None
                    elif value is None:
                        code = None
                    else:
                        code = str(value)
                elif name == "mcptf_error_message":
                    msg_field = value if isinstance(value, str) else str(value)
            prop_msg: str | None = None
            if msg_field is not None:
                prop_msg = f"[{code}] {msg_field}" if code else msg_field

            # longrepr fallback for failure_message (operator surface: first
            # line only, matching the parse_junit_xml <failure message="...">
            # single-line attribute shape).
            lr = getattr(any_failed, "longrepr", None)
            longrepr_msg: str | None = None
            if lr is not None:
                lr_text = str(lr)
                if lr_text.strip():
                    longrepr_msg = lr_text.splitlines()[0]

            if prop_msg is not None and bucket.failure_message is None:
                bucket.failure_message = prop_msg
            elif longrepr_msg and bucket.failure_message is None:
                bucket.failure_message = longrepr_msg

            # failure_body: full longrepr text (gated to --debug by renderer).
            if lr is not None and bucket.failure_body is None:
                body = str(lr).strip()
                if body:
                    bucket.failure_body = body
            continue

        # Skip handling: setup-skip or call-skip (mirror parse_junit_xml:617-625).
        skip_report = next(
            (r for r in (setup, call) if r is not None and r.skipped),
            None,
        )
        if skip_report is not None:
            lr = getattr(skip_report, "longrepr", None)
            reason: str | None = None
            if isinstance(lr, tuple) and len(lr) >= 3:
                # pytest.skip(reason=...) longrepr is (file, lineno, "Skipped: reason")
                reason = _strip_pytest_skipped_prefix(str(lr[2]))
            elif lr is not None:
                reason = _strip_pytest_skipped_prefix(str(lr))
            if reason and reason not in bucket.skip_reasons:
                bucket.skip_reasons.append(reason)
            # Demote to SKIP only when no FAIL set AND no PASS case seen
            # (matches parse_junit_xml:623 _has_pass guard).
            if bucket.verdict != "FAIL" and not _has_pass.get(tool, False):
                bucket.verdict = "SKIP"
            continue

        # All phases passed (or only teardown ran and it passed) -> PASS.
        _has_pass[tool] = True
        if bucket.verdict != "FAIL":
            bucket.verdict = "PASS"

    # Aggregate totals from the bucketed verdicts. Differs semantically from
    # parse_junit_xml which reads <testsuite> attributes: here we compute
    # from the per-tool dict so the numbers always match what the renderer
    # will display. total_errors is 0 on this path (TestReport-driven
    # aggregation does not distinguish error from failure at the phase
    # level; parse_junit_xml's distinction comes from JUnit's separate
    # <error> vs <failure> XML children).
    run.total_cases = sum(v.case_count for v in run.per_tool.values())
    run.total_failures = sum(1 for v in run.per_tool.values() if v.verdict == "FAIL")
    run.total_skipped = sum(1 for v in run.per_tool.values() if v.verdict == "SKIP")
    run.total_time = sum(v.duration for v in run.per_tool.values())
    run.total_errors = 0
    return run


# ===========================================================================
# Domain UI renderer
# ===========================================================================
#
# Consumes ParsedRun plus a RenderContext (non-XML metadata from cli.py:run)
# and emits the operator-facing header / per-tool rows / summary line.
#
# Architectural note: the state-(a)/(c) skip composer is a PURE FUNCTION
# (_compose_unparametrized_skips_from_config) that takes discovered_tools as
# an argument rather than reading a module global off the deleted plugin.
# The wrapper runs outside the pytest process and cannot reach the in-pytest
# cache; it performs its own discovery call before launching the subprocess.
#
# Em-dash U+2014 ("—") appears verbatim in this source file -- the locked
# separator is re-pinned by tests/test_runner_renderer.py.
# ===========================================================================


@dataclass
class RenderContext:
    """Non-XML data the renderer needs.

    Header inputs come from the resolved Config (server cmd, judges) and a
    wrapper-side discovery call (discovered tool list). ``total_planned_cases``
    is the count of ``<testcase>`` elements we EXPECT (typically
    discovered-and-allowed tools * cases per tool); today this equals
    ``parsed.total_cases`` for the header's "Test plan: N contract cases"
    line, since pytest's collected count IS the plan.
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
    """State-(a)/(c) SKIP rows the wrapper composes outside the pytest process.

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

    Architectural note: this function is PURE -- discovered_tools is an
    argument, not a module global. The wrapper rediscovers tools before
    launching pytest (cli.py:_discover_tools_for_run) because the in-pytest
    cache lives in another process.
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
    """Pre-run skip-reason map for ``--explain``.

    Pre-run wrapper that exposes ONLY state-(a) unlisted + state-(c) explicit
    skips. State-(b) tools (listed AND skip=False) are running pre-run and
    must NOT appear in the skip-explain output. The post-run composer's
    defensive ``skip=False -> _REASON_NOT_SELECTED`` fallback is correct for
    post-run (a state-b tool that produced no testcase is anomalous) but
    incorrect pre-run (state-b is the running set).

    Returns: ``{tool_name: reason_string}`` for state-(a)/(c) skips only.
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
    """Build the digest's ``Judges:`` union, honoring ToolConfig.judges semantics.

    ToolConfig.judges semantics (locked at models.py + contract gates at
    tests/contract/test_mcp_tool_contract.py):
      - None  (default, unset)      -> run ALL rubrics in RUBRIC_IDS
      - []    (explicit empty list) -> explicit opt-out, run no rubrics on this tool
      - [...] (subset list)         -> run literally these rubrics

    The pre-run digest must reflect what will actually execute. An earlier
    union loop used ``getattr(tool_cfg, "judges", []) or []``, which silently
    collapsed the None default to ``[]`` and produced an empty union even
    when every tool was running all three rubrics at runtime.

    Returns: sorted list of rubric IDs that will fire for at least one
    configured tool. Empty list iff every tool explicitly opts out via [].
    """
    judges_set: set[str] = set()
    for tool_cfg in tools_config.values():
        declared = getattr(tool_cfg, "judges", None)
        if declared is None:
            judges_set.update(RUBRIC_IDS)  # None default = run all rubrics
        else:
            judges_set.update(declared)    # [] is a no-op; subset passes through
    return sorted(judges_set)


# ---------------------------------------------------------------------------
# ANSI guard helpers (codes only when stdout is a TTY)
# ---------------------------------------------------------------------------


def _ansi_enabled(file) -> bool:
    """ANSI codes only when ``file`` is a TTY. Piped output stays plain."""
    return hasattr(file, "isatty") and file.isatty()


def _green(s: str, file) -> str:
    return f"\x1b[32m{s}\x1b[0m" if _ansi_enabled(file) else s


def _red(s: str, file) -> str:
    return f"\x1b[31m{s}\x1b[0m" if _ansi_enabled(file) else s


def _dim(s: str, file) -> str:
    return f"\x1b[2m{s}\x1b[0m" if _ansi_enabled(file) else s


# ---------------------------------------------------------------------------
# Header (verbatim shape for the v1.2 mockup)
# ---------------------------------------------------------------------------


def _render_header(ctx: RenderContext, parsed: ParsedRun, file=None) -> None:
    """Verbatim shape for the v1.2 mockup.

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

    ``file=None`` defaults to ``sys.stdout`` resolved at call-time so pytest
    ``capsys`` capture works (capsys replaces sys.stdout per-test; a
    ``file=sys.stdout`` default would capture the pre-test stdout at function
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
# Pre-run digest -- emitted BEFORE pytest runs.
# ---------------------------------------------------------------------------


def _render_pre_run_digest(
    ctx: RenderContext,
    with_framework: bool = False,
    explain: bool = False,
    file=None,
) -> None:
    """Pre-run digest emitted before pytest runs.

    Lines (exact order, <= 10 total in default mode; up to 11 with with_framework=True):
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

    ``file=None`` -> ``sys.stdout`` at call-time (capsys-friendly; see
    ``_render_header`` docstring for the rationale).

    Two buckets only -- Running and Skipping. The state-(a) / state-(c)
    distinction is visible in ``--explain`` output, not here. Digest height
    remains <= 10 lines regardless of N (the Skipping list is NEVER
    inline-expanded here -- ``--explain`` is the expansion surface).

    Running list is derived from ``ctx.discovered_tools`` filtered by
    ``ctx.tools_config`` (state-b: listed AND not skip:true). This matches
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
    # Omit "(use --explain to list)" hint when explain=True (the explain block
    # renders right below, so the hint would lie).
    if explain:
        print(f"Skipping:    {skipping_n:>2}", file=file)
    else:
        print(f"Skipping:    {skipping_n:>2}  (use --explain to list)", file=file)
    print(f"Judges:      {judges_text}", file=file)
    print(f"Test plan:   {planned_cases} contract cases", file=file)
    # --with-framework suffix emits IMMEDIATELY after Test plan line, BEFORE
    # the trailing blank, as a continuation line. 13-space indent matches
    # the label column width so "+ framework self-tests" visually hangs
    # under the contract-cases value.
    if with_framework:
        print("             + framework self-tests", file=file)
    print("", file=file)  # blank line before next section


def _render_scenario_pre_run_digest(
    ctx: RenderContext,
    scenarios: list[str],
    skipped_scenarios: dict[str, str],
    with_framework: bool = False,
    explain: bool = False,
    file=None,
) -> None:
    """Scenario-aware variant of ``_render_pre_run_digest``.

    Buckets are scenario MODULE stems (``tests/test_code/test_proxmox_vm_lifecycle.py``
    -> ``'proxmox_vm_lifecycle'``). Same line-budget as
    ``_render_pre_run_digest`` (<= 10 lines). The em-dash separator U+2014
    is the locked rendering character; do not substitute an ASCII hyphen.

    The em-dash literal U+2014 appears in:
      1. judges_text = "(none — test-code scope)"   -- signals no Ollama grading
      2. The --explain expansion line               -- matches the locked separator

    Args:
        ctx: shared RenderContext (server_cmd field consumed).
        scenarios: list of scenario module stems to run (alphabetized on emit).
        skipped_scenarios: dict[stem, reason] for scenarios pytest collected
            but skipped (pytest.mark.skip / parametrize skip / preflight skip).
        with_framework: if True, append the framework-self-tests breadcrumb.
        explain: if True, expand the Skipping line into one-per-stem rows
            with em-dash + reason; else show the (use --explain to list) hint.
        file: stream to write to; defaults to sys.stdout (matches sibling).
    """
    if file is None:
        file = sys.stdout
    running = sorted(scenarios)
    running_n = len(running)
    skipping_n = len(skipped_scenarios)
    judges_text = "(none — test-code scope)"   # em-dash U+2014
    running_text = ", ".join(running) if running else "(none)"

    print("=" * 40, file=file)
    print("MCP Test Framework (test-code)", file=file)
    print("=" * 40, file=file)
    print(f"MCP server:  {ctx.server_cmd}", file=file)
    print(f"Discovered:  {running_n + skipping_n} scenarios", file=file)
    print(f"Running:     {running_n:>2}  ({running_text})", file=file)
    if explain:
        print(f"Skipping:    {skipping_n:>2}", file=file)
        for stem in sorted(skipped_scenarios):
            print(f"  {stem}  — {skipped_scenarios[stem]}", file=file)   # em-dash U+2014
    else:
        print(f"Skipping:    {skipping_n:>2}  (use --explain to list)", file=file)
    print(f"Judges:      {judges_text}", file=file)
    if with_framework:
        print("             + framework self-tests", file=file)
    print("", file=file)


def _collect_test_code_scenarios(
    ctx: "RenderContext",
) -> tuple[list[str], dict[str, str]]:
    """Enumerate scenario module stems under ``tests/test_code/``
    (and the legacy ``tests/sdet/`` path as a v1.4 fallback).  # noqa: sdet-rename-shim

    The discovery side ships scenario stems; preflight-skip detection (for
    scenarios skipped by env-reachability probes) is a future extension.
    For now the skipped dict is always empty.

    The ``ctx`` parameter is currently unused but kept on the signature so
    a future revision can read RenderContext-carried scenario-skip state
    without a breaking API change.

    Returns:
        (scenario_stems: list[str] sorted alphabetically, skipped: dict[str, str])
    """  # noqa: sdet-rename-shim
    stems: list[str] = []
    for dir_path in (Path("tests/test_code"), Path("tests/sdet")):  # noqa: sdet-rename-shim
        if not dir_path.is_dir():
            continue
        for p in dir_path.glob("test_*.py"):
            stems.append(p.stem.removeprefix("test_"))
    # De-duplicate (legacy and primary may both exist transiently).
    return (sorted(set(stems)), {})


def _render_skipped_tools_explain(ctx: RenderContext, file=None) -> None:
    """``--explain`` expansion of the digest's Skipping hint.

    Lines (alphabetical order):
      Skipping (N):
        <tool>  — <reason>      [N times, sorted alphabetically]
      (blank line)

    Reasons sourced from ``_compose_pre_run_skip_reasons`` (the pure composer
    called with ``ran_tools=set()`` since pytest hasn't run yet).

    Format invariants (grep-able at N=70):
      - One tool per line, no wrapping.
      - U+2014 em-dash separator (matches the locked separator in
        ``_render_per_tool_rows``).
      - Tool name left-justified to width(longest skipped tool name) for visual scan.
      - Output footprint <= N+2 lines (header + N tool lines + 1 trailing blank).

    ``file=None`` -> ``sys.stdout`` at call-time (capsys-friendly).
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
# Per-tool rows (ordering: FAIL -> SKIP -> PASS; em-dash separator)
# ---------------------------------------------------------------------------


def _render_per_tool_rows(
    parsed: ParsedRun,
    unparam_skips: dict[str, str],
    file=None,
) -> None:
    """Render per-tool rows.

    Ordering: FAIL -> SKIP -> PASS, alphabetical within each. The FAIL row
    appends ``failure_message`` after the em-dash separator.

    Scenario keys carry ``'::'`` (e.g. ``'group::row_label'``) and render as
    a bare group header followed by indented per-test rows; these keys are
    excluded from the contract ``name_width`` ljust.

    Em-dash separator = U+2014 (literal '—'), not ASCII hyphen.

    ``file=None`` -> ``sys.stdout`` at call time (capsys-friendly).
    """
    if file is None:
        file = sys.stdout

    # Split per_tool into contract entries (no '::') and scenario entries.
    contract_per_tool = {k: v for k, v in parsed.per_tool.items() if "::" not in k}
    scenario_entries: dict[str, list[tuple[str, ToolVerdict]]] = {}
    for k, v in parsed.per_tool.items():
        if "::" not in k:
            continue
        group, _, row_label = k.partition("::")
        scenario_entries.setdefault(group, []).append((row_label, v))

    # -- Contract block (BYTE-IDENTICAL when no scenarios are present) --
    fails = sorted(t for t, v in contract_per_tool.items() if v.verdict == "FAIL")
    skips_xml = {t for t, v in contract_per_tool.items() if v.verdict == "SKIP"}
    passes = sorted(t for t, v in contract_per_tool.items() if v.verdict == "PASS")

    # Union XML-derived SKIPs with state-(a)/(c) composer entries.
    all_skips = sorted(skips_xml | set(unparam_skips.keys()))

    all_names = list(contract_per_tool.keys()) + list(unparam_skips.keys())
    name_width = max((len(n) for n in all_names), default=0)

    if fails:
        print("failures:", file=file)
        for tool in fails:
            v = contract_per_tool[tool]
            tag = _red("FAIL", file)
            if v.failure_message:
                # U+2014 em-dash; locked separator.
                print(f"  {tool.ljust(name_width)}  ✗ {tag} — {v.failure_message}", file=file)
            else:
                print(f"  {tool.ljust(name_width)}  ✗ {tag}", file=file)

    if all_skips:
        print("skipped:", file=file)
        for tool in all_skips:
            if tool in contract_per_tool and contract_per_tool[tool].verdict == "SKIP":
                reasons_text = _format_skip_reasons(contract_per_tool[tool].skip_reasons)
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

    # -- Scenario blocks --
    # Bare group header, indented per-test rows (glyph + row_label;
    # NO tag word). FAIL rows append em-dash + failure_message; SKIP
    # rows append em-dash + reasons. Groups and rows sorted alphabetically.
    for group in sorted(scenario_entries):
        print(group, file=file)
        for row_label, v in sorted(scenario_entries[group], key=lambda pair: pair[0]):
            if v.verdict == "PASS":
                print(f"  ✓ {row_label}", file=file)
            elif v.verdict == "FAIL":
                if v.failure_message:
                    # U+2014 em-dash; locked separator.
                    print(f"  ✗ {row_label} — {v.failure_message}", file=file)
                else:
                    print(f"  ✗ {row_label}", file=file)
            else:  # SKIP
                reasons_text = _format_skip_reasons(v.skip_reasons)
                if reasons_text:
                    print(f"  – {row_label} — {reasons_text}", file=file)
                else:
                    print(f"  – {row_label}", file=file)


# ---------------------------------------------------------------------------
# Summary line
# ---------------------------------------------------------------------------


def _render_summary_line(
    parsed: ParsedRun,
    unparam_skips: dict[str, str],
    file=None,
) -> None:
    """Render the summary line: ``Result: N PASS / M FAIL  in T.Ts``.

    Skip count includes state-(a)/(c) composer entries so the summary line
    agrees with the per-tool rows (discovered / running / skipping counts
    agree with what the runner actually executes).

    ``file=None`` -> ``sys.stdout`` at call time (capsys-friendly).
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
    """Top-level renderer (batch render, stdlib + ANSI guard).

    Order: per-tool rows -> summary line. (The header was moved pre-run to
    ``_render_pre_run_digest``.) State-(a)/(c) SKIP rows merge with
    XML-derived SKIPs via ``_compose_unparametrized_skips_from_config``.

    ``file=None`` -> ``sys.stdout`` at call time (capsys-friendly).
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
# Verbosity ladder helpers
# ===========================================================================
#
# Two orthogonal renderers extending render_domain_ui:
#   - render_summary_only: `-q` -- prints only the summary line.
#   - render_debug_appendix: `--debug` -- printed AFTER whatever the
#     default/quiet rung produced. Default UI shape unchanged regardless
#     of --debug (invariant: each rung adds info; none re-shapes the layer
#     below).
#
# `--explain` is owned by the cli wrapper, not this module.
# ===========================================================================


def render_summary_only(
    parsed: ParsedRun,
    ctx: RenderContext,
    file=None,
) -> None:
    """``-q`` / ``--quiet`` -- summary line only.

    No header, no per-tool rows. Same summary content as the last line of
    ``render_domain_ui``, including state-(a)/(c) SKIP count contribution
    so the quiet-mode summary agrees with the default-mode summary.

    ``file=None`` -> ``sys.stdout`` at call time (capsys-friendly), matching
    the other renderers in this module.
    """
    if file is None:
        file = sys.stdout
    ran_tools = set(parsed.per_tool.keys())
    unparam_skips = _compose_unparametrized_skips_from_config(
        ctx.discovered_tools, ctx.tools_config, ran_tools
    )
    _render_summary_line(parsed, unparam_skips, file=file)


@dataclass(frozen=True)
class _ToolCallErrorRecord:
    """``--debug`` appendix record. tool/code/message/raw are all reconstructed
    from JUnit user_properties (set by
    ``tests/test_code/conftest.py:pytest_exception_interact``).

    ``raw`` carries the ``CallToolResult.model_dump_json(indent=2)`` string
    that ``pytest_exception_interact`` emits as the ``mcptf_error_raw``
    property. Empty string when the test did not raise ``ToolCallError``, OR
    when ``exc.raw`` was None.
    """

    tool: str
    code: str | None
    message: str
    raw: str  # the mcptf_error_raw user_property value; "" when absent / None


def _extract_tool_call_errors_from_xml(xml_path: Path) -> list[_ToolCallErrorRecord]:
    """Scan a JUnit XML file for ``ToolCallError``-attached testcases.

    Testcases with ``mcptf_error_message`` user_property are picked up; code
    and raw are optional. Returns one record per such testcase. Returns
    ``[]`` when none are present (invariant: ``--debug`` appendix unchanged
    when no ``ToolCallError`` failures occurred).

    Reads ALL THREE user_properties emitted by
    ``pytest_exception_interact``:
      - mcptf_error_code    -> .code  (None if missing or value="")
      - mcptf_error_message -> .message (required -- testcase skipped if absent)
      - mcptf_error_raw     -> .raw  (""  if missing or exc.raw was None;
                                       otherwise the CallToolResult JSON dump)

    The XML is re-parsed here (rather than threading dump strings through
    ToolVerdict) so the dataclass surface stays unchanged. O(N) extra pass
    is negligible at MVP scale.
    """
    if not xml_path.is_file():
        return []
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError:
        return []
    out: list[_ToolCallErrorRecord] = []
    root = tree.getroot()
    for tc in root.iter("testcase"):
        props = tc.find("properties")
        if props is None:
            continue
        code: str | None = None
        message: str | None = None
        raw_dump: str = ""
        for prop in props.iter("property"):
            n = prop.get("name", "")
            v = prop.get("value", "")
            if n == "mcptf_error_code":
                code = v or None
            elif n == "mcptf_error_message":
                message = v
            elif n == "mcptf_error_raw":
                # Full CallToolResult.model_dump_json(indent=2) string.
                # Empty value means exc.raw was None -- render as "(none)".
                raw_dump = v
        if message is None:
            continue
        tool_name = tc.get("name", "(unknown)")
        out.append(_ToolCallErrorRecord(
            tool=tool_name, code=code, message=message, raw=raw_dump,
        ))
    return out


def render_debug_appendix(
    captured_stdout: str,
    captured_stderr: str,
    parsed: ParsedRun,
    file=None,
    xml_path: Path | None = None,
) -> None:
    """``--debug`` -- appended AFTER the domain UI.

    Order (only printed if non-empty):
      --- raw pytest output ---
      {captured_stdout verbatim}
      --- captured stderr ---
      {captured_stderr verbatim}     (only if non-empty)
      --- failure tracebacks ---     (only if any tool has failure_body)
      {tool_name}:
        {failure_body indented by 2 spaces}

    Default UI must be UNCHANGED whether ``--debug`` is passed or not
    (invariant: each rung adds info; none re-shapes the layer below).

    The ``--- raw pytest output ---`` separator string is grep-able
    regression-pin material; do not reword.

    When ``xml_path`` is provided AND the JUnit XML carries
    ``ToolCallError``-attached testcases (``mcptf_error_*`` user_properties
    set by ``tests/test_code/conftest.py:pytest_exception_interact``), a
    ``--- ToolCallError dump ---`` block is emitted BEFORE
    ``--- raw pytest output ---`` for each such testcase. When ``xml_path``
    is None or the XML lacks those properties, the appendix is byte-identical
    to the legacy baseline (invariant: each rung adds info; none re-shapes
    the layer below).
    """
    if file is None:
        file = sys.stdout

    # ToolCallError dump block emits BEFORE raw pytest output so operators
    # get a parseable summary they can grep first. The `raw:` section carries
    # the full CallToolResult.model_dump_json(indent=2) string emitted by
    # pytest_exception_interact as the mcptf_error_raw property. When
    # xml_path is absent (legacy callers) or no ToolCallError-attached
    # testcases are present, this block emits zero bytes -- appendix-shape
    # invariant preserved.
    if xml_path is not None:
        tool_call_errors = _extract_tool_call_errors_from_xml(xml_path)
        for err in tool_call_errors:
            print("--- ToolCallError dump ---", file=file)
            print(f"tool: {err.tool}", file=file)
            print(f"code: {err.code or '(none)'}", file=file)
            print(f"message: {err.message}", file=file)
            if err.raw:
                # Render the indented JSON dump. Each line of the dump (which
                # already comes back from model_dump_json(indent=2) with its
                # own 2-space internal indent) gets an ADDITIONAL 2-space
                # prefix so the appendix layout matches the contract.
                print("raw:", file=file)
                for line in err.raw.splitlines():
                    print(f"  {line}", file=file)
            else:
                # exc.raw was None OR mcptf_error_raw property absent --
                # explicit sentinel: "raw: (none)". No fallback workaround
                # because the dump is supposed to traverse the JUnit cycle.
                print("raw: (none)", file=file)
            print("---", file=file)
            print("", file=file)

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
# In-pytest discovery cache (used by tests/conftest.py during parametrize)
# ===========================================================================
#
# This cache lives in `_runner` (a real importable module under src/) rather
# than `tests/conftest.py` because `tests/` is NOT a Python package (no
# `tests/__init__.py`). Surviving allowlist unit tests need to patch this
# cache via a real import path:
#
#     from mcp_test_framework import _runner as _r
#     _r._DISCOVERED_TOOL_NAMES = ["alpha", "beta"]
#
# This cache is SEPARATE from the wrapper-side discovery in
# `cli.py:_discover_tools_for_run`. The TWO-cache architecture is intentional
# (each discovery costs <1s); consolidation is a future-work candidate. The
# wrapper cache lives only on the RenderContext; this cache lives at module
# scope because `pytest_generate_tests` in conftest needs to read it across
# multiple parametrize calls within a single pytest session.
# ===========================================================================

_DISCOVERED_TOOL_NAMES: "list[str] | None" = None


def _set_discovered_tool_names(names: list[str]) -> None:
    """Helper for ``tests/conftest.py:_resolve_tool_names`` to populate the
    in-pytest discovery cache without using a ``global`` declaration at the
    call site. Tests can patch the cache directly via
    ``_runner._DISCOVERED_TOOL_NAMES = [...]``."""
    global _DISCOVERED_TOOL_NAMES
    _DISCOVERED_TOOL_NAMES = list(names)
