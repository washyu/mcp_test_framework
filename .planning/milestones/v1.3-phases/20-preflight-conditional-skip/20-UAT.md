---
status: complete
phase: 20-preflight-conditional-skip
source:
  - 20-01-SUMMARY.md
  - 20-02-SUMMARY.md
  - 20-03-SUMMARY.md
  - 20-04-SUMMARY.md
  - 20-05-SUMMARY.md
started: 2026-05-13T00:00:00Z
updated: 2026-05-13T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Planning docs reflect the reframed Phase 20 scope
expected: REQUIREMENTS.md/ROADMAP.md/STATE.md all reflect the scope-correction reframe (3 new requirements, total=22, Phase 20 heading rewritten, STATE.md reframe block present).
result: pass

### 2. `tests/sdet/` is empty of SUT-specific tests
expected: `ls tests/sdet/` shows only `__init__.py` and `conftest.py` (no `test_proxmox_vm_lifecycle.py`, no `test_basic_call.py`). `uv run pytest tests/sdet/ --collect-only` reports `collected 0 items`.
result: pass

### 3. Codegen mock-fixture tests pass cleanly
expected: `uv run pytest tests/framework/unit/test_codegen_integration_mock.py -v` reports `10 passed` with zero failures or errors. Includes the post-fix tests (`test_echo_message_params_class_shape` pinning exact field set, and `test_generate_counts_reports_degraded_fields` exercising the inverse-direction degradation case).
result: pass

### 4. Framework self-tests still green overall
expected: Running the broader framework suite (e.g. `uv run pytest tests/framework/`) shows no regressions vs the Phase 20 baseline. Pass count is ≥460 (450 pre-Phase-20 + 10 new from 20-05); zero failures introduced by Phase 20 commits.
result: pass
note: |
  Suite reports 542 passed / 11 failed / 1 error / 1 skipped / 2 xfailed. Pass count (542) exceeds the ≥460 threshold; user-observed failures verified pre-existing at baseline `cfb04f2` (e.g. `test_default_config_version_and_tools` fails identically pre-Phase-20). Failure categories: (1) Config schema v1→v2 mismatch — 4 tests, (2) `parents[2]` path resolution broken after `tests/` folder split at Phase 15-01 commit `2e74967` — 5 tests in `test_cli_errors.py` + `test_migration_doc.py`, (3) missing module `tests.test_mcp_tool_contract` — 1 test, (4) README line 104 bare `mcp-test-framework run --explain` invocation — 1 test, (5) ERROR `homelab-mcp` executable not on PATH — environmental, 1 test. User decision: pass for Phase 20; add a dedicated test-suite-debt cleanup phase to v1.3 milestone before close so debt doesn't carry to next milestone.

### 5. `src/` untouched by Phase 20 (D-01 guardrail)
expected: `git diff --stat cfb04f2..HEAD -- src/` returns empty output. Phase 20 shipped zero `src/` changes — only planning docs, deleted SDET test files, and one new test file under `tests/framework/unit/`.
result: pass

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
