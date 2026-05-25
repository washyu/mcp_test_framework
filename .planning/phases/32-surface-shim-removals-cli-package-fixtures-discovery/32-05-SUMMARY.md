---
phase: 32-surface-shim-removals-cli-package-fixtures-discovery
plan: 05
subsystem: testing
tags: [pytest-fixtures, shim-removal, operator-tone-error, pytest-fail, parametrize, pytester, v1.5]

# Dependency graph
requires:
  - phase: 32-04
    provides: tests/sdet/ dual-discovery strip, module-level _mcptf_formatwarning helper, sdet->test_code kwarg rename
provides:
  - Six removal-stub fixtures in _plugin.py (config / judge / target_tool / rubric_clarity / rubric_disambiguation / rubric_parameters) replacing the v1.4 warn+passthrough aliases
  - Parameter-less stub signatures (Pitfall 1) preventing prefixed-fixture session-scoped setup from running before pytest.fail fires
  - Parametrized pytester regression test pinning operator-tone three-part text + prefixed-name pointer + 'next:' line for all six aliases
  - Plugin module docstring updated from "six unprefixed deprecation aliases" to "six removal stubs"
affects: [Phase 35 SHIM-09 regression gate, future EOL planner for full-removal pass]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Parameter-less stub-raise fixture pattern (drops prefixed-fixture parameter to prevent session-scoped setup before failure)"
    - "Parametrized pytester regression test over (legacy, prefixed) alias pairs with errors=1 outcome assertion"

key-files:
  created:
    - tests/framework/unit/test_plugin_unprefixed_fixtures_removed.py
  modified:
    - src/mcp_test_framework/_plugin.py

key-decisions:
  - "Add # noqa: sdet-rename-shim markers on the six new stub def lines per the plan template (the prior fixture bodies did not carry markers; the plan's target template explicitly grandfathers the stubs through v1.5 with these markers)"
  - "Drop explicit -p mcp_test_framework._plugin from pytester subprocess invocations to avoid 'Plugin already registered' conflict with the auto-loaded pytest11 entry point (Rule 1 auto-fix; mirrors the pattern locked in tests/framework/unit/test_plugin_tests_sdet_warning.py from 32-04)"

patterns-established:
  - "Stub-raise fixture: parameter-less signature + pytest.fail(MSG, pytrace=False) inside session-scoped @pytest.fixture; future fixture removals reuse this shape"
  - "Parametrized pytester regression over alias pairs: pytest.mark.parametrize with (legacy, prefixed) tuple + ids list, errors=1 outcome, combined stdout/stderr substring assertion"

requirements-completed: [SHIM-07]

# Metrics
duration: ~10min
completed: 2026-05-25
---

# Phase 32 Plan 05: SHIM-07 Unprefixed Fixture Removal Stubs Summary

**Six unprefixed pytest fixture aliases (config/judge/target_tool/rubric_clarity/rubric_disambiguation/rubric_parameters) rewritten as parameter-less stub-raise fixtures emitting operator-tone three-part migration text pointing at the mcp_*-prefixed equivalents.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-05-25T15:24:00Z (approx — after worktree base reset)
- **Completed:** 2026-05-25T15:34:00Z
- **Tasks:** 3 (1 fixture rewrite + 1 regression test + 1 in-tree audit no-op)
- **Files modified:** 1 source + 1 test created

## Accomplishments

- All six unprefixed fixture aliases in `_plugin.py` (L433-502) now fail at fixture-resolution time via `pytest.fail(MSG, pytrace=False)` with verbatim operator-tone text naming the `mcp_*`-prefixed equivalent.
- Pitfall 1 satisfied: each stub signature drops the prefixed-fixture parameter, so the prefixed fixture's session-scoped setup (potential MCP subprocess spawn) does NOT run before the failure fires.
- Plugin module docstring updated from "six unprefixed deprecation aliases" to "six removal stubs"; comment block above the stubs (L454-467) rewritten to describe the removal-stub contract.
- Six `# noqa: sdet-rename-shim -- stub-raise; prefixed-fixture parameter dropped` markers on the new stub def lines grandfather the stubs through v1.5 per the plan template.
- New parametrized pytester regression test (`tests/framework/unit/test_plugin_unprefixed_fixtures_removed.py`) pins the post-removal contract across all six (legacy, prefixed) pairs with `assert_outcomes(errors=1)` + verbatim substring checks (summary line + prefixed name + `next:` line).
- Task 3 audit confirmed no in-tree framework self-tests still consume the unprefixed fixture names — zero renames required.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite six unprefixed fixture aliases as stub-raise fixtures** - `045c9bf` (feat)
2. **Task 2: Create parametrized pytester regression test for all six removal stubs** - `0696bfa` (test)
3. **Task 3: Audit + rename in-tree framework self-tests still consuming unprefixed names** - no commit (no-op; sweep returned zero hits)

**Plan metadata commit:** pending (this SUMMARY commit).

## Files Created/Modified

- `src/mcp_test_framework/_plugin.py` — Rewrote six fixture bodies (L454-538 region) from warn+passthrough to parameter-less stub-raise; updated module docstring L7-16; rewrote comment block L454-467 above the stubs.
- `tests/framework/unit/test_plugin_unprefixed_fixtures_removed.py` — New parametrized pytester regression test (51 lines, 6 parametrized cases).

## Decisions Made

- **Marker placement on the new stub def lines.** The plan's `<behavior>` says "Each fixture's `# noqa: sdet-rename-shim` marker on its `def` line survives (grandfathered through v1.5)" while the pre-rewrite bodies did NOT carry such markers on the def lines (the existing 6 markers in `_plugin.py` are inside the 32-04 `tests/sdet/` warn-on-presence block). The plan's Step B target template explicitly includes `# noqa: sdet-rename-shim -- stub-raise; prefixed-fixture parameter dropped` on the stub def line, so the template's marker placement is what shipped — six markers added on the new stub def lines.
- **Drop `-p mcp_test_framework._plugin` from pytester invocation.** Initial draft of the regression test included an explicit `-p mcp_test_framework._plugin` in the sandbox's `addopts`. Running it triggered `ValueError: Plugin already registered under a different name: mcp_test_framework=...` because the plugin auto-loads via the project's `[project.entry-points.pytest11]`. Dropping the explicit `-p` mirrors the pattern already locked in `tests/framework/unit/test_plugin_tests_sdet_warning.py` (32-04 sister test).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plugin double-registration in pytester sandbox**
- **Found during:** Task 2 (regression test first run)
- **Issue:** Test sandbox `addopts = "-p mcp_test_framework._plugin"` conflicted with the auto-loaded pytest11 entry point, raising `ValueError: Plugin already registered under a different name: mcp_test_framework=...` before any test ran.
- **Fix:** Dropped the explicit `-p` flag from the synthesized `pyproject.toml`'s `addopts`; the plugin auto-loads via entry-points in the subprocess. Added an inline comment citing the conflict + pointing to the 32-04 sister-test precedent.
- **Files modified:** `tests/framework/unit/test_plugin_unprefixed_fixtures_removed.py`
- **Verification:** `uv run pytest tests/framework/unit/test_plugin_unprefixed_fixtures_removed.py -x` → 6 passed in 13.59s.
- **Committed in:** `0696bfa` (Task 2 commit — fix applied before initial commit, so single commit contains the working test).

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary correction to test scaffolding; matches the convention already established by the 32-04 sister test. No scope creep.

## Issues Encountered

- The post-Task-1 marker count in `_plugin.py` did not match the plan's `<done>` criterion phrasing ("the six fixture `def` line markers are unchanged"). Pre-rewrite `grep -c "sdet-rename-shim" src/mcp_test_framework/_plugin.py` returned 6 markers, ALL inside the 32-04 `tests/sdet/` warn-on-presence block (L77, L293, L296, L301, L303, L308) — none on the fixture def lines. Post-rewrite count is 12 (6 existing + 6 new stub def line markers). The plan's Step B template explicitly added markers on the stub def lines, so the net `+6` is the intended outcome.

## Threat Flags

None — Plan touches existing pytest fixture-resolution surface only; the new stub-raise behaviour is strictly less privileged than the prior warn+passthrough (no MCP subprocess spawn before failure, no return value flow). Threat register entries T-32-14..16 (information disclosure, tampering, denial-of-service) all marked `accept` per plan; no new surface introduced.

## Self-Check

Verification of claimed artefacts (run 2026-05-25T15:34Z):

- `src/mcp_test_framework/_plugin.py` — FOUND (modified)
- `tests/framework/unit/test_plugin_unprefixed_fixtures_removed.py` — FOUND (created)
- Commit `045c9bf` (feat: rewrite six unprefixed fixture aliases) — FOUND in git log
- Commit `0696bfa` (test: add parametrized pytester regression test) — FOUND in git log
- Inline Python verify (Pitfall 1 + verbatim text) — PASS ("PASS: all six stub-raise fixtures present + parameter-less + verbatim-text")
- `uv run pytest tests/framework/unit/test_plugin_unprefixed_fixtures_removed.py -x` — PASS (6 passed)
- `uv run pytest tests/framework/unit/test_no_planning_ids_in_src.py -x` — PASS (1 passed)
- `uv run pytest tests/framework/ --tb=short` — PASS (700 passed, 2 skipped, 18 deselected, 1 xfailed, 2 warnings)
- Banned tokens (`Phase 32` / `Plan 32-05` / `SHIM-07` / `D-06`) in `src/mcp_test_framework/_plugin.py` — NONE FOUND
- Task 3 in-tree audit sweep — ZERO MATCHES (no framework self-tests consume the unprefixed fixture names)

## Self-Check: PASSED

## Next Phase Readiness

- v1.5 Phase 32 wave 5 complete for SHIM-07. The six removal stubs survive as the operator-facing migration surface; the regression test pins their wording.
- Phase 35 SHIM-09 (regression gate capstone) can now assert zero residual unprefixed fixture aliases in the v1.4 deprecation surface; the new regression test stands as the post-removal invariant.
- No blockers introduced for downstream waves in Phase 32 or subsequent v1.5 phases.

---
*Phase: 32-surface-shim-removals-cli-package-fixtures-discovery*
*Plan: 05*
*Completed: 2026-05-25*
