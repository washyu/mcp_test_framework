---
phase: 14-hybrid-runner-with-domain-ui
plan: 01
subsystem: cli
tags: [cli, subprocess, pytest, junit-xml, exit-codes, typer]

# Dependency graph
requires:
  - phase: 13-config-safety-opt-in-tool-selection
    provides: "_load_config(path) resolver as the pre-flight gate (Phase 13 D-01/D-03); MCPTF_CONFIG_FILE export so the subprocess pytest sees the same YAML"
provides:
  - "src/mcp_test_framework/_runner.py module: run_pytest_subprocess + _map_exit_code + _dispatch_default_mode_or_error"
  - "cli.py:run rewritten to invoke pytest as a subprocess (no more pytest.main); --raw flag added"
  - "Tempfile JUnit XML capture in default mode; operator --junit-xml=PATH fan-out via post-subprocess shutil.copy (RUNNER-05 preserved)"
  - "Exit-code mapping per Phase 14 D-15 (pytest 5 -> 0 with stderr warning; others pass through; SIGINT propagates naturally)"
  - "tests/test_runner_subprocess.py: 18 unit tests pinning subprocess dispatch, --raw bypass, --junit-xml preservation, exit-code mapping"
affects: [14-02-junit-xml-parser, 14-03-domain-renderer, 14-04-verbosity-flags, 14-05-reporter-cleanup]

# Tech tracking
tech-stack:
  added: []  # no new deps -- stdlib subprocess + tempfile + shutil only
  patterns:
    - "Subprocess pytest dispatch (Phase 14 D-01): [sys.executable, '-m', 'pytest', ...] -- decouples wrapper from pytest plugin globals"
    - "Tempfile JUnit XML capture (Phase 14 D-02): wrapper owns its own tempfile exclusively; operator --junit-xml=PATH is a post-subprocess fan-out (NOT a second pytest --junitxml argument)"
    - "Helper promotion to avoid circular import: _build_pytest_args + _emit_operator_error moved to _runner.py with re-export shim in cli.py so existing test imports keep working"
    - "Exit-code mapping table (D-15): pytest 5 -> 0 with stderr warning; KeyboardInterrupt never caught so SIGINT propagates to 130 via Typer standalone_mode"

key-files:
  created:
    - "src/mcp_test_framework/_runner.py - subprocess pytest dispatch + tempfile JUnit + exit-code mapping + D-16 error helper"
    - "tests/test_runner_subprocess.py - 18 unit tests pinning the Phase 14 contract"
  modified:
    - "src/mcp_test_framework/cli.py - rewrote run() body to use _runner.run_pytest_subprocess on both default and --raw paths; moved _build_pytest_args + _emit_operator_error to _runner.py with re-export shim"

key-decisions:
  - "Promoted _build_pytest_args + _emit_operator_error from cli.py to _runner.py with re-export shim in cli.py to avoid the cli.py <-> _runner.py circular import the plan flagged; existing test imports from mcp_test_framework.cli keep working unchanged"
  - "Tempfile fan-out for operator --junit-xml=PATH (shutil.copy post-subprocess) instead of relying on pytest's last-occurrence rule -- this gives the wrapper an exclusive tempfile to parse in plan 14-02, while still satisfying RUNNER-05 contract that the operator path is populated"
  - "Tempfile cleanup is best-effort (try/except OSError on unlink) -- on Windows the subprocess child may hold a transient handle; never block teardown on cleanup failure"

patterns-established:
  - "Subprocess-with-tempfile + post-subprocess fan-out: the wrapper's tempfile is the canonical artifact for downstream parsing; operator paths receive a copy"
  - "Re-export shim pattern for breaking circular imports: helpers move to the upstream module, the downstream module imports + re-binds the symbol so callers don't change"

requirements-completed: [RUNNER-01, RUNNER-03, RUNNER-05, RUNNER-06]

# Metrics
duration: ~45min
completed: 2026-05-11
---

# Phase 14 Plan 01: Subprocess Pytest Spine + --raw Flag + Tempfile JUnit Summary

**Rewrote cli.py:run to invoke pytest as a child subprocess (D-01) with an internal tempfile JUnit XML capture (D-02), added --raw flag (RUNNER-03) that bypasses the wrapper but NOT the config pre-flight gate (D-11), and wired exit-code mapping per D-15 -- all behind a new src/mcp_test_framework/_runner.py module that plans 14-02..05 will extend.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-05-11 (UTC)
- **Completed:** 2026-05-11 (UTC)
- **Tasks:** 3 (all TDD, all atomic commits)
- **Files modified:** 2 production (`cli.py`, `_runner.py` created), 1 test (`test_runner_subprocess.py` created)

## Accomplishments

- **Phase 14 spine delivered.** `mcp-test-framework run` now invokes pytest as `[sys.executable, '-m', 'pytest', ...]` via `_runner.run_pytest_subprocess`, replacing the v1.1 in-process `pytest.main()` call. The wrapper process is decoupled from pytest's plugin globals -- plans 14-02..05 can extend the runner without re-introducing the coupling.
- **`--raw` escape hatch shipped (RUNNER-03).** Exposed in `--help`; bypasses the (future) domain UI renderer, the internal tempfile, and stdout/stderr capture; equivalent to `uv run pytest tests/` modulo the `_load_config` pre-flight gate (which still runs -- SAFE-03/04 cannot be bypassed via `--raw` per D-11).
- **Tempfile JUnit XML + operator-path fan-out (D-02 + RUNNER-05).** Default mode allocates an internal tempfile via `tempfile.NamedTemporaryFile(suffix='.xml', delete=False)` and passes it as `--junitxml=<tempfile>` to the child pytest. After the subprocess exits, if the operator supplied `--junit-xml=PATH`, `shutil.copy(tempfile, PATH)` populates the operator's path. The wrapper retains exclusive ownership of the tempfile for plan 14-02's parser.
- **Exit-code mapping per D-15.** `_map_exit_code(5)` returns `(0, "no tests collected")`; 0/1/2 pass through; 130 pass-through is defensive. KeyboardInterrupt is never caught -- SIGINT propagates so Typer's standalone_mode emits 130 naturally (Phase 04.1 / Phase 14 D-15 contract preserved).
- **No regressions.** All 183 unit tests under `tests/unit/` pass; all 29 non-live tests under `tests/test_reporter.py` pass. The `_build_pytest_args` + `_emit_operator_error` re-export shim in `cli.py` keeps existing `from mcp_test_framework.cli import _build_pytest_args` imports working.

## Task Commits

Each task was committed atomically (TDD: test commit + implementation commit):

1. **Task 1 RED: failing tests for subprocess runner** - `f655c85` (test)
2. **Task 1 GREEN: _runner.py with subprocess dispatch + tempfile + exit-code map** - `adc7543` (feat)
3. **Task 2 GREEN: cli.py:run delegates to _runner.run_pytest_subprocess + --raw flag** - `f9bb612` (feat)
4. **Task 1 refactor: scrub `pytest.main` docstring refs to satisfy acceptance grep** - `e5c667a` (docs)

Task 3 (test file creation) was satisfied by the Task 1 RED commit: the failing-test set already covered all behaviors Task 3 enumerates (subprocess argv shape, exit-code mapping, --raw bypass, --junit-xml preservation, CLI surface, re-export shim). No additional commit was needed -- 18 named test functions across the file, all passing under `uv run pytest tests/test_runner_subprocess.py`.

## Files Created/Modified

### Created

- **`src/mcp_test_framework/_runner.py`** (266 lines) -- new module exporting:
  - `run_pytest_subprocess(*, junit_xml, pytest_args, raw) -> (rc, tmp_path, stdout, stderr)`: spawns pytest, captures or passes through streams, handles operator junit_xml fan-out
  - `_map_exit_code(rc) -> (mapped_rc, warning)`: D-15 mapping table
  - `_dispatch_default_mode_or_error(tmp_path, exit_code, stderr) -> None`: D-16 helper -- raises `typer.Exit(2)` with a domain-tone diagnostic when pytest crashed before writing the tempfile
  - `_build_pytest_args(junit_xml, pytest_args) -> list[str]`: moved here from `cli.py`
  - `_emit_operator_error(summary, detail, next_step, *, exit_code=2)`: moved here from `cli.py`
- **`tests/test_runner_subprocess.py`** (254 lines, 18 tests):
  - 5 `_map_exit_code` regression-pin tests (0/1/2/5/130)
  - 5 `run_pytest_subprocess` argv-shape tests (sys.executable + -m + pytest; default tempfile junitxml count; raw mode no tempfile; operator junit-xml fan-out; default mode exactly one --junitxml even with operator path supplied)
  - 8 CLI-surface tests via `typer.testing.CliRunner` (--help lists --raw / --junit-xml; --help excludes --debug; _load_config preflight on both default + --raw paths; exit-code 5 -> 0 + warning; exit-code 1 pass-through; re-export shim for backward compat)

### Modified

- **`src/mcp_test_framework/cli.py`**:
  - Module docstring: replaced "pytest.main(...)" prose with Phase 14 subprocess contract
  - `_emit_operator_error` function body deleted; replaced with `from mcp_test_framework._runner import _emit_operator_error` (re-export shim)
  - `_build_pytest_args` function body deleted; replaced with `from mcp_test_framework._runner import _build_pytest_args` (re-export shim)
  - `run()` Typer command: added `--raw` flag; rewrote body to call `_runner.run_pytest_subprocess` on both paths; added try/finally for tempfile cleanup; transitional verbatim stdout/stderr emit marked `# PLAN-03 REMOVES`; removed function-local `import pytest`

## Decisions Made

1. **Helpers promoted to `_runner.py` with re-export shim in `cli.py`** (plan-locked decision, plan-line 153). The cli.py <-> _runner.py circular import the plan flagged is avoided by hosting `_build_pytest_args` and `_emit_operator_error` in `_runner.py`, and re-binding both symbols in `cli.py` via `from mcp_test_framework._runner import ...`. Existing test imports from `mcp_test_framework.cli` keep working unchanged -- the re-export is a strict superset of the old contract.
2. **Tempfile fan-out via `shutil.copy` instead of pytest last-occurrence trick** (plan-locked, plan-line 129). The wrapper passes operator junit_xml as `None` to `_build_pytest_args` so only ONE `--junitxml=<tempfile>` reaches pytest. After the subprocess returns, `shutil.copy(tempfile, operator_path)` fans out. This gives the wrapper an exclusive tempfile to parse (plan 14-02) and avoids depending on pytest's argparse last-occurrence behavior.
3. **Tempfile `delete=False` + immediate `.unlink()` of the empty placeholder** (implementation detail beyond the plan, justifiable). `NamedTemporaryFile(delete=False)` creates an empty file; the child pytest subprocess opens that path for write and replaces the contents. To make "did pytest write XML?" detectable via `.exists()` after the subprocess, the empty placeholder is unlinked immediately. On Windows this avoids a transient-handle race that would otherwise hold the file open across the subprocess boundary.
4. **`uv` is on PATH but `homelab-mcp` is not in this worktree** (environment observation, not a code decision). Tests were run with `MCPTF_CONFIG_FILE=./config-v2-worktree.yaml` pointing at a fresh v2 config so the autouse `_preflight` session fixture's check-1 (`shutil.which(config.mcp_server.command)`) passes for the test surface. The actual pytest subprocess is mocked in every test in `test_runner_subprocess.py`, so no live homelab-mcp invocation occurs.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Docstring scrub for acceptance grep] Removed remaining `pytest.main` references from `_runner.py` docstrings**
- **Found during:** Task 1 acceptance-criteria audit (post-Task-2 verification)
- **Issue:** Plan acceptance criterion `grep -n "pytest.main" src/mcp_test_framework/_runner.py returns ZERO matches`; my initial module docstring and `_build_pytest_args` docstring referenced `pytest.main()` historically. Two literal matches remained.
- **Fix:** Reworded both docstring passages to use "the in-process pytest entry point" instead of `pytest.main()`. Behavior unchanged; grep count now 0.
- **Files modified:** `src/mcp_test_framework/_runner.py` (3 lines)
- **Verification:** `grep -c "pytest.main" src/mcp_test_framework/_runner.py` returns `0`. All 18 tests still pass.
- **Committed in:** `e5c667a` (docs(14-01): scrub pytest.main references)

**2. [Rule 1 - Docstring scrub for acceptance grep] Removed `pytest.main` references from `cli.py` module docstring and inline comments**
- **Found during:** Task 2 acceptance-criteria audit
- **Issue:** Plan acceptance criterion for cli.py: `grep -n "pytest.main" src/mcp_test_framework/cli.py returns ZERO matches`; three literal matches remained in (a) module docstring describing the historical run command, (b) `_build_pytest_args` re-export comment, (c) the new `run()` docstring's contract statement.
- **Fix:** Reworded all three sites to "in-process pytest entry point" / "Phase 14 runner module" framing.
- **Files modified:** `src/mcp_test_framework/cli.py` (4 lines)
- **Verification:** `grep -c "pytest.main" src/mcp_test_framework/cli.py` returns `0`. `grep -c "_runner.run_pytest_subprocess"` returns `2` (the two call sites, no docstring noise).
- **Committed in:** `f9bb612` (part of Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1: docstring scrub to satisfy plan acceptance grep criteria; both behavior-preserving prose edits)
**Impact on plan:** Zero scope creep. Both were grep-target-only edits to satisfy the plan's "ZERO matches" acceptance gates on docstring/comment text.

## Issues Encountered

- **Worktree environment missing homelab-mcp + matching Ollama model.** The autouse session-scope `_preflight` fixture (fixtures.py:128-280) gates every `tests/test_*.py` (non-unit) suite on (1) `shutil.which(mcp_server.command)`, (2) Ollama `/api/tags` reachability + configured model installed, (3) MCP brief handshake. This worktree had a v1 `config.yaml` (rejected by Phase 13 v2 schema) so bare `Config()` fell back to defaults (`command='homelab-mcp'`, not on PATH). **Resolution:** Created `config-v2-worktree.yaml` (v2 schema, `command: uvx`, `model: qwen3:0.6b` matching the Ollama install) and set `MCPTF_CONFIG_FILE` for the test invocation. The actual subprocess.run is mocked in every test, so no live MCP/Ollama call happens during the unit tests. This worktree-config issue is documented in user memory (`project_worktree_config.md`) and is environmental, not a code defect. **The `config-v2-worktree.yaml` is a worktree-only test asset; it should NOT be committed to main.**
- **Docstring scrub was needed twice (cli.py + _runner.py) to satisfy strict `grep -n "pytest.main" returns ZERO matches` acceptance gates.** This is the cost of grep-based acceptance criteria that don't distinguish code from comments. Resolution covered above under Deviations.

## User Setup Required

None -- no external service configuration required. The `config-v2-worktree.yaml` file is a per-worktree convenience for running the test suite locally and is git-untracked; the production code path resolves config via `_load_config` exactly as in Phase 13.

## Next Phase Readiness

- **Plan 14-02 (JUnit XML parser) unblocked.** The wrapper owns an exclusive tempfile JUnit XML (Path returned from `run_pytest_subprocess`) for the parser to consume. The tempfile path flows through the try/finally cleanup block in `cli.py:run`, so plan 14-02 inserts `parsed = _runner.parse_junit_xml(tmp_xml)` between `_dispatch_default_mode_or_error` and the transitional `typer.echo(captured_stdout, ...)` block.
- **Plan 14-03 (domain renderer) unblocked.** The `PLAN-03 REMOVES` marker in `cli.py:run` tags the exact lines plan 14-03 replaces (the transitional verbatim stdout/stderr emit). The renderer hook plugs into the same try/finally.
- **Plan 14-04 (--debug / --quiet flags) unblocked.** Plan 14-04 adds `debug: bool` and `quiet: bool` Typer options to the `run()` signature; the body already has the subprocess + tempfile + (future) parse + render skeleton in place. `--debug` appends raw stdout post-render; `-q` suppresses the per-tool rows.
- **Plan 14-05 (_reporter.py deletion) unblocked.** The wrapper no longer relies on the `_reporter` pytest plugin -- the in-subprocess pytest still loads the plugin (via `tests/conftest.py:pytest_plugins`), but its terminal output is captured and discarded by the wrapper in default mode. Plan 14-05 deletes the plugin + its conftest registration + retargets reporter unit tests against XML fixtures.

**No blockers.** The phase 14 spine is in place; plans 02-05 plug into well-defined seams.

---
*Phase: 14-hybrid-runner-with-domain-ui*
*Completed: 2026-05-11*

## Self-Check: PASSED

- src/mcp_test_framework/_runner.py: FOUND
- src/mcp_test_framework/cli.py: FOUND
- tests/test_runner_subprocess.py: FOUND
- .planning/phases/14-hybrid-runner-with-domain-ui/14-01-SUMMARY.md: FOUND
- f655c85 (RED: failing tests): FOUND
- adc7543 (GREEN: _runner.py): FOUND
- f9bb612 (cli.py: subprocess + --raw): FOUND
- e5c667a (docs: pytest.main scrub): FOUND
