---
phase: 01-foundation-pure-data-core
plan: 03
subsystem: validation
tags: [jsonschema, pydantic, validation, json-pointer, mcp-tool]

requires:
  - "01-01: src/mcp_test_framework package, jsonschema 4.26.0 + mcp 1.27.0 runtime deps"
provides:
  - "src/mcp_test_framework/schema_validator.py with ValidationIssue + validate_tool_schema(tool: Tool) -> list[ValidationIssue]"
  - "All 7 spec structural checks coded as a pure function over mcp.types.Tool (no I/O, no subprocess)"
  - "JSON-Pointer-style paths (RFC 6901) on every issue -- the contract Phase 4 TEST-02 will assert against"
  - "_pointer_from_deque helper (per RESEARCH Pattern 4) reserved for any future iter_errors-driven check"
  - "12 unit tests (1 baseline + 7 per-check + 1 disjunction + 2 cross-cutting invariants)"
affects:
  - 04-tests-scaffold       # tests/unit/test_schema_validator.py is the second file under tests/unit/, alongside test_config.py
  - 04-integration-tests    # Phase 4 TEST-02 (test_tool_schema_is_structurally_valid) calls validate_tool_schema(target_tool) and asserts == []; Phase 4 TEST-04 (focused diagnostic on input-schema property documentation) intentionally overlaps on checks 6+7

tech-stack:
  added: []
  patterns:
    - "Pattern: validate_tool_schema is hand-coded against the dict (not iter_errors-driven). Inline f-string paths replace _pointer_from_deque for now -- the helper is retained for future iter_errors callers."
    - "Pattern: Check 3 short-circuits -- on a non-dict inputSchema or a meta-schema-invalid schema, the validator returns early because checks 4..7 require a dict to inspect."
    - "Pattern: severity is a required Literal['error'] field with NO default -- callers MUST construct severity explicitly. This honors D-02's forward-compat intent (adding 'warning' is a typed schema migration, not a semantic flip)."
    - "Test pattern: model_construct() is used to inject inputSchema=None past pydantic's mcp.types.Tool validation -- the validator's defensive 'not a dict' branch otherwise cannot be exercised because Tool(inputSchema=None) raises ValidationError."
    - "Test pattern: cross-cutting invariants use a TWO-tool union because Check 3 short-circuits -- one synthetic tool exercises checks 1, 2, 4, 5, 6, 7 (valid meta-schema, broken structure); a separate tool exercises check 3b (invalid meta-schema)."

key-files:
  created:
    - "src/mcp_test_framework/schema_validator.py (205 lines: ValidationIssue model + 7-check validator + JSON-Pointer helper)"
    - "tests/unit/test_schema_validator.py (356 lines: 12 tests, all sync)"
  modified: []
  deleted: []

key-decisions:
  - "validator_for(schema, default=Draft202012Validator) is the auto-detect entry point; Draft202012Validator is the FALLBACK only, not the hardcoded validator. Acceptance grep `validator_for(` matches the call site."
  - "Severity field has no default -- Literal['error'] is required at construction. This is intentional per CONTEXT.md D-02 to make adding 'warning' post-MVP a typed schema migration. Every call site in schema_validator.py constructs severity='error' explicitly."
  - "Paths are constructed inline as f-strings (e.g., f'/inputSchema/properties/{prop_name}/description') rather than via _pointer_from_deque. The helper is reserved for any future iter_errors-driven check (e.g., Phase 4 response-schema validation) that needs RFC 6901 escaping for arbitrary path components."
  - "Check 3 short-circuits and returns issues immediately. This means a single 'everything broken' tool cannot trigger all 7 checks at once -- the cross-cutting invariant tests use a two-tool union strategy to cover all 7."
  - "model_construct() is the chosen escape hatch for testing the 'inputSchema is not a dict' branch. mcp.types.Tool's pydantic validator rejects None for inputSchema, so the only way to exercise the validator's defensive 'not a dict' code path is to bypass validation via model_construct."

requirements-completed: [CORE-02]

duration: "3 min 0 sec"
completed: 2026-05-04
---

# Phase 1 Plan 3: Schema Validator Summary

**Pure-data schema validator for MCP tools: ValidationIssue Pydantic model (Literal["error"] severity, JSON-Pointer path, message) and validate_tool_schema(tool) function performing the spec's 7 deterministic structural checks with auto-detected JSON Schema draft via validator_for. 12 unit tests (1 baseline + 7 per-check + 1 disjunction + 2 cross-cutting invariants) all passing.**

## Performance

- **Duration:** 3 min 0 sec (180 seconds)
- **Started:** 2026-05-04T22:14:17Z
- **Completed:** 2026-05-04T22:17:17Z
- **Tasks:** 2
- **Files created:** 2
- **Files modified:** 0
- **Files deleted:** 0

## Accomplishments

- Implemented `src/mcp_test_framework/schema_validator.py` exactly per RESEARCH Pattern 4: the `ValidationIssue` Pydantic model with `severity: Literal["error"]`, `path: str` (JSON-Pointer), `message: str`; the `_pointer_from_deque` helper (RFC 6901 escaping); and `validate_tool_schema(tool: Tool) -> list[ValidationIssue]` performing the 7 spec checks in order with `validator_for(schema, default=Draft202012Validator).check_schema(schema)` for Check 3 and short-circuit returns when the schema dict is unusable.
- Wrote `tests/unit/test_schema_validator.py` with 12 tests in three groups:
  1. **Baseline (1):** `test_clean_tool_returns_empty_list` proves the Phase 4 TEST-02 contract (`validate_tool_schema(target_tool) == []`).
  2. **Per-check (8):** one test per spec check #1..#5, two tests for #6 and #7 (one missing-description, one missing-type), plus a disjunction-positive test (`oneOf` alone satisfies #7) -- proves each check fires *only* when its specific failure mode is present.
  3. **Cross-cutting invariants (2):** `test_all_issues_have_severity_error` guards D-01 (no `warning` tier in MVP output) and `test_all_issue_paths_use_json_pointer` guards RESEARCH Pitfall 2 (paths must be `/-`prefixed, contain no `$`, and contain no JSONPath dot-separators).
- Verified the JSON-Pointer-vs-JSONPath pitfall is mechanically guarded: the regression test asserts `not issue.path.startswith("$")`, no `".properties."` substring, no `".required."` substring, AND every non-empty path starts with `/`. `error.json_path` is not referenced anywhere in `schema_validator.py` (acceptance grep `! grep -E '\.json_path' src/mcp_test_framework/schema_validator.py` passes).
- Verified the full test suite is green and ruff is clean: `uv run pytest tests/ -v` reports 21/21 passing (9 prior config tests + 12 new validator tests); `uv run ruff check src tests` reports `All checks passed!`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement schema_validator.py** -- `3992323` (feat)
2. **Task 2: Write 12 unit tests for schema_validator** -- `60b1eb2` (test)

## Files Created/Modified

- `src/mcp_test_framework/schema_validator.py` -- 205 lines. Imports `validator_for` and `Draft202012Validator` from `jsonschema.validators`, `Tool` from `mcp.types`, `BaseModel` from `pydantic`. Defines `ValidationIssue(BaseModel)`, `_pointer_from_deque(absolute_path)`, and `validate_tool_schema(tool: Tool) -> list[ValidationIssue]`. The 7 checks are coded inline; paths are built as f-strings against the schema dict. Check 3 short-circuits; checks 4..7 only run if the schema dict is structurally valid. Created in commit `3992323`.
- `tests/unit/test_schema_validator.py` -- 356 lines. 12 sync test functions. Imports `Tool` from `mcp.types` and `ValidationIssue, validate_tool_schema` from `mcp_test_framework.schema_validator`. Helper functions `_clean_tool()`, `_everything_broken_tool()`, `_issues_covering_all_seven_checks()` factor out tool construction. Cross-cutting tests use a two-tool union to surface issues from all 7 checks despite Check 3's short-circuit. Created in commit `60b1eb2`.

## Decisions Made

- **Inline f-string paths instead of `_pointer_from_deque` at every call site.** The 7 structural checks are hand-coded against the schema dict (not driven by `iter_errors`), so the path components are always literal strings (e.g., `prop_name`, the index of a `required` entry) that don't contain `~` or `/` and don't need RFC 6901 escaping in practice. The `_pointer_from_deque` helper is kept in the module for any future check that switches to `iter_errors` and needs RFC 6901 escaping for arbitrary path components.
- **`severity` is a required field with no default.** Per CONTEXT.md D-02, every call site (in both the validator and the tests) writes `severity="error"` explicitly. If a future "warning" tier is added, every call site must be revisited -- this is the intent. A `severity: Literal["error"] = "error"` default would silently mask uncovered call sites.
- **Two-tool union strategy in cross-cutting tests.** Check 3 short-circuits, so a single "all 7 broken" tool cannot exist. The cross-cutting tests construct two tools (one for checks 1,2,4,5,6,7; one for check 3b) and concatenate their issue lists before asserting D-01 and the JSON-Pointer property. This keeps the regression coverage complete without weakening the short-circuit (which is a correctness requirement -- you cannot run checks 4..7 against a non-dict schema).
- **`Tool.model_construct(...)` to inject `inputSchema=None`.** `mcp.types.Tool`'s pydantic validator rejects `None` for `inputSchema`, so the only way to exercise the validator's defensive "not a dict" branch in `test_check_3_invalid_input_schema_not_dict` is to bypass validation via `model_construct`. This is documented inline in the test.

## Tool Construction Shape (for downstream phases)

The exact `Tool(...)` construction shape used in tests (per the plan's `<output>` request):

```python
from mcp.types import Tool

# Minimum valid tool: name, description, inputSchema with type=object, properties={}, required=[]
Tool(
    name="my_tool",
    description="A clean tool with a non-empty description.",
    inputSchema={
        "type": "object",
        "properties": {},
        "required": [],
    },
)
```

`mcp.types.Tool` is a pydantic `BaseModel`; `__init__` accepts `**data: Any`. Required fields per pydantic validation are `name`, `description`, `inputSchema`. Optional fields exist (`title`, `outputSchema`, `annotations`, `_meta`) but Phase 1 tests do not exercise them. Setting `inputSchema=None` raises `ValidationError`, hence the `model_construct` workaround in `test_check_3_invalid_input_schema_not_dict`.

## Test Count + Pass/Fail

- **12 tests collected, 12 passed, 0 failed** (`uv run pytest tests/unit/test_schema_validator.py -v`).
- Combined with prior plans: **21 tests collected, 21 passed, 0 failed** (`uv run pytest tests/ -v`).
- Pytest 9.0.3 + pytest-asyncio 1.3.0 strict mode active; no test marked `@pytest.mark.asyncio` (none of the validator tests are async).

## Confirmations Required by Plan Output Spec

1. **Tool(...) construction shape used in tests:** documented above. Required pydantic fields are `name`, `description`, `inputSchema`; no other fields needed for Phase 1.
2. **Test count and pass status:** 12/12 passing. See "Test Count + Pass/Fail" section.
3. **Any deviation from Pattern 4:** None functionally. The implementation is a verbatim lift of Pattern 4 from `01-RESEARCH.md`. The only addition is the inline `Exception` catch on `check_schema(...)` (RESEARCH Pattern 4 already specifies this) -- `noqa: BLE001` was added because ruff's `flake8-blind-except` rule (not enabled in this project, but defensive against future enabling) would otherwise flag the broad except. `jsonschema` raises `SchemaError` from `check_schema`; the broader catch is documented as "be defensive" since unusual schemas can occasionally trigger non-`SchemaError` exceptions in the meta-schema walker.
4. **Confirmation that no `error.json_path` references exist in the module:** CONFIRMED. `grep -E '\.json_path' src/mcp_test_framework/schema_validator.py` returns 0 matches. The only path-construction code is inline f-strings; the `_pointer_from_deque` helper takes a generic `absolute_path` argument with no `json_path` reference.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Ruff `I001` import-block ordering on `tests/unit/test_schema_validator.py`**

- **Found during:** Task 2 verify step (`uv run ruff check src tests` reported `I001 [*] Import block is un-sorted or un-formatted`)
- **Issue:** Ruff's import-sorting rule wanted the `from __future__ import annotations` line and the subsequent regular imports separated by formatting that ruff's auto-fix knew how to apply (a single contiguous block). My initial layout had a blank line between `from __future__ import annotations` and `from mcp.types import Tool`, which ruff treated as an unformatted block.
- **Fix:** Ran `uv run ruff check --fix tests/unit/test_schema_validator.py` -- auto-fix collapsed the import block. Functional behavior unchanged; only whitespace.
- **Files modified:** `tests/unit/test_schema_validator.py` (one blank-line removal)
- **Verification:** `uv run ruff check src tests` passes; `uv run pytest tests/unit/test_schema_validator.py -v` still 12/12 passing.
- **Committed in:** `60b1eb2` (Task 2 commit; the ruff fix was applied before staging)

---

**Total deviations:** 1 auto-fixed (Rule 3 - Blocking)

**Impact on plan:** None on outcome. Pure formatting change applied via ruff's own auto-fixer. All `<success_criteria>` items met:

- [x] CORE-02: `validate_tool_schema(tool)` returns the 7 structural-issue checks against a synthetic tool with `severity`, `path`, `message` populated.
- [x] CORE-02: JSON Schema draft is auto-detected via `validator_for`; `Draft202012Validator` is the fallback default, not hardcoded.
- [x] D-02: `severity` is typed `Literal["error"]` (no default).
- [x] CONTEXT.md ValidationIssue.path representation: `path` uses JSON-Pointer syntax.
- [x] D-03: Phase 4 TEST-02 contract (`validate_tool_schema(target_tool) == []` on a clean tool) is the literal first test in the suite.

## Issues Encountered

- **Pydantic blocks `inputSchema=None` on `mcp.types.Tool`.** Direct construction via `Tool(name='ok', description='ok', inputSchema=None)` raises `ValidationError` because pydantic enforces the field type at construction. The workaround is `Tool.model_construct(...)`, which bypasses validation. The choice is documented inline in `test_check_3_invalid_input_schema_not_dict`. An alternative would have been to add a `# type: ignore` and use `cast` -- but `model_construct` is the pydantic-blessed escape hatch and is explicitly designed for this use case.
- **Windows CRLF warnings on every staged text file.** Same as Plans 01-01 and 01-02. Harmless; git auto-normalizes on next checkout.

## User Setup Required

None. No external services configured in this plan. The schema validator is pure-data: no I/O, no subprocess, no network.

## TDD Gate Compliance

The plan declares `type: execute` (not `type: tdd`) at the plan level, so plan-level TDD-gate enforcement is N/A. However, individual tasks carry `tdd="true"` markers. The chosen execution order was implementation-then-tests (Task 1 before Task 2), as the plan body itself specifies (Task 1's `<behavior>` lists the tests *that Task 2 will assert*; Task 2's `<read_first>` includes `src/mcp_test_framework/schema_validator.py` as the module under test). Tests passed on first run after Task 1's implementation -- no Rule 1 fix loop was needed (in contrast to Plan 01-02 where 4/9 tests initially failed). The implementation matched the spec on first try because Pattern 4 in RESEARCH.md is verbatim-liftable.

## Verification Evidence

- `uv run pytest tests/unit/test_schema_validator.py -v`: 12 passed, 0 failed (370ms wall)
- `uv run pytest tests/ -v`: 21 passed, 0 failed (combined with Plans 01-01 + 01-02)
- `uv run python -c "from mcp_test_framework.schema_validator import ValidationIssue, validate_tool_schema; from mcp.types import Tool; t = Tool(name='t', description='d', inputSchema={'type':'object','properties':{},'required':[]}); assert validate_tool_schema(t) == []; bad = Tool(name='', description='', inputSchema={'type':'string'}); issues = validate_tool_schema(bad); assert len(issues) >= 3; assert all(i.severity == 'error' for i in issues); assert all(i.path.startswith('/') for i in issues if i.path); print('OK')"` -- exits 0 with output `OK`
- `grep -q 'from jsonschema.validators import' src/mcp_test_framework/schema_validator.py` -- exit 0 (and the import contains `validator_for`)
- `grep -q 'from mcp.types import Tool' src/mcp_test_framework/schema_validator.py` -- exit 0
- `grep -E 'Literal\[.error.\]' src/mcp_test_framework/schema_validator.py` -- 1 match
- `grep -E '\.json_path' src/mcp_test_framework/schema_validator.py` -- 0 matches (correct -- not used)
- `grep -E '_pointer_from_deque|absolute_path' src/mcp_test_framework/schema_validator.py` -- 4 matches (helper defined, helper called signature includes `absolute_path` param)
- `grep -E 'validator_for\(' src/mcp_test_framework/schema_validator.py` -- 1 match (the call site)
- `grep -c '^def test_' tests/unit/test_schema_validator.py` returns 12 (exactly the spec-required count)
- `grep -E '@pytest.mark.asyncio' tests/unit/test_schema_validator.py` returns 0 matches (correct -- all tests are sync)
- `grep -E 'from mcp.types import Tool' tests/unit/test_schema_validator.py` -- 1 match
- `uv run ruff check src tests`: `All checks passed!`

## Next Phase Readiness

- **Plan 01-04 (tests scaffold + smoke)** is unblocked: `tests/unit/` already has two test modules (`test_config.py`, `test_schema_validator.py`); the next thing to land is `tests/conftest.py` with the `sys.modules` belt-and-suspenders guard for the TID251 submodule gap (Pitfall 4 from `01-RESEARCH.md`) and the deliberately-failing import-ban smoke test.
- **Phase 4 TEST-02** is fully unblocked: `validate_tool_schema` accepts `mcp.types.Tool` directly, so no translation layer is needed in Phase 4. The contract (`validate_tool_schema(target_tool) == []`) is locked.
- **Phase 4 TEST-04** (focused property-documentation diagnostic) intentionally overlaps on checks 6+7 per D-05 -- no Phase 1 work to do for that overlap; the redundancy is by design.
- No outstanding blockers.

## Threat Surface Scan

No new security-relevant surface introduced. The plan implements a pure-data function over a Pydantic model from the MCP SDK; no I/O, no subprocess, no network. The plan's `<threat_model>` already disposed T-03-01 as `accept` (DoS via deeply recursive schemas -- Phase 1 has no untrusted input), T-03-02 as `mitigate` (test_check_3_invalid_meta_schema verifies check_schema doesn't raise -- shipped and passing), and T-03-03 as `accept` (exception detail in dev/test diagnostics is desirable). All mitigations honored.

## Self-Check: PASSED

Verified via filesystem and git:

- `src/mcp_test_framework/schema_validator.py` -- FOUND (committed in `3992323`)
- `tests/unit/test_schema_validator.py` -- FOUND (committed in `60b1eb2`)
- Commit `3992323` -- FOUND in `git log` (`feat(01-03): implement schema_validator with 7 structural checks`)
- Commit `60b1eb2` -- FOUND in `git log` (`test(01-03): add 12 unit tests for schema_validator (7 checks + cross-cutting)`)

---
*Phase: 01-foundation-pure-data-core*
*Completed: 2026-05-04*
