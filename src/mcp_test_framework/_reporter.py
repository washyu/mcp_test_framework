"""mcp_test_framework live domain-UI reporter — second pytest11 plugin.

Registered via [project.entry-points.pytest11] in pyproject.toml as
``mcp_test_framework_reporter = "mcp_test_framework._reporter"``. Loaded
alongside the contract plugin (``mcp_test_framework = "..._plugin"``); the
two plugins are independently disable-able via ``pytest -p no:KEY``.

Behavior:
  - Default OFF. Operator opts in with ``--mcp-domain-ui``
    (bare = auto = on iff stdout is a TTY) or ``--mcp-domain-ui=force``
    (on regardless of TTY) or ``--mcp-domain-ui=off`` (explicit off).
  - xdist controller-only emission. Worker processes early-return; the
    controller's ``pytest_runtest_logreport`` receives every worker test's
    TestReport via xdist's standard forwarding.
  - Additive coexistence with pytest-native output. NO terminal
    summary hook, NO stdout hijack. Renders header at
    ``pytest_collection_finish``, accumulates TestReports in
    ``pytest_runtest_logreport``, batch-renders per-tool rows + summary
    at ``pytest_sessionfinish``.

This plugin is intentionally framework-primitive: NO SUT-aware logic, NO
imports of any specific MCP server under test. It only consumes pytest's
TestReport stream and the Config the contract plugin stashed on
``config._mcp_contracts_config``.

TTY detection uses ``sys.__stdout__`` (cached at module load) rather than
``sys.stdout`` at call time -- pytest's capturemanager and plugins like
pytest-sugar / pytest-html wrap ``sys.stdout`` with non-TTY proxies, but
``sys.__stdout__`` remains the un-wrapped CPython original (docs:
"used during finalization, and could be useful to print to the actual
standard stream no matter if the sys.std* object has been redirected").

xdist worker detection uses the duck-typed ``hasattr(config,
"workerinput")`` probe rather than importing xdist; the plugin works
identically whether or not pytest-xdist is installed.
"""
from __future__ import annotations

import sys
import warnings
from dataclasses import dataclass, field

import pytest

from mcp_test_framework import _runner


# Pitfall: always probe the UN-wrapped original stream. pytest's
# capturemanager replaces sys.stdout but never touches sys.__stdout__.
# Evaluating isatty() against sys.stdout would return False inside a
# captured pytest run even on a real terminal.
#
# WR-02: on pythonw (Windows GUI launcher) and frozen-binary contexts
# (pyinstaller/--noconsole), CPython sets sys.__stdout__ to None because
# there is no underlying stdio fd. Fall back to sys.stdout so the cached
# reference is always writable. The fallback stream may be a non-TTY
# wrapper (which is fine: `isatty` returns False and auto-mode resolves
# to "off" -- the desired behavior in those contexts).
_ORIGINAL_STDOUT = sys.__stdout__ or sys.stdout


@dataclass
class _ReporterState:
    """Accumulator for the live TestReport stream.

    Single-instance-per-process invariant -- one pytest session per
    process, master-only (workers early-return in pytest_configure).
    """

    enabled: bool = False
    reports: list[pytest.TestReport] = field(default_factory=list)
    ctx: "_runner.RenderContext | None" = None


# pytest_runtest_logreport(report) provides no config backref. Stash the
# active state at module level so the hook can find it. One pytest session
# per process; workers early-return and never create state; no concurrency.
_STATE: "_ReporterState | None" = None


def pytest_addoption(parser: pytest.Parser) -> None:
    """Declare the ``--mcp-domain-ui`` option.

    Responsibilities:
      - Reuses the ``mcp_test_framework`` option group declared by the
        contract plugin (no second group).
      - Surfaces three states via ``nargs='?'`` + ``const='auto'``:
        flag absent -> 'off'; bare flag -> 'auto'; '=force' -> 'force';
        '=off' -> 'off'.

    When the reporter is disabled via
    ``pytest -p no:mcp_test_framework_reporter``, this hook never runs and
    the option becomes unrecognized -- exactly the surface the entry-point-
    keyed disable promise requires.
    """
    group = parser.getgroup("mcp_test_framework", "MCP test framework options")
    group.addoption(
        "--mcp-domain-ui",
        action="store",
        nargs="?",
        const="auto",
        default="off",
        choices=["auto", "force", "off"],
        help=(
            "Render the MCP domain UI (header / per-tool rows / summary) "
            "alongside pytest's native output. Bare flag = 'auto' (on iff "
            "stdout is a TTY). '=force' = on regardless of TTY. '=off' = "
            "off (the default when the flag is absent)."
        ),
    )


def pytest_configure(config: pytest.Config) -> None:
    """Resolve mode and initialize the accumulator.

    Responsibilities:
      - xdist worker no-op: early-return when running under xdist worker
        (``hasattr(config, "workerinput")``).
      - Read --mcp-domain-ui choice; if 'off' -> silent no-op.
      - If 'auto' and ``_ORIGINAL_STDOUT.isatty()`` is False -> silent no-op.
      - Initialize ``_ReporterState(enabled=True)`` and stash on module-level
        ``_STATE``.
    """
    global _STATE
    if hasattr(config, "workerinput"):
        return  # xdist worker -- controller forwards events.
    try:
        choice = config.getoption("--mcp-domain-ui", default="off")
    except (ValueError, AttributeError):
        # Option not registered (defensive only; pytest_addoption above
        # registers it for every plugin-loaded run).
        return
    if choice == "off":
        return
    if choice == "auto" and not bool(getattr(_ORIGINAL_STDOUT, "isatty", lambda: False)()):
        return
    # WR-04: defensive re-init guard. The module-global _STATE assumes one
    # pytest session per process and is torn down in pytest_unconfigure.
    # That assumption holds for the operator's normal `pytest` / `mcp-
    # contracts run` invocations (each spawns a fresh interpreter) but
    # breaks for in-process re-entry: IDE test runners (PyCharm, VS Code)
    # that keep the interpreter warm across runs, or library callers
    # invoking pytest.main() twice. If _STATE is still populated when we
    # arrive here, the previous session's reports list would otherwise
    # silently merge into this session's accumulator.
    if _STATE is not None:
        warnings.warn(
            "mcp_test_framework reporter: _STATE was populated at "
            "pytest_configure -- previous pytest_unconfigure did not fire "
            "(in-process re-entry or library-mode pytest.main re-use). "
            "Resetting accumulator; reports from the prior session are "
            "discarded.",
            RuntimeWarning,
            stacklevel=2,
        )
    _STATE = _ReporterState(enabled=True)


def pytest_collection_finish(session: pytest.Session) -> None:
    """Emit the pre-run domain header.

    Responsibilities:
      - Worker no-op: even with master-gating in ``pytest_configure``,
        xdist re-invokes collection on workers. Re-check ``workerinput``
        here.
      - State-presence gate: if ``_STATE`` is None (off/auto-off path)
        -> no-op.
      - Config-presence gate: if the contract plugin's
        ``_mcp_contracts_config`` stash is missing (operator disabled the
        contract plugin or didn't set ``mcp_config_file`` ini), skip the
        header gracefully -- per-tool rows + summary still render at
        sessionfinish.
      - Scope gate (CR-02): if no collected items carry the
        ``mcp_contract`` keyword, the session is running under a non-
        contract scope (test-code / scenario, ``--with-framework``-only,
        operator's own pytest invocation against arbitrary tests). The
        contract-shaped pre-run digest banner does not describe that
        scope and the CLI already emits the test-code banner under
        ``mcp-contracts run --test-code``. Short-circuit before the
        header render -- per-tool rows + summary still emit at
        ``pytest_sessionfinish`` for scenario buckets via the test_code
        fall-through in ``_build_parsed_run_from_reports``.
    """
    if hasattr(session.config, "workerinput"):
        return
    if _STATE is None or not _STATE.enabled:
        return
    cfg = getattr(session.config, "_mcp_contracts_config", None)
    if cfg is None:
        return  # Graceful degrade: no header; rows + summary still print.

    # CR-02: contract-scope gate. The reporter owns the contract surface;
    # the CLI owns the scenario surface (test-code _render_scenario_pre_run_digest).
    # Without this gate, mcp-contracts run --test-code emits the CLI's
    # scenario banner immediately followed by the reporter's contract
    # banner (with discovered_tools=[] because test-code items collect
    # from tests/test_code/) -- two banners per run.
    #
    # Scope detection: classify items by tool-extractability. Items whose
    # nodeids carry a [<tool>] parametrize suffix are contract-shape
    # (either framework-injected via _ContractsModule + mcp_contract
    # marker, or operator-authored parametrized tests that have opted in
    # via --mcp-domain-ui=force). Items WITHOUT a [<tool>] suffix that
    # collect from tests/test_code/ or the legacy tests/sdet/ shim are  # noqa: sdet-rename-shim
    # scenario-shape (no banner; the CLI emits its scenario digest at
    # the wrapper level). Items that are neither (e.g., framework self-
    # tests under tests/framework/ when --with-framework is the only
    # scope) also get no contract banner -- they have no per-tool
    # dimension to report on.
    has_contract_shape_items = any(
        _runner._extract_tool_name(item.nodeid) is not None
        for item in session.items
    )
    if not has_contract_shape_items:
        return  # Scenario / test-code / framework-only scope -- CLI owns the banner.

    server_cmd = f"{cfg.mcp_server.command} {' '.join(cfg.mcp_server.args)}".strip()
    # Dedupe: every contract test parametrizes over the same tool list, so a
    # tool with N contract cases produces N session.items with the same
    # [<tool>] suffix. RenderContext.discovered_tools is a per-tool surface;
    # without `set()` the banner shows N*tools and the downstream "Running"
    # filter iterates duplicates, inflating both counts.
    discovered = sorted(
        {
            name
            for name in (
                _runner._extract_tool_name(item.nodeid)
                for item in session.items
            )
            if name is not None
        }
    )
    judges = _runner._compose_judges_from_tool_configs(cfg.tools)
    _STATE.ctx = _runner.RenderContext(
        server_cmd=server_cmd,
        discovered_tools=discovered,
        tools_config=cfg.tools,
        judges=judges,
        total_planned_cases=len(session.items),
    )
    _runner._render_pre_run_digest(_STATE.ctx)


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Accumulate TestReport events.

    xdist note: under ``-n N``, the controller's logreport hook fires for
    every worker test (xdist forwards events). Workers early-returned in
    ``pytest_configure`` so their ``_STATE`` is None -- no risk of
    double-counting.

    WR-03 filter: only accept reports whose ``when`` is one of the three
    canonical pytest phases (``setup``, ``call``, ``teardown``). Plugins
    like pytest-rerunfailures emit additional report kinds and xdist
    may forward duplicated reports under certain failure modes;
    accepting those would inflate ``bucket.duration`` and ``case_count``
    in ``_build_parsed_run_from_reports`` because the bucketing dict
    keys on ``(nodeid, when)`` and an unknown ``when`` produces a
    distinct entry rather than a no-op.
    """
    if _STATE is None or not _STATE.enabled:
        return
    if report.when not in ("setup", "call", "teardown"):
        return
    _STATE.reports.append(report)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Batch-render per-tool rows + summary line.

    Calls ``_build_parsed_run_from_reports`` (live event-driven adapter)
    + ``render_domain_ui`` (frozen renderer). No I/O beyond stdout writes
    inside the renderer's print() calls.

    If ``_STATE.ctx`` is None (header gracefully degraded because the
    contract plugin had no Config stashed), construct a minimal
    ``RenderContext`` with empty discovered_tools so ``render_domain_ui``
    still emits the per-tool rows + summary line.
    """
    if _STATE is None or not _STATE.enabled:
        return
    parsed = _runner._build_parsed_run_from_reports(_STATE.reports)
    ctx = _STATE.ctx
    if ctx is None:
        # Degraded mode: contract plugin disabled or no config. Synthesize
        # a minimal RenderContext so the post-run renderer still works.
        ctx = _runner.RenderContext(server_cmd="(config not loaded)")
    _runner.render_domain_ui(parsed, ctx)


def pytest_unconfigure(config: pytest.Config) -> None:
    """Tear down module-level state at session end."""
    global _STATE
    _STATE = None
