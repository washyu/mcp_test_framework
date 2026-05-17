---
phase: 29-live-domain-ui-reporter-plugin
plan: 02
subsystem: testing
tags: [pytest-plugin, reporter, entry-point, xdist, tty, additive-output]

# Dependency graph
requires:
  - phase: 29-live-domain-ui-reporter-plugin
    plan: 01
    provides: _build_parsed_run_from_reports adapter + module-level pytest import in _runner.py
  - phase: 26-packaging
    provides: [project.entry-points.pytest11] block in pyproject.toml (first key already declared)
provides:
  - mcp_test_framework._reporter pytest11 plugin module (6 hooks)
  - mcp_test_framework_reporter pytest11 entry-point key
  - --mcp-domain-ui option (auto|force|off) with TTY-aware auto-resolution
  - Live event-driven domain UI emission alongside pytest-native output
affects:
  - 29-03 (CLI rewire: cli.py will pass --mcp-domain-ui=force and delete the JUnit-parse postprocessing branch)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sibling pytest11 entry-point keys: two plugins under one distribution, independently disable-able via `-p no:KEY`"
    - "Un-wrapped stdout TTY probe (Pitfall 7): cache `sys.__stdout__` at module load, probe `_ORIGINAL_STDOUT.isatty()` regardless of capture state"
    - "xdist controller-only emission via duck-typed `hasattr(config, 'workerinput')` probe (no pytest-xdist import)"
    - "Module-level state singleton for hooks lacking config backref (TestReport.session does not exist; `_STATE` global is the canonical workaround)"
    - "Additive coexistence (D-02): no `pytest_terminal_summary` hook, no `sys.stdout` reassignment"

key-files:
  created:
    - src/mcp_test_framework/_reporter.py (215 lines, 6 pytest hooks)
    - tests/framework/test_reporter_plugin.py (361 lines, 10 integration tests)
  modified:
    - pyproject.toml (+5 lines: second pytest11 entry-point key)
    - src/mcp_test_framework/_runner.py (deviation fix: added 1 noqa line inside Plan 01's _build_parsed_run_from_reports docstring + rephrased 1 SDET reference + 1 trailing noqa)
    - tests/framework/test_runner_subprocess.py (deviation fix: inverted Phase 14 reporter-no-longer-importable gate to positive hook-shape assertion)

key-decisions:
  - "Module docstring uses 'imports of any specific MCP server under test' (not the literal SUT name) to avoid tripping the project's banned-name lint and to keep the framework-primitive constraint clearly stated."
  - "Configured choices=['auto','force','off'] verbatim per D-04; nargs='?' + const='auto' + default='off' gives the three documented states without a separate --force flag."
  - "Module-level `_STATE` singleton (per Pitfall 5) over `config._mcp_reporter_state` stash: TestReport.session attribute does not exist, so pytest_runtest_logreport has no config backref; one pytest session per process makes the singleton safe; pytest_unconfigure tears it down."
  - "Subprocess-pytest test pattern (Analog B from PATTERNS.md) for all 10 integration tests — isolates plugin state from the outer framework session."

patterns-established:
  - "Banner-presence tests write a minimal config.yaml + [tool.pytest.ini_options].mcp_config_file ini + a parametrized contract-style test in the tmp_path payload (Option A path from the plan); banner-absence tests omit both."
  - "Parametrized payloads `@pytest.mark.parametrize('tool', ['mytool', 'othertool'])` produce `[mytool]` / `[othertool]` nodeids that `_extract_tool_name` (Plan 01 helper) recognizes — so the per-tool render path fires without needing an MCP server spawn."

requirements-completed: [REPORTER-02]

# Metrics
duration: ~9min
completed: 2026-05-17
---

# Phase 29 Plan 02: Live domain-UI reporter plugin Summary

**Second pytest11 entry-point key plus the `_reporter.py` plugin module that wires live `pytest_runtest_logreport` events through Plan 01's adapter into the existing domain UI renderer — additive to pytest-native output, default OFF, xdist-controller-only, TTY-aware auto-resolution via `sys.__stdout__`.**

## Performance

- **Duration:** ~9 min
- **Started:** 2026-05-17T19:14:39Z
- **Completed:** 2026-05-17T19:23:55Z
- **Tasks:** 3 (plugin module, entry-point declaration, integration tests)
- **Files created:** 2 (`_reporter.py`, `test_reporter_plugin.py`)
- **Files modified:** 3 (`pyproject.toml`, `_runner.py` deviation, `test_runner_subprocess.py` deviation)

## Reporter Module Hook Layout

`src/mcp_test_framework/_reporter.py` (215 lines):

| Hook | Lines | Responsibility |
|------|-------|----------------|
| `pytest_addoption` | 75-104 | Declare `--mcp-domain-ui` with `action='store', nargs='?', const='auto', default='off', choices=['auto','force','off']` |
| `pytest_configure` | 107-131 | xdist worker no-op (workerinput probe); resolve mode; `sys.__stdout__.isatty()` TTY check; initialize `_STATE` |
| `pytest_collection_finish` | 134-175 | Worker no-op + state-presence gate + config-presence graceful-degrade; build `RenderContext` from session.items keyword-filtered to `mcp_contract`; call `_render_pre_run_digest` |
| `pytest_runtest_logreport` | 178-188 | Defensive state check; append to accumulator |
| `pytest_sessionfinish` | 191-211 | Call `_build_parsed_run_from_reports` + `render_domain_ui`; degraded-mode `RenderContext` if header skipped |
| `pytest_unconfigure` | 214-217 | Reset module-level `_STATE` for session-clean teardown |

Module-level state:
- `_ORIGINAL_STDOUT = sys.__stdout__` (line 48) — cached at module load per Pitfall 7
- `_STATE: _ReporterState | None = None` (line 66) — single-instance accumulator

## pyproject.toml Diff

```diff
 [project.entry-points.pytest11]
 # Phase 26 D-09 / PACK-01: pytest auto-loads this plugin via the pytest11
 # entry-point group. Operators no longer need `pytest_plugins=[...]` in
 # their conftest. Module body is created in Plan 26-02; this declaration
 # only references it (the wheel-shape gate in 26-04 verifies both halves).
 mcp_test_framework = "mcp_test_framework._plugin"
+# Phase 29 D-04 / REPORTER-02: second pytest11 key for the live domain-UI
+# reporter. Independently disable-able via
+# `pytest -p no:mcp_test_framework_reporter` while keeping the contract
+# fixtures registered under the key above.
+mcp_test_framework_reporter = "mcp_test_framework._reporter"
```

After `uv sync --reinstall-package mcp-contracts`, `importlib.metadata.entry_points(group='pytest11')` shows both names; `pytest --help` displays `--mcp-domain-ui=[{auto,force,off}]`.

## Integration Tests

`tests/framework/test_reporter_plugin.py` — **10 tests, 9 passed, 1 skipped (xdist gated)**:

| # | Test | Status | What it pins |
|---|------|--------|--------------|
| 1 | `test_mcp_domain_ui_option_appears_in_help` | PASS | Option visible in `pytest --help` after plugin auto-load |
| 2 | `test_default_off_no_domain_ui` | PASS | No flag → no banner; reporter's pytest_configure short-circuits at `choice == "off"` |
| 3 | `test_force_emits_domain_ui_in_piped_stdout` | PASS | `=force` emits banner + `Result:` + `mytool` row in piped (non-TTY) stdout via full Option A path |
| 4 | `test_bare_flag_auto_resolves_to_off_when_no_tty` | PASS | Bare flag → `auto` → `sys.__stdout__.isatty()=False` → silent off |
| 5 | `test_explicit_off_value` | PASS | `=off` matches default-off |
| 6 | `test_bogus_value_rejected_by_choices` | PASS | argparse `choices=` enforcement (Pitfall 6) |
| 7 | `test_p_no_disables_reporter_and_removes_option` | PASS | `-p no:mcp_test_framework_reporter --mcp-domain-ui=force` → unrecognized argument |
| 8 | `test_additive_coexistence_pytest_native_output_present` | PASS | D-02: `PASSED` + `FAILED` + nodeid + banner all present under `--mcp-domain-ui=force -v` |
| 9 | `test_force_emits_per_tool_rows_and_summary` | PASS | `mytool` (PASS row) + `othertool` (FAIL row) + `Result:` summary all rendered |
| 10 | `test_xdist_master_only_emission` | SKIPPED | `pytest.importorskip("xdist")` — pytest-xdist not installed in this env; assumption A3 (controller-only banner count==1) not exercised here |

**Assumption A3 (xdist controller ordering):** **Not verified** in this plan because pytest-xdist is not installed in the dev environment. The test is in place and will activate the moment `pytest-xdist` is added as a dev dep. The runtime path is defensive regardless: the duck-typed `hasattr(config, "workerinput")` probe early-returns on workers without importing xdist, so the worker no-op contract holds independent of whether the smoke test runs.

## Payload Path Chosen

**Option A (config.yaml + `mcp_config_file` ini + parametrized payload).** The contract plugin's `pytest_configure` stashes `_mcp_contracts_config` and the reporter renders the header end-to-end. The empty `tools: {}` short-circuits the MCP handshake in `_plugin.py:pytest_collection` at the empty-allowlist branch, so no MCP server is spawned. Worked first try — no fallback to Option B needed.

The `_MINIMAL_CONFIG_YAML` includes:
- `version: 2` (Config requires it)
- `mcp_server.command: "true"` (never invoked; defaults work too)
- `test_code.generated_root: "generated"` (required field with no default in TestCodeConfig)
- `tools: {}` (empty allowlist short-circuit)

## Task Commits

1. **Task 1** — `0388b61` (feat): create `_reporter.py` with 6 pytest hooks
2. **Task 2** — `3f65eb6` (feat): declare `mcp_test_framework_reporter` entry-point in pyproject.toml
3. **Task 3** — `4971ce2` (test): subprocess integration tests + deviation fixes

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Phase 14 reporter-no-longer-importable gate inverted Phase 29's intent**
- **Found during:** Task 3 verification (full framework test sweep)
- **Issue:** `tests/framework/test_runner_subprocess.py::test_reporter_module_no_longer_importable` was a Phase 14 Plan 05 regression pin that hard-asserted `_reporter` module would never re-appear. Phase 29 by design re-introduces `_reporter` with a different surface (live event-driven reporter, not the v1.1 design that was deleted).
- **Fix:** Renamed to `test_reporter_module_importable_with_live_event_hooks`; inverted from "must not exist" to "must exist and expose the 5 locked pytest hooks". Updated docstring to record the supersession and explain why the prior gate was inverted by design.
- **Files modified:** `tests/framework/test_runner_subprocess.py`
- **Verification:** `uv run pytest tests/framework/test_runner_subprocess.py` — 21 passed.
- **Committed in:** `4971ce2`

**2. [Rule 1 - Bug] RENAME-06 sdet-terminology leak gate failure introduced by Plan 01**
- **Found during:** Task 3 verification (full framework test sweep)
- **Issue:** `tests/framework/test_sdet_rename_leak_gate.py::test_no_residual_match_in_src_python_strings[sdet_terminology-...]` flagged two new lines in `_runner.py` added by Plan 01:
  1. The `_build_parsed_run_from_reports` docstring (string Constant spanning lines 663-717) contained `tests.sdet.test_` and `SDET-authored scenarios` without any noqa marker inside the docstring range.
  2. The comment on line 735 `# tests/sdet/ is the v1.4 dual-discovery legacy path. Both share` lacked the trailing `# noqa: sdet-rename-shim`.
  Plan 01's SUMMARY documented a planning-ID leak fix but missed the sdet-terminology gate.
- **Fix:**
  - Added a noqa-marker line inside the docstring: `(noqa: sdet-rename-shim covers the legacy classname-prefix mention.)` — the gate's `_range_is_noqa` check finds this line within the string-Constant range and excludes the whole node.
  - Rephrased `SDET-authored scenarios` to `scenario tests` (terminology cleanup, not a shim).
  - Appended `# noqa: sdet-rename-shim` to the line-735 comment to match the surrounding pattern.
- **Files modified:** `src/mcp_test_framework/_runner.py`
- **Verification:** `uv run pytest tests/framework/test_sdet_rename_leak_gate.py` — 4 passed.
- **Committed in:** `4971ce2`

**3. [Plan-spec adjustment] Subprocess-pytest `--rootdir` flag added**
- **Found during:** Task 3 implementation
- **Issue:** Without `--rootdir`, the subprocess pytest walks up the directory tree and finds the framework's outer `pyproject.toml`, leaking the outer `addopts = "-m 'not live_homelab and not live_ollama'"` and the framework's `mcp_config_file = "./config.test.yaml"` into the test payload. Tests intermittently failed with confusing-but-correct framework-config errors.
- **Fix:** Added `"--rootdir", str(cwd)` to every `subprocess.run` argv so the embedded pytest treats the tmp_path as the rootdir and ignores any parent pyproject.toml. Matches the pattern in `tests/framework/test_phase27_spike_synthetic_module.py`.
- **Files modified:** `tests/framework/test_reporter_plugin.py` (new file; convention adopted before any test was run)
- **Verification:** All 9 non-skipped tests pass.
- **Committed in:** `4971ce2`

---

**Total deviations:** 3 auto-fixed (2 leak/gate scrubs from Plan 01's blast radius, 1 in-flight payload-isolation refinement that's standard subprocess-pytest hygiene)
**Impact on plan:** None of these change the locked surface of `_reporter.py` or the integration-test coverage. The two Plan 01 inherited gate failures were strictly out of Plan 02's stated scope but were directly affected by the same module (`_reporter` / `_runner`) Plan 02 touches; the scope-boundary rule permits inclusion under Rule 1 since they would have blocked the final verification anyway.

## Issues Encountered

- **TestReport.session attribute does not exist.** Pitfall 5 documents the workaround (module-level `_STATE` singleton), which is what the implementation uses. No surprise during execution.
- **Default-payload test choice for absence-assertions.** Initially considered `_write_payload_with_config` for the absence path too, but that would force the contract plugin's MCP handshake gate to be exercised under unusual conditions. Settled on the documented Option A split: `_with_config` for banner-presence tests; `_no_config` for banner-absence tests.

## Known Stubs

None. The reporter plugin is complete; downstream Plan 03 (CLI rewire) consumes the `--mcp-domain-ui=force` argv path.

## User Setup Required

None — the reporter activates automatically on the next `uv sync` (entry-point auto-load).

## Verification Evidence

```
$ uv run python -c "from mcp_test_framework import _reporter; print([n for n in dir(_reporter) if n.startswith('pytest_')])"
['pytest_addoption', 'pytest_collection_finish', 'pytest_configure', 'pytest_runtest_logreport', 'pytest_sessionfinish', 'pytest_unconfigure']

$ uv run python -c "from importlib.metadata import entry_points; eps = entry_points(group='pytest11'); names = sorted(e.name for e in eps if 'mcp_test_framework' in e.name); print(names)"
['mcp_test_framework', 'mcp_test_framework_reporter']

$ uv run pytest --help 2>&1 | grep -- "--mcp-domain-ui"
  --mcp-domain-ui=[{auto,force,off}]

$ uv run pytest tests/framework/test_reporter_plugin.py -v
============================ 9 passed, 1 skipped in 21.91s ============================

$ uv run pyright src/mcp_test_framework/_reporter.py
0 errors, 0 warnings, 0 informations

$ uv run pytest tests/framework -q --ignore=tests/framework/test_runner_live_smoke.py
657 passed, 2 skipped, 14 deselected, 1 xfailed, 45 warnings in 49.40s
```

## Next Plan Readiness

- **Plan 29-03 (CLI rewire)** is unblocked. The reporter is auto-loaded; `mcp-contracts run` can now append `--mcp-domain-ui=force` to its pytest argv and delete the `cli.py:912-980` JUnit-parse postprocessing branch. The locked surface tests (banner present under `=force`; banner absent under default; per-tool rows render) ensure the CLI rewire has a stable target.
- **Open Question 1 (xdist controller-only ordering, A3)** is documented as not-yet-verified; the test scaffold exists and will exercise A3 the moment pytest-xdist is added as a dev dep.

## Self-Check: PASSED

- `src/mcp_test_framework/_reporter.py` — exists (215 lines, 6 pytest hooks confirmed via `dir()`).
- `tests/framework/test_reporter_plugin.py` — exists (361 lines, 10 test functions).
- `pyproject.toml` — entry-point block contains both `mcp_test_framework` and `mcp_test_framework_reporter`.
- Commit `0388b61` — present (feat: _reporter.py).
- Commit `3f65eb6` — present (feat: pyproject.toml entry-point).
- Commit `4971ce2` — present (test: integration tests + deviations).
- All 9 non-skipped integration tests pass; xdist test skips gracefully.
- Existing 657 framework tests still pass.

---
*Phase: 29-live-domain-ui-reporter-plugin*
*Completed: 2026-05-17*
