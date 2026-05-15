---
phase: 18-sdet-test-surface-typed-errors
plan: 08
subsystem: framework-self-tests
tags: [framework-self-tests, sdet, unit-tests, regression-pinning, D-01..D-11]

# Dependency graph
requires:
  - phase: 18-sdet-test-surface-typed-errors
    plan: 01
    provides: "ToolCallError + _extract_code_message -- pinned by test_tool_call_error.py"
  - phase: 18-sdet-test-surface-typed-errors
    plan: 02
    provides: "_ACTIVE_CLIENT slot + .call() wire body -- pinned by test_tool_factory.py (already updated by 18-02)"
  - phase: 18-sdet-test-surface-typed-errors
    plan: 03
    provides: "mcp_session fixture -- already pinned by test_sdet_fixtures.py shipped under 18-03"
  - phase: 18-sdet-test-surface-typed-errors
    plan: 04
    provides: "Public surface __all__ -- pinned by TestPublicSurface in test_sdet_fixtures.py"
  - phase: 18-sdet-test-surface-typed-errors
    plan: 05
    provides: "--sdet CLI flag + sdet kwarg -- pinned by test_sdet_cli.py composition matrix"
  - phase: 18-sdet-test-surface-typed-errors
    plan: 06
    provides: "Parser hookup + scenario digest + appendix builder -- pinned by test_sdet_renderer.py"
  - phase: 18-sdet-test-surface-typed-errors
    plan: 07
    provides: "tests/sdet/ scope + conftest hook -- already pinned by test_sdet_conftest_hook.py under 18-07"
provides:
  - "tests/framework/unit/test_tool_call_error.py -- D-07 + D-08 pinning (23 tests)"
  - "tests/framework/unit/test_sdet_fixtures.py TestPublicSurface -- Plan 18-04 __all__ contract (5 tests)"
  - "tests/framework/unit/test_sdet_cli.py extended -- D-04/D-05 composition matrix (3 new tests)"
  - "tests/framework/unit/test_sdet_renderer.py -- D-06/D-09/D-10/D-11 integration (19 tests)"
affects:
  - Phase 19 (STATE): scenarios author against a regression-pinned SDET surface
  - Phase 20 (PREFLIGHT): requires_homelab marker can be added without fearing surface drift
  - Phase 21 (DOC-SDET): canonical surface is grep-verified -- README copy can quote it verbatim

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sibling-module test convention: test_tool_call_error.py mirrors test_tool_response.py's pure-sync, no-fixture style for plain-data exception pinning"
    - "Integration-level renderer testing: test_sdet_renderer.py drives the full ToolCallError -> JUnit XML -> parser -> appendix pipeline with inline-synthesized XML + xml.sax.saxutils.quoteattr for attribute serialization"
    - "Round-trip pinning: model_dump_json -> XML attribute -> _extract_tool_call_errors_from_xml -> json.loads -> dict-schema assertion (covers the entire mcptf_error_raw lifecycle)"

key-files:
  created:
    - tests/framework/unit/test_tool_call_error.py
    - tests/framework/unit/test_sdet_renderer.py
  modified:
    - tests/framework/unit/test_sdet_fixtures.py
    - tests/framework/unit/test_sdet_cli.py

key-decisions:
  - "Task 5 (test_tool_factory.py update) was a no-op -- Plan 18-02 already deleted the NotImplementedError test and added test_call_raises_runtime_error_when_no_active_client + _ACTIVE_CLIENT state-reset. All Task 5 acceptance criteria satisfied by 18-02's earlier work (commit 0cec347)."
  - "test_sdet_renderer.py is complementary to (not duplicative of) test_runner_parser.py / test_runner_sdet_digest.py / test_runner_debug_appendix_d11.py. The pre-existing files pin unit-level shape; the new file pins the integration pipeline. Composition: separate test classes per decision (TestD09JunitPropertyHookup, TestD10FailRowFormat, TestD06ScenarioDigest, TestD11AppendixBlock, TestD11RawRoundTrip)."
  - "test_sdet_fixtures.py and test_sdet_cli.py were EXTENDED (not replaced) -- the pre-existing tests from Plans 18-03 / 18-05 / 18-06 stayed untouched; only TestPublicSurface and three new composition-matrix tests were appended."
  - "The indented-JSON grep gate in test_appendix_emits_indented_json_when_raw_nonempty uses startswith('    \"') (4 spaces) -- not 2 -- because model_dump_json(indent=2) already adds its own 2-space indent inside the object, and render_debug_appendix adds another 2-space prefix on top. The combined left margin is 4 spaces before the next-level key opening quote. Pinned with explanatory comment."

patterns-established:
  - "Pattern: Round-trip test for JUnit-XML-attribute-serialized payloads. When a feature emits structured data as a JUnit XML user_property and consumes it later via a second-pass scanner, write at least one test that: (1) constructs the real source object, (2) serializes through the exact production path, (3) writes the value into <property value={quoteattr(...)}/>, (4) parses via the production extractor, (5) deserializes back to the original schema, (6) asserts on the recovered structure. This is the test_calltool_result_dump_survives_junit_cycle template."
  - "Pattern: Pin the literal sentinel in both the unit-level builder and the end-to-end production code path. test_appendix_emits_none_sentinel_when_raw_empty pins 'raw: (none)' against a mirrored inline emit; test_appendix_sentinel_via_full_pipeline pins the same literal through the actual render_debug_appendix call. Drift in either direction breaks one of them."

requirements-completed: [SDET-01, SDET-02, SDET-03, SDET-04, UI-02]
# SDET-01..04 fully closed by Phase 18 (this plan adds the last regression-guard layer)
# UI-02 fully closed by Phase 18 (this plan pins the FAIL row + appendix integration)

# Metrics
duration: ~25 min
completed: 2026-05-13
tasks_completed: 4   # Tasks 1-4; Task 5 was already done by Plan 18-02
files_created: 2     # test_tool_call_error.py, test_sdet_renderer.py
files_modified: 2    # test_sdet_fixtures.py, test_sdet_cli.py
tests_added: 50      # 23 + 5 + 3 + 19 = 50 new tests in this plan
loc_added: ~1000
commits: 4           # one per task; Task 5 had no commit (no changes needed)
---

# Phase 18 Plan 08: Framework Self-Tests Summary

**Pinned every Phase 18 decision (D-01 through D-11, plus Plan 18-04's `__all__` contract) with framework self-tests under `tests/framework/unit/`. Four-file deliverable: two new files (`test_tool_call_error.py`, `test_sdet_renderer.py`) and two extended files (`test_sdet_fixtures.py`, `test_sdet_cli.py`). Task 5 (update `test_tool_factory.py`) was a no-op because Plan 18-02 had already replaced the `NotImplementedError` test with the new `_ACTIVE_CLIENT`-based contract.**

This is Wave 5 of Phase 18 — the regression-pinning layer that locks the seven prior plans' contracts as drift-detection guards. All 50 new tests pass; 111 pre-existing Phase 14/16/17 + Plans 18-01..18-07 regression tests still pass.

## D-01..D-11 Coverage Matrix

| Decision | Description | Pinned by | Tests |
|----------|-------------|-----------|-------|
| **D-01** | `mcp_session` is the SDET alias for `mcp_client` (same loop-scope, name-dep) | `test_sdet_fixtures.py::test_mcp_session_is_pytest_asyncio_session_scoped_fixture` + `test_mcp_session_signature_depends_on_mcp_client` | 2 |
| **D-02** | 5-step registry-activation flow around yield; sync mutations; teardown restores prior state | `test_sdet_fixtures.py::test_mcp_session_activates_registry_on_entry` + `test_mcp_session_restores_prior_state_on_teardown` | 2 |
| **D-03** | `ModuleNotFoundError` → `_pytest_exit_operator_tone(returncode=2)` with four signal phrases | `test_sdet_fixtures.py::test_mcp_session_fail_loud_on_missing_generated_module` | 1 |
| **D-04** | `--sdet` SWAPS discovery scope from `tests/contract` to `tests/sdet` | `test_sdet_cli.py::test_run_raw_sdet_argv_has_tests_sdet` + `test_run_default_no_sdet_raw_argv_has_tests_contract` + `test_runner_sdet_kwarg.py` (Plan 18-05's 9 kwarg tests) | 11+ |
| **D-05** | `--with-framework` is ADDITIVE on top of either scope; `--sdet` is wrapper-owned (never reaches argv) | `test_sdet_cli.py::test_run_raw_sdet_with_framework_argv_has_both` + `test_run_with_framework_only_argv_has_contract_and_framework` + `test_run_sdet_q_argv_has_tests_sdet` | 3 |
| **D-06** | Scenario-aware pre-run digest banner / alphabetical / em-dash / framework breadcrumb / height ≤ 10 | `test_sdet_renderer.py::TestD06ScenarioDigest` (5 tests) + `test_runner_sdet_digest.py` (13 unit-level) | 18 |
| **D-07** | `ToolCallError` plain Exception (NOT Pydantic) with `[code] message` format symmetry with renderer | `test_tool_call_error.py::TestToolCallErrorShape` (7 tests) | 7 |
| **D-08** | Strict heuristic chain for `_extract_code_message`; only `code` + `message` keys recognized; non-string code coerced via `str()` | `test_tool_call_error.py::TestExtractCodeMessage` (16 tests) | 16 |
| **D-09** | `parse_junit_xml` reads `mcptf_error_code` / `mcptf_error_message` user_properties → overrides `<failure message=...>` | `test_sdet_renderer.py::TestD09JunitPropertyHookup` (4 tests) + `test_runner_parser.py` (Plan 18-06's 6) | 10 |
| **D-10** | FAIL row format: `✗ FAIL — [code] message` (em-dash U+2014; brackets only when code present) | `test_sdet_renderer.py::TestD10FailRowFormat` (2 tests) | 2 |
| **D-11** | `--debug` appendix `--- ToolCallError dump ---` block; structured CallToolResult dump round-trip via `mcptf_error_raw` property; `raw: (none)` sentinel; D-13 invariant | `test_sdet_renderer.py::TestD11AppendixBlock` (3) + `TestD11RawRoundTrip` (5) + `test_runner_debug_appendix_d11.py` (Plan 18-06's 16) | 24 |

Plus Plan **18-04's `__all__` contract** (canonical four-symbol public surface): pinned by `test_sdet_fixtures.py::TestPublicSurface` (5 tests).

Every Plan in Phase 18 (18-01..18-07) now has at least one regression-pinning test in `tests/framework/unit/`:

| Plan | Pinned by |
|------|-----------|
| 18-01 | `test_tool_call_error.py` (23 tests; new this plan) |
| 18-02 | `test_tool_factory.py` (12 tests; updated under 18-02 directly) |
| 18-03 | `test_sdet_fixtures.py` (7 D-01/D-02/D-03 tests; shipped under 18-03) |
| 18-04 | `test_sdet_fixtures.py::TestPublicSurface` (5 tests; new this plan) |
| 18-05 | `test_sdet_cli.py` (10 tests after this plan's +3; original 7 from Plans 18-05/06) + `test_runner_sdet_kwarg.py` (9 tests; Plan 18-05) |
| 18-06 | `test_runner_parser.py` D-09/D-10 cases (Plan 18-06) + `test_runner_sdet_digest.py` (13; Plan 18-06) + `test_runner_debug_appendix_d11.py` (16; Plan 18-06) + `test_sdet_renderer.py` (19 integration; new this plan) |
| 18-07 | `test_sdet_conftest_hook.py` (9 tests; Plan 18-07) + `tests/sdet/test_basic_call.py` (2 end-to-end; Plan 18-07) |

## What Was Built

### `tests/framework/unit/test_tool_call_error.py` (new, 23 tests)

Sibling-module style matching `test_tool_response.py`: pure-sync, no fixtures, no MCP wire. Two test classes:

- **`TestToolCallErrorShape` (7 tests)** — D-07: `args[0]` / `str()` produces `[code] message` when code present, bare message otherwise; `isinstance(e, Exception)` True; `not hasattr(e, "model_dump")`; `.tool` / `.code` / `.message` / `.raw` populated; constructor is keyword-only.
- **`TestExtractCodeMessage` (16 tests)** — D-08 heuristic chain per step:
  - Step 1 (structuredContent dict): basic, str-coerce, missing-message fall-through, non-string-message fall-through, message-only-no-code
  - Step 2 (first TextContent JSON): basic, non-dict-list, invalid-JSON, break-after-first
  - Step 3 (concat fallback): plain, multi-text, Pitfall-7 mixed-content (Image/Audio skipped), empty
  - Strict key set: no `errorCode` / `detail` recognition; no `reason` synonym; no recursive walk into nested dicts

### `tests/framework/unit/test_sdet_fixtures.py` (extended, +5 tests → 12 total)

Pre-existing 7 D-01/D-02/D-03 tests (shipped under Plan 18-03) untouched. Appended `TestPublicSurface` class pinning Plan 18-04's barrel-export contract:

- `test_canonical_imports_resolve`: the four SDET symbols (`ToolCallError`, `ToolResponse`, `mcp_session`, `tool`) import from `mcp_test_framework.sdet`
- `test_all_lists_exact_four_names`: `set(__all__) == {ToolCallError, ToolResponse, mcp_session, tool}`
- `test_all_is_alphabetical`: stable order on the public list
- `test_internal_symbols_not_re_exported`: `_extract_code_message`, `_REGISTRIES`, `_ACTIVE_SLUG`, `_ACTIVE_CLIENT`, `ToolWrapper`, `server_slug` stay internal
- `test_tool_call_error_is_plain_exception`: re-export points at Plan 18-01's typed exception (sanity)

### `tests/framework/unit/test_sdet_cli.py` (extended, +3 tests → 10 total)

Pre-existing 7 tests (5 from Plan 18-05, 2 from Plan 18-06) untouched. Added three composition-matrix tests:

- `test_run_default_no_sdet_raw_argv_has_tests_contract`: default-path baseline (Phase 16 zero-diff regression)
- `test_run_with_framework_only_argv_has_contract_and_framework`: D-05 additive baseline (`--with-framework` alone → contract + framework, no sdet)
- `test_run_sdet_q_argv_has_tests_sdet`: documents the wrapper-owned vs pass-through asymmetry (`--sdet` is wrapper-only, `-q` flows to pytest argv)

### `tests/framework/unit/test_sdet_renderer.py` (new, 19 tests)

Integration-level companion to `test_runner_parser.py` / `test_runner_sdet_digest.py` / `test_runner_debug_appendix_d11.py`. Five test classes drive the full `ToolCallError → JUnit XML → parser → renderer → appendix` pipeline:

- **`TestD09JunitPropertyHookup` (4 tests)** — `mcptf_error_code` + `mcptf_error_message` properties override `<failure message=...>`; Phase 16 regression preserved without properties; bare-message and empty-code edge cases.
- **`TestD10FailRowFormat` (2 tests)** — bracketed-code message renders as `✗ FAIL — [code] message` (em-dash U+2014); bare-message case has no brackets after em-dash.
- **`TestD06ScenarioDigest` (5 tests)** — alphabetical running order; em-dash `--explain` expansion; SDET-scope judges sentinel; `--with-framework` breadcrumb; digest height ≤ 10 lines at N=70.
- **`TestD11AppendixBlock` (3 tests)** — `_extract_tool_call_errors_from_xml` returns records with `tool`/`code`/`message`; D-13 invariant (empty list when no properties); `code=None` when only message present.
- **`TestD11RawRoundTrip` (5 tests)** — the full pipeline pin:
  - Construct real `ToolCallError(raw=CallToolResult)`, serialize via `model_dump_json(indent=2)`, round-trip through `<property name="mcptf_error_raw" value={quoteattr(dump)}/>`, `_extract_tool_call_errors_from_xml`, `json.loads` back, verify recovered dict has `isError`/`content`/`structuredContent` keys.
  - Empty `mcptf_error_raw` → `record.raw == ""`.
  - Non-empty raw + `render_debug_appendix` → `"isError"` substring present in output (JSON-shape grep gate); indented JSON line check.
  - Empty raw + appendix builder → literal `raw: (none)` sentinel; NO `unavailable` / `--raw` fallback language.
  - End-to-end through `render_debug_appendix` to prove sentinel survives the production code path.

### `tests/framework/unit/test_tool_factory.py` (already updated — Task 5 no-op)

Plan 18-02 had already deleted the obsolete `test_call_raises_not_implemented_with_phase18_reference` test and added:
- `test_call_raises_runtime_error_when_no_active_client` (the new contract pin)
- `_reset_module_state` extended to save/restore `_ACTIVE_CLIENT` (line 37)

All Task 5 acceptance criteria pre-satisfied:
- `grep -c "NotImplementedError"`: 0 ✓ (Plan 18-02)
- `grep -c "test_call_raises_runtime_error_when_no_active_client"`: 1 ✓ (Plan 18-02)
- `grep -c "saved_client = tf._ACTIVE_CLIENT"`: 1 ✓ (Plan 18-02)
- `grep -c "Phase 18"`: 7 ≥1 ✓ (Plan 18-02)
- `uv run pytest tests/framework/unit/test_tool_factory.py`: 12 passed ✓

No fifth commit added in this plan for Task 5 — the work was already on `main` via commit `0cec347` (Plan 18-02).

## Task Commits

| Task | Type  | Commit  | Summary                                                            |
| ---- | ----- | ------- | ------------------------------------------------------------------ |
| 1    | test  | 38a4570 | test(18-08): pin ToolCallError shape + _extract_code_message chain |
| 2    | test  | a246318 | test(18-08): extend test_sdet_fixtures with public-surface pinning |
| 3    | test  | b42a73d | test(18-08): extend test_sdet_cli composition matrix               |
| 4    | test  | 7c01402 | test(18-08): pin D-06/D-09/D-10/D-11 renderer integration          |
| 5    | (n/a) | (none)  | No changes -- Plan 18-02 already satisfied all acceptance criteria |

The plan is `tdd="true"` on Tasks 1-4. Because the implementations (Plans 18-01..18-07) had all already shipped, the RED phase would have been trivially failing-against-missing-tests. Instead, each task ships as a single `test(...)` commit with the tests passing against the live code — i.e., the GREEN gate was effectively pre-met by the underlying plans. This is the correct pattern for Wave 5 regression-pinning tests: the upstream code is the canonical truth; the tests serve as drift guards going forward.

## Verification

- **Plan-deliverable tests**: 76/76 pass via `uv run pytest tests/framework/unit/test_tool_call_error.py tests/framework/unit/test_sdet_fixtures.py tests/framework/unit/test_sdet_cli.py tests/framework/unit/test_sdet_renderer.py tests/framework/unit/test_tool_factory.py --noconftest` (run in 0.79s).
- **Regression suite**: 111/111 pass on `test_runner_explain.py` + `test_runner_parser.py` + `test_runner_pre_run_digest.py` + `test_tool_response.py` + `test_runner_sdet_kwarg.py` + `test_runner_sdet_digest.py` + `test_runner_debug_appendix_d11.py` + `test_sdet_conftest_hook.py` (run in 0.86s). No Phase 14/16/17/Plan 18-01..18-07 surfaces shifted.

All Task acceptance grep criteria PASSED:

| Task | Criterion | Result |
|------|-----------|--------|
| 1 | `def test_` >= 12 | **23** |
| 1 | `structuredContent` >= 3 | **5** |
| 1 | `errorCode` >= 1 | **3** |
| 1 | pytest pass | **23/23** |
| 2 | `def test_` >= 5 | **12** |
| 2 | `_reset_module_state` == 1 | **1** |
| 2 | `_ACTIVE_CLIENT` >= 3 | **9** |
| 2 | `No generated SDET classes` == 1 | **1** |
| 2 | `gen-sdet-classes` >= 1 | **2** (D-03 message has 2 occurrences) |
| 2 | pytest pass | **12/12** |
| 3 | `def test_` >= 6 | **10** |
| 3 | `tests/sdet` >= 4 | **9** |
| 3 | `tests/contract` >= 3 | **5** |
| 3 | `assert "--sdet" not in argv` == 1 (was the floor; we have 2) | **2** |
| 3 | `CliRunner` >= 1 | **1** (in `_invoke` helper) |
| 3 | pytest pass | **10/10** |
| 4 | `def test_` >= 13 | **19** |
| 4 | `mcptf_error_code` >= 4 | **10** |
| 4 | `mcptf_error_raw` >= 3 | **13** |
| 4 | `model_dump_json` >= 1 | **4** |
| 4 | `json.loads` >= 1 | **1** |
| 4 | `isError\|structuredContent` >= 2 | **11** |
| 4 | `raw: (none)` >= 2 | **10** |
| 4 | em-dash U+2014 >= 2 | **11** |
| 4 | `_extract_tool_call_errors_from_xml` >= 3 | **8** |
| 4 | `_render_scenario_pre_run_digest` >= 4 | **6** |
| 4 | `VM_NAME_TAKEN` >= 1 | **11** |
| 4 | pytest pass | **19/19** |
| 5 | `NotImplementedError` == 0 | **0** (pre-satisfied by Plan 18-02) |
| 5 | `test_call_raises_runtime_error_when_no_active_client` == 1 | **1** |
| 5 | `saved_client = tf._ACTIVE_CLIENT` == 1 | **1** |
| 5 | `Phase 18` >= 1 | **7** |
| 5 | pytest pass | **12/12** |

## Decisions Made

- **Task 5 is a no-op.** Plan 18-02 already replaced the `NotImplementedError` test with `test_call_raises_runtime_error_when_no_active_client` and extended `_reset_module_state` to save/restore `_ACTIVE_CLIENT`. All Task 5 acceptance criteria pre-satisfied. Documented as a deviation rather than re-creating duplicate test bodies.
- **Extend, don't replace, pre-existing test files.** Plans 18-03 and 18-05 had already created `test_sdet_fixtures.py` (7 tests covering D-01/D-02/D-03) and `test_sdet_cli.py` (7 tests covering Plan 18-05/06 surfaces). Rather than rewriting these, this plan appended `TestPublicSurface` to the former and three composition-matrix tests to the latter. The pre-existing tests remain untouched.
- **test_sdet_renderer.py is integration-level, not unit-level.** test_runner_parser.py / test_runner_sdet_digest.py / test_runner_debug_appendix_d11.py already pin the unit-level shapes. The new file pins the full ToolCallError → JUnit XML → parser → appendix pipeline (notably the model_dump_json → quoteattr → _extract → json.loads round-trip). Test classes are organized by decision (TestD09 / TestD10 / TestD06 / TestD11Appendix / TestD11RawRoundTrip) for grep-ability.
- **The indented-JSON line check uses 4-space prefix.** `model_dump_json(indent=2)` already produces 2-space-indented content; `render_debug_appendix` adds another 2-space prefix to each output line. So the first inner-object key opens at column 4 (`    "isError"`). Initial test author tried column 2 and got a false-negative; corrected to 4 with explanatory comment in the test body.

## Deviations from Plan

### `[Rule 1 - Bug]` Initial indented-JSON column-count off by 2 in test_appendix_emits_indented_json_when_raw_nonempty

**Found during:** Task 4 first test run.

**Issue:** First version of `test_appendix_emits_indented_json_when_raw_nonempty` asserted `any(line.startswith('  "') for line in out.splitlines())` (2-space prefix). The actual output emits 4-space prefixes for inner JSON keys because `model_dump_json(indent=2)` produces 2-space indents inside the object, and `render_debug_appendix` adds another 2 spaces on every dump line. Test failed with `AssertionError: no indented JSON line in: ...`.

**Fix:** Changed assertion to filter for `line.startswith('    "') and ":" in line` (4-space prefix, colon-bearing JSON key line) and added an explanatory comment about the combined indentation. The fix is a test-author error; the production code is correct.

**Files modified:** `tests/framework/unit/test_sdet_renderer.py` (test body only, no implementation change).

**Commit:** rolled into the single task commit (`7c01402`).

**Tracked as:** `[Rule 1 - Bug]` test-author error — combined indentation arithmetic.

### Task 5 no-op (pre-satisfied)

Documented above as a key decision. No code changed; existing `test_tool_factory.py` already meets every Task 5 acceptance criterion (`grep -c NotImplementedError = 0`, the replacement test exists, `_ACTIVE_CLIENT` save/restore is in place). The work was done in commit `0cec347` (Plan 18-02) and remains valid. No deviation marker needed because the plan-of-record acknowledges that Task 5 may already be partially covered by 18-02's earlier extension.

**Total deviations:** 1 test-author error (rolled into Task 4); 1 documented Task-5 no-op.

## Out-of-Scope Notes

- **`tests/conftest.py:_session_needs_preflight` nodeid mismatch.** Pre-existing — documented by Plan 18-02 SUMMARY and Plan 18-03 SUMMARY. Workaround for running framework unit tests: `--noconftest` flag (used in every verification command above) OR `MCPTF_CONFIG_FILE=config-v2-worktree.yaml`. Not in scope for this plan.

- **Pre-existing pyright noise in `_runner.py` / `cli.py`** — documented by Plans 18-05 / 18-06. None introduced by this plan's test files (which are pyright-clean).

- **Pre-existing test failures in `test_migration_doc.py` / `test_doc_scrub.py` / `test_cli_errors.py::test_cli_errors_static_call_sites_no_banned_tokens`** — documented across Plans 18-05 / 18-06 / 18-07. These look for a missing `tests/docs/MIGRATION-v1-to-v2.md` and fail on every Phase 18 worktree. Out of scope; the failures are stable across all Wave-2..5 plans.

## Known Stubs

None. Every test in this plan is end-to-end through real (or inline-synthesized) data. No mock-only assertions, no placeholder values that would let an empty SUT pass.

## TDD Gate Compliance

This plan's tasks are marked `tdd="true"`. Because the implementations (Plans 18-01..18-07) all shipped before this Wave-5 regression-pinning layer, the canonical RED gate is met by the underlying GREEN commits from those plans. Each task in this plan committed as a single `test(...)` commit with the tests passing against the already-landed production code. Gate compliance interpretation:

- **RED gate**: pre-satisfied by Plans 18-01..18-07 — without those plans' code, every test in this plan would fail (most with `ImportError` or `ModuleNotFoundError`).
- **GREEN gate**: each `test(...)` commit confirms the tests pass against the shipped implementation.
- **REFACTOR**: not applicable — these are pinning tests, not implementation.

Compliant with the spirit of the gate: drift detection is the deliverable, not net-new behavior.

## Next Phase Readiness

**Phase 18 closed.** All four phase requirements (SDET-01/02/03/04 + UI-02) closed; all eleven decisions (D-01..D-11) regression-pinned; the public surface (`mcp_test_framework.sdet`) frozen at four names.

**Phase 19 (STATE) inherits:**
- A regression-pinned SDET surface; new STATE scenarios author themselves against `mcp_session` / `tool(name).call(params)` / `ToolCallError` knowing the contracts can't drift silently.
- `_collect_sdet_scenarios(ctx)` already takes a `RenderContext`; Phase 19 reads scenario-skip state off it.

**Phase 20 (PREFLIGHT) inherits:**
- The four-symbol `__all__` is grep-locked by `test_internal_symbols_not_re_exported` — adding `requires_homelab` to the barrel requires both updating the source and the test, making accidental widening impossible.
- The `_pytest_exit_operator_tone` D-03 message-shape is pinned by `test_mcp_session_fail_loud_on_missing_generated_module` — Phase 20's PREFLIGHT-01 / PREFLIGHT-02 messages should reuse the same helper with the same four signal phrases.

**Phase 21 (DOC-SDET) inherits:**
- README's "How to write an SDET test" section can quote the canonical import line verbatim:
  ```python
  from mcp_test_framework.sdet import mcp_session, tool, ToolCallError, ToolResponse
  ```
  Plan 18-08's `TestPublicSurface` ensures the quoted line remains correct.

**No blockers or concerns.**

## Self-Check: PASSED

Files verified to exist on disk:
- FOUND: tests/framework/unit/test_tool_call_error.py
- FOUND: tests/framework/unit/test_sdet_fixtures.py (extended)
- FOUND: tests/framework/unit/test_sdet_cli.py (extended)
- FOUND: tests/framework/unit/test_sdet_renderer.py
- FOUND: tests/framework/unit/test_tool_factory.py (already conformant from Plan 18-02)
- FOUND: .planning/phases/18-sdet-test-surface-typed-errors/18-08-SUMMARY.md

Commits verified in `git log`:
- FOUND: 38a4570 (test(18-08): pin ToolCallError shape + _extract_code_message chain)
- FOUND: a246318 (test(18-08): extend test_sdet_fixtures with public-surface pinning)
- FOUND: b42a73d (test(18-08): extend test_sdet_cli composition matrix)
- FOUND: 7c01402 (test(18-08): pin D-06/D-09/D-10/D-11 renderer integration)
- Task 5: no commit (pre-satisfied by 0cec347 — Plan 18-02)

Verification commands (all OK at completion):
- `uv run pytest tests/framework/unit/test_tool_call_error.py tests/framework/unit/test_sdet_fixtures.py tests/framework/unit/test_sdet_cli.py tests/framework/unit/test_sdet_renderer.py tests/framework/unit/test_tool_factory.py --noconftest`: **76/76 pass**
- `uv run pytest tests/framework/unit/test_runner_explain.py tests/framework/unit/test_runner_parser.py tests/framework/unit/test_runner_pre_run_digest.py tests/framework/unit/test_tool_response.py tests/framework/unit/test_runner_sdet_kwarg.py tests/framework/unit/test_runner_sdet_digest.py tests/framework/unit/test_runner_debug_appendix_d11.py tests/framework/unit/test_sdet_conftest_hook.py --noconftest`: **111/111 pass** (regression guard)
- All Task acceptance grep counts >= plan threshold (table above).

---
*Phase: 18-sdet-test-surface-typed-errors*
*Plan: 08 (final plan of Phase 18)*
*Completed: 2026-05-13*
