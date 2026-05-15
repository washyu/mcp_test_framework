---
phase: 17-schema-driven-codegen-surface
plan: 06
subsystem: codegen
tags: [codegen, pyright, imports, gap-closure, 17-HUMAN-UAT]
gap_closure: true
gap_closed: Gap-1
dependency_graph:
  requires:
    - 17-02 (walker + translate_tool)
    - 17-05 (pyright strict gate)
  provides:
    - "Conditional import-block emission in translate_tool() — `import typing` and `Field` emitted only when the rendered body references them"
    - "Synthetic pyright fixture coverage of the empty-params / no-Field / no-typing.Any shape"
  affects:
    - "src/mcp_test_framework/sdet/_codegen.py::translate_tool"
    - "tests/framework/unit/test_codegen_emitter.py"
    - "tests/framework/unit/test_codegen_typecheck.py"
    - "tests/framework/unit/test_codegen_walker.py (one test updated to match new conditional contract)"
tech-stack:
  added: []
  patterns:
    - "Post-render string inspection for import-block emission decisions (robust against future walker changes)"
key-files:
  created:
    - .planning/phases/17-schema-driven-codegen-surface/17-06-SUMMARY.md
  modified:
    - src/mcp_test_framework/sdet/_codegen.py
    - tests/framework/unit/test_codegen_emitter.py
    - tests/framework/unit/test_codegen_typecheck.py
    - tests/framework/unit/test_codegen_walker.py
decisions:
  - "String-scan approach (vs structured tracking) for needs_typing/needs_field — robust to future walker degradation paths; if a new path emits typing.Any or Field(...), the import follows automatically"
  - "Walker test test_emits_future_annotations_and_pydantic_imports updated to drive translate_tool with a tool that DOES use both Field(...) and typing.Any rather than relying on the buggy unconditional emission for an empty-schema tool"
metrics:
  duration: ~15 minutes (executor-time)
  completed: 2026-05-12
  tasks_completed: 4/4
  commits: 3 (per-task)
---

# Phase 17 Plan 06: Conditional Import Emission (Gap-1 Closure) Summary

Closed Gap-1 from 17-HUMAN-UAT: `translate_tool` now emits `import typing` and `Field` only when the rendered body references them, eliminating the 29 `reportUnusedImport` pyright-strict errors that the live `gen-sdet-classes` UAT against homelab-mcp produced on 2026-05-12.

## What Changed

### `src/mcp_test_framework/sdet/_codegen.py` (Task 1, commit fcadd31)

Inside `translate_tool()`, added a 5-line block before the `source = (...)` assembly that inspects the already-rendered `params_body + response_class` for `"typing."` and `"Field("` substrings, then composes the pydantic import line and the `import typing` line conditionally:

```python
body_text = params_body + response_class
needs_typing = "typing." in body_text
needs_field = "Field(" in body_text

pydantic_imports = "BaseModel, ConfigDict"
if needs_field:
    pydantic_imports += ", Field"
typing_import_line = "import typing\n\n" if needs_typing else ""
```

The `source = (...)` f-string was then updated to interpolate `{typing_import_line}` and `{pydantic_imports}` instead of the hard-coded literals.

**Invariants preserved:** `from __future__ import annotations`, `from mcp_test_framework.sdet.response import ToolResponse`, `BaseModel`, and `ConfigDict` are still unconditional — every Params class subclasses `BaseModel` and sets `model_config = ConfigDict(extra="forbid")`.

### `tests/framework/unit/test_codegen_emitter.py` (Task 2, commit 5a6c752)

Three new tests appended after `test_emitter_loud_fail_on_empty_server_name`:

1. `test_emitter_omits_unused_typing_import_when_no_typing_any` — negative gate: empty-params tool must NOT contain `import typing` anywhere in the rendered file.
2. `test_emitter_omits_unused_field_import_when_no_field_calls` — negative gate: empty-params tool's pydantic import line must be `from pydantic import BaseModel, ConfigDict\n` with no `Field`.
3. `test_emitter_still_emits_typing_and_field_when_used` — positive control: a tool that exercises BOTH a degraded enum (`typing.Any`) AND `Field(default=1)` must still emit both imports.

The negative tests are real regression gates — reverting Task 1 would cause both `import typing` and `Field` to be re-emitted on the empty-params tool, breaking both `omits_unused_*` tests.

### `tests/framework/unit/test_codegen_typecheck.py` (Task 3, commit 8d15054)

Extended `_synthetic_tools()` from 5 to 6 tools, adding `basic_tool` (zero properties, zero required). Updated:
- The fixture docstring to enumerate all 6 tools and cross-reference Gap-1 / 17-HUMAN-UAT.
- The `counts["tools"] == 5` invariant to `== 6` (the `degraded_fields == 3` invariant is unchanged because `basic_tool` has zero fields and contributes zero degradations).

The pyright strict gate now covers the exact shape that bypassed Plan 17-05's gate in live UAT.

### `tests/framework/unit/test_codegen_walker.py` (Task 1, commit fcadd31)

One test updated: `TestWalkerHeader::test_emits_future_annotations_and_pydantic_imports` previously called `translate_tool(_t("create_vm"))` (empty-schema default) and tacitly relied on the buggy unconditional emission to satisfy its `Field` and `typing` assertions. Updated to drive `translate_tool` with a tool that exercises both `Field(...)` and a degraded enum (`typing.Any`) so the assertions match the new conditional contract.

## Test Counts

| Surface | Pre-Plan baseline | Post-Plan |
| --- | --- | --- |
| `tests/framework/unit/test_codegen_emitter.py` | 9 passed | 12 passed (+3 new) |
| `tests/framework/unit/test_codegen_walker.py` | 34 passed | 34 passed (1 test updated, same count) |
| `tests/framework/unit/test_codegen_typecheck.py` | 2 passed | 2 passed (6-tool fixture; pyright clean) |
| `tests/framework/unit/test_codegen_*.py` + `test_tool_response.py` + `test_gen_sdet_classes_cli.py` | 62 passed | 65 passed (+3 new) |
| `tests/framework/` total | 377 passed, 10 failed (baseline), 1 skipped, 16 deselected, 1 xfailed | 377 passed, 10 failed (baseline), 1 skipped, 16 deselected, 1 xfailed |

The 10 baseline failures (`test_migration_doc.py` × 4, `test_tool_config.py` × 4, `test_cli_errors.py` × 1, `test_doc_scrub.py` × 1) are all caused by a missing `tests/docs/MIGRATION-v1-to-v2.md` from the worktree base commit — these are pre-existing and documented in `17-05-SUMMARY.md` as out-of-scope. Confirmed unchanged by Plan 17-06's edits (verified by `git checkout HEAD~3 -- ...` regression check).

## Live UAT Re-Verification (HUMAN-UAT Gap-1)

**Status: EXECUTED — Gap-1 closed.**

Per `17-HUMAN-UAT.md` "Re-verification expectation (Live UAT — re-run after fix)":

```powershell
$env:MCPTF_CONFIG_FILE = "config.yaml"
uv run mcp-test-framework gen-sdet-classes
uv run pyright src/mcp_test_framework/sdet/generated/homelab_mcp/
```

Executed against live homelab-mcp v1.7.0 (uvx homelab-mcp) on 2026-05-12.

**gen-sdet-classes output (relevant tail):**

```
gen-sdet-classes: wrote SDET classes for homelab-mcp

  server:    homelab-mcp v1.7.0
  slug:      homelab_mcp
  target:    src/mcp_test_framework/sdet/generated/homelab_mcp/
  tools:     58 generated
  degraded:  35 fields (grep "codegen: degraded" for details)
```

**pyright output:**

```
0 errors, 0 warnings, 0 informations
```

The pre-Plan-17-06 baseline was **29 errors** (all `reportUnusedImport` per 17-HUMAN-UAT). Post-Plan-17-06: **0 errors**. Gap-1 is fully closed at the live-UAT level.

## Operator Follow-Up

To flip `17-HUMAN-UAT.md` from `status: diagnosed` → `status: resolved`, the operator (or a subsequent docs commit) should update the frontmatter `status:` field. The live re-run captured above is the acceptance signal.

## TDD Gate Compliance

This plan was not a TDD-typed plan (frontmatter `type: execute`, not `type: tdd`), so RED/GREEN/REFACTOR sequencing is not mandatory. However, the per-task commits naturally split as:
- `fix(17-06)`: Task 1 (production code fix + walker-test update)
- `test(17-06)`: Task 2 (3 new regression tests, all pass against Task 1's fix)
- `test(17-06)`: Task 3 (synthetic fixture extension, passes against Task 1's fix)

Tasks 2 and 3 are post-hoc regression gates pinning the contract Task 1 establishes; they do not exhibit RED-before-GREEN ordering by design (Task 1 ships first because the bug is operator-facing).

## Self-Check: PASSED

- `src/mcp_test_framework/sdet/_codegen.py` modified with conditional import emission (grep `needs_typing` returns 2 — one definition + one usage; grep `needs_field = ` returns 1; grep `body_text = params_body` returns 1).
- `tests/framework/unit/test_codegen_emitter.py` contains 3 new tests (grep returns 1 each for the three new test function names; grep `Gap-1` returns 3).
- `tests/framework/unit/test_codegen_typecheck.py` synthetic fixture grew to 6 tools (grep `basic_tool` returns 2; `counts["tools"] == 6` returns 1; old `counts["tools"] == 5` returns 0; `6-tool synthetic fixture` returns 1).
- Three task commits exist: fcadd31, 5a6c752, 8d15054.
- `uv run pytest tests/framework/unit/test_codegen_walker.py tests/framework/unit/test_codegen_emitter.py tests/framework/unit/test_codegen_typecheck.py tests/framework/unit/test_tool_response.py tests/framework/unit/test_gen_sdet_classes_cli.py -v` → 65 passed.
- `uv run pyright src/mcp_test_framework/sdet/generated/homelab_mcp/` → 0 errors, 0 warnings, 0 informations.
