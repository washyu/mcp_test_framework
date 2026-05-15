---
status: complete
phase: 17-schema-driven-codegen-surface
source: [17-VERIFICATION.md]
started: 2026-05-13
updated: 2026-05-12
gap_closure_plan: 17-06
---

## Current Test

[complete -- Gap-1 closed by Plan 17-06; live re-verification passed]

## Tests

### 1. Live `gen-sdet-classes` against real homelab-mcp
expected: Operator runs `mcp-test-framework gen-sdet-classes` against live homelab-mcp with a real `config.yaml`, then inspects `src/mcp_test_framework/sdet/generated/homelab_mcp/`. Every advertised tool produces a `<tool>.py` file with PascalCase Params + Response classes; `__init__.py` re-exports + `_REGISTRY` populated; stdout digest shows server name + version + slug + tool count + degraded count; rerunning produces byte-identical output modulo the Regenerated timestamp line.
result: passed -- live codegen ran against homelab-mcp; output tree populated; per-tool files emitted with Params/Response pair and CODEGEN-06 header

### 2. Pyright strict against the live-generated tree
expected: Operator runs `uv run pyright src/mcp_test_framework/sdet/generated/homelab_mcp/` after the live codegen run. Exit 0 -- every Params/Response class type-checks clean under strict mode, including degraded `typing.Any` fields. Real homelab-mcp schemas surface enum/oneOf/anyOf/nested-object combinations the synthetic 5-tool fixture doesn't model.
result: passed -- Plan 17-06 shipped conditional `import typing` / `Field` emission in `translate_tool()` plus a 6th synthetic fixture tool (`basic_tool`, empty-params shape) that pins the regression at unit-test time. Live re-verification on 2026-05-12 (executor-run inside Plan 17-06's worktree): `uv run pyright src/mcp_test_framework/sdet/generated/homelab_mcp/` returned **0 errors, 0 warnings, 0 informations**, down from 29 reportUnusedImport errors pre-fix. See `17-06-SUMMARY.md` for the captured pyright output and commit chain (fcadd31, 5a6c752, 8d15054).

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

### Gap-1: Emitter unconditionally writes unused imports (CODEGEN-04 / SC1 violation) — RESOLVED 2026-05-12

**Status:** resolved by Plan 17-06 (commits fcadd31 / 5a6c752 / 8d15054). Live re-verification: 0 pyright errors against homelab-mcp generated tree.

**Severity:** blocking-for-SC1 -- "generated files compile under mypy/pyright with no errors" fails for 27/~50 tools against the live homelab-mcp surface.

**Reproducer:**
```powershell
$env:MCPTF_CONFIG_FILE = "config.yaml"
uv run mcp-test-framework gen-sdet-classes
uv run pyright src/mcp_test_framework/sdet/generated/homelab_mcp/
# -> 29 errors, 0 warnings, 0 informations
```

**Two error patterns observed:**
- `Import "typing" is not accessed` -- tool's params body uses only `str`/`int`/`bool` (no `typing.Any` fallback)
- `Import "Field" is not accessed` -- tool has zero params, or params don't carry descriptions/defaults that warrant `Field(...)`

**Fix sketch:**
1. In `_codegen.py` after rendering `params_body` + `response_body`, inspect the rendered string for `typing.` and `Field(` occurrences.
2. Emit `import typing` only when `"typing."` appears in the body.
3. Emit `Field` in the pydantic import only when `"Field("` appears in the body. If neither `Field` nor anything beyond `BaseModel, ConfigDict` is needed, simplify the import line accordingly.

**Test coverage gap to close in the same plan:**
- Add a fixture tool to `test_codegen_typecheck.py` with ALL-basic-type params and no degradation, asserting the generated file pyright-clean. (Today's 5-tool fixture never produces this shape.)
- Add an explicit emitter test pinning "unused imports are NOT emitted" for the simple-types-only case.

**Suggested plan title:** `17-06 gap-PLAN.md -- conditional import emission in codegen (gap_closure: true)`
