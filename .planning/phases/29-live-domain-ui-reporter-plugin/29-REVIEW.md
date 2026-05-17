---
phase: 29-live-domain-ui-reporter-plugin
reviewed: 2026-05-17T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - src/mcp_test_framework/_runner.py
  - src/mcp_test_framework/_reporter.py
  - src/mcp_test_framework/cli.py
  - pyproject.toml
  - tests/framework/unit/test_runner_reports_adapter.py
  - tests/framework/test_reporter_plugin.py
  - tests/framework/test_cli_reporter_rewire.py
findings:
  critical: 2
  warning: 4
  info: 3
  total: 9
status: issues_found
---

# Phase 29: Code Review Report

**Reviewed:** 2026-05-17
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 29 introduces a second pytest11 plugin (`_reporter.py`) that emits the
operator-facing domain UI from inside the pytest subprocess via live
`TestReport` events, plus a CLI rewire that delegates the contract-path digest
to the reporter. The adapter (`_build_parsed_run_from_reports`), the reporter
hooks, the pyproject entry-point addition, and the AST-pinned CLI-deletion
proofs are all coherent and the unit tests cover the locked semantics
(any-fail-wins, three-phase bucketing, user_properties read path,
scenario fall-through).

However, the integration between the CLI's captured-subprocess invocation
pattern and the reporter's stdout-write strategy is broken: the reporter
prints to subprocess stdout, but the CLI captures subprocess stdout and only
forwards it to the operator under `--debug`. The default `mcp-contracts run`
path therefore silently swallows the domain UI it was supposed to render.
A second blocker is that under `--test-code` the reporter still emits the
contract-mode header (with empty `discovered_tools`) on top of the CLI's
scenario-mode header — two banners per run.

## Critical Issues

### CR-01: Default `mcp-contracts run` swallows the reporter's domain UI

**File:** `src/mcp_test_framework/cli.py:920-994` (in conjunction with
`src/mcp_test_framework/_runner.py:317-325` and
`src/mcp_test_framework/_reporter.py:189-209`)

**Issue:** The reporter renders header / per-tool rows / summary via
`print(..., file=file)` where `file` defaults to `sys.stdout` inside the
pytest subprocess. The CLI invokes that subprocess with
`subprocess.run(argv, capture_output=True, text=True, ...)`
(`_runner.run_pytest_subprocess` line 317-325), so the reporter's stdout is
captured into the parent's `captured_stdout` string rather than reaching the
operator's terminal.

`cli.run` only forwards `captured_stdout` to the operator inside
`render_debug_appendix` (cli.py line 987). On the default path
(no `-q`, no `--debug`) `captured_stdout` is discarded — the reporter's
output is buffered into a string that is never printed. Net effect:
`mcp-contracts run` shows nothing where the v1.3 JUnit-parse + render path
used to print header + rows + summary.

The integration test `test_force_emits_domain_ui_in_piped_stdout`
(test_reporter_plugin.py:174-199) passes because it invokes `pytest`
directly (no capturing wrapper). The CLI tests
(test_cli_reporter_rewire.py) stub `run_pytest_subprocess` entirely, so the
defect is invisible to them — no test exercises `mcp-contracts run` against
a real subprocess end-to-end.

Under `--debug` the reporter's UI is reachable via the
`--- raw pytest output ---` block in the appendix, but that defeats the
purpose of a live reporter (the operator sees the UI labelled as raw output
and after the appendix header — not as the primary surface).

**Fix:** Pick one of:

1. (Preferred for the live-domain-UI premise) Run the subprocess WITHOUT
   captured stdout on the default path (`stdout=None`, i.e., inherit), and
   capture only stderr if needed for `_dispatch_default_mode_or_error`.
   This requires `_dispatch_default_mode_or_error` to fall back to the
   exit-code-plus-tempfile signal instead of `captured_stderr.splitlines()`
   in the operator-error body.
2. After the subprocess returns, replay `captured_stdout` to
   `sys.stdout` unconditionally on the default path (i.e., when not `-q`,
   regardless of `--debug`). This preserves the capturing mechanism the
   `--debug` appendix relies on but loses the "live" promise — the
   operator only sees the UI after pytest exits.

Whichever path is chosen, add an integration test under `tests/framework/`
that spawns `mcp-contracts run --config=<path>` against a non-empty fixture
and asserts the banner reaches the operator's stdout — the current test
matrix does not cover this seam.

```python
# Sketch: tests/framework/test_cli_run_emits_domain_ui.py
def test_cli_run_default_emits_domain_ui(tmp_path):
    # write minimal config.yaml + a parametrized contract test, then:
    res = subprocess.run(
        [sys.executable, "-m", "mcp_test_framework.cli", "run",
         "--config", str(tmp_path / "config.yaml")],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )
    assert "MCP Test Framework" in res.stdout, res.stdout
```

### CR-02: Double-banner under `mcp-contracts run --test-code`

**File:** `src/mcp_test_framework/_reporter.py:132-173` and
`src/mcp_test_framework/cli.py:882-905`

**Issue:** Under `mcp-contracts run --test-code` (no `-q`, no `--debug`):
- The CLI computes `domain_ui_mode = "force"` (cli.py:918) and forwards
  `--mcp-domain-ui=force` to the subprocess unconditionally — the reporter
  is enabled regardless of test scope.
- The CLI then renders the scenario-mode digest itself via
  `_render_scenario_pre_run_digest` (cli.py:893).
- Inside the subprocess, `_reporter.pytest_collection_finish` runs and
  builds a contract-mode `RenderContext` by filtering `session.items` for
  `mcp_contract` in keywords (line 156). Under `--test-code` the collected
  items live in `tests/test_code/` and have no `mcp_contract` keyword, so
  `discovered_tools` is `[]` — but the function does NOT return early on
  empty discovered_tools, it still calls `_render_pre_run_digest` (line
  173) which prints the contract banner with `Discovered: 0 tools`,
  `Running: 0 (none)`, etc.

Net effect: the operator sees a `MCP Test Framework (test-code)` banner
(from the CLI) immediately followed by a `MCP Test Framework` banner with
zero tools (from the reporter inside the captured subprocess — see CR-01
for the captured-output path, but this still surfaces under `--debug` or
once CR-01 is fixed). The two banners contradict each other.

The reporter has no way to know it's running under `--test-code` because
that flag is wrapper-owned and never reaches pytest's argv (per
`_build_pytest_args` line 113-116 docstring).

**Fix:** Either:
1. In the reporter's `pytest_collection_finish`, short-circuit (no header,
   no `_STATE.ctx` assignment) when no items carry the `mcp_contract`
   keyword. The reporter is for the contract surface; under scenario mode
   the CLI's `_render_scenario_pre_run_digest` is the right banner. The
   sessionfinish per-tool rendering should still run because scenario
   nodeids do produce per-tool buckets via the test_code fall-through in
   `_build_parsed_run_from_reports`, but those should be guarded too — or,
   the scenario path should pass `--mcp-domain-ui=off` from the CLI and
   keep the entire rendering in cli.py.

```python
# _reporter.py:pytest_collection_finish, after the cfg None check:
contract_items = [
    item for item in session.items if "mcp_contract" in item.keywords
]
if not contract_items:
    # Scenario / test-code scope -- CLI owns the banner here.
    return
```

2. (Alternative) Have cli.run compute `domain_ui_mode = "off"` when
   `test_code` is True so the reporter stays silent on the test-code path.
   Then add an explicit CLI-side post-run scenario summary render (CLI
   already owns the scenario pre-run digest, so this preserves single
   ownership of the test-code surface).

Pick one — both surfaces (CLI + reporter) emitting under `--test-code` is
the bug; either one alone is fine. Then add a regression test
`test_test_code_mode_emits_exactly_one_banner` analogous to
`test_xdist_master_only_emission`.

## Warnings

### WR-01: `_build_parsed_run_from_reports` over-counts duration vs JUnit parser

**File:** `src/mcp_test_framework/_runner.py:780-784`

**Issue:** The live adapter sums `r.duration` across all three phase reports
(`setup` + `call` + `teardown`) per nodeid. The JUnit parser at line 594
reads a SINGLE `<testcase time="...">` value per testcase, which pytest's
JUnit writer populates with the call-phase duration only (or the total —
the behavior is JUnit-writer-specific). The byte-equality / field-equality
parity test `test_field_equal_to_parse_junit_xml`
(test_runner_reports_adapter.py:260) only asserts `case_count`, `verdict`,
and `failure_message` agree across the two adapters — it does NOT assert
`duration` agreement, so the drift is silent.

If pytest's JUnit writer emits `time=` as call-phase only, the live path
will report durations roughly 1-3x larger than the XML path. Either is
defensible, but they should match (the renderer reads `bucket.duration`
identically downstream).

**Fix:** Either (a) add `assert x.duration == pytest.approx(live.duration)`
to the parity test to lock current behavior, and document the chosen
semantic in a comment; or (b) restrict the live sum to `r.when == "call"`:

```python
# _runner.py:780-784, replace with:
call_phase = phases.get("call")
if call_phase is not None:
    bucket.duration += float(getattr(call_phase, "duration", 0.0) or 0.0)
else:
    # setup-skip path -- attribute the setup duration.
    bucket.duration += sum(
        float(getattr(r, "duration", 0.0) or 0.0) for r in phases.values()
    )
```

### WR-02: Reporter assumes `sys.__stdout__` is non-None at module load

**File:** `src/mcp_test_framework/_reporter.py:51`

**Issue:** `_ORIGINAL_STDOUT = sys.__stdout__` is evaluated once at module
load. In `pythonw` (Windows GUI) and pyinstaller-frozen contexts,
`sys.__stdout__` is `None` because there is no underlying CPython stdout
file descriptor. The defensive `getattr(_ORIGINAL_STDOUT, "isatty",
lambda: False)()` at line 127 handles the None case by returning False (so
auto-mode resolves to "off") — that part is fine.

The risk is downstream: the docstring at line 27 implies the cached value
is the un-wrapped stream the reporter could write to in `finalization`
contexts. The reporter never actually writes to `_ORIGINAL_STDOUT` (it
relies on the renderer's `file=sys.stdout` default), so this is currently
docstring-only drift, but the comment block sets an expectation the code
does not deliver. If a future edit attempts `print(..., file=_ORIGINAL_STDOUT)`
it will crash on `None.write`.

**Fix:** Either remove the misleading "could be useful to print to the
actual standard stream" docstring fragment (lines 28-31), or capture
`_ORIGINAL_STDOUT = sys.__stdout__ or sys.stdout` so the cached value is
always writable.

### WR-03: Reporter does not validate `report.when` before bucketing

**File:** `src/mcp_test_framework/_runner.py:744-746` (bucketing) and
`src/mcp_test_framework/_reporter.py:176-186`

**Issue:** `pytest_runtest_logreport(report)` accepts every TestReport
event. The adapter buckets by `r.when` (`setup` / `call` / `teardown`) and
treats unknown phases as silent ignored entries. pytest-rerunfailures,
pytest-replay, and some custom plugins emit additional report kinds; xdist
may forward duplicated reports under certain failure modes.

The `case_count += 1` at line 779 is computed once per `nodeid`, so a
duplicate logreport for the same `(nodeid, when)` overwrites the dict
entry rather than double-counting cases — that protects the case total.
But `bucket.duration` at lines 782-784 still sums across all `phases.values()`
including any unknown phases, so an extra report (e.g., a rerun) inflates
the duration for that tool.

**Fix:** Filter at the report-accumulation boundary:

```python
def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if _STATE is None or not _STATE.enabled:
        return
    if report.when not in ("setup", "call", "teardown"):
        return
    _STATE.reports.append(report)
```

### WR-04: Module-level `_STATE` global breaks pytest re-entrancy / multi-session

**File:** `src/mcp_test_framework/_reporter.py:70`

**Issue:** `_STATE: "_ReporterState | None" = None` is module-scoped. The
docstring claims "One pytest session per process; workers early-return and
never create state; no concurrency." That assumption holds for the
operator's normal invocation, but breaks for:

- `pytest --collect-only` followed by `pytest run` in the same Python
  process via `pytest.main()` (the framework's own tests use
  `subprocess.run([sys.executable, '-m', 'pytest', ...])` which sidesteps
  this, but library-mode operators may not).
- IDE test runners (PyCharm, VS Code) that hold the process alive between
  runs to keep imports warm.
- `pytest_unconfigure` is called, sets `_STATE = None` — but if a second
  session starts BEFORE the first session's `pytest_unconfigure` fires
  (rare but possible under threading-based runners), the reports list
  gets corrupted.

The pattern is fragile relative to the alternative of stashing
`_ReporterState` on `config.stash` or on `config._mcp_reporter_state`,
which is what the contract plugin already does for its own Config
(`config._mcp_contracts_config`, _plugin.py line 203).

**Fix:** Mirror the contract plugin's `config._mcp_contracts_config`
pattern:

```python
# pytest_configure
config._mcp_reporter_state = _ReporterState(enabled=True)  # type: ignore[attr-defined]

# pytest_runtest_logreport -- pytest provides config? No, it does not.
# This hook genuinely has no config backref. Either keep the module
# global with a documented "single-session-per-process" caveat, OR
# look up the active session via pytest's session fixture cache.
```

If staying module-global, add an explicit re-init guard in
`pytest_configure` (assert `_STATE is None` before assignment, or log a
warning if it isn't) so a stale state is detected rather than silently
re-used.

## Info

### IN-01: `_classname_from_nodeid` Windows path replacement is double-cost

**File:** `src/mcp_test_framework/_runner.py:679`

**Issue:** `head.replace("\\", "/").replace("/", ".")` — the intermediate
slash normalization is unnecessary; a single regex or two-step replacement
walking the unique separator is cheaper.

**Fix:** Cosmetic; combine into one pass:

```python
return head.replace("\\", ".").replace("/", ".")
```

(Behavior is identical because no test nodeid mixes both separators.)

### IN-02: Adapter docstring claims byte-identical failure_message but live path coerces non-string codes

**File:** `src/mcp_test_framework/_runner.py:803-816`

**Issue:** The docstring at line 730-731 says "MUST be byte-identical
across both adapters." The live path defensively coerces non-string `code`
values via `str(value)`; the JUnit parser at line 624 reads XML attributes
which are always strings. If a test sets a non-string code via
`record_property("mcptf_error_code", 42)`, the live path will format
`"[42] message"` while the JUnit path will format `"[42] message"` as
well (XML coerces to string at serialization time). Both arrive at the
same string, but the type-narrowing in the live path is not symmetric
with the XML reader.

**Fix:** Add a unit test asserting both paths produce identical
`failure_message` for a non-string code value, or document the type
contract on `record_property` so the assumption is explicit.

### IN-03: `pytest_collection_finish` re-checks `workerinput` redundantly

**File:** `src/mcp_test_framework/_reporter.py:147-148`

**Issue:** `pytest_configure` already early-returns on workers without
setting `_STATE`. The re-check in `pytest_collection_finish` (line 147) is
defensive belt-and-suspenders but unreachable in practice — if `_STATE`
were None due to the worker path, line 149 catches it. The redundant
check is harmless but the explanatory comment ("xdist re-invokes
collection on workers") is misleading: xdist DOES re-invoke collection on
workers, but those workers never executed our `pytest_configure` setup
path, so `_STATE` is None there regardless.

**Fix:** Either delete the line 147-148 check (line 149-150 covers it), or
adjust the comment to clarify it's defense-in-depth rather than the
load-bearing gate.

---

_Reviewed: 2026-05-17_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
