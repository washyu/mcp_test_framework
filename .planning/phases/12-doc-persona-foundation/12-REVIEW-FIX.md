---
phase: 12-doc-persona-foundation
fixed_at: 2026-05-09T00:00:00Z
review_path: .planning/phases/12-doc-persona-foundation/12-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 8
skipped: 0
status: all_fixed
---

# Phase 12: Code Review Fix Report

**Fixed at:** 2026-05-09
**Source review:** .planning/phases/12-doc-persona-foundation/12-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 8 (2 blocker, 6 warning -- all severities included; "blocker" treated as critical-equivalent per orchestrator note)
- Fixed: 8
- Skipped: 0

All 138 unit tests pass after the fixes (`uv run pytest tests/unit/`).

## Fixed Issues

### BL-01: examples/homelab-mcp.yaml leaks 18+ planning IDs into the operator-facing example

**Files modified:** `examples/homelab-mcp.yaml`, `tests/unit/test_examples_dir.py`
**Commit:** 9d29378
**Applied fix:** Rewrote the file's leading commentary in operator terms, scrubbing every `Phase \d`, `TOOLCFG-XX`, `CD-XX`, `SEED-XXX`, `TEST-XX`, `Plan \d-\d`, and `\d{6}-[a-z0-9]{3}` token. Removed the deprecated `target:` block to match `config.example.yaml`'s decision (the scaffold doesn't emit it either). Preserved every per-tool `judges:`/`skip:`/`skip_reason:` entry verbatim -- only the comments above them were touched. Added two regression tests in `test_examples_dir.py` (`test_homelab_mcp_yaml_no_banned_tokens`, `test_homelab_mcp_yaml_no_target_block`) so future doc-scrub runs cannot regress this file.

### BL-02: operator-facing version-mismatch error leaks pydantic's "Value error," jargon

**Files modified:** `src/mcp_test_framework/cli.py`, `tests/unit/test_cli_errors.py`
**Commit:** 619ce1e
**Applied fix:** Added a small local `_scrub_pydantic_jargon` helper inside `_emit_operator_error_for_validation` that strips both pydantic v2 prefixes (`"Value error, "` and `"Assertion failed, "`) before interpolating the message into operator-facing detail blocks. Applied it to both interpolation sites (the version-mismatch branch on line ~131 and the generic-fallback per-error formatter on line ~177). Tightened `test_load_config_validation_error_version` to assert stderr contains neither `"Value error"` (v2) nor `"Assertion failed"` (v2 assert-style) nor `"value_error"` (v1 type-string).

### WR-01: `_pytest_exit_operator_tone` annotated `-> None` but never returns

**Files modified:** `src/mcp_test_framework/fixtures.py`
**Commit:** 44de31c
**Applied fix:** Imported `typing` and changed the helper's return annotation from `-> None` to `-> typing.NoReturn`, mirroring `cli._emit_operator_error`. Type-checkers will now correctly mark caller code after the helper as unreachable, matching the docstring's claim that this is a parallel implementation of `_emit_operator_error`.

### WR-02: `_emit_operator_error_for_validation` claims `target.tool_name` is "removed in v1.2" but the field is still active

**Files modified:** `src/mcp_test_framework/cli.py`
**Commit:** 6795e31
**Applied fix:** Chose review option (b) -- deleted the dead/misleading `if err_type == "extra_forbidden" and "tool_name" in loc:` branch and removed its bullet from the docstring's "Mapping rules" list. `TargetConfig.tool_name` remains a live optional field consumed by `fixtures.py` for single-target mode; option (a) (actually removing the field) is a wider v1.2 cut that belongs in a dedicated phase, not a code-review fix.

### WR-03: README "Per-tool configuration" still documents `skip` semantics that contradict the v2 opt-in direction

**Files modified:** `README.md`
**Commit:** e974c6e
**Applied fix:** Chose review option (a) -- added an explicit "Heads-up on opt-in scaffolds" callout under the §Per-tool configuration heading explaining that the schema this release ships is opt-out (`no entry = runs`) but the `config-init` scaffold emits `skip: true` for every discovered tool, so a freshly-generated config is opt-in by construction. Also flagged the likely future schema flip so the asymmetry is documented as a known v1 quirk rather than read as a bug.

### WR-04: `test_scaffold_empty_tool_list_returns_empty_mapping` accepts `tools: None`, defeating its own intent

**Files modified:** `tests/unit/test_config_init.py`
**Commit:** b65b7ca
**Applied fix:** Replaced `assert data["tools"] in (None, {})` with `assert data["tools"] == {}` plus a diagnostic message. The test now actively rejects `tools: None`, which would silently pass the old assertion if a future refactor dropped the literal `{}` from the scaffold template.

### WR-05: `test_cli_errors_static_call_sites_no_banned_tokens` reads source via fragile relative path

**Files modified:** `tests/unit/test_cli_errors.py`
**Commit:** f29eef4
**Applied fix:** Replaced the bare `Path("src/mcp_test_framework/cli.py")` with a walk up from `Path(__file__).resolve().parents[2]`, the same pattern `tests/unit/test_doc_scrub.py` already uses. Test now passes regardless of pytest's cwd.

### WR-06: `_format_tools_text` line 612 omits parentheses present on lines 528-529, relying on operator precedence

**Files modified:** `src/mcp_test_framework/cli.py`
**Commit:** 6e0e920
**Applied fix:** Added explicit parentheses so the line reads `props = (schema.get("properties") or {}) if isinstance(schema, dict) else {}`, matching the style of the parallel idiom on lines 528-529. Behaviour unchanged; the change is for readability and refactor safety.

---

_Fixed: 2026-05-09_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
