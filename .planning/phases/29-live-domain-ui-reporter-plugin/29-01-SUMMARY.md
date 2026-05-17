---
phase: 29-live-domain-ui-reporter-plugin
plan: 01
subsystem: testing
tags: [pytest-plugin, reporter, adapter, testreport, pytest9, junit-parity]

# Dependency graph
requires:
  - phase: 14-runner
    provides: parse_junit_xml + ParsedRun + ToolVerdict + render_domain_ui (frozen renderer surface)
  - phase: 25-rename
    provides: tests.test_code.* + tests.sdet.* dual-discovery classname prefixes (rename-shim window)
provides:
  - _build_parsed_run_from_reports(list[pytest.TestReport]) -> ParsedRun — live event-driven adapter
  - _classname_from_nodeid helper for JUnit-style classname derivation from report.nodeid
  - Module-level `import pytest` in _runner.py (was previously absent)
affects:
  - 29-02 (reporter plugin will accumulate TestReport objects and call this adapter at pytest_sessionfinish)
  - 29-03 (CLI rewire deletes the JUnit-parse callsite; live path is the canonical input adapter)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sibling-adapter colocation: live TestReport adapter sits next to JUnit adapter in _runner.py (D-01a co-location lock)"
    - "Phase-precedence bucketing (Pitfall 1): bucket reports by nodeid BEFORE aggregating to avoid 3x case counts"
    - "user_properties parity with JUnit <property> (Pitfall 4): identical failure_message formatting across both adapters"

key-files:
  created:
    - tests/framework/unit/test_runner_reports_adapter.py (322 lines, 11 tests)
  modified:
    - src/mcp_test_framework/_runner.py (+221 lines: import pytest + _classname_from_nodeid + _build_parsed_run_from_reports)

key-decisions:
  - "Phase anchor comments scrubbed from src/ to satisfy planning-ID leak gate (test_no_planning_ids_in_src); cross-references retained in plan/summary docs only."
  - "Module-level `import pytest` accepted in _runner.py (pytest is a hard project dep; no circular-import surfaced)."

patterns-established:
  - "TestReport factory helper pattern: _make_report() in tests constructs reports without running pytest, mirroring the public TestReport(...) constructor"
  - "Paired-fixture parity test: same logical run expressed as both JUnit XML and TestReport list; assert field-equality on per_tool / verdicts / totals"

requirements-completed: [REPORTER-01]

# Metrics
duration: 6min
completed: 2026-05-17
---

# Phase 29 Plan 01: Live TestReport adapter Summary

**Pure-Python adapter `_build_parsed_run_from_reports(list[pytest.TestReport]) -> ParsedRun` co-located with `parse_junit_xml` in `_runner.py`, with paired-fixture parity verified across 11 unit tests.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-05-17T19:04:37Z
- **Completed:** 2026-05-17T19:10:10Z
- **Tasks:** 2 (TDD RED + GREEN; refactor was a typing-tightening absorbed into GREEN)
- **Files modified:** 1 (`src/mcp_test_framework/_runner.py`)
- **Files created:** 1 (`tests/framework/unit/test_runner_reports_adapter.py`)

## Accomplishments

- **`_build_parsed_run_from_reports`** lands at line 663 of `_runner.py`, immediately after `parse_junit_xml` (line 492). D-01a co-location lock satisfied.
- **Phase-precedence bucketing (Pitfall 1)** — reports bucketed by `nodeid` before aggregating, eliminating the 3x case-count failure mode and the call-FAIL-overwritten-by-teardown-PASS failure mode.
- **user_properties path (Pitfall 4)** — `mcptf_error_code` + `mcptf_error_message` read from `report.user_properties`, formatted byte-identically to `parse_junit_xml`'s `<property>` child reading (`"[code] message"` when code present, bare message otherwise).
- **Scenario fall-through replicated** — classnames starting with `tests.test_code.test_` OR `tests.sdet.test_` (rename-shim parity) produce the synthetic `<group>::<row_label>` bucket key, verbatim from `parse_junit_xml:540-563`.
- **Paired-fixture parity** — `test_field_equal_to_parse_junit_xml` constructs a JUnit XML AND a TestReport sequence for the same logical run; asserts equal per_tool keys, verdicts, failure_messages, case_counts, and totals.

## Task Commits

Each task was committed atomically (TDD ordering: RED then GREEN):

1. **RED — failing adapter tests** — `e16aea2` (test)
2. **GREEN — adapter implementation + module-level pytest import** — `d4565d9` (feat)

_Note: the typing-tightening on `user_properties` value handling (object → str narrowing) was applied inline before commit; no separate refactor commit needed._

## Files Created/Modified

- `src/mcp_test_framework/_runner.py` — added `import pytest` at module-level (line 41); added `_classname_from_nodeid` helper (lines 636-655); added `_build_parsed_run_from_reports` (lines 661-882). `parse_junit_xml` body is byte-identical (shifted by 1 line due to the new import).
- `tests/framework/unit/test_runner_reports_adapter.py` — 11 unit tests covering: three-phase PASS bucketing, call-failure FAIL verdict, setup-failure FAIL verdict, teardown-failure promotion to FAIL, setup-skip with reason, user_properties code+message extraction, user_properties message-only (no code), test_code scenario fall-through, sdet legacy scenario fall-through (rename-shim), totals summing across buckets, paired-fixture parity with `parse_junit_xml`.

## Decisions Made

- **Module-level `import pytest`** in `_runner.py` (over a string-quoted annotation). Pytest is a hard project dep (`pyproject.toml`) and the CLI wrapper which imports `_runner` runs in the same Python env. No circular import surfaced; tests confirm.
- **Phase-anchor cross-references moved out of `src/` comments.** The plan's acceptance criteria required a `Phase 29 D-01` anchor comment immediately above the function. The project's `test_no_planning_ids_in_src` CI gate enforces a hard-zero policy on planning IDs in `src/` (22-CONTEXT.md D-04). The gate wins; planning anchors live in this SUMMARY and the PLAN file. The function's docstring and adjacent comment describe the role ("Live event-driven adapter colocated with parse_junit_xml") without leaking IDs.
- **`_classname_from_nodeid` is module-level (not nested).** Both file-path normalization (`os.sep` vs `/`) and the `tests.test_code.*` / `tests.sdet.*` startswith checks are isolated in one named helper, making the scenario fall-through branch trivially testable in isolation if Plan 02 surfaces an edge case.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Planning-ID leak in src/ comments**
- **Found during:** Task 1 verification (broader unit-test sweep)
- **Issue:** Plan instruction to add `# Phase 29 D-01 / D-01a / REPORTER-01:` anchor comment above the new function tripped the locked `test_no_planning_ids_in_src` CI gate (22-CONTEXT.md D-04, hard-zero policy on `(CLI|PERSONA|CODEGEN|...|SDET|...)-\d+|\bD-\d+\b` in `src/`). Same pattern as Plan 27-01's deviation memory: "Planning-ID gate takes precedence over plan's verbatim docstring instructions in src/".
- **Fix:** Scrubbed both anchor sites in `_runner.py` — the comment above the function ("Phase 29 D-01 / D-01a / REPORTER-01: Live event-driven adapter..." → "Live event-driven adapter...") and the docstring tail in `_classname_from_nodeid` ("Phase 29 / REPORTER-01" → "live event-driven path"). Cross-references retained in this SUMMARY and the PLAN file (both live under `.planning/` which the leak gate ignores).
- **Files modified:** `src/mcp_test_framework/_runner.py`
- **Verification:** `uv run pytest tests/framework/unit/test_no_planning_ids_in_src.py` — PASSED. `uv run pytest tests/framework/unit/test_runner_reports_adapter.py tests/framework/unit/test_runner_parser.py` — 41 PASSED, 0 failures.
- **Committed in:** `d4565d9` (GREEN commit; absorbed before commit)

**2. [Rule 1 - Bug] Pyright type narrowing on user_properties value**
- **Found during:** Task 1 verification (`uv run pyright src/mcp_test_framework/_runner.py`)
- **Issue:** Initial implementation wrote `code = (value or None) if isinstance(value, str) else value`; the `else value` branch returned `object` (the static type of the tuple element), which pyright flagged as not assignable to declared `str | None`.
- **Fix:** Replaced the conditional expression with an explicit isinstance/None/str ladder that always produces `str | None`.
- **Files modified:** `src/mcp_test_framework/_runner.py`
- **Verification:** `uv run pyright src/mcp_test_framework/_runner.py` — the new function is clean (2 pre-existing errors in `parse_junit_xml` lines 608/613 remain; scope-boundary rule applies — those are not Phase 29's responsibility).
- **Committed in:** `d4565d9` (GREEN commit; absorbed before commit)

---

**Total deviations:** 2 auto-fixed (1 leak-gate scrub, 1 type narrowing)
**Impact on plan:** Neither affects the runtime behavior or surface; both preserve the locked function signature, docstring tone, and acceptance behavior. The leak-gate scrub is a documented project-wide constraint (memory: project_phase_27_pivot_register_to_ini.md + Plan 27-01 deviation), not a deviation from the spirit of the plan.

## Issues Encountered

- **TDD ordering vs. plan task ordering.** The plan listed Task 1 (impl) then Task 2 (tests). The plan's Task 1 frontmatter set `tdd="true"`, which forces RED-before-GREEN per the executor's TDD execution flow. Resolved by writing the test file (Task 2's deliverable) first as the RED gate, then committing the implementation (Task 1's deliverable) as the GREEN gate. Both tasks' acceptance criteria are satisfied by the two-commit sequence.
- **Plan's `grep -n "Phase 29 D-01"` acceptance criterion** cannot be satisfied alongside the locked leak gate. Documented under deviations above; planning anchors live in `.planning/` files.

## Known Stubs

None. The adapter is complete; downstream Plan 02 (reporter plugin) wires it into `pytest_sessionfinish`.

## User Setup Required

None - no external service configuration required.

## Verification Evidence

```
$ uv run pytest tests/framework/unit/test_runner_reports_adapter.py -v
============================= 11 passed in 0.15s ==============================

$ uv run pytest tests/framework/unit/test_runner_parser.py -q
30 passed in 0.20s

$ uv run pytest tests/framework/unit/test_no_planning_ids_in_src.py -q
1 passed in 0.41s

$ uv run python -c "from mcp_test_framework._runner import _build_parsed_run_from_reports; print(_build_parsed_run_from_reports.__doc__[:80])"
Build a ParsedRun from accumulated TestReport objects (live event-driven path).
```

Pyright: 2 pre-existing errors in `parse_junit_xml` lines 608/613 (unchanged by this plan; out of scope per scope-boundary rule). The new function and its helper produce zero new pyright errors.

## Next Phase Readiness

- **Plan 29-02 (reporter plugin)** is unblocked. `_build_parsed_run_from_reports` is importable from `mcp_test_framework._runner`, accepts `list[pytest.TestReport]`, and produces a `ParsedRun` field-equal to the JUnit path. The reporter plugin can accumulate reports in `pytest_runtest_logreport` and call this adapter at `pytest_sessionfinish` without further changes to `_runner.py`.
- **Plan 29-03 (CLI rewire)** can proceed once Plan 29-02 ships; `parse_junit_xml` remains in `_runner.py` for its 50+ existing test-site consumers (D-05a audit confirmed STAY).
- **No blockers.** Open Question 3 from RESEARCH ("does the reporter need to replicate scenario fall-through?") is now answered affirmatively in code — both `tests.test_code.test_*` and `tests.sdet.test_*` prefixes route through the synthetic bucket.

## Self-Check: PASSED

- `src/mcp_test_framework/_runner.py` — exists, line 663 hosts `_build_parsed_run_from_reports`.
- `tests/framework/unit/test_runner_reports_adapter.py` — exists, 322 lines, 11 tests.
- Commit `e16aea2` — present (RED tests).
- Commit `d4565d9` — present (GREEN adapter).

---
*Phase: 29-live-domain-ui-reporter-plugin*
*Completed: 2026-05-17*
