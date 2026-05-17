# Phase 29: Live domain-UI reporter plugin - Research

**Researched:** 2026-05-17
**Domain:** pytest plugin authoring (reporting hooks), pytest-xdist coexistence, entry-point packaging
**Confidence:** HIGH

## Summary

Phase 29 ships a second pytest plugin (`mcp_test_framework_reporter`, module `src/mcp_test_framework/_reporter.py`) under a dedicated `[project.entry-points.pytest11]` key alongside the existing contract plugin. It listens to live `pytest_runtest_logreport` events, accumulates `TestReport` objects, then at `pytest_sessionfinish` builds a `ParsedRun` via a new `_runner._build_parsed_run_from_reports(...)` adapter and calls the existing `render_domain_ui(parsed, ctx)` unchanged. Header emission rides `pytest_collection_finish` (pytest 9.0.3 guarantees `session.items` populated before this hook fires). The CLI's JUnit-parse postprocessing at `cli.py:920-934` is deleted; `mcp-contracts run` passes `--mcp-domain-ui=force` so operators always get the domain UI even in non-TTY CI.

The pattern is already well-established in the codebase: `_plugin.py` is the contract plugin, `_reporter.py` is the new sibling. The renderer (`render_domain_ui`, `_render_per_tool_rows`, `_render_summary_line`) is frozen and reused as-is — Phase 29 only adds a new INPUT adapter on top of the existing `ParsedRun` shape. `parse_junit_xml` itself stays in `_runner.py` because ~50 test sites under `tests/framework/unit/` still consume it via fixtures; the planner just removes the single live caller in `cli.py`.

**Primary recommendation:** Mirror the existing `_plugin.py` shape verbatim — module-level hooks, single `_state` accumulator dataclass owned by the plugin module, `_build_parsed_run_from_reports(reports: list[TestReport]) -> ParsedRun` colocated with `parse_junit_xml` in `_runner.py`. Use `report.when == "call"` as the canonical outcome phase, falling back to `setup` for setup-errored tests. Detect xdist master via `not hasattr(config, "workerinput")` in `pytest_configure`; reporter hooks register only on master.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Renderer reuse:**
- **D-01:** **Build `ParsedRun` at session end, batch-render.** Reporter accumulates `TestReport` objects in `pytest_runtest_logreport`, then at `pytest_sessionfinish` builds a `ParsedRun` via a new `_build_parsed_run_from_reports()` helper (mirror of `_runner.py:491` `parse_junit_xml`) and calls the existing `render_domain_ui(parsed, ctx)` unchanged. Single renderer, no per-tool live emission. Per-tool rows print at session end exactly like today — no row-streaming, no parametrize interleaving problem.
- **D-01a:** `_build_parsed_run_from_reports` lives alongside `parse_junit_xml` in `_runner.py` (NOT inside the reporter plugin) so both input adapters sit next to the renderer they feed.

**Output coexistence with pytest-native:**
- **D-02:** **Alongside (additive).** Reporter does NOT suppress pytest's native dots/-v progress, native summary, native tracebacks, or any other pytest plugin's output. Reporter emits the domain header (pre-run) + per-tool rows + domain summary at session end. Operator sees BOTH outputs.

**CI / no-TTY detection:**
- **D-03:** **`sys.stdout.isatty()` only.** Auto-OFF when `sys.stdout.isatty()` is `False`. NO checks for `CI`, `GITHUB_ACTIONS`, `JENKINS_URL`, or any other CI-env-var heuristics.

**Override syntax:**
- **D-04:** **`--mcp-domain-ui=force` (valued option, choices=`auto|force|off`).** Three states: flag absent → OFF; `--mcp-domain-ui` (no value) → `auto`; `--mcp-domain-ui=force` → ON regardless of TTY; `--mcp-domain-ui=off` → OFF. Pytest `addoption` declared with `action='store', nargs='?', const='auto', default='off', choices=['auto','force','off']`.

**CLI wrapper integration:**
- **D-05:** **`mcp-contracts run` passes `--mcp-domain-ui=force`; JUnit-parse path is deleted.** CLI becomes a thin pytest subprocess wrapper. `--junitxml=...` still passed to pytest (XML file still written for external CI consumers) but framework no longer reads it back.
- **D-05a:** **Single-renderer, single-input-path end-state.** Only `_build_parsed_run_from_reports` survives at the framework's UI boundary. Legacy `parse_junit_xml` reader callsite removed from `cli.py`; function MAY remain in `_runner.py` if other callers exist. Planner: audit `parse_junit_xml` callers before deletion.
- **D-05b:** **xdist master-only emission** via `pytest-xdist`'s standard worker_id detection (`config.workerinput` presence → worker; absence → master).

### Claude's Discretion

- Exact reporter module path: `src/mcp_test_framework/_reporter.py` (matches existing `_runner.py` / `_plugin.py` underscore-prefix convention).
- Entry-point key name **locked by ROADMAP**: `[project.entry-points.pytest11] mcp_test_framework_reporter = "mcp_test_framework._reporter"`.
- Header emission timing: pre-run via `pytest_collection_finish` (after collection, before any test runs) — matches the existing `_render_pre_run_digest` pre-run timing in `_runner.py:841`. Planner double-checks RenderContext availability at that hook; if not, defer header to `pytest_sessionstart` or accept it appearing after the first test result.
- `RenderContext` construction inside the reporter: read config via the same `mcp_config_file` ini route the contract plugin uses (Phase 27 D-locked).
- No new operator-facing CLI flags beyond `--mcp-domain-ui` and its three values.

### Deferred Ideas (OUT OF SCOPE)

- **xdist load-balancing strategy / per-worker domain-UI surfaces** — out of scope for Phase 29.
- **CI-env-var heuristic auto-OFF (`CI=true`, `GITHUB_ACTIONS`, etc.)** — explicitly rejected as D-03.
- **Domain-UI live row streaming (per-tool rows printed as each test finishes)** — explicitly rejected as D-01 (option b).
- **JUnit XML parsing as resilient fallback path** — explicitly rejected as D-05 (option c).
- **`--mcp-domain-ui=off` value** — lowest-priority sub-case; included in choices but candidate for removal in v1.5 if unused.
- **`-p no:mcp_test_framework_reporter` documentation** — falls in Phase 30 (CLOSE) docs sweep.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REPORTER-01 | Operator passing `--mcp-domain-ui` to `pytest` sees MCP domain-language output (header / per-tool rows / summary) alongside or replacing pytest's native output — driven by live `pytest_runtest_logreport` events, NOT JUnit XML parsing. Default OFF; CI / no-TTY environments default OFF even with flag set unless `--mcp-domain-ui=force` is passed. | `pytest_runtest_logreport(report: TestReport)` fires for every test on the controller (xdist forwards worker events to controller per `how-it-works.md`). Hook semantics verified §"pytest_runtest_logreport semantics". Renderer reuse satisfied by `_build_parsed_run_from_reports` adapter populating the existing `ParsedRun` dataclass (`_runner.py:469`). Default-OFF + `isatty()`-gated `auto` resolution implemented in `pytest_configure` per §"Option declaration & resolution". |
| REPORTER-02 | Operator running under `pytest-xdist` sees domain UI emitted from master process only; worker output not multiplexed into domain UI rows. Reporter loaded under separate `[project.entry-points.pytest11]` key so operator can `-p no:mcp_test_framework_reporter` while keeping contract fixtures. | xdist's controller-side hook forwarding (verified §"xdist event ordering") delivers all `TestReport` objects to the controller's `pytest_runtest_logreport`, so the reporter never needs to register on workers. Master detection via `not hasattr(config, "workerinput")` in `pytest_configure` early-returns on workers. Second entry-point key (separate from existing `mcp_test_framework = "..._plugin"`) declared in `pyproject.toml`; `-p no:NAME` disables a single plugin by entry-point key per pytest docs (§"Entry-point separation & `-p no:` disable"). |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

- **Python 3.14** pinned in `.python-version` + `requires-python`; reporter must run on 3.14.
- **No raw `subprocess.Popen`** for MCP transport — irrelevant here (reporter does no MCP I/O) but reaffirms the "framework primitives, SDET owns safety" principle (cited memory: `project_framework_primitives_sdet_safety_principle.md`): reporter does no SUT-aware logic.
- **No `homelab-mcp` imports** anywhere in `src/` — reporter is black-box clean by construction (it only consumes `TestReport` events).
- **GSD workflow enforcement** — Phase 29 lands via `/gsd-execute-phase`; CLAUDE.md "Project Status" instruction.
- **Pytest-asyncio strict mode** — reporter hooks are SYNC functions per pytest's hook protocol; no asyncio concerns inside the reporter module itself.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Event capture (`pytest_runtest_logreport`) | Plugin (reporter) | — | Pytest's reporting protocol; reporter is the natural owner per the existing `_plugin.py` lineage. |
| `ParsedRun` adapter (`_build_parsed_run_from_reports`) | Library code (`_runner.py`) | — | D-01a locks this co-located with `parse_junit_xml`; both are pure input adapters for the same renderer. |
| Rendering (header / per-tool rows / summary) | Library code (`_runner.py`) | — | Existing frozen surface (`render_domain_ui`, `_render_pre_run_digest`); reporter consumes verbatim, no shape changes. |
| Option declaration (`--mcp-domain-ui`) | Plugin (reporter) | — | Owned by the reporter entry-point so `-p no:mcp_test_framework_reporter` removes both option AND behavior cleanly. |
| Mode resolution (auto/force/off + TTY check) | Plugin (reporter) | — | Single canonical evaluation point in `pytest_configure`; cached on `config._mcp_reporter_state`. |
| Master/worker detection | Plugin (reporter) | — | Standard `config.workerinput` probe at `pytest_configure`; workers no-op cleanly. |
| RenderContext construction | Plugin (reporter) | Contract plugin's stashed Config | Reporter reads the same `config._mcp_contracts_config` the contract plugin set during `pytest_configure` — single config-load path (Phase 27 D-lock). |
| CLI argv composition | `cli.py` (`run` command) | `_runner._build_pytest_args` | CLI adds `--mcp-domain-ui=force` to the pytest argv; reporter does the rest. |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | >=9.0 (project pinned 9.0.3) | Plugin host | Existing project dep; the `pytest_runtest_logreport`, `pytest_collection_finish`, `pytest_sessionfinish` hooks are stable public API since pytest 7.x. [VERIFIED: pyproject.toml line 42, pytest 9.0.3 confirmed by `uv pip list`] |
| pytest-xdist | none — reporter detects without depending | Distributed testing | Phase 29 does NOT add a dep on xdist. Reporter probes `config.workerinput` (an attribute xdist injects on workers) without importing xdist. Verified pattern in xdist docs ("xdist API Functions for Detection" — `config.workerinput` set on workers, absent on controller). [VERIFIED: Context7 /pytest-dev/pytest-xdist conftest.py example] |

### Supporting

No new runtime dependencies required. Standard library only (`sys`, `typing`) inside `_reporter.py`. The reporter reuses Pydantic `Config`, the existing `_runner.RenderContext` / `ParsedRun` dataclasses, and pytest's own `TestReport` type.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pytest_runtest_logreport` accumulator + sessionfinish batch render | `pytest_terminal_summary(terminalreporter, exitstatus, config)` hook | Would let us hook into pytest's own terminal section. Rejected: terminal_summary is for adding a SECTION to pytest's terminal output; we want full canonical render via `render_domain_ui`. The accumulator pattern is what `pytest-html` and `pytest-json-report` use; aligns with Phase 29's scope. [VERIFIED: pytest docs `reference.rst` "Reporting hooks"] |
| `pytest_runtest_makereport(item, call)` wrapper hook | `pytest_runtest_logreport(report)` (chosen) | makereport gives `(item, call)` and runs once per phase; logreport gives a pre-built `TestReport` and fires after makereport. logreport is the documented "central hook for reporting about test execution" — better fit for downstream consumption. [VERIFIED: Context7 /pytest-dev/pytest "Reporting hooks" — "pytest_runtest_logreport hook is the central hook for reporting about test execution"] |
| xdist's `pytest_testnodedown(node, error)` hook | Master-side `pytest_runtest_logreport` (chosen) | testnodedown fires once per worker shutdown; doesn't give per-test data. logreport already arrives on the controller for every worker test (xdist forwards events). [VERIFIED: Context7 /pytest-dev/pytest-xdist `how-it-works.md`] |

**Installation:** No new packages. Verify pytest >= 9.0:
```bash
uv pip show pytest  # already pinned to >=9.0 in pyproject.toml
```

**Version verification:**
```bash
uv pip show pytest  # 9.0.3 installed (verified 2026-05-17)
uv pip show pytest-asyncio  # 1.3.0 installed (verified 2026-05-17)
# pytest-xdist NOT installed; reporter detects without depending
```

---

## Architecture Patterns

### System Architecture Diagram

```
Operator invocation
   │
   ├─ CLI mode:  `mcp-contracts run --config PATH`
   │     └─→ cli.py builds pytest argv: pytest tests/contract --junitxml=tmp.xml
   │            -o "mcp_config_file=PATH" --mcp-domain-ui=force
   │            └─→ subprocess.run(...)
   │
   └─ Library mode: `pytest --mcp-domain-ui` (or `--mcp-domain-ui=force`)
         └─→ pytest auto-loads entry-points:
                ├─ mcp_test_framework = "..._plugin"      (contract plugin — fixtures + injection)
                └─ mcp_test_framework_reporter = "..._reporter"  (this phase)

Inside pytest process:
   ┌───────────────────────────────────────────────────────────────┐
   │  pytest_configure (both plugins)                              │
   │   ├─ _plugin.py: loads Config, stashes on config._mcp_contracts_config
   │   └─ _reporter.py:                                            │
   │        1. Detect xdist worker (config.workerinput) → early-return on workers
   │        2. Read --mcp-domain-ui choice                         │
   │        3. Resolve mode: 'off'→disable; 'force'→on;            │
   │           'auto'→on if sys.stdout.isatty() else off           │
   │        4. If disabled: early-return (no further hooks fire)   │
   │        5. Cache state on config._mcp_reporter_state           │
   │        6. Init reports accumulator (list[TestReport])         │
   └──────────┬────────────────────────────────────────────────────┘
              │
              ▼
   ┌───────────────────────────────────────────────────────────────┐
   │  pytest_collection_finish(session)                            │
   │   - pytest 9.0.3 guarantees session.items populated here      │
   │   - Build RenderContext from stashed Config + session.items   │
   │     (discovered tools = parametrize ids of mcp_contract items)│
   │   - Call _runner._render_pre_run_digest(ctx) → header on stdout
   └──────────┬────────────────────────────────────────────────────┘
              │
              ▼
   ┌───────────────────────────────────────────────────────────────┐
   │  pytest_runtest_logreport(report: TestReport)  [N x 3 calls] │
   │   - Fires for each of setup/call/teardown phases              │
   │   - Append to accumulator unconditionally                     │
   │   (xdist: forwarded from workers to controller automatically) │
   └──────────┬────────────────────────────────────────────────────┘
              │
              ▼
   ┌───────────────────────────────────────────────────────────────┐
   │  pytest_sessionfinish(session, exitstatus)                    │
   │   - parsed = _build_parsed_run_from_reports(accumulator)      │
   │   - _runner.render_domain_ui(parsed, ctx)                     │
   │     → per-tool rows + summary line on stdout                  │
   └───────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | File | Owns |
|-----------|------|------|
| Reporter plugin | `src/mcp_test_framework/_reporter.py` (NEW) | All pytest hooks; option declaration; mode resolution; accumulator; RenderContext construction |
| Adapter | `src/mcp_test_framework/_runner.py` (`_build_parsed_run_from_reports` — NEW function, ~line 634 after `parse_junit_xml`) | TestReport list → ParsedRun translation; mirror of `parse_junit_xml` |
| Renderer (UNCHANGED) | `src/mcp_test_framework/_runner.py:1171` `render_domain_ui` | Verbatim consumed by reporter |
| Pre-run digest (UNCHANGED) | `src/mcp_test_framework/_runner.py:841` `_render_pre_run_digest` | Verbatim consumed by reporter for header |
| Packaging | `pyproject.toml` lines 27-32 | Second entry-point key alongside existing `mcp_test_framework` |
| CLI wiring | `src/mcp_test_framework/cli.py` (delete `cli.py:920-934` JUnit-parse branch; insert `--mcp-domain-ui=force` into argv) | Argv composition only |

### Pattern 1: Sibling pytest11 plugins under one distribution

**What:** Two plugin modules registered under separate entry-point keys; pytest treats them as independent plugins (each can be disabled with `-p no:KEY`).

**When to use:** When a single distribution ships two orthogonal pytest capabilities that should be independently disable-able. Phase 29's case: operators may want contract fixtures without the domain UI, or vice versa.

**Example:** [CITED: pytest docs `how-to/writing_plugins.rst`, `how-to/usage.rst`]
```toml
# pyproject.toml — multiple pytest11 keys in one block
[project.entry-points.pytest11]
mcp_test_framework = "mcp_test_framework._plugin"
mcp_test_framework_reporter = "mcp_test_framework._reporter"
```

Both modules are loaded by pytest at startup. To disable just the reporter:
```bash
pytest -p no:mcp_test_framework_reporter
```

### Pattern 2: TestReport accumulator + sessionfinish batch render

**What:** Collect `TestReport` objects in `pytest_runtest_logreport`, render once at `pytest_sessionfinish` from the accumulated list.

**When to use:** When per-test live rendering is unwanted (D-01 rejects row-streaming due to parametrize interleaving) but the operator wants a domain-specific summary distinct from pytest's native terminal output.

**Example:** [CITED: pytest docs `example/simple.rst` "Pytest Hook to Stash Test Reports in Fixtures"]
```python
# _reporter.py (sketch)
import pytest

class _ReporterState:
    def __init__(self):
        self.reports: list[pytest.TestReport] = []
        self.enabled: bool = False
        self.ctx = None  # RenderContext, built at collection_finish

def pytest_configure(config: pytest.Config) -> None:
    # Worker no-op (xdist forwards events to controller)
    if hasattr(config, "workerinput"):
        return
    choice = config.getoption("--mcp-domain-ui")  # 'off' | 'auto' | 'force'
    if choice == "off":
        return
    if choice == "auto" and not sys.stdout.isatty():
        return
    state = _ReporterState()
    state.enabled = True
    config._mcp_reporter_state = state

def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    state = getattr(report.session.config if hasattr(report, "session") else None,
                    "_mcp_reporter_state", None)
    # Real impl: use pytest's `pytest_runtest_logreport(report)` signature —
    # access config via a module-level handle stashed in pytest_configure.
    ...
```

### Pattern 3: Outcome attribution from TestReport.when phases

**What:** Each test produces three `TestReport` objects (`when` ∈ {`"setup"`, `"call"`, `"teardown"`}). The "test outcome" is conventionally taken from the `"call"` phase, but setup errors and teardown errors must also surface as failures.

**Rule (canonical):** [CITED: pytest docs `example/simple.rst`]
- If `report.when == "setup"` and `report.failed` → setup error → mark test FAIL.
- If `report.when == "setup"` and `report.skipped` → skip (e.g. `pytest.mark.skip`, fixture skip) → mark test SKIP.
- If `report.when == "call"` → use `report.outcome` ("passed" | "failed" | "skipped").
- If `report.when == "teardown"` and `report.failed` → teardown error → still mark FAIL (don't downgrade a PASS).

The existing `parse_junit_xml` does NOT have this multi-phase nuance — JUnit XML emits one `<testcase>` per test with consolidated outcome. `_build_parsed_run_from_reports` must dedupe by `report.nodeid` and apply the phase precedence above.

**Example bucket attribution per nodeid:**
```python
# Pseudocode for _build_parsed_run_from_reports
def _build_parsed_run_from_reports(reports: list[pytest.TestReport]) -> ParsedRun:
    by_nodeid: dict[str, dict[str, pytest.TestReport]] = {}
    for r in reports:
        by_nodeid.setdefault(r.nodeid, {})[r.when] = r

    run = ParsedRun()
    for nodeid, phases in by_nodeid.items():
        tool = _extract_tool_name(nodeid)  # reuse _runner.py:388
        if tool is None:
            # scenario fall-through (see parse_junit_xml lines 540-563)
            continue
        bucket = run.per_tool.setdefault(tool, ToolVerdict(name=tool, verdict="PASS"))
        bucket.case_count += 1
        # Sum durations across phases (matches JUnit <testcase time="..."> semantics)
        bucket.duration += sum(getattr(r, "duration", 0.0) for r in phases.values())

        setup = phases.get("setup")
        call = phases.get("call")
        teardown = phases.get("teardown")

        if (setup and setup.failed) or (call and call.failed) or (teardown and teardown.failed):
            bucket.verdict = "FAIL"
            failing = next(r for r in (call, setup, teardown) if r and r.failed)
            if bucket.failure_message is None:
                bucket.failure_message = _summarize_longrepr(failing.longrepr)
            # mcptf_error_code/message bridge — see Pitfall 4 below
        elif (setup and setup.skipped) or (call and call.skipped):
            skipped = setup if (setup and setup.skipped) else call
            reason = _extract_skip_reason(skipped)
            if reason and reason not in bucket.skip_reasons:
                bucket.skip_reasons.append(reason)
            if bucket.verdict not in ("FAIL", "PASS"):
                bucket.verdict = "SKIP"
        # else PASS (default ToolVerdict verdict)

    # Totals
    run.total_cases = sum(v.case_count for v in run.per_tool.values())
    run.total_failures = sum(1 for v in run.per_tool.values() if v.verdict == "FAIL")
    run.total_skipped = sum(1 for v in run.per_tool.values() if v.verdict == "SKIP")
    run.total_time = sum(v.duration for v in run.per_tool.values())
    return run
```

### Pattern 4: xdist controller-side hook forwarding

**What:** When pytest-xdist runs with `-n N`, worker processes execute tests and ship `TestReport` objects back to the controller. The controller's `pytest_runtest_logreport` hook fires for every worker result automatically — no special multiplexing code required.

**When to use:** Always. The reporter writes one hook implementation that works in both standalone and xdist modes.

**Source:** [VERIFIED: Context7 /pytest-dev/pytest-xdist `how-it-works.md`]
> "As tests are executed on the workers, their results are sent back to the controller, which then forwards them to the appropriate pytest hooks, ensuring compatibility with other plugins."

[VERIFIED: Context7 /pytest-dev/pytest-xdist CHANGELOG 1.10] "Fixed pytest issue 382 by producing the 'pytest_runtest_logstart' event again in the master process."

### Anti-Patterns to Avoid

- **Per-test live row emission:** Rejected by D-01 (option b). Interleaves with pytest's native dots/-v output AND with parametrize ordering; produces an unreadable wall.
- **CI env-var probing (`CI`, `GITHUB_ACTIONS`, `JENKINS_URL`):** Rejected by D-03. Use `sys.stdout.isatty()` only.
- **JUnit XML fallback path on hook failure:** Rejected by D-05. Single source of truth.
- **Registering hooks on xdist workers:** Wastes work; worker accumulators are never rendered. Early-return in `pytest_configure` on `hasattr(config, "workerinput")`.
- **Importing xdist as a hard dependency:** Phase 29 must work without pytest-xdist installed. Use `hasattr(config, "workerinput")` (a duck-typed check), NOT `from xdist import is_xdist_worker`.
- **Suppressing pytest's native output:** D-02 mandates additive coexistence. Do NOT register `pytest_terminal_summary` to replace pytest's summary; just add the domain section.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-test outcome aggregation | A custom test-result protocol that wraps `TestReport` | Consume `TestReport.outcome / .failed / .skipped / .when` directly | pytest's `TestReport` IS the protocol; wrapping adds zero value. |
| Master/worker detection | A custom IPC scheme reading `os.environ["PYTEST_XDIST_WORKER"]` | `hasattr(config, "workerinput")` | The `workerinput` attribute is xdist's documented inter-process channel; `PYTEST_XDIST_WORKER` env var works too but is less idiomatic. [VERIFIED: Context7 /pytest-dev/pytest-xdist worker-specific logging example] |
| Plugin disable mechanism | Custom env-var check inside the plugin to opt out | `pytest -p no:mcp_test_framework_reporter` | First-class pytest feature; one entry-point key = one disable knob. [VERIFIED: pytest docs `how-to/usage.rst` "Deactivate a pytest plugin by name"] |
| Marker filtering on reports | Re-parse `report.keywords` strings | `"mcp_contract" in report.keywords` | `report.keywords` is a dict mapping marker names to truthy values; the contract plugin's `pytest_collection_modifyitems` already applies the marker per item; it round-trips into reports. [VERIFIED: pytest source — `_pytest/reports.py` populates keywords from `item.keywords`] |
| TestReport-to-ParsedRun translation | A serialization/JSON roundtrip | Direct in-memory dataclass population | Both live in the same pytest process; ParsedRun's frozen field set (`_runner.py:469`) is the boundary. |

**Key insight:** Pytest's reporting protocol already gives us everything: `TestReport` carries `nodeid`, `outcome`, `when`, `duration`, `longrepr`, `keywords`, `user_properties`. No custom event format needed.

---

## Common Pitfalls

### Pitfall 1: Confusing `TestReport.when` phases with test outcome

**What goes wrong:** Naïve implementation uses every `TestReport.outcome` event — counts a test 3× (setup PASSED, call PASSED, teardown PASSED) or worse, sees a `setup PASSED` immediately followed by `call FAILED` and ends up with verdict "PASS" because the call event was overwritten by a later teardown PASSED.

**Why it happens:** Pytest fires `pytest_runtest_logreport` THREE times per test (one per phase). Each report carries the phase-level outcome, not the test-level outcome.

**How to avoid:** Bucket reports by `report.nodeid` first, then derive outcome from the bucket's phases using the precedence rule in Pattern 3 (call.outcome dominates; setup-error or teardown-error promotes to FAIL; setup-skip means SKIP).

**Warning signs:** `total_cases` in the rendered output is 3× the number of tests actually run.

[VERIFIED: pytest docs `example/simple.rst` "Pytest Hook to Stash Test Reports in Fixtures" — explicit guidance that `rep.when` can be `"setup"`, `"call"`, or `"teardown"`]

### Pitfall 2: Header emitted before RenderContext is constructible

**What goes wrong:** Reporter registers `pytest_collection_finish` to emit the header, but at that point `config._mcp_contracts_config` is not set (e.g. operator hasn't set `mcp_config_file` ini, OR contract plugin's `pytest_configure` was disabled via `-p no:mcp_test_framework`).

**Why it happens:** The reporter assumes the contract plugin always populates the config stash, but the two plugins can be independently disabled.

**How to avoid:**
1. In `pytest_configure`, the reporter caches `state.config = config` (module-level handle).
2. In `pytest_collection_finish`, check `getattr(config, "_mcp_contracts_config", None)`. If None, emit a degraded header ("MCP server: (config not loaded)") OR skip the header entirely and let the per-tool rows still render. Recommendation: skip the header gracefully — render only the per-tool block + summary line.
3. Document this behavior in the reporter's module docstring.

**Warning signs:** `AttributeError: 'Config' object has no attribute '_mcp_contracts_config'` during collection_finish.

### Pitfall 3: `pytest_collection_finish` fires on the controller AND on each worker under xdist

**What goes wrong:** Even with master-only hook gating in `pytest_configure`, `pytest_collection_finish` runs on every node (workers AND controller) because xdist still does its own collection on each worker for pytest-internal reasons.

**Why it happens:** xdist's distribution model requires workers to know the full collected item list. The collection-finish hook fires post-collection on every process.

**How to avoid:** Apply the same `hasattr(config, "workerinput")` worker-early-return at the TOP of `pytest_collection_finish`, NOT only in `pytest_configure`. (The state-presence check from Pitfall 2 also implicitly handles this, since the worker's pytest_configure already early-returned and never created the state.)

[VERIFIED: Context7 /pytest-dev/pytest-xdist CHANGELOG 1.2] "sessionfinish/teardown hooks are now called systematically on the slave side." — confirms session-level hooks fire on workers.

### Pitfall 4: ToolCallError properties on the call-phase report

**What goes wrong:** SDET-authored scenarios use the `mcptf_error_code` / `mcptf_error_message` `user_properties` mechanism (set by `tests/test_code/conftest.py:pytest_exception_interact`) to attach structured failure info. The existing `parse_junit_xml` reads these from `<property>` children. `_build_parsed_run_from_reports` must read them from `report.user_properties` (a list of `(name, value)` tuples) instead.

**Why it happens:** Different transport (in-memory TestReport vs. JUnit XML <property> elements), same payload semantics.

**How to avoid:** In `_build_parsed_run_from_reports`, iterate `report.user_properties` on the failing report:
```python
code = msg = None
for name, value in (call.user_properties or []):
    if name == "mcptf_error_code":
        code = value
    elif name == "mcptf_error_message":
        msg = value
if msg:
    bucket.failure_message = f"[{code}] {msg}" if code else msg
```

This mirrors `parse_junit_xml` lines 591-611 exactly. Both adapters must produce identical `bucket.failure_message` text given the same underlying error.

[VERIFIED: `_runner.py:591-611` — JUnit-XML reads `<property name="mcptf_error_code">` and `<property name="mcptf_error_message">`; `report.user_properties` is the in-memory equivalent per pytest docs "Adding custom properties to test reports"]

### Pitfall 5: `pytest_runtest_logreport` hook arrives with no `report.session` attribute

**What goes wrong:** Reporter tries to access `report.session.config._mcp_reporter_state` to find the accumulator, but `TestReport` does not carry a session backref.

**Why it happens:** `TestReport` is a plain data carrier; the hook signature is `pytest_runtest_logreport(report)` with no access to session/config.

**How to avoid:** Stash a module-level handle to the accumulator in `pytest_configure`:
```python
# _reporter.py
_STATE: dict[int, _ReporterState] = {}  # keyed by id(config) for test-suite isolation

def pytest_configure(config):
    ...
    _STATE[id(config)] = state
    # Also stash on config for cleanup
    config._mcp_reporter_state = state

def pytest_runtest_logreport(report):
    # Find the active state — only one is "current" within a pytest session,
    # so the most recent one set wins. For full safety: pytest gives the
    # config via the `pytest_runtest_protocol` chain, but logreport doesn't.
    # Use a single module-level state instance for the lifetime of one
    # pytest run — workers early-return so there's no concurrency.
    state = next(iter(_STATE.values()), None)
    if state is None or not state.enabled:
        return
    state.reports.append(report)

def pytest_unconfigure(config):
    _STATE.pop(id(config), None)
```

Simpler alternative: use a module-level `_REPORTER_STATE: _ReporterState | None` since only one pytest session runs per process. Document the invariant in the module docstring.

### Pitfall 6: `--mcp-domain-ui` value parsing under nargs='?'

**What goes wrong:** Operator passes `--mcp-domain-ui force` (space, not equals) expecting "force"; argparse interprets `force` as a positional arg because `nargs='?'` makes the value optional.

**Why it happens:** `nargs='?'` + `const='auto'` means "bare flag → const, =VALUE → VALUE". The space-separated form `--mcp-domain-ui force` is ambiguous to argparse.

**How to avoid:** Document the equals-only spelling in `--help`. Pytest's parser is argparse under the hood; the convention `--flag=value` is unambiguous. Add a test that verifies:
- `pytest` (absent) → `"off"`
- `pytest --mcp-domain-ui` (bare) → `"auto"`
- `pytest --mcp-domain-ui=force` → `"force"`
- `pytest --mcp-domain-ui=off` → `"off"`
- `pytest --mcp-domain-ui=bogus` → argparse error (`choices` enforced)

[CITED: pytest docs `example/simple.rst` "Add validation to custom command line options" — confirms `choices=(...)` is honored by pytest's parser]

### Pitfall 7: `isatty()` evaluated after another plugin reassigns `sys.stdout`

**What goes wrong:** Reporter evaluates `sys.stdout.isatty()` in `pytest_configure` to resolve `--mcp-domain-ui=auto`, but a plugin loaded earlier (e.g. `pytest-html`'s capture, `pytest-sugar`) has wrapped `sys.stdout` with a non-TTY proxy.

**Why it happens:** Plugin load order is alphabetical-ish by entry-point key; `pytest_configure` order depends on registration. The reporter cannot guarantee it's first.

**How to avoid:** Evaluate `isatty()` against the ORIGINAL stream stashed by pytest, NOT `sys.stdout` at call time. Pytest's `capturemanager` exposes the original via `config.pluginmanager.get_plugin("capturemanager")._global_capturing.in_.tmpfile`, but the simpler and more portable approach is:
```python
# At reporter module load time (NOT in pytest_configure), capture the original stream.
import sys as _sys
_ORIGINAL_STDOUT = _sys.__stdout__  # Always the un-wrapped original

def _is_tty() -> bool:
    return bool(getattr(_ORIGINAL_STDOUT, "isatty", lambda: False)())
```

`sys.__stdout__` is the unwrapped stream pytest never touches. This is the canonical CPython idiom for "what is the real stdout regardless of capture/redirection."

[CITED: CPython docs `sys.__stdout__` — "These objects contain the original values of stdin, stderr and stdout at the start of the program. They’re used during finalization, and could be useful to print to the actual standard stream no matter if the sys.std* object has been redirected."]

### Pitfall 8: Pytest-sugar / pytest-html DO hook `pytest_runtest_logreport`

**What goes wrong:** D-02 says "additive coexistence with pytest-sugar / pytest-html." Both DO register `pytest_runtest_logreport` themselves; the reporter must not assume it's the only hook.

**Why it happens:** `pytest_runtest_logreport` is a non-firstresult hook (per pytest's hook spec); all registered implementations fire. No hijack risk.

**How to avoid:** Nothing — the additive contract is preserved by pytest's hook semantics by default. Validation: confirm `pytest -p pytest-sugar --mcp-domain-ui=force` still renders the domain UI (suggest adding a UAT note for Phase 30).

[VERIFIED: pytest docs `how-to/writing_hook_functions.rst` "Control pytest hook execution order" — non-firstresult hooks chain]

---

## Code Examples

### Reporter plugin skeleton (locked structure)

```python
# src/mcp_test_framework/_reporter.py
"""Live domain-UI reporter — second pytest11 plugin.

Listens to pytest_runtest_logreport events, accumulates TestReport objects,
and at sessionfinish builds a ParsedRun via _build_parsed_run_from_reports
and renders the existing domain UI verbatim. Default OFF; `--mcp-domain-ui`
flips it on (auto/force/off three-state). xdist controller-only emission via
workerinput probe.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field

import pytest

from mcp_test_framework import _runner


# Always probe the un-wrapped original stream (capture-proxies are common).
_ORIGINAL_STDOUT = sys.__stdout__


@dataclass
class _ReporterState:
    enabled: bool = False
    reports: list[pytest.TestReport] = field(default_factory=list)
    ctx: _runner.RenderContext | None = None


# Single-state-per-process invariant (one pytest session per process).
_STATE: _ReporterState | None = None


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("mcp_test_framework")  # group already exists from _plugin
    group.addoption(
        "--mcp-domain-ui",
        action="store",
        nargs="?",
        const="auto",
        default="off",
        choices=["auto", "force", "off"],
        help=(
            "Render the MCP domain UI alongside pytest's native output. "
            "Bare flag = auto (on if stdout is a TTY); =force forces on; "
            "=off (or flag absent) disables."
        ),
    )


def pytest_configure(config: pytest.Config) -> None:
    global _STATE
    # xdist worker no-op: controller forwards events to its own logreport hook.
    if hasattr(config, "workerinput"):
        return
    choice = config.getoption("--mcp-domain-ui", default="off")
    if choice == "off":
        return
    if choice == "auto" and not bool(getattr(_ORIGINAL_STDOUT, "isatty", lambda: False)()):
        return
    _STATE = _ReporterState(enabled=True)


def pytest_collection_finish(session: pytest.Session) -> None:
    if _STATE is None or not _STATE.enabled:
        return
    # Build RenderContext from the contract plugin's stashed Config.
    cfg = getattr(session.config, "_mcp_contracts_config", None)
    if cfg is None:
        return  # No contract plugin / no config → degrade gracefully (no header).
    server_cmd = f"{cfg.mcp_server.command} {' '.join(cfg.mcp_server.args)}".strip()
    # Discovered tools = parametrize ids of mcp_contract items.
    discovered = sorted({
        _runner._extract_tool_name(item.nodeid)
        for item in session.items
        if "mcp_contract" in item.keywords
        and _runner._extract_tool_name(item.nodeid) is not None
    })
    judges = _runner._compose_judges_from_tool_configs(cfg.tools)
    _STATE.ctx = _runner.RenderContext(
        server_cmd=server_cmd,
        discovered_tools=discovered,
        tools_config=cfg.tools,
        judges=judges,
    )
    _runner._render_pre_run_digest(_STATE.ctx)


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if _STATE is None or not _STATE.enabled:
        return
    _STATE.reports.append(report)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if _STATE is None or not _STATE.enabled or _STATE.ctx is None:
        return
    parsed = _runner._build_parsed_run_from_reports(_STATE.reports)
    _runner.render_domain_ui(parsed, _STATE.ctx)
```

### `_build_parsed_run_from_reports` adapter (lives in `_runner.py`)

See Pattern 3 above for the full pseudocode. Key invariants:
- Bucket by `report.nodeid`; one bucket per test.
- Sum durations across phases.
- Apply phase-precedence verdict rule.
- Reuse `_extract_tool_name` (`_runner.py:388`), `_strip_pytest_skipped_prefix` (`_runner.py:403`), `_REASON_*` constants (`_runner.py:377-378`) for symmetry with `parse_junit_xml`.
- Read `mcptf_error_code` / `mcptf_error_message` from `report.user_properties` (mirror of `parse_junit_xml:591-611`).

### CLI argv composition change

```python
# src/mcp_test_framework/cli.py — inside `run` command, NEAR _build_pytest_args caller
# DELETE: lines 920-934 (parse_junit_xml + post-run render branch)
# DELETE: tempfile junit XML allocation if no operator --junit-xml supplied
# ADD: --mcp-domain-ui=force to the argv list

# In `_build_pytest_args` (in _runner.py around line 144):
# After `args.append(f"--junitxml={junit_xml}")` insert:
args.append("--mcp-domain-ui=force")
```

Alternative (cleaner): pass `domain_ui: bool = True` kwarg to `_build_pytest_args` so the CLI explicitly opts in. Planner decides; the locked surface is just "argv carries `--mcp-domain-ui=force` when CLI invokes pytest."

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| CLI wrapper round-trips JUnit XML through `parse_junit_xml` to render domain UI | Live `TestReport` event accumulator → `_build_parsed_run_from_reports` → same `render_domain_ui` | Phase 29 (this phase) | Library-mode operators get the domain UI without needing the CLI; CLI mode becomes a thin pytest argv wrapper. |
| `--mcp-domain-ui` as a boolean flag (proposed in roadmap) | Three-state `--mcp-domain-ui=auto\|force\|off` with TTY-aware auto resolution | CONTEXT.md D-04 | Cleaner override semantics; explicit "force on against TTY default" affordance for CI. |

**Deprecated / outdated:**
- The CLI's `parse_junit_xml` callsite in `cli.py:920-934` — removed by D-05.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Pytest's `pytest_runtest_logreport` is non-firstresult and chains all registered hooks (so pytest-sugar/pytest-html don't suppress us) | Pitfall 8 | LOW — this is a default pytest behavior, but worth a smoke test in plan to confirm with sugar installed |
| A2 | `report.keywords` is a dict containing marker names with truthy values, populated for items that carry `pytest.mark.mcp_contract` | Don't Hand-Roll table; pattern 4 | LOW — pytest's `_pytest/reports.py` populates from item.keywords; consistent across pytest 7+. Plan should verify with a tiny `assert "mcp_contract" in report.keywords` test against an actual injected contract test |
| A3 | `pytest_sessionfinish` fires AFTER the last `pytest_runtest_logreport` even under xdist (controller waits for all worker results) | Pitfall 3; pattern diagram | MEDIUM — xdist CHANGELOG 1.2 says sessionfinish runs on workers too, but doesn't explicitly state controller-side ordering relative to forwarded worker events. Plan should include a Wave-0-style smoke test under `-n 2` to confirm event ordering |
| A4 | The contract plugin's `pytest_configure` runs BEFORE the reporter's `pytest_collection_finish`, guaranteeing `config._mcp_contracts_config` is set when the reporter needs it | Reporter plugin skeleton | LOW — pytest runs all `pytest_configure` hooks before any collection hook; standard hook lifecycle. Pitfall 2 already documents the degraded-header fallback if absent |
| A5 | `sys.__stdout__` is reliably the un-wrapped original even when pytest's capture is active | Pitfall 7 | LOW — this is documented CPython behavior; pytest's capturemanager replaces `sys.stdout` but never touches `sys.__stdout__` |

**If user confirms or rejects any of the above**, planner adjusts the plan accordingly. A3 is the only one that warrants an explicit verification task in the plan (a tiny xdist smoke test).

---

## Open Questions

1. **xdist `pytest_sessionfinish` ordering under `-n auto`**
   - What we know: Controller forwards `pytest_runtest_logreport` from workers (xdist `how-it-works.md`). `pytest_sessionfinish` runs on every node (xdist CHANGELOG 1.2).
   - What's unclear: Whether the controller's `pytest_sessionfinish` strictly fires AFTER all worker `pytest_runtest_logreport` events have been forwarded. Empirically yes (otherwise xdist's own terminal summary wouldn't work), but no doc says so explicitly.
   - Recommendation: Plan includes a smoke-test task: install pytest-xdist as a dev-dependency, run `pytest -n 2 --mcp-domain-ui=force` against the framework's own contract suite, assert per-tool rows include every test. Mark assumption A3 verified at that point.

2. **`-p no:mcp_test_framework_reporter` interaction with `--mcp-domain-ui`**
   - What we know: `-p no:KEY` unregisters the plugin entirely; its `pytest_addoption` never runs.
   - What's unclear: When the plugin is disabled, `--mcp-domain-ui` will trip pytest's argparse with "unrecognized argument" if the operator still passes it.
   - Recommendation: Document this in the reporter docstring. The operator behavior "I disabled the plugin so I expect the flag to not exist" matches user expectations. No special handling needed.

3. **Test-code (scenario) rows under library mode**
   - What we know: `parse_junit_xml` has a scenario fall-through (`_runner.py:540-563`) for `tests.test_code.test_*` classnames; `_render_per_tool_rows` (`_runner.py:1062-1132`) renders scenario blocks distinctly.
   - What's unclear: In library mode under the reporter, do operator-authored test-code scenarios produce TestReports that go through the same fall-through, and does `_build_parsed_run_from_reports` need to replicate the classname-based grouping? CONTEXT.md doesn't explicitly mention scenario rendering for Phase 29.
   - Recommendation: Planner asks user. Two answers possible: (a) Phase 29 covers contract-only; scenario rendering stays via JUnit XML or is deferred. (b) Phase 29 includes scenario fall-through in the adapter. Both are buildable.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pytest | All hooks | ✓ | 9.0.3 | — |
| pytest-asyncio | Existing test infra | ✓ | 1.3.0 | — |
| pytest-xdist | xdist coexistence smoke test (Open Question 1) | ✗ | — | Phase 29 plan adds it as a dev-dep for one smoke test; runtime behavior validated without installing it (reporter uses `hasattr(config, "workerinput")`) |
| Python | Reporter module | ✓ | 3.14 | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** `pytest-xdist` — install as a dev-dep solely for the Open Question 1 smoke test; reporter has no runtime dep on it.

---

## `parse_junit_xml` caller audit (D-05a action item)

**Active callers as of 2026-05-17 (excluding worktrees, excluding the function definition itself):**

| Site | Type | Disposition |
|------|------|-------------|
| `src/mcp_test_framework/cli.py:922` | Production call (CLI wrapper) | **DELETE** per D-05 |
| `tests/framework/test_runner_renderer.py` | 13 test sites | KEEP — these are parser/renderer unit tests; deleting `parse_junit_xml` would orphan them. Planner decides whether to migrate to `_build_parsed_run_from_reports` or keep both adapters tested. |
| `tests/framework/test_runner_verbosity.py` | 5 test sites | KEEP — same rationale |
| `tests/framework/unit/test_runner_parser.py` | ~20 test sites | KEEP — these test `parse_junit_xml` SPECIFICALLY; they ARE the parser's contract tests. |
| `tests/framework/unit/test_runner_debug_appendix_d11.py` | 9 test sites | KEEP — debug appendix tests |
| `tests/framework/unit/test_runner_sdet_rows.py` | 10 test sites | KEEP — scenario fall-through tests |
| `tests/framework/unit/test_sdet_renderer.py` | 6 test sites | KEEP — SDET renderer property-prop reading |

**Conclusion:** `parse_junit_xml` STAYS in `_runner.py`. Only the production callsite (`cli.py:922`) is deleted. Tests retain coverage of the JUnit adapter (still useful for any operator wiring junit-XML to ParsedRun externally, and as a regression net since the renderer is shared).

**Planner action:** Delete the 15-line block at `cli.py:912-969` that runs `parse_junit_xml(tmp_xml)` + `render_domain_ui(parsed, ctx)`. Also delete the surrounding `tmp_xml` lifecycle (`finally:` cleanup at lines 975-980) since no production code reads it anymore. The `--junit-xml=PATH` operator flag still works (passes through to pytest); only the framework's internal post-processing is removed.

---

## Sources

### Primary (HIGH confidence)

- **Context7 `/pytest-dev/pytest` v9.0.0** — Reporting hooks reference, `pytest_runtest_logreport` semantics, `pytest_runtest_makereport` phase-aware example (`example/simple.rst`), addoption with `choices=` (`example/simple.rst` "Add validation to custom command line options"), plugin entry-point declaration (`how-to/writing_plugins.rst`), `-p no:NAME` disable (`how-to/usage.rst`), `pytest_collection_finish` populates `session.items` (Changelog pytest 9.0.3).
- **Context7 `/pytest-dev/pytest-xdist`** — `is_xdist_worker` / `config.workerinput` detection patterns, controller forwards events to hooks (`how-it-works.md`), CHANGELOG 1.2 (sessionfinish on workers), CHANGELOG 1.10 (logstart on master).
- **`src/mcp_test_framework/_plugin.py` (project source)** — Existing pytest11 plugin pattern; reporter mirrors this shape.
- **`src/mcp_test_framework/_runner.py:469` (project source)** — `ParsedRun` shape (the renderer's input contract).
- **`src/mcp_test_framework/_runner.py:491-633` (project source)** — `parse_junit_xml` model implementation for `_build_parsed_run_from_reports`.
- **`pyproject.toml` lines 27-32 (project source)** — current pytest11 entry-point block; reporter adds a sibling key.
- **CPython docs `sys.__stdout__`** — un-wrapped original stream (Pitfall 7).

### Secondary (MEDIUM confidence)

- `report.user_properties` parallel to JUnit XML `<property>` children — inferred from `parse_junit_xml` reading lines 591-611 and pytest docs "Adding custom properties to test reports"; cross-verified by pytest's `record_property` fixture which writes to both.

### Tertiary (LOW confidence)

- None. All claims either verified via Context7 + project source or explicitly tagged `[ASSUMED]` in the Assumptions Log.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — only pytest required, version already pinned; xdist NOT a runtime dep.
- Architecture: HIGH — sibling-plugin pattern is established in the codebase; renderer is frozen.
- Pitfalls: HIGH — 8 pitfalls drawn directly from pytest docs and existing `parse_junit_xml` source.
- xdist coexistence: MEDIUM-HIGH — controller-forwarding documented; one smoke-test recommended to lock A3.

**Research date:** 2026-05-17
**Valid until:** 2026-06-17 (30 days; pytest 9.x and xdist are stable)
