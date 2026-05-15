---
phase: 20-preflight-conditional-skip
reviewed: 2026-05-13T00:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - tests/framework/unit/test_codegen_integration_mock.py
findings:
  critical: 0
  warning: 2
  info: 5
  total: 7
status: issues_found
---

# Phase 20: Code Review Report

**Reviewed:** 2026-05-13T00:00:00Z
**Depth:** standard
**Files Reviewed:** 1
**Status:** issues_found

## Summary

`tests/framework/unit/test_codegen_integration_mock.py` is a new 320-line unit module (Phase 20-05) that drives the `mcp_test_framework.sdet._codegen.generate(...)` pipeline end-to-end against a hand-crafted three-tool synthetic fixture, then loads the emitted modules via `importlib.util.spec_from_file_location` and asserts the Pydantic model surface.

Traced each test against `src/mcp_test_framework/sdet/_codegen.py`, `_slugs.py`, and `response.py`. **Every assertion-vs-implementation pairing checks out** — no false-positive tests, no skipped branches relative to the docstring's coverage claim, no logic bugs in the importlib helpers. The fixture genuinely covers required scalar, optional-with-default scalar, required array-of-scalar, omitted-outputSchema (D-06 stub), and declared-outputSchema-with-optional-fields (which the codegen renders as `T | None` via the `default_is_none` signal).

No critical issues. Two warnings on test tightness (one redundant fixture-vs-test assertion, one weak shape assertion that could mask spurious-field regressions). Five info items around dead imports, naming hygiene, and `sys.modules` housekeeping that bound module accumulation in long-lived pytest sessions.

## Warnings

### WR-01: `test_echo_message_params_class_shape` does not pin the field set, only checks membership

**File:** `tests/framework/unit/test_codegen_integration_mock.py:174-181`
**Issue:** The test name implies it verifies the `EchoMessageParams` "class shape," but the body only asserts `"message" in Params.model_fields`. If a future codegen regression spuriously emits an extra field (e.g., from a misrouted property walk), this test passes silently. Compare the matching assertion in `test_add_numbers_response_is_stub_inheriting_tool_response` (line 220) which DOES pin the exact set: `declared_fields == {"raw"}`. The same pinning belongs here.
**Fix:**
```python
def test_echo_message_params_class_shape(generated: Path) -> None:
    """Required scalar string field; outputSchema declared."""
    mod = _load_generated_module(generated, "echo_message")
    Params = mod.EchoMessageParams
    assert set(Params.model_fields) == {"message"}, list(Params.model_fields)
    field = Params.model_fields["message"]
    assert field.annotation is str
    assert field.is_required()
```
Apply the same tightening to `test_ping_with_timeout_params_int_default` (lines 225-233) which checks two fields by name but not the exact set.

### WR-02: `test_generate_counts_no_degraded_fields` duplicates the `generated` fixture's count assertion

**File:** `tests/framework/unit/test_codegen_integration_mock.py:306-319`
**Issue:** The `generated` fixture at line 166 already asserts `counts == {"tools": 3, "degraded_fields": 0}` on every test invocation (six other tests). `test_generate_counts_no_degraded_fields` calls `generate(...)` a second time with the same inputs and re-asserts the same equality. The "loud-fail on future degradation" intent is already satisfied implicitly — this test pays for a second `generate()` call (full wipe + write of three .py files + __init__.py to `tmp_path`) to verify a property already locked by the fixture pre-condition.

Worse, the redundancy hides a meaningful coverage gap: there is no test that exercises a *degraded* schema and confirms `degraded_fields > 0`. The fixture's "0 degradations" invariant is symmetrical — it can be broken in either direction (a previously-clean field starts degrading, OR the degradation counter stops incrementing). A targeted regression test for the latter is missing.
**Fix:** Either (a) drop `test_generate_counts_no_degraded_fields` entirely (the fixture already enforces it), or (b) replace its body with the missing inverse case:
```python
def test_generate_counts_reports_degraded_fields(tmp_path: Path) -> None:
    """A schema with an enum field must increment degraded_fields."""
    degraded_tool = Tool(
        name="enum_tool",
        description="One enum field.",
        inputSchema={
            "type": "object",
            "properties": {"mode": {"type": "string", "enum": ["a", "b"]}},
            "required": ["mode"],
        },
        outputSchema=None,
    )
    counts = generate(
        server_name=_SYNTHETIC_SERVER_NAME,
        server_version=_SYNTHETIC_SERVER_VERSION,
        tools=[degraded_tool],
        out_root=tmp_path,
        timestamp=_FIXED_TS,
    )
    assert counts == {"tools": 1, "degraded_fields": 1}
```

## Info

### IN-01: Unused `import importlib`

**File:** `tests/framework/unit/test_codegen_integration_mock.py:24`
**Issue:** `import importlib` is never referenced in the module — only `importlib.util` (line 25) is used. The docstring at line 13 mentions `importlib.import_module` but the test code never calls it. Ruff F401 will flag this once enabled on the test tree.
**Fix:** Delete line 24. Update the docstring at line 13 to reflect that modules are loaded via `importlib.util.spec_from_file_location`, not `importlib.import_module`.

### IN-02: Docstring claim diverges from actual loading mechanism

**File:** `tests/framework/unit/test_codegen_integration_mock.py:13`
**Issue:** Module docstring item (4) says "Generated modules import cleanly via `importlib.import_module`." The actual implementation uses `importlib.util.spec_from_file_location` + `exec_module` because the generated tree is in `tmp_path` and not on `sys.path`. Future readers chasing the `import_module` claim will be confused.
**Fix:** Reword line 13 to: "Generated modules load cleanly via `importlib.util.spec_from_file_location`."

### IN-03: `sys.modules` entries are never cleaned up after each test

**File:** `tests/framework/unit/test_codegen_integration_mock.py:108-151`
**Issue:** Both `_load_generated_module` and `_load_generated_init` clear any *prior* registration before loading but never remove their own registration after the test completes. Across a full pytest session this accumulates ~21 entries (7 tests × 3 module loads via `_load_generated_module` + several package + submodule entries from `_load_generated_init`). The synthetic prefix `_phase20_mock_*` plus `tmp_path`-derived unique names guarantees no collision, so this is bounded; the concern is the wrapper at `src/mcp_test_framework/_runner.py` invokes `pytest.main()` from a long-lived process during dev iteration, where repeated runs compound the leak.
**Fix:** Add a small autouse fixture (function-scoped, finalizer) that removes the registered names:
```python
@pytest.fixture(autouse=True)
def _cleanup_synthetic_modules() -> Generator[None, None, None]:
    yield
    for k in [k for k in list(sys.modules) if k.startswith("_phase20_mock_")]:
        del sys.modules[k]
```
Low priority — bounded by test count, no correctness impact.

### IN-04: `from pydantic import BaseModel` is buried inside a loop body

**File:** `tests/framework/unit/test_codegen_integration_mock.py:273-274`
**Issue:** `from pydantic import BaseModel` is performed inside the `for name, entry in registry.items():` loop body in `test_registry_dict_shape`. The import runs three times per test invocation. Python caches the module, so the net cost is one `sys.modules` lookup × 3, but the style is non-idiomatic and grep-unfriendly (someone scanning top-of-file imports for "what does this test need from pydantic" misses it).
**Fix:** Hoist `from pydantic import BaseModel` to the module's import block at line 30-34.

### IN-05: Brittle exact-equality on `counts` dict will fail on additive schema changes

**File:** `tests/framework/unit/test_codegen_integration_mock.py:166, 319`
**Issue:** `counts == {"tools": 3, "degraded_fields": 0}` (in the fixture and in `test_generate_counts_no_degraded_fields`) uses exact-equality on the returned counts dict. If `generate()` ever adds a new informational key (e.g., `"tools_skipped"`, `"warnings"`, or `"elapsed_ms"`), every test that uses the `generated` fixture breaks — even though no behavior under test has changed. The comment at lines 307-311 frames this as intentional ("if a future change degrades any of these fields, this test fails loudly"), but the comment defends only the `degraded_fields` direction; the `tools` key direction is a pure additive-change tripwire that catches non-regressions.
**Fix:** Either (a) accept this as a contract-lock and document it explicitly in the fixture docstring, or (b) loosen to per-key assertions:
```python
assert counts["tools"] == 3
assert counts["degraded_fields"] == 0
```
The looser form still fails loudly on a real regression (degraded_fields jumps to non-zero) but tolerates future bookkeeping additions to the return shape.

---

_Reviewed: 2026-05-13T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
