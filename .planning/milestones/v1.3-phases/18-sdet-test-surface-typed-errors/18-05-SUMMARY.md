---
phase: 18-sdet-test-surface-typed-errors
plan: 05
subsystem: testing
tags: [typer, cli, pytest, sdet, --sdet, wrapper-owned-flag]

# Dependency graph
requires:
  - phase: 14-runner-domain-ui
    provides: _build_pytest_args + run_pytest_subprocess subprocess seam
  - phase: 15-test-surface-split
    provides: with_framework=True additive pattern (tests/contract + tests/framework)
  - phase: 16-reporter-ux
    provides: --explain wrapper-owned-flag (D-07) precedent, inherited verbatim
provides:
  - --sdet Typer flag on `run` command
  - sdet kwarg on _build_pytest_args + run_pytest_subprocess (D-04 SWAP, D-05 additive)
  - Pre-run plumbing point for Plan 18-06 (scenario-aware digest dispatch)
affects:
  - 18-06 (XML parser + scenario-aware pre-run digest both inherit sdet kwarg)
  - 18-07 (tests/sdet/ scope becomes addressable via this flag)
  - 18-08 (full D-04/D-05 composition-matrix test suite)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wrapper-owned flag: --sdet consumed by Typer layer; literal string never reaches pytest argv (Phase 16 D-07 inherit)"
    - "Discovery-scope SWAP (D-04): --sdet replaces tests/contract with tests/sdet; not additive"
    - "Composition rule (D-05): --with-framework remains ALWAYS additive on top of whichever operator-surface scope is active"

key-files:
  created:
    - tests/framework/unit/test_runner_sdet_kwarg.py
    - tests/framework/unit/test_sdet_cli.py
  modified:
    - src/mcp_test_framework/_runner.py
    - src/mcp_test_framework/cli.py

key-decisions:
  - "sdet kwarg position: after with_framework — logical grouping by purpose (discovery-scope flags adjacent)"
  - "Default False on both kwargs preserves Phase 16 default-path byte-identically (existing test_runner_explain.py suite is the regression guard)"
  - "Help text taken VERBATIM from CONTEXT.md / PATTERNS.md (D-04/D-05 composition matrix) — no rewording at the executor seam"

patterns-established:
  - "Pattern: Wrapper-owned flag — Typer layer consumes the bool; runner layer reads it to alter discovery paths only; flag literal never propagates to subprocess argv. Inherited from Phase 16 D-07 (--explain)."

requirements-completed: [SDET-04]
# Note: SDET-01 (tests/sdet/ discovery scope) and SDET-02 (mcp_session/tool() fixtures)
# are PARTIALLY UNBLOCKED by this plan but not COMPLETED — they require Plans 18-06/07
# to land the renderer + tests/sdet/ directory + fixtures. Only SDET-04 (CLI flag) closes here.

# Metrics
duration: 18min
completed: 2026-05-13
---

# Phase 18 Plan 05: --sdet CLI Flag Summary

**--sdet Typer flag on `run` that SWAPS the operator-surface discovery scope from tests/contract/ to tests/sdet/, composes with --with-framework additively, and never leaks to pytest argv (Phase 16 D-07 wrapper-owned pattern inherited)**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-05-13 (worktree-agent-abdbb2609b1288f3f)
- **Completed:** 2026-05-13
- **Tasks:** 2 (both TDD)
- **Files modified:** 2 (src/mcp_test_framework/_runner.py, src/mcp_test_framework/cli.py)
- **Files created:** 2 (tests/framework/unit/test_runner_sdet_kwarg.py, tests/framework/unit/test_sdet_cli.py)
- **Tests added:** 14 (9 runner-kwarg + 5 CLI)

## Accomplishments

- `_build_pytest_args(sdet=True)` returns argv with `tests/sdet` as the first path; `tests/contract` is absent (D-04 SWAP, not additive)
- `_build_pytest_args(sdet=True, with_framework=True)` returns `["tests/sdet", "tests/framework", ...]` (D-05 framework remains additive on top of either scope)
- `_build_pytest_args(sdet=False, ...)` byte-identical to Phase 16 default-path behavior (zero-diff regression preserved)
- `run_pytest_subprocess` signature gains `sdet: bool = False` and forwards to `_build_pytest_args(sdet=sdet)` at both internal call sites (raw and default modes)
- `--sdet` registered as a Typer boolean option on `run`, immediately after `--with-framework`; help text verbatim from CONTEXT.md
- Both `run_pytest_subprocess` call sites in `cli.py:run` (the `--raw` branch and the domain-UI branch) thread `sdet=sdet`
- `--sdet` string is consumed by the wrapper and never appears in argv handed to pytest (Phase 16 D-07 wrapper-owned-flag invariant pinned by tests)
- `mcp-test-framework run --help` lists `--sdet` with its composition matrix
- Full regression: `tests/framework/unit/test_runner_explain.py` (11/11), `tests/framework/test_runner_subprocess.py` (26/26), `tests/framework/unit/test_runner_pre_run_digest.py` (14/14), `tests/framework/unit/test_runner_parser.py` (24/24) all pass

## Task Commits

Each task was committed atomically using the TDD red-green pattern:

1. **Task 1 RED: failing tests for _runner sdet kwarg** - `01da85d` (test)
2. **Task 1 GREEN: implement sdet kwarg in _build_pytest_args + run_pytest_subprocess** - `17ca1ca` (feat)
3. **Task 2 RED: failing CLI tests for --sdet Typer flag** - `cef6fbe` (test)
4. **Task 2 GREEN: register --sdet on `run` + thread to both call sites** - `86034e8` (feat)

No REFACTOR commits needed — the GREEN implementations are already at minimal/clean shape.

## Files Created/Modified

- `src/mcp_test_framework/_runner.py` - Added `sdet: bool = False` kwarg to `_build_pytest_args` and `run_pytest_subprocess`; new `if sdet:` branch in the discovery-path block (D-04 SWAP); preserved `with_framework` additive logic (D-05); both internal call sites in `run_pytest_subprocess` forward `sdet=sdet`.
- `src/mcp_test_framework/cli.py` - Added `sdet: bool = typer.Option(...)` parameter to `run` command (after `with_framework`); help text verbatim from CONTEXT.md / PATTERNS.md; threaded `sdet=sdet` into BOTH `run_pytest_subprocess` call sites (the `--raw` branch at line 486 and the domain-UI branch at line 541).
- `tests/framework/unit/test_runner_sdet_kwarg.py` - 9 tests pinning: signature contract (default False on both functions), D-04 SWAP semantics, D-05 additive semantics, --sdet-literal-never-in-argv invariant, default-path zero-diff regression, run_pytest_subprocess forwards sdet to _build_pytest_args.
- `tests/framework/unit/test_sdet_cli.py` - 5 tests pinning: --sdet in `run --help`, composition mention with --with-framework, --raw branch argv contains tests/sdet (not tests/contract), --raw + --sdet + --with-framework argv contains both paths, default-path argv preserved when --sdet absent.

## Decisions Made

- **sdet kwarg position: after with_framework, not alphabetical.** Discovery-scope flags grouped by purpose. Improves call-site readability over alphabetical ordering. Plan explicitly specified this position.
- **Help text VERBATIM from CONTEXT.md.** Re-wording would require a second source of truth and drift; the planner-locked help string lands word-for-word in the Typer Option.
- **Defaults False on both functions.** Phase 16 default-path output must be byte-identical to pre-plan behavior; the existing test_runner_explain.py suite acts as the regression guard.

## Deviations from Plan

None — plan executed exactly as written.

The plan was tightly scoped (two files, two functions, one Typer option, two call-site updates) and pre-validated the interface shape via `<interfaces>` block + PATTERNS.md analogs. No bugs surfaced, no missing critical functionality, no blockers, no architectural reframing.

**Total deviations:** 0
**Impact on plan:** None — clean execution.

## Issues Encountered

**Environment setup (not a deviation; worktree-specific):**
- The worktree initially lacked `config.yaml` (it's `.gitignore`d). Copied from parent's `config-v2-worktree.yaml` per the project memory note "Worktree config setup". Set `MCPTF_CONFIG_FILE` for test runs (the conftest's session-level preflight resolves `Config()` via the env-var fallback when no local `./config.yaml` is autodiscovered). Once configured, all 51 targeted tests pass.

**Pre-existing pyright noise (out of scope, not introduced by this plan):**
- `src/mcp_test_framework/_runner.py` reports 2 `reportOptionalMemberAccess` errors at lines 512 and 515 (the `elem` variable in `parse_junit_xml`). Pre-existing — outside the modified region.
- `src/mcp_test_framework/cli.py` reports 9 errors (mostly `Config | None` access). All pre-existing — none reference `sdet` or the new option block.

**Pre-existing test failures (out of scope, not introduced by this plan):**
- `tests/framework/unit/test_migration_doc.py` (4 tests), `tests/framework/unit/test_cli_errors.py::test_cli_errors_static_call_sites_no_banned_tokens`, `tests/framework/unit/test_doc_scrub.py::test_doc_invocations_consistently_pair_with_config[path0]` — all fail looking for `tests/docs/MIGRATION-v1-to-v2.md` which doesn't exist in this worktree. Verified pre-existing by `git stash` of my changes and re-running: same 6 failures on a clean base. Likely a cwd / worktree-environment artifact unrelated to Plan 18-05.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

**Plan 18-06 (XML parser + scenario-aware pre-run digest) inherits:**
- The `sdet: bool = False` kwarg on `run_pytest_subprocess` is the entry seam for Plan 18-06's pre-run digest dispatch: when `sdet=True` the wrapper should call `_render_scenario_pre_run_digest(...)` instead of `_render_pre_run_digest(...)` (CONTEXT.md D-06).
- The CLI `sdet` parameter is wired and ready; Plan 18-06 only adds the dispatch shape around `_render_pre_run_digest` and a new XML-parse branch for `<property>` element extraction (D-09).

**Plan 18-07 (tests/sdet/ directory + fixtures) inherits:**
- Once `tests/sdet/` exists with pytest-discoverable scenario modules, `mcp-test-framework run --sdet` will collect them automatically — no further wiring needed in cli.py or _runner.py beyond what landed here.

**Plan 18-08 (full D-04/D-05 composition-matrix tests) inherits:**
- The 14 tests added here pin the SCOPE-PATH layer (argv shape). Plan 18-08 will extend with full integration through the digest + renderer surface once Plan 18-06 ships.

**No blockers or concerns.**

## Self-Check: PASSED

Files verified to exist on disk:
- FOUND: src/mcp_test_framework/_runner.py
- FOUND: src/mcp_test_framework/cli.py
- FOUND: tests/framework/unit/test_runner_sdet_kwarg.py
- FOUND: tests/framework/unit/test_sdet_cli.py
- FOUND: .planning/phases/18-sdet-test-surface-typed-errors/18-05-SUMMARY.md

Commits verified in `git log`:
- FOUND: 01da85d (test: failing tests for sdet kwarg)
- FOUND: 17ca1ca (feat: sdet kwarg in _runner)
- FOUND: cef6fbe (test: failing CLI tests for --sdet)
- FOUND: 86034e8 (feat: --sdet Typer flag + threading)

Verification commands (all OK at completion):
- `_build_pytest_args(sdet=True/False, with_framework=True/False)` matrix per plan: OK
- `CliRunner().invoke(app, ['run', '--help']).output` contains '--sdet': OK
- `tests/framework/unit/test_runner_sdet_kwarg.py` (9/9 pass)
- `tests/framework/unit/test_sdet_cli.py` (5/5 pass)
- `tests/framework/unit/test_runner_explain.py` (11/11 pass — Phase 16 default-path zero-diff regression guard)
- `tests/framework/test_runner_subprocess.py` (26/26 pass — Phase 14+16 subprocess contract guard)

---
*Phase: 18-sdet-test-surface-typed-errors*
*Plan: 05*
*Completed: 2026-05-13*
