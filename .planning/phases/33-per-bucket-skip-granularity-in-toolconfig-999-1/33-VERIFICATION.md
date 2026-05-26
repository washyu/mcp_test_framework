---
phase: 33-per-bucket-skip-granularity-in-toolconfig-999-1
verified: 2026-05-26T00:00:00Z
status: gaps_found
score: 2/3 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Operator running with --explain sees a grep-able per-tool block listing which buckets were skipped and the config field that drove the skip; the pre-run digest reflects per-bucket skip counts alongside the existing whole-tool skip counts"
    status: partial
    reason: "The --explain block and the Bucket skips: count line are correctly implemented and tested. However, the Test plan: N contract cases line in _render_pre_run_digest uses planned_cases = running_n * CASES_PER_CONTRACT_TOOL (line 1184 of _runner.py) without deducting skip_buckets-filtered cases. A tool with skip_buckets: ['output'] contributes 10 to the plan instead of 7; a tool opting out of all three buckets contributes 10 to the plan instead of 0. Code reviewer CR-01 confirmed this is a BLOCKER. SC#3 says the digest reflects per-bucket skip counts — the Bucket skips: line does this correctly, but the Test plan: line contradicts it by overstating what will actually be collected, making the digest internally inconsistent as an authoritative preview."
    artifacts:
      - path: "src/mcp_test_framework/_runner.py"
        issue: "Line 1184: planned_cases = running_n * CASES_PER_CONTRACT_TOOL does not account for skip_buckets; for create_proxmox_vm with skip_buckets=['output'], Test plan shows 10 but pytest will collect 7"
    missing:
      - "Replace planned_cases = running_n * CASES_PER_CONTRACT_TOOL with a per-tool calculation that subtracts the case count for each bucket in skip_buckets (using TEST_FUNCTION_BUCKETS to get the per-bucket size)"
      - "Add a regression test that asserts the digest Test plan: number agrees with actual collected item count when skip_buckets is set"
---

# Phase 33: Per-bucket skip granularity in ToolConfig Verification Report

**Phase Goal:** Operator can opt out of named test buckets (`schema`, `judge`, `output`) per tool in `config.yaml` while leaving other buckets enabled — the required-field-tool escape hatch identified during Phase 30 UAT-1.
**Verified:** 2026-05-26
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Operator setting `tools.<name>.skip_buckets: ["output"]` sees schema + judge tests run while output-bucket tests do not appear in `pytest --collect-only` (collection-time filtering, no runtime-SKIPPED rows) | ✓ VERIFIED | `_plugin.py` imports `TEST_FUNCTION_BUCKETS`, filters `names` per test function in `pytest_generate_tests`, strips `[NOTSET]` placeholder items in `pytest_collection_modifyitems`. Five mandatory subprocess + synthetic-Metafunc tests in `test_plugin_bucket_filter.py` pin collect-only absence AND zero SKIPPED rows in full-run output (including the all-opts-out edge case). Tests green per 33-03-SUMMARY. |
| 2 | Operator typing `skip_buckets: ["otput"]` sees a Pydantic validation error at load time naming the three valid buckets | ✓ VERIFIED | `ToolConfig.skip_buckets: list[BucketName]` where `BucketName = Literal["schema","judge","output"]` in `_buckets.py`. Pydantic's stock Literal error names all three valid values. Seven tests in `test_tool_config.py` pin accept/reject cases including the typo case. `_skip_buckets_not_with_whole_tool_skip` model_validator also rejects `skip=True` + non-empty `skip_buckets`. All green per 33-01-SUMMARY and 33-02-SUMMARY. |
| 3 | Operator running with `--explain` sees a grep-able per-tool block listing which buckets were skipped and the config field that drove the skip; the pre-run digest reflects per-bucket skip counts alongside the existing whole-tool skip counts | ✗ FAILED (partial) | **--explain block**: VERIFIED — `_render_skipped_tools_explain` emits `Bucket-skipped tools (M):` section with `bucket=<name>: skipped via tools.<name>.skip_buckets` lines (grep-able on `bucket=`); four tests in `test_explain_buckets.py` pin the format including the grep-anchor. **Bucket skips: count line**: VERIFIED — `_count_bucket_skips` helper + `Bucket skips:{N}  (use --explain to list)` line emitted in digest when N > 0; four tests in `test_pre_run_digest_buckets.py` pin behavior. **Test plan: count line**: FAILED — `_runner.py:1184` computes `planned_cases = running_n * CASES_PER_CONTRACT_TOOL` (constant 10) without deducting skip_buckets-filtered cases. For `create_proxmox_vm` with `skip_buckets: ["output"]` the digest says "10 contract cases" but pytest will collect 7. Code reviewer CR-01 flagged this as a BLOCKER. The digest is internally inconsistent: `Bucket skips: 1` signals something was filtered, but `Test plan: 10` ignores the filter. |

**Score:** 2/3 truths fully verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/mcp_test_framework/contracts/_buckets.py` | `TEST_FUNCTION_BUCKETS` source-of-truth mapping + `BucketName` alias | ✓ VERIFIED | Exists, substantive, exports both symbols; imported by `_plugin.py` and `models.py` |
| `src/mcp_test_framework/models.py` | `ToolConfig.skip_buckets` field + `_skip_buckets_not_with_whole_tool_skip` validator | ✓ VERIFIED | Field present at line 103, validator at line 152-173; both wired and tested |
| `src/mcp_test_framework/_plugin.py` | Per-bucket filter in `pytest_generate_tests` + `[NOTSET]` cleanup in `pytest_collection_modifyitems` | ✓ VERIFIED | Import of `TEST_FUNCTION_BUCKETS` confirmed; `owning_bucket` filter logic at lines 479-490; `[NOTSET]` strip at line 423 |
| `src/mcp_test_framework/_runner.py` | `_count_bucket_skips` helper + `Bucket skips:` digest line + `_render_skipped_tools_explain` Section 2 | ✓ VERIFIED (partial) | Helper at line 1019; `Bucket skips:` line at 1204/1207; explain Section 2 at 1376-1384. `Test plan:` count at line 1184 does NOT account for skip_buckets — STUB behavior for this sub-requirement |
| `tests/framework/test_bucket_map.py` | Self-tests pinning `TEST_FUNCTION_BUCKETS` completeness and disjointness | ✓ VERIFIED | 3 tests exist; all green per 33-01-SUMMARY |
| `tests/framework/test_tool_config.py` | Pydantic validation tests for skip_buckets accept/reject + redundancy rejection | ✓ VERIFIED | 7 new tests (plan 01) + 4 new tests (plan 02) all green |
| `tests/framework/test_plugin_bucket_filter.py` | 5 mandatory subprocess + synthetic-Metafunc self-tests | ✓ VERIFIED | All 5 tests named per plan 03 exist and are green per 33-03-SUMMARY |
| `tests/framework/test_explain_buckets.py` | 4 self-tests for --explain bucket= line | ✓ VERIFIED | All 4 tests exist and green per 33-04-SUMMARY |
| `tests/framework/test_pre_run_digest_buckets.py` | 4 self-tests for digest per-bucket counts | ✓ VERIFIED (partial) | 4 tests exist and green, but no test checks the `Test plan:` count against actual collected items — the CR-01 gap has no regression test |
| `docs/ERROR-STYLE.md` | Redundancy message registered verbatim | ✓ VERIFIED | `### skip and skip_buckets are both set` section present with locked verbatim string |
| `README.md` | Worked example with `create_proxmox_vm` + `skip_buckets: ["output"]` | ✓ VERIFIED | `### Skipping individual test buckets per tool` subsection present with YAML, `--explain` output, digest slice, and test-bucket vs result-bucket disambiguation |
| `docs/LIBRARY-MODE.md` | Same worked example (D-03 parity) | ✓ VERIFIED | Identical subsection present with byte-aligned YAML and output blocks |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/mcp_test_framework/contracts/_buckets.py` | `contracts/_tests.py` function names | 10 string literals in `TEST_FUNCTION_BUCKETS` | ✓ WIRED | All 10 test function names present; `test_bucket_map.py` introspects `_tests` module to pin the mapping |
| `src/mcp_test_framework/models.py` | `BucketName` Literal | Import from `_buckets.py` | ✓ WIRED | `from mcp_test_framework.contracts._buckets import BucketName` present; `skip_buckets: list[BucketName]` field uses it |
| `src/mcp_test_framework/_plugin.py` | `TEST_FUNCTION_BUCKETS` | Import + use in `pytest_generate_tests` | ✓ WIRED | Import confirmed; `TEST_FUNCTION_BUCKETS.items()` iterated at line 480; `.skip_buckets` read at line 488 |
| `src/mcp_test_framework/_plugin.py` | `pytest_collection_modifyitems` | `callspec.id == "NOTSET"` guard | ✓ WIRED | Guard at line 423 inside the per-item loop within `pytest_collection_modifyitems` |
| `src/mcp_test_framework/_runner.py` | `ToolConfig.skip_buckets` | `_count_bucket_skips` + `_render_skipped_tools_explain` Section 2 | ✓ WIRED | `getattr(tcfg, "skip_buckets", [])` at line 1028; `tcfg.skip_buckets` at lines 1357-1358 and 1372-1374 |
| `src/mcp_test_framework/_runner.py::_render_pre_run_digest` | `TEST_FUNCTION_BUCKETS` bucket sizes | `planned_cases` computation | ✗ NOT WIRED | `planned_cases = running_n * CASES_PER_CONTRACT_TOOL` at line 1184 does not import or consult `TEST_FUNCTION_BUCKETS`; per-bucket deductions absent |
| `README.md` + `docs/LIBRARY-MODE.md` | `ToolConfig.skip_buckets` field | `skip_buckets: ["output"]` YAML snippet | ✓ WIRED | Both docs contain `skip_buckets` field reference; `create_proxmox_vm` example in both |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `_plugin.pytest_generate_tests` | `names` (filtered tool list) | `ToolConfig.skip_buckets` via `cfg.tools.get(tool_name)` | Yes — reads live config at parametrize time | ✓ FLOWING |
| `_runner._render_pre_run_digest` | `planned_cases` | `running_n * CASES_PER_CONTRACT_TOOL` | Partially — ignores skip_buckets deduction | ✗ HOLLOW — produces an overcount when skip_buckets is non-empty |
| `_runner._render_skipped_tools_explain` (Section 2) | `bucket_skipped` dict | `ctx.tools_config.items()` filtering by `tcfg.skip_buckets` | Yes — reads live tools_config | ✓ FLOWING |
| `_runner._count_bucket_skips` | `bucket_skip_n` | `len(getattr(tcfg, "skip_buckets", []))` per tool | Yes — sums real skip_buckets lengths | ✓ FLOWING |

### Behavioral Spot-Checks

Step 7b skipped — requires live MCP server subprocess. Subprocess-based collection tests (Tests 1-5 in `test_plugin_bucket_filter.py`) serve as the behavioral equivalent using a stub harness, and are all green per 33-03-SUMMARY.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| BUCKET-01 | Plan 33-01 | `tools.<name>.skip_buckets: list[Literal[...]] = []` accepted by ToolConfig | ✓ SATISFIED | `ToolConfig.skip_buckets` field implemented with `BucketName` Literal type; 7 tests pin accept/reject behavior |
| BUCKET-02 | Plan 33-03 | Per-bucket skip filters at collection time, not runtime | ✓ SATISFIED | Two-hook mechanism in `_plugin.py`; 5 subprocess tests pin collect-only absence AND zero SKIPPED rows |
| BUCKET-03 | Plan 33-01 | Invalid bucket name rejected by Pydantic naming valid buckets | ✓ SATISFIED | `list[BucketName]` where `BucketName = Literal["schema","judge","output"]`; stock Pydantic Literal error names all three; typo test (`"otput"`) green |
| BUCKET-04 | Plan 33-04 | Pre-run digest reflects per-bucket skip counts; `--explain` surfaces bucket-level rationale | ✗ PARTIAL | `--explain` block (VERIFIED): grep-able `bucket=<name>: skipped via tools.<name>.skip_buckets` line per bucket per tool. `Bucket skips: N` count line (VERIFIED). `Test plan: N` line (FAILED): overstates collected cases by ignoring skip_buckets deduction — CR-01 BLOCKER |
| BUCKET-05 | Plan 33-05 | README + `docs/LIBRARY-MODE.md` worked example for required-field tool skipping output bucket | ✓ SATISFIED | Both docs contain `### Skipping individual test buckets per tool` with `create_proxmox_vm`, YAML snippet, `--explain` output slice, digest slice, test-bucket vs result-bucket disambiguation |

### Anti-Patterns Found

| File | Location | Pattern | Severity | Impact |
|------|----------|---------|----------|--------|
| `src/mcp_test_framework/_runner.py` | Line 1184 | `planned_cases = running_n * CASES_PER_CONTRACT_TOOL` — ignores skip_buckets deduction | Blocker | Digest `Test plan:` line overstates collected cases by `len(skip_buckets_for_tool) * bucket_size` per tool; contradicts `Bucket skips: N` line which correctly reflects the filter |
| `src/mcp_test_framework/_runner.py` | Lines 1357-1362 (Section 1 defensive path) | Section 1 bucket lines use 2-space indent; Section 2 uses 4-space indent under a tool header | Warning (WR-03) | Visual inconsistency if defensive path fires; lower-priority |
| `src/mcp_test_framework/models.py` | `skip_buckets` field | List semantics allow silent duplicates (`["output","output"]`); no deduplication validator | Warning (WR-01) | `_count_bucket_skips` would double-count; explain renderer would emit duplicate lines |

### Human Verification Required

None — all critical behaviors are covered by automated tests (subprocess-based collection tests cover the operator-visible behavior end-to-end).

### Gaps Summary

One gap blocks the phase goal:

**CR-01: `Test plan:` count in pre-run digest ignores `skip_buckets` (BLOCKER)**

The `_render_pre_run_digest` function computes `planned_cases = running_n * CASES_PER_CONTRACT_TOOL` (line 1184 of `_runner.py`), treating all running tools as contributing a full 10 contract cases regardless of their `skip_buckets` setting. For `create_proxmox_vm` with `skip_buckets: ["output"]`, the digest will print:

```
Bucket skips:  1  (use --explain to list)
Test plan:   10 contract cases
```

But pytest will collect 7 items (4 schema + 3 judge; 3 output tests are filtered). The two lines contradict each other — the `Bucket skips` line signals a filter was applied; the `Test plan` line ignores it.

SC#3 requires "the pre-run digest reflects per-bucket skip counts alongside the existing whole-tool skip counts." The `Bucket skips:` count line satisfies this. However, a digest that shows `Test plan: 10` when 3 tests are filtered is not an accurate operator preview — it is internally inconsistent. Code reviewer CR-01 classified this as a BLOCKER.

The code review also identified several warnings (WR-01 duplicate skip_buckets not rejected; WR-02 undiscovered-tool count inflation in bucket-skip surfaces; WR-03 indentation inconsistency in Section 1 defensive path; WR-04 `Judges:` digest line not updated when judge bucket is suppressed; WR-05 column alignment drift; WR-06 validator ordering) but these are not blocker-level for the phase goal.

**Fix required:**
Replace line 1184 in `_runner.py`:
```python
# Current (wrong):
planned_cases = running_n * CASES_PER_CONTRACT_TOOL

# Replace with per-tool bucket-aware calculation:
from mcp_test_framework.contracts._buckets import TEST_FUNCTION_BUCKETS
_BUCKET_SIZE = {b: len(fns) for b, fns in TEST_FUNCTION_BUCKETS.items()}
planned_cases = 0
for t in running:
    skipped_buckets = set(getattr(ctx.tools_config.get(t), "skip_buckets", []) or [])
    planned_cases += sum(sz for b, sz in _BUCKET_SIZE.items() if b not in skipped_buckets)
```

Add a regression test to `test_pre_run_digest_buckets.py` that asserts the `Test plan:` count matches the actual filtered item count (e.g., 7 for one tool with `skip_buckets: ["output"]`, not 10).

---

_Verified: 2026-05-26_
_Verifier: Claude (gsd-verifier)_
