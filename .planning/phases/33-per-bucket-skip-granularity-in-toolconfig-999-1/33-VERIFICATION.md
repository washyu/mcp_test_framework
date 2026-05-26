---
phase: 33-per-bucket-skip-granularity-in-toolconfig-999-1
verified: 2026-05-26T12:00:00Z
status: passed
score: 3/3 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 2/3
  gaps_closed:
    - "Operator running with --explain sees a grep-able per-tool block listing which buckets were skipped and the config field that drove the skip; the pre-run digest reflects per-bucket skip counts alongside the existing whole-tool skip counts"
  gaps_remaining: []
  regressions: []
---

# Phase 33: Per-bucket skip granularity in ToolConfig Verification Report

**Phase Goal:** Operator can opt out of named test buckets (`schema`, `judge`, `output`) per tool in `config.yaml` while leaving other buckets enabled — the required-field-tool escape hatch identified during Phase 30 UAT-1.
**Verified:** 2026-05-26 (re-verification after plan 33-06 gap closure)
**Status:** passed
**Re-verification:** Yes — supersedes the initial 2026-05-26 `gaps_found` report

## Re-verification Summary

Plan 33-06 (gap_closure: true) landed two commits to close CR-01:

- `99d3775` `fix(33-06): make Test plan count bucket-aware in pre-run digest` — replaced the constant-multiplier at `_runner.py:1184` (`planned_cases = running_n * CASES_PER_CONTRACT_TOOL`) with a per-tool loop that subtracts the case count of each bucket listed in that tool's `skip_buckets`, using `_BUCKET_SIZE` derived from `TEST_FUNCTION_BUCKETS`.
- `1df8772` `test(33-06): pin Test plan count against bucket-aware expected value` — added `test_digest_test_plan_count_deducts_skip_buckets` (4 scenarios) to `tests/framework/test_pre_run_digest_buckets.py`.

Truth #3 flips from FAILED (partial) to VERIFIED. Plans 33-01..33-05 were untouched; their previously-verified must-haves remain green (full framework suite: 728 passed, 0 failed, 0 regressions vs prior 727).

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Operator setting `tools.<name>.skip_buckets: ["output"]` sees schema + judge tests run while output-bucket tests do not appear in `pytest --collect-only` (collection-time filtering, no runtime-SKIPPED rows) | VERIFIED | `_plugin.py` imports `TEST_FUNCTION_BUCKETS`, filters `names` per test function in `pytest_generate_tests`, strips `[NOTSET]` placeholder items in `pytest_collection_modifyitems`. Five mandatory subprocess + synthetic-Metafunc tests in `test_plugin_bucket_filter.py` pin collect-only absence AND zero SKIPPED rows. Re-confirmed green in the 728-test run. |
| 2 | Operator typing `skip_buckets: ["otput"]` sees a Pydantic validation error at load time naming the three valid buckets | VERIFIED | `ToolConfig.skip_buckets: list[BucketName]` where `BucketName = Literal["schema","judge","output"]` in `_buckets.py`. Pydantic's stock Literal error names all three valid values. Seven tests in `test_tool_config.py` pin accept/reject cases including the typo case; `_skip_buckets_not_with_whole_tool_skip` rejects `skip=True` + non-empty `skip_buckets`. All green. |
| 3 | Operator running with `--explain` sees a grep-able per-tool block listing which buckets were skipped and the config field that drove the skip; the pre-run digest reflects per-bucket skip counts alongside the existing whole-tool skip counts | VERIFIED (gap closed by 33-06) | **--explain block**: `_render_skipped_tools_explain` emits `Bucket-skipped tools (M):` section with `bucket=<name>: skipped via tools.<name>.skip_buckets` lines; pinned by `test_explain_buckets.py`. **Bucket skips: count line**: `_count_bucket_skips` + `Bucket skips: N (use --explain to list)`; pinned by Tests 2/3 in `test_pre_run_digest_buckets.py`. **Test plan: count line** (CR-01 resolved): `_runner.py:1199-1206` now computes `planned_cases` via a per-tool loop deducting bucket sizes per `skip_buckets`. Manual smoke for `create_proxmox_vm` + `skip_buckets=["output"]` prints `Test plan: 7 contract cases` and `Bucket skips: 1` — internally consistent. Pinned by new Test 5 (`test_digest_test_plan_count_deducts_skip_buckets`) across 4 scenarios (baseline 20, single-bucket 7, all-buckets 0, multi-tool 14). |

**Score:** 3/3 truths fully verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/mcp_test_framework/contracts/_buckets.py` | `TEST_FUNCTION_BUCKETS` source-of-truth mapping + `BucketName` alias | VERIFIED | Exists, substantive, exports both symbols; imported by `_plugin.py`, `models.py`, AND now `_runner.py` (new in 33-06) |
| `src/mcp_test_framework/models.py` | `ToolConfig.skip_buckets` field + `_skip_buckets_not_with_whole_tool_skip` validator | VERIFIED | Unchanged since initial verification |
| `src/mcp_test_framework/_plugin.py` | Per-bucket filter in `pytest_generate_tests` + `[NOTSET]` cleanup in `pytest_collection_modifyitems` | VERIFIED | Unchanged since initial verification |
| `src/mcp_test_framework/_runner.py` | `_count_bucket_skips` helper + `Bucket skips:` digest line + bucket-aware `Test plan:` calculation + `_render_skipped_tools_explain` Section 2 | VERIFIED (was partial) | New: `from mcp_test_framework.contracts._buckets import TEST_FUNCTION_BUCKETS` at line 45; module-level `_BUCKET_SIZE` cache at line 50; per-tool loop at lines 1199-1206 replaces the constant-multiplier. `CASES_PER_CONTRACT_TOOL` constant retained at line 437 (still referenced in docstring). |
| `tests/framework/test_bucket_map.py` | Self-tests pinning `TEST_FUNCTION_BUCKETS` completeness and disjointness | VERIFIED | Unchanged |
| `tests/framework/test_tool_config.py` | Pydantic validation tests for skip_buckets accept/reject + redundancy rejection | VERIFIED | Unchanged |
| `tests/framework/test_plugin_bucket_filter.py` | 5 mandatory subprocess + synthetic-Metafunc self-tests | VERIFIED | Unchanged |
| `tests/framework/test_explain_buckets.py` | 4 self-tests for --explain bucket= line | VERIFIED | Unchanged |
| `tests/framework/test_pre_run_digest_buckets.py` | Self-tests for digest per-bucket counts INCLUDING `Test plan:` regression test | VERIFIED (was partial) | 5 tests now (was 4); new `test_digest_test_plan_count_deducts_skip_buckets` covers 4 scenarios; expected values derived dynamically from `TEST_FUNCTION_BUCKETS` so future bucket re-balance shifts impl + expected in lockstep |
| `docs/ERROR-STYLE.md` | Redundancy message registered verbatim | VERIFIED | Unchanged |
| `README.md` | Worked example with `create_proxmox_vm` + `skip_buckets: ["output"]` | VERIFIED | Unchanged |
| `docs/LIBRARY-MODE.md` | Same worked example (D-03 parity) | VERIFIED | Unchanged |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/mcp_test_framework/contracts/_buckets.py` | `contracts/_tests.py` function names | 10 string literals in `TEST_FUNCTION_BUCKETS` | WIRED | Unchanged |
| `src/mcp_test_framework/models.py` | `BucketName` Literal | Import from `_buckets.py` | WIRED | Unchanged |
| `src/mcp_test_framework/_plugin.py` | `TEST_FUNCTION_BUCKETS` | Import + use in `pytest_generate_tests` | WIRED | Unchanged |
| `src/mcp_test_framework/_runner.py` | `TEST_FUNCTION_BUCKETS` | Module import at line 45 + `_BUCKET_SIZE` cache at line 50 (NEW in 33-06) | WIRED | `grep -n "from mcp_test_framework.contracts._buckets import TEST_FUNCTION_BUCKETS" src/mcp_test_framework/_runner.py` returns line 45 (exactly one match, matches plan 33-06 acceptance criterion). |
| `src/mcp_test_framework/_runner.py::_render_pre_run_digest` | `ctx.tools_config[t].skip_buckets` | Per-tool loop at lines 1199-1206 (NEW in 33-06) | WIRED | `ctx.tools_config.get(t)` + `getattr(..., "skip_buckets", []) or []` defensive read; bucket sizes summed via `_BUCKET_SIZE.items()` set-membership filter. |
| `src/mcp_test_framework/_runner.py` | `ToolConfig.skip_buckets` | `_count_bucket_skips` + `_render_skipped_tools_explain` Section 2 | WIRED | Unchanged |
| `README.md` + `docs/LIBRARY-MODE.md` | `ToolConfig.skip_buckets` field | `skip_buckets: ["output"]` YAML snippet | WIRED | Unchanged |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `_plugin.pytest_generate_tests` | `names` (filtered tool list) | `ToolConfig.skip_buckets` via `cfg.tools.get(tool_name)` | Yes — reads live config at parametrize time | FLOWING |
| `_runner._render_pre_run_digest` | `planned_cases` | Per-tool loop summing `_BUCKET_SIZE[b]` for buckets not in `tcfg.skip_buckets` | Yes — reads live `ctx.tools_config[t].skip_buckets` (NEW in 33-06; was HOLLOW) | FLOWING |
| `_runner._render_skipped_tools_explain` (Section 2) | `bucket_skipped` dict | `ctx.tools_config.items()` filtering by `tcfg.skip_buckets` | Yes — reads live tools_config | FLOWING |
| `_runner._count_bucket_skips` | `bucket_skip_n` | `len(getattr(tcfg, "skip_buckets", []))` per tool | Yes — sums real skip_buckets lengths | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Targeted test file passes all 5 tests (4 pre-existing + 1 new regression) | `uv run pytest tests/framework/test_pre_run_digest_buckets.py -v` | `5 passed in 0.02s` | PASS |
| Full framework suite has no regressions | `uv run pytest tests/framework/ -x` | `728 passed, 2 skipped, 18 deselected, 1 xfailed in 91.20s` | PASS (matches SUMMARY claim of 728 vs prior 727; +1 from new test) |
| Manual smoke — single tool with skip_buckets=["output"] prints `Test plan: 7` | Python one-liner rendering digest for `create_proxmox_vm` + `skip_buckets=["output"]` | Output contains literal `Test plan:   7 contract cases` and `Bucket skips:  1`; the two lines now agree | PASS |
| Digest internal-consistency invariant: when no skip_buckets, baseline byte-identity preserved | Implicit via Scenario A of Test 5 (2 tools, no skip_buckets, expects 20) | Scenario A asserts `_plan_count == 20`; passing in the test run above | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| BUCKET-01 | Plan 33-01 | `tools.<name>.skip_buckets: list[Literal[...]] = []` accepted by ToolConfig | SATISFIED | `ToolConfig.skip_buckets` field with `BucketName` Literal type; 7 tests pin accept/reject behavior |
| BUCKET-02 | Plan 33-03 | Per-bucket skip filters at collection time, not runtime | SATISFIED | Two-hook mechanism in `_plugin.py`; 5 subprocess tests pin collect-only absence AND zero SKIPPED rows |
| BUCKET-03 | Plan 33-01 | Invalid bucket name rejected by Pydantic naming valid buckets | SATISFIED | `list[BucketName]` where `BucketName = Literal["schema","judge","output"]`; stock Pydantic Literal error names all three; typo test green |
| BUCKET-04 | Plan 33-04 + Plan 33-06 (gap closure) | Pre-run digest reflects per-bucket skip counts; `--explain` surfaces bucket-level rationale | SATISFIED (was PARTIAL) | All three sub-deliverables now verified: (a) `--explain` `bucket=<name>: skipped via tools.<name>.skip_buckets` grep-able lines; (b) `Bucket skips: N` count line; (c) `Test plan: N` line now subtracts bucket-skip cases (CR-01 fix). 5 tests in `test_pre_run_digest_buckets.py` + 4 in `test_explain_buckets.py`. |
| BUCKET-05 | Plan 33-05 | README + `docs/LIBRARY-MODE.md` worked example for required-field tool skipping output bucket | SATISFIED | Both docs contain `### Skipping individual test buckets per tool` with `create_proxmox_vm`, YAML snippet, `--explain` output slice, digest slice, test-bucket vs result-bucket disambiguation |

### Anti-Patterns Found

| File | Location | Pattern | Severity | Impact |
|------|----------|---------|----------|--------|
| `src/mcp_test_framework/_runner.py` | Docstring at lines 1143-1174 | Still claims `Test plan: {R * CASES_PER_CONTRACT_TOOL}` — the formula is now an upper bound, not the exact value | Info | Documentation drift only; the runtime behavior is correct. Plan 33-06 deliberately left this for a future polish pass per its out-of-scope rule (WR-04..WR-06). Operators reading the docstring may briefly miscalculate, but the actual emitted line is correct and pinned by tests. Not blocker-level. |
| `src/mcp_test_framework/models.py` | `skip_buckets` field | List semantics allow silent duplicates (`["output","output"]`) | Warning (WR-01) | Out of scope per 33-06; carries forward from initial verification. Operator-facing impact: `_count_bucket_skips` would double-count; explain renderer would emit duplicate lines. Should be addressed in a future hardening pass. |
| `src/mcp_test_framework/_runner.py` | Lines ~1357-1362 (Section 1 defensive path) | Section 1 bucket lines use 2-space indent; Section 2 uses 4-space indent | Warning (WR-03) | Visual inconsistency if defensive path fires; lower-priority. Out of scope per 33-06. |

### Human Verification Required

None — all critical behaviors are covered by automated tests. The gap closure was code-level (computation correctness) and is pinned by Test 5's four scenarios. The subprocess-based collection tests (Tests 1-5 in `test_plugin_bucket_filter.py`) already cover the operator-visible runtime behavior end-to-end.

### Gaps Summary

**No gaps remaining.** The single BLOCKER from the initial verification (CR-01) was closed by plan 33-06:

- Root cause `_runner.py:1184` constant-multiplier — REMOVED (grep returns 0 matches for `planned_cases = running_n \* CASES_PER_CONTRACT_TOOL`).
- Replacement per-tool loop at lines 1199-1206 — IN PLACE, imports `TEST_FUNCTION_BUCKETS` via `_BUCKET_SIZE` cache.
- Regression test `test_digest_test_plan_count_deducts_skip_buckets` — IN PLACE, green across 4 scenarios.
- Full framework suite — 728 passed (vs 727 before), no regressions.
- Manual smoke confirms digest is internally consistent: `Bucket skips: 1` + `Test plan: 7` when `create_proxmox_vm` has `skip_buckets=["output"]`.

Warnings WR-01..WR-06 from the initial verification remain open as non-blocker tech debt, deliberately deferred by 33-06's surgical scope. They do not block phase closure.

---

_Verified: 2026-05-26 (re-verification)_
_Verifier: Claude (gsd-verifier)_
_Supersedes: initial verification 2026-05-26 (gaps_found, 2/3)_
