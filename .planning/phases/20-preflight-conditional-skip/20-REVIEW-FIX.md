---
phase: 20-preflight-conditional-skip
fixed_at: 2026-05-13T00:00:00Z
review_path: .planning/phases/20-preflight-conditional-skip/20-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 20: Code Review Fix Report

**Fixed at:** 2026-05-13T00:00:00Z
**Source review:** `.planning/phases/20-preflight-conditional-skip/20-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 2 (Critical + Warning only; Info findings excluded by fix_scope)
- Fixed: 2
- Skipped: 0

All in-scope findings were fixed cleanly. The full `test_codegen_integration_mock.py` suite (10 tests) passes after both fixes.

## Fixed Issues

### WR-01: `test_echo_message_params_class_shape` does not pin the field set, only checks membership

**Files modified:** `tests/framework/unit/test_codegen_integration_mock.py`
**Commit:** `dc46e44`
**Applied fix:** Replaced membership-only assertion (`"message" in Params.model_fields`) with exact-set assertion (`set(Params.model_fields) == {"message"}`) in `test_echo_message_params_class_shape`. Applied the same tightening to `test_ping_with_timeout_params_int_default` by adding an exact-set assertion (`set(Params.model_fields) == {"host", "timeout_ms"}`) before the per-field checks. Both tests now fail loudly if a future codegen regression emits a spurious extra field.

Verification: `python -c "import ast; ast.parse(...)"` syntax check passed; both tightened tests still PASS under pytest.

### WR-02: `test_generate_counts_no_degraded_fields` duplicates the `generated` fixture's count assertion

**Files modified:** `tests/framework/unit/test_codegen_integration_mock.py`
**Commit:** `6508ff6`
**Applied fix:** Replaced the redundant `test_generate_counts_no_degraded_fields` (option b from the review) with `test_generate_counts_reports_degraded_fields`, which exercises the *inverse* direction: it feeds a single-tool fixture whose `inputSchema` declares an enum field (a known degradation trigger per `_codegen.py:212`) and asserts `counts == {"tools": 1, "degraded_fields": 1}`. This locks the previously-uncovered direction — a regression that silently stopped incrementing `degraded_fields` would now fail loudly. The clean-direction invariant remains locked by the `generated` fixture's pre-condition that runs on every other test in the module.

Verification: `python -c "import ast; ast.parse(...)"` syntax check passed; full test module (10 tests) PASSES under pytest, including the new test which actually exercises the degradation counter end-to-end.

## Skipped Issues

The following findings were out of scope for this run (`fix_scope: critical_warning`) and were NOT attempted. They remain as documented in `20-REVIEW.md` for the developer to address separately if desired:

### IN-01: Unused `import importlib`

**File:** `tests/framework/unit/test_codegen_integration_mock.py:24`
**Reason:** Info severity — out of scope for this run.
**Original issue:** `import importlib` is never referenced; only `importlib.util` (line 25) is used. Ruff F401 will flag this once enabled.

### IN-02: Docstring claim diverges from actual loading mechanism

**File:** `tests/framework/unit/test_codegen_integration_mock.py:13`
**Reason:** Info severity — out of scope for this run.
**Original issue:** Module docstring item (4) says modules import via `importlib.import_module`, but actual code uses `importlib.util.spec_from_file_location` + `exec_module`.

### IN-03: `sys.modules` entries are never cleaned up after each test

**File:** `tests/framework/unit/test_codegen_integration_mock.py:108-151`
**Reason:** Info severity — out of scope for this run.
**Original issue:** `_load_generated_module` / `_load_generated_init` clear prior registrations on load but never remove their own after the test completes; accumulates ~21 entries per session in long-lived pytest processes.

### IN-04: `from pydantic import BaseModel` is buried inside a loop body

**File:** `tests/framework/unit/test_codegen_integration_mock.py:273-274`
**Reason:** Info severity — out of scope for this run.
**Original issue:** Import is performed inside the `for name, entry in registry.items():` loop body; should be hoisted to the module's import block.

### IN-05: Brittle exact-equality on `counts` dict will fail on additive schema changes

**File:** `tests/framework/unit/test_codegen_integration_mock.py:166, 319`
**Reason:** Info severity — out of scope for this run.
**Original issue:** `counts == {"tools": 3, "degraded_fields": 0}` uses exact-equality on the returned counts dict; any future additive key (`tools_skipped`, `warnings`, `elapsed_ms`) breaks every test that touches the `generated` fixture. (Note: WR-02's replacement test also uses exact-equality; the same concern applies there if the team later loosens this contract.)

---

_Fixed: 2026-05-13T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
