---
phase: 17-schema-driven-codegen-surface
fixed_at: 2026-05-12T00:00:00Z
review_path: .planning/phases/17-schema-driven-codegen-surface/17-REVIEW.md
iteration: 1
findings_in_scope: 10
fixed: 10
skipped: 0
status: all_fixed
---

# Phase 17: Code Review Fix Report

**Fixed at:** 2026-05-12
**Source review:** `.planning/phases/17-schema-driven-codegen-surface/17-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 10 (4 Critical + 6 Warning; Info deferred per `fix_scope: critical_warning`)
- Fixed: 10
- Skipped: 0

All in-scope findings landed cleanly. After every commit the codegen-surface
test suite (73 tests across `test_codegen_walker`, `test_codegen_emitter`,
`test_codegen_typecheck`, `test_tool_factory`, `test_tool_response`,
`test_gen_sdet_classes_cli`) passed; only one pre-existing deselected case
remained. Pre-existing baseline failures in `test_migration_doc.py` /
`test_tool_config.py` / `test_doc_scrub.py` / `test_cli_errors.py` are
documented as out-of-scope per 17-05-SUMMARY.md and were not touched.

## Fixed Issues

### CR-01: Source injection via unescaped `serverInfo.name` / `version` in generated file headers

**Files modified:** `src/mcp_test_framework/sdet/_codegen.py`
**Commit:** f32bb48
**Applied fix:** Added `import json` and a new `_render_header(...)` helper.
Reworked `HEADER_TEMPLATE` to use `{server_name_repr}` / `{server_version_repr}`
placeholders rather than embedding `"{server_name}"` / `"{server_version}"`
literals. The helper feeds `json.dumps(...)` of each value into the template,
producing a safely-escaped double-quoted literal that survives embedded `"`,
newlines, and unicode. Updated both call sites in `translate_tool` and
`_render_init` to use `_render_header(...)`. Verified the existing pin
`'serverInfo.name="homelab-mcp"'` in `test_codegen_walker.py` still matches
(safe inputs render byte-identically). Confirmed adversarial input
`'foo"\nimport os; os.system("rm")\n#'` stays inside a single comment line.

### CR-02: Source injection via unescaped tool name in generated `__init__.py` registry

**Files modified:** `src/mcp_test_framework/sdet/_codegen.py`
**Commit:** 7e196ad
**Applied fix:** Replaced `f'    "{tool_name}": (...)'` with
`f"    {json.dumps(tool_name)}: (...)"` inside `_render_init`. For spec-
compliant tool names (`[A-Za-z_][A-Za-z0-9_]*`) the visible form is
byte-identical to the prior interpolation, so the existing
`'"create_vm": (CreateVmParams, CreateVmResponse),'` test pin still matches.
Verified an adversarial tool name `x", __import__("os").system("rm"), "y`
produces a valid Python dict literal with the original key intact and no
injected call.

### CR-03: No identifier sanitization on field names

**Files modified:** `src/mcp_test_framework/sdet/_codegen.py`
**Commit:** 62a74a8
**Applied fix:** Added `import keyword` / `import re`, introduced
`_safe_field_ident(name) -> (ident, alias_or_None)` mirroring
`_slugs.module_name`'s strategy: non-ident chars → `_`, strip leading /
trailing `_`, keyword → suffix `_`. Diverged on leading-digit / empty
inputs: prefix with `f_` (not `_`) because Pydantic v2 raises `NameError`
on any field whose attribute name begins with underscore. Added
`_inject_alias(default_expr, alias)` to splice `alias=<json.dumps(original)>`
into the `Field(...)` call, handling both `Field(...)` and `Field(default=...)`
shapes. Updated `_format_field_line` to consult both and emit the rename
together with the alias. Verified that python keyword (`class`), leading
digit (`2fa_code`), kebab (`vm-id`), space (`vm id`), and all-non-ident
(`---`) names all parse cleanly and round-trip through
`Model.model_validate({wire_name: ...})` →
`m.model_dump(by_alias=True)` → original keys.

### CR-04: Description-string substring scan re-introduces the Gap-1 unused-import bug

**Files modified:** `src/mcp_test_framework/sdet/_codegen.py`
**Commit:** b6ed194
**Applied fix:** Introduced `_BodyEmission` dataclass with explicit
`uses_typing_any` and `has_fields` flags. Replaced the
`(body_text, degraded_count)` return shape of `_emit_params_body` /
`_emit_response_body` with a `_BodyEmission` instance whose flags are
computed at field-emission time over the typed `FieldSpec` (specifically
`spec.py_type` substring-check for `"typing."` — which is over the type
annotation only, not the rendered Field() call, so descriptions cannot
poison it). `translate_tool` now consults `params.uses_typing_any |
response.uses_typing_any` and `params.has_fields | response.has_fields`
directly, dropping the rendered-body substring scan. Verified that a tool
with one plain-`str` required field whose description contains the literal
text `"typing.Any-compatible value. Pass via Field(default)."` no longer
emits `import typing`.

### WR-01: Module-level monkey-patch of `ClientSession.initialize` is process-global

**Files modified:** `src/mcp_test_framework/cli.py`
**Commit:** cc10a41
**Applied fix:** Added a module-level `_codegen_handshake_lock = asyncio.Lock()`
above `_run_codegen_handshake` and wrapped the entire patched window
(`ClientSession.initialize` patch, `AsyncExitStack` body, and `finally`
restoration) in `async with _codegen_handshake_lock`. Concurrent
in-process callers now serialize linearly through the patched section
instead of corrupting each other's `holder` capture and racing the
`finally`. Single-CLI-invocation behavior is unchanged. Comment block
records the rationale and the constraint the lock guards.

### WR-02: `_render_init` types `_REGISTRY` value as `type`, not `type[BaseModel]`

**Files modified:** `src/mcp_test_framework/sdet/_codegen.py`,
`tests/framework/unit/test_codegen_emitter.py`
**Commit:** 46d70ed
**Applied fix:** Tightened both the populated and empty registry blocks to
`dict[str, tuple[type[BaseModel], type[ToolResponse]]]`, and added
`from pydantic import BaseModel` to the rendered `__init__.py` import
block. Updated `test_emitter_init_py_carries_registry` to pin the tighter
annotation plus the new `BaseModel` import.

### WR-03: `_emit_field` has an unused `name` parameter

**Files modified:** `src/mcp_test_framework/sdet/_codegen.py`
**Commit:** 783084a
**Applied fix:** Dropped the unused `name: str` parameter from
`_emit_field`'s signature and updated the single call site in
`_emit_params_body`. The JSON-Schema property name (and its safe-Python
ident / alias) is owned by `_format_field_line`, which receives `name`
separately.

### WR-04: `_codegen.py` has imports mid-file

**Files modified:** `src/mcp_test_framework/sdet/_codegen.py`
**Commit:** d45a41e
**Applied fix:** Hoisted `datetime`, `shutil`, `Path`, and `server_slug`
to the top of the module so they sit alongside `module_name` /
`pascal_case` in a single import block per PEP 8. Replaced the mid-file
import section with a one-line comment noting the imports were hoisted.

### WR-05: Dead `_ = (Draft202012Validator, validator_for)` keep-alive

**Files modified:** `src/mcp_test_framework/sdet/_codegen.py`
**Commit:** 722aeea
**Applied fix:** Dropped both the `from jsonschema.validators import ...`
line and the `_ = (...)` no-op pin. The rationale (why `check_schema()`
is deliberately not called) is now a top-of-file comment block, which is
the form the original intent was reaching for.

### WR-06: `_check_schema_structural` only runs when input_schema is truthy

**Files modified:** `src/mcp_test_framework/sdet/_codegen.py`
**Commit:** 673232f
**Applied fix:** Removed the `if input_schema:` guard so the structural
check runs unconditionally on dict inputs. The function already
short-circuits on non-dict input, so this aligns the gating with the
function's documented contract. A schema like `{"required": "not-a-list"}`
(no `type` / `properties`) now surfaces the malformed `required` field
instead of being silently accepted via the `pass`-body path.

## Skipped Issues

None — all 10 in-scope findings were fixed cleanly. Three Info findings
(IN-01, IN-02, IN-03) were out-of-scope per `fix_scope: critical_warning`
and were not attempted.

---

_Fixed: 2026-05-12_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
