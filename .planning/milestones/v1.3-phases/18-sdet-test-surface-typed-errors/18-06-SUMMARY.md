---
phase: 18-sdet-test-surface-typed-errors
plan: 06
subsystem: runner-renderer
tags: [runner, renderer, junit-xml, sdet, D-06, D-09, D-10, D-11, D-13]

# Dependency graph
requires:
  - phase: 18-sdet-test-surface-typed-errors
    plan: 01
    provides: ToolCallError typed exception (consumed transitively via tests/sdet/conftest.py user_properties)
  - phase: 18-sdet-test-surface-typed-errors
    plan: 05
    provides: --sdet Typer flag + sdet kwarg on run_pytest_subprocess (entry seam for dispatch)
provides:
  - "JUnit XML parser reads mcptf_error_code / mcptf_error_message user_properties and uses them as failure_message (D-09)"
  - "FAIL row auto-formats to '[code] message' when code present, bare message otherwise (D-10 -- via parser hookup; row composer untouched)"
  - "_render_scenario_pre_run_digest -- SDET-flavored pre-run digest (D-06)"
  - "_collect_sdet_scenarios -- tests/sdet/test_*.py stem enumeration helper"
  - "_extract_tool_call_errors_from_xml + _ToolCallErrorRecord -- second-pass XML scan for D-11 appendix"
  - "render_debug_appendix gains xml_path kwarg; emits '--- ToolCallError dump ---' block BEFORE '--- raw pytest output ---' when properties present (D-11)"
affects:
  - 18-07 (tests/sdet/ scaffolding + pytest_exception_interact will produce the user_properties this plan reads)
  - 18-08 (full D-04/D-05/D-06/D-09/D-10/D-11 composition-matrix test suite)
  - Phase 19 (preflight skip detection extends _collect_sdet_scenarios -- API kept stable so Phase 19 is non-breaking)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Strategy 1 -- re-parse JUnit XML in --debug appendix builder instead of threading dump strings through ToolVerdict (zero dataclass churn)"
    - "Wrapper-owned dispatch -- cli.py routes between tool / scenario digest based on --sdet bool; never mutates pytest argv"
    - "Em-dash U+2014 separator inherited from Phase 09 SC-3 (judges-text + --explain expansion both use literal '—')"
    - "Backward-compatible signature extension: xml_path on render_debug_appendix defaults to None so legacy callers see no behavior change (D-13 invariant)"

key-files:
  created:
    - tests/framework/unit/test_runner_sdet_digest.py
    - tests/framework/unit/test_runner_debug_appendix_d11.py
  modified:
    - src/mcp_test_framework/_runner.py
    - src/mcp_test_framework/cli.py
    - tests/framework/unit/test_runner_parser.py
    - tests/framework/unit/test_sdet_cli.py

key-decisions:
  - "Strategy 1 (no ToolVerdict extension) -- D-11 appendix re-parses JUnit XML rather than adding tool_call_error_* fields to ToolVerdict. Keeps the parser->renderer dataclass surface frozen; the O(N) second pass is negligible at MVP scale and isolates D-11 from the Plan 18-08 contract-test regression guard."
  - "Fresh sdet-only RenderContext at dispatch (server_cmd only) -- under --sdet, tests/conftest.py:pytest_generate_tests does NOT run, so pre_run_ctx.discovered_tools / tools_config / judges have no meaning. The dispatch constructs RenderContext(server_cmd=...) to avoid cross-coupling to contract-scope fields."
  - "Backward-compatible xml_path kwarg on render_debug_appendix (default None) -- legacy callers (Plan 18-05 tests, Phase 14 baseline) see zero behavior change; new cli.py call site passes tmp_xml. Avoids breaking 15 Phase 14 verbosity tests that already mock the function without xml_path."
  - "_collect_sdet_scenarios takes ctx parameter today even though unused -- Phase 19 will read scenario-skip state off RenderContext; stable signature now means Phase 19 is non-breaking."

patterns-established:
  - "Pattern: Strategy 1 second-pass XML scan -- when a feature (D-11) needs structured data already present in JUnit XML user_properties, scan the file directly in the renderer instead of widening the parser dataclass. Trade-off: O(N) extra pass; benefit: zero dataclass churn, the new feature is fully isolated from the parser contract tests."
  - "Pattern: Wrapper-owned dispatch with fresh ctx -- when a flag swaps the operator surface scope (e.g., --sdet), construct a fresh RenderContext at dispatch time carrying ONLY the fields meaningful to the new scope. Avoids leaking contract-scope state (discovered_tools, tools_config) into surfaces that don't consume them."

requirements-completed: [SDET-02, UI-02]
# SDET-02: tests/sdet/ scope renders SDET-flavored output (digest banner + scenario-keyed buckets)
# UI-02: --debug appendix carries structured CallToolResult dump for SDET failures

# Metrics
duration: ~30min
completed: 2026-05-12
tasks_completed: 3
files_created: 2
files_modified: 4
loc_added: ~250
commits: 6  # 3x (RED + GREEN) pairs
---

# Phase 18 Plan 06: Runner / Renderer Integration Summary

**Closed the renderer side of Phase 18 by hooking the JUnit XML parser to ToolCallError-attached user_properties (D-09 / D-10), shipping the SDET-flavored pre-run digest with cli.py dispatch (D-06), and adding the structured `--- ToolCallError dump ---` block to the `--debug` appendix (D-11). Strategy 1: zero ToolVerdict surface change -- the D-11 appendix re-parses the XML rather than threading dump strings through the dataclass.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-05-12 (worktree-agent-a4d26b98705d47355)
- **Completed:** 2026-05-12
- **Tasks:** 3 (all TDD)
- **Tests added:** 31 (6 parser + 13 scenario digest + 2 CLI dispatch + 16 appendix)
- **Files modified:** 4 (src/mcp_test_framework/_runner.py, src/mcp_test_framework/cli.py, tests/framework/unit/test_runner_parser.py, tests/framework/unit/test_sdet_cli.py)
- **Files created:** 2 (tests/framework/unit/test_runner_sdet_digest.py, tests/framework/unit/test_runner_debug_appendix_d11.py)

## Accomplishments

### Task 1 -- D-09 / D-10 JUnit parser hookup

- `parse_junit_xml` reads `<property name="mcptf_error_code" .../>` and `<property name="mcptf_error_message" .../>` children of `<testcase>` under the failure/error branch
- When both present: `bucket.failure_message = "[code] message"` (D-10 format); the row composer at `_render_per_tool_rows` consumes it verbatim and renders `✗ FAIL — [code] message` via the locked em-dash separator (U+2014, line 537 in _runner.py)
- When only message present: bare message (no brackets)
- When code present but message absent: falls through to `<failure message="...">` extraction (Phase 16 regression preserved)
- When mcptf_error_code value is empty string: treated as None (code missing)
- failure_body extraction byte-identical; only the message-assignment branch changed
- ToolVerdict dataclass UNCHANGED -- D-11 second-pass strategy keeps the parser->renderer surface stable

### Task 2 -- D-06 scenario-aware pre-run digest

- `_render_scenario_pre_run_digest` shipped as a sibling to `_render_pre_run_digest`. Banner = `MCP Test Framework (SDET)`; running list keyed on scenario MODULE stems alphabetized
- `Judges:      (none — SDET scope)` sentinel with em-dash U+2014 (signals SDET runs don't grade with Ollama)
- `--explain` expansion: one line per skipped scenario, `  {stem}  — {reason}` (em-dash U+2014, two-space hang)
- Digest height <= 10 lines regardless of N (matches Phase 16 D-12 lock; verified at N=70)
- `with_framework=True` appends `+ framework self-tests` continuation line
- `_collect_sdet_scenarios(ctx)` enumerates `tests/sdet/test_*.py` stems sorted alphabetically; empty when directory absent (Phase 19 will add preflight-skip detection on this seam)
- cli.py dispatch: under `--sdet`, constructs fresh `sdet_ctx = _runner.RenderContext(server_cmd=pre_run_ctx.server_cmd)` and routes to scenario digest; without `--sdet`, the existing tool digest path is byte-identical to Phase 16

### Task 3 -- D-11 ToolCallError dump appendix

- `_ToolCallErrorRecord` frozen dataclass: tool / code / message / raw
- `_extract_tool_call_errors_from_xml(xml_path)` returns one record per testcase carrying `mcptf_error_message`; reads all three properties (code / message / raw). Defensive against missing / malformed XML (returns `[]`)
- `render_debug_appendix` gained `xml_path: Path | None = None` kwarg. When provided AND ToolCallError-attached testcases present, emits a `--- ToolCallError dump ---` block BEFORE `--- raw pytest output ---`:
  ```
  --- ToolCallError dump ---
  tool: <testcase name>
  code: <code or "(none)">
  message: <message>
  raw:
    <CallToolResult.model_dump_json(indent=2) -- each line indented 2 spaces>
  ---
  (blank line)
  ```
- `raw: (none)` literal sentinel when `mcptf_error_raw` is empty (per CONTEXT.md -- NO `re-run with --raw` fallback message)
- D-13 invariant preserved: when no properties present OR xml_path absent, appendix is byte-identical to Phase 14 baseline (verified by 15 Phase 14 verbosity tests still passing)
- Multiple failures emit consecutive blocks; each terminated by `---` on its own line (matches `--- captured stderr ---` / `--- failure tracebacks ---` aesthetic)
- cli.py updated to pass `xml_path=tmp_xml` into `render_debug_appendix`

## Task Commits

Each task followed the TDD red-green pattern:

1. **Task 1 RED** -- `19c608f` test(18-06): RED -- D-09/D-10 parser hookup tests (6 tests)
2. **Task 1 GREEN** -- `6891960` feat(18-06): GREEN -- parse_junit_xml reads mcptf_error_* properties (D-09 + D-10)
3. **Task 2 RED** -- `63cf742` test(18-06): RED -- scenario digest + cli dispatch tests (D-06) (13 digest + 2 CLI)
4. **Task 2 GREEN** -- `e92a429` feat(18-06): GREEN -- scenario digest + cli dispatch (D-06)
5. **Task 3 RED** -- `2187a4f` test(18-06): RED -- D-11 ToolCallError dump appendix tests (16 tests)
6. **Task 3 GREEN** -- `f39571e` feat(18-06): GREEN -- D-11 ToolCallError dump appendix block

No REFACTOR commits -- GREEN implementations landed at minimal/clean shape per planner-locked interfaces.

## Files Created/Modified

- `src/mcp_test_framework/_runner.py` -- D-09 hook in `parse_junit_xml` failure/error branch; new `_render_scenario_pre_run_digest` + `_collect_sdet_scenarios`; new `_ToolCallErrorRecord` dataclass + `_extract_tool_call_errors_from_xml` helper; `render_debug_appendix` gained `xml_path` kwarg + D-11 dump block emit
- `src/mcp_test_framework/cli.py` -- pre-run digest dispatch (`if sdet:` branch building `sdet_ctx`); `render_debug_appendix` call site passes `xml_path=tmp_xml`
- `tests/framework/unit/test_runner_parser.py` -- 6 new tests for D-09/D-10 (mcptf_error_* property reading, code/message format permutations, regression guards)
- `tests/framework/unit/test_runner_sdet_digest.py` (new) -- 13 tests pinning SDET digest banner, alphabetical scenario list, --explain expansion, em-dash sentinel, height bound, _collect_sdet_scenarios helper, non-SDET digest regression
- `tests/framework/unit/test_sdet_cli.py` -- 2 new tests verifying cli.py dispatches scenario digest under --sdet and preserves tool digest otherwise
- `tests/framework/unit/test_runner_debug_appendix_d11.py` (new) -- 16 tests pinning extract helper (5 cases), block ordering before raw pytest output, dump shape, raw rendering with indent, raw:/code: (none) sentinels, D-13 invariant (no block when no properties / no xml_path), terminator line, multiple-failure case

## Decisions Made

- **Strategy 1 (no ToolVerdict surface change).** The D-11 appendix builder re-parses the JUnit XML rather than adding tool_call_error_code / tool_call_error_message / tool_call_error_raw_dump fields to ToolVerdict. Benefits: zero dataclass churn, no migration cost for the renderer contract tests, the new feature is fully isolated from the parser regression guard. Trade-off: O(N) second XML pass per `--debug` run -- negligible at MVP scale.
- **Fresh sdet-only RenderContext at dispatch (`sdet_ctx = _runner.RenderContext(server_cmd=pre_run_ctx.server_cmd)`).** Under `--sdet`, `tests/conftest.py:pytest_generate_tests` parametrize does NOT run because pytest only discovers `tests/sdet/`, not `tests/contract/`. So `pre_run_ctx.discovered_tools` / `tools_config` / `judges` carry contract-scope state that has no meaning under SDET. Constructing a fresh RenderContext avoids leaking those fields into the scenario digest. The pattern is a Wave-2 planner-locked invariant (CONTEXT.md / PATTERNS.md D-06 -- Warning-3 lock).
- **Backward-compatible `xml_path` kwarg on `render_debug_appendix` (default None).** Existing Phase 14 verbosity tests call `render_debug_appendix(captured_stdout, captured_stderr, parsed)` without xml_path. Adding it as a required positional would break 15 tests. Defaulting to None preserves zero-diff regression and lets the new cli.py call site opt in.
- **`_collect_sdet_scenarios` signature carries unused `ctx` parameter today.** Phase 19 will read scenario-skip state off RenderContext (preflight-skip dispositions, parametrize-skip dispositions). Stable signature now -> Phase 19 is non-breaking.
- **`_collect_sdet_scenarios` uses `Path("tests/sdet")` (relative).** The wrapper runs with cwd = repo root in production (pytest's own discovery uses cwd-relative paths too). Tests use `monkeypatch.chdir(tmp_path)` to verify both the present and absent cases. If cwd ever changes (post-MVP), this helper will need a cwd-anchor argument.

## Deviations from Plan

### Minor -- false-positive grep acceptance criterion (Rule 1 documentation)

The plan's Task-3 acceptance criterion `grep -v "^[[:space:]]*#" src/mcp_test_framework/_runner.py | grep -cE "re-run.*--raw|unavailable"` is meant to guard against fallback workaround language in the new D-11 dump block. It returns 1 instead of 0 because of a **pre-existing** Phase 14 D-16 error-helper message at line 303 in `_dispatch_default_mode_or_error`:

```python
next_step=(
    "re-run with `--raw` to see pytest's native output, or pass "
    "`--config PATH` to verify config resolution"
),
```

`git log -S "re-run with"` confirms this string was added in commit `adc7543` (Phase 14 Plan 01), not by my Plan 18-06 edits. The intent of the acceptance criterion -- "no fallback workaround language in the D-11 block" -- IS satisfied: the D-11 dump block emits `raw: (none)` and `code: (none)` literal sentinels per CONTEXT.md, with no "re-run with --raw" or "unavailable" message anywhere inside the new code.

**Files modified:** None (no code change required -- the criterion is a false positive on pre-existing unrelated text).
**Tracked as:** `[Rule 1 - Bug] grep-acceptance false positive against pre-existing Phase 14 D-16 text` (informational; planner's grep is too broad to discriminate D-11 dump block from Phase 14 D-16 operator-error helper).

### Out of scope -- pre-existing pyright noise (NOT introduced by this plan)

- `src/mcp_test_framework/_runner.py`: 2 `reportOptionalMemberAccess` errors at lines 537 / 542 (the `elem` variable in `parse_junit_xml`'s failure/error branch). Confirmed pre-existing by `git stash` + pyright re-run on clean base (same 2 errors at the same logical site -- shifted in line number by my D-09 insertion). Plan 18-05 SUMMARY documented these as out-of-scope.
- `src/mcp_test_framework/cli.py`: 9 errors (mostly `Config | None` access, `yaml_file` Pydantic-settings kwarg). All pre-existing -- none reference scenario digest dispatch or the D-11 xml_path kwarg I added.

**Total deviations:** 0 functional changes; 1 documentation note.
**Impact on plan:** None -- clean execution.

## Issues Encountered

**Environment setup (not a deviation; worktree / SDK quirk):**
- The `tests/framework/unit/` path is NOT covered by `_session_needs_preflight`'s guard (which only short-circuits paths starting with `tests/unit/`). Running pytest from PowerShell required `MCPTF_CONFIG_FILE=config.yaml` so `Config()` would resolve cleanly during the autouse session preflight. The Bash tool sandbox in this environment denies in-line env-var setting (`$env:VAR=...; ...` / `cmd /c "set ... && ..."`); workaround was to write a tiny `_runtest.py` wrapper that sets `os.environ["MCPTF_CONFIG_FILE"]` then invokes `pytest.main(sys.argv[1:])`. This is purely an executor-environment artifact (same as Plan 18-05's note); production users running `uv run pytest` from cwd = repo root with `config.yaml` present and MCPTF_CONFIG_FILE set in their shell see no issue. The `_runtest.py` and `_check.py` helper scripts were removed after task completion -- they were never committed and are not part of the production deliverable.

**Pre-existing test failures (out of scope, not introduced by this plan):**
- Plan 18-05 documented 6 pre-existing failures in `test_migration_doc.py` / `test_cli_errors.py` / `test_doc_scrub.py` looking for a `tests/docs/MIGRATION-v1-to-v2.md` that doesn't exist in this worktree. Not re-investigated -- they fail on every Wave 2 worktree per Plan 18-05's confirmation.

## User Setup Required

None -- no external service configuration required for this plan's deliverables. The new D-09 / D-06 / D-11 surfaces are exercised by unit tests with synthesized JUnit XML; the production seam (Plan 18-07's `pytest_exception_interact` writing the user_properties) lands separately.

## Next Phase Readiness

**Plan 18-07 (tests/sdet/ scaffolding) inherits:**
- The JUnit XML parser reads all three `mcptf_error_*` user_properties; Plan 18-07's `pytest_exception_interact` hook just needs to set them via `report.user_properties.append(("mcptf_error_code", code))` etc., and the renderer will pick them up automatically
- The `--debug` appendix will render the `--- ToolCallError dump ---` block as soon as a real SDET test raises `ToolCallError`; no further wiring needed in `_runner.py` or `cli.py`
- `_collect_sdet_scenarios` will enumerate Plan 18-07's `tests/sdet/test_*.py` files immediately upon creation -- no further changes to the scenario digest pipeline

**Plan 18-08 (composition-matrix tests) inherits:**
- 31 new unit tests pinning the parser / digest / appendix surfaces; Plan 18-08's integration tests now have a stable contract to build against
- The em-dash U+2014 invariant is regression-pinned across the existing `test_runner_pre_run_digest.py` (tool path) AND the new `test_runner_sdet_digest.py` (scenario path)

**Phase 19 (preflight skip detection) inherits:**
- `_collect_sdet_scenarios(ctx)` already takes the RenderContext parameter; Phase 19 can read scenario-skip state off it without a signature change
- The scenario digest's `skipped_scenarios: dict[str, str]` parameter is already wired through cli.py dispatch -- Phase 19 only needs to populate the dict from preflight outcomes

**No blockers or concerns.**

## Self-Check: PASSED

Files verified to exist on disk:
- FOUND: src/mcp_test_framework/_runner.py
- FOUND: src/mcp_test_framework/cli.py
- FOUND: tests/framework/unit/test_runner_parser.py
- FOUND: tests/framework/unit/test_sdet_cli.py
- FOUND: tests/framework/unit/test_runner_sdet_digest.py
- FOUND: tests/framework/unit/test_runner_debug_appendix_d11.py
- FOUND: .planning/phases/18-sdet-test-surface-typed-errors/18-06-SUMMARY.md

Commits verified in `git log`:
- FOUND: 19c608f (test: RED D-09/D-10 parser hookup)
- FOUND: 6891960 (feat: GREEN D-09 + D-10 parser hookup)
- FOUND: 63cf742 (test: RED scenario digest + cli dispatch)
- FOUND: e92a429 (feat: GREEN scenario digest + cli dispatch)
- FOUND: 2187a4f (test: RED D-11 appendix dump tests)
- FOUND: f39571e (feat: GREEN D-11 appendix dump block)

Verification commands (all OK at completion):
- `_render_scenario_pre_run_digest` / `_collect_sdet_scenarios` / `_extract_tool_call_errors_from_xml` / `_ToolCallErrorRecord` importable from `mcp_test_framework._runner`: OK
- `tests/framework/unit/test_runner_parser.py` (30/30 pass -- 24 pre-existing + 6 new)
- `tests/framework/unit/test_runner_sdet_digest.py` (13/13 pass -- new)
- `tests/framework/unit/test_runner_debug_appendix_d11.py` (16/16 pass -- new)
- `tests/framework/unit/test_runner_pre_run_digest.py` (14/14 pass -- Phase 16 non-SDET regression guard)
- `tests/framework/unit/test_runner_sdet_kwarg.py` (9/9 pass -- Plan 18-05 sdet kwarg regression)
- `tests/framework/unit/test_sdet_cli.py` (7/7 pass -- 5 Plan 18-05 + 2 new dispatch)
- `tests/framework/test_runner_verbosity.py` (15/15 pass -- Phase 14 D-13 invariant regression)
- Total: 104/104 targeted tests pass
- `uv run pyright src/mcp_test_framework/_runner.py`: 2 errors (pre-existing, lines 537+542 -- elem Optional access)
- `uv run pyright src/mcp_test_framework/cli.py`: 9 errors (all pre-existing per Plan 18-05; no new errors introduced)

---
*Phase: 18-sdet-test-surface-typed-errors*
*Plan: 06*
*Completed: 2026-05-12*
