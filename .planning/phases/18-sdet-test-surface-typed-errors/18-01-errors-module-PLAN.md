---
phase: 18-sdet-test-surface-typed-errors
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/mcp_test_framework/sdet/errors.py
autonomous: true
requirements: [UI-02]
must_haves:
  truths:
    - "ToolCallError is importable from mcp_test_framework.sdet.errors"
    - "ToolCallError is a plain Exception subclass (NOT Pydantic BaseModel)"
    - "ToolCallError carries .tool / .code / .message / .raw attributes"
    - "str(ToolCallError) is '[code] message' when code present, bare message otherwise"
    - "_extract_code_message implements the D-08 strict heuristic chain"
    - "Only 'code' and 'message' keys are recognized — no synonyms"
  artifacts:
    - path: "src/mcp_test_framework/sdet/errors.py"
      provides: "ToolCallError class (D-07) + _extract_code_message helper (D-08)"
      exports: ["ToolCallError", "_extract_code_message"]
  key_links:
    - from: "sdet/errors.py"
      to: "mcp.types.CallToolResult, mcp.types.TextContent"
      via: "import statements"
      pattern: "from mcp.types import CallToolResult, TextContent"
---

<objective>
Ship the typed `ToolCallError` exception (UI-02) and its companion `_extract_code_message` heuristic helper as a sibling module to `response.py` under `src/mcp_test_framework/sdet/`. Plain Exception subclass with `.tool` / `.code` / `.message` / `.raw` fields, per D-07's locked snippet. The D-08 heuristic chain (`structuredContent` dict -> first-TextContent JSON -> concat fallback) is implemented exactly as written in CONTEXT.md — no synonyms, strict `code`/`message` keys only.

Purpose: This is Wave 1. Every downstream plan that surfaces tool-side errors (`_tool_factory.py` raises it, `tests/sdet/conftest.py` catches it, `_runner.py` reads its JUnit-property breadcrumbs) imports from here. Ship it first so the other plans have a stable import target.

Output: One new file (`src/mcp_test_framework/sdet/errors.py`).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/18-sdet-test-surface-typed-errors/18-CONTEXT.md
@.planning/phases/18-sdet-test-surface-typed-errors/18-PATTERNS.md
@src/mcp_test_framework/sdet/response.py

<interfaces>
<!-- D-07 verbatim from 18-CONTEXT.md (lines 79-99) — THIS IS THE LOCKED SHAPE.
     Do not deviate; do not add synonyms; do not "improve" the formatter. -->

ToolCallError signature:
```python
class ToolCallError(Exception):
    def __init__(
        self,
        *,
        tool: str,
        code: str | None,
        message: str,
        raw: CallToolResult,
    ) -> None:
        self.tool = tool
        self.code = code
        self.message = message
        self.raw = raw
        super().__init__(self._format_default())

    def _format_default(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message
```

D-08 heuristic (verbatim from 18-PATTERNS.md):
```python
def _extract_code_message(raw: CallToolResult) -> tuple[str | None, str]:
    """D-08 heuristic chain. Returns (code, message)."""
    # Step 1: structuredContent dict
    sc = getattr(raw, "structuredContent", None)
    if isinstance(sc, dict):
        code = sc.get("code")
        message = sc.get("message")
        if isinstance(message, str):
            return (str(code) if code is not None else None, message)

    # Step 2: first TextContent JSON
    for block in raw.content:
        if isinstance(block, TextContent):
            try:
                parsed = json.loads(block.text)
            except (json.JSONDecodeError, ValueError):
                parsed = None
            if isinstance(parsed, dict):
                code = parsed.get("code")
                message = parsed.get("message")
                if isinstance(message, str):
                    return (str(code) if code is not None else None, message)
            break  # only try the first TextContent

    # Step 3: concat fallback
    concat = "".join(b.text for b in raw.content if isinstance(b, TextContent))
    return (None, concat)
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create sdet/errors.py with ToolCallError + _extract_code_message</name>
  <files>src/mcp_test_framework/sdet/errors.py</files>
  <read_first>
    - src/mcp_test_framework/sdet/response.py (sibling-module convention: header docstring shape, future-import, one-class-per-file style)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-CONTEXT.md (D-07 locked snippet lines 79-99; D-08 locked algorithm lines 102-107)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-PATTERNS.md (errors.py target shape lines 146-223; Pitfall 7 TextContent filter note lines 225-227)
  </read_first>
  <behavior>
    - Test: `ToolCallError(tool="t", code="X", message="m", raw=fake_result)` -> `.tool == "t"`, `.code == "X"`, `.message == "m"`, `.raw is fake_result`, `str(e) == "[X] m"`, `e.args[0] == "[X] m"`.
    - Test: code=None -> `str(e) == "m"` (bare message; no brackets).
    - Test: `isinstance(e, Exception) is True` AND `not hasattr(e, "model_dump")` (not Pydantic).
    - Test: D-08 step 1 — `raw.structuredContent = {"code": "VM_NAME_TAKEN", "message": "name in use"}` -> `("VM_NAME_TAKEN", "name in use")`.
    - Test: D-08 step 1 coercion — `{"code": 404, "message": "x"}` -> `("404", "x")` (int->str via str()).
    - Test: D-08 step 1 missing message — `{"code": "X"}` only -> falls through to step 2/3.
    - Test: D-08 step 2 — structuredContent=None, content=[TextContent(text='{"code":"X","message":"Y"}')] -> `("X", "Y")`.
    - Test: D-08 step 2 list/scalar non-dict — content[0].text='[1,2,3]' -> falls through (break after first TextContent; no looping past it).
    - Test: D-08 step 3 plain — content=[TextContent(text="boom")] only -> `(None, "boom")`.
    - Test: D-08 step 3 multi-text — two TextContent blocks "a"+"b" -> `(None, "ab")`.
    - Test: D-08 step 3 mixed types — TextContent("a") + ImageContent(...) -> `(None, "a")` (Pitfall 7: only TextContent.text contributes; never AttributeError).
    - Test: D-08 strict key set — `{"errorCode": "X", "detail": "Y"}` -> falls all the way through to step 3 (no synonym recognition).
  </behavior>
  <action>
Create `src/mcp_test_framework/sdet/errors.py` with the exact shape from 18-PATTERNS.md lines 146-223. Module structure:

1. Module docstring referencing Phase 18 D-07 (plain Exception not Pydantic) and D-08 (strict heuristic chain; strict `code`/`message`; non-string `code` coerced via `str(...)`; non-string `message` falls through; only `code` and `message` recognized — NO synonyms like `error`/`detail`/`reason`/`errorCode`; no recursive walk).
2. `from __future__ import annotations`.
3. `import json`.
4. `from mcp.types import CallToolResult, TextContent`.
5. `class ToolCallError(Exception)` — VERBATIM body from D-07 (CONTEXT.md lines 79-99). Constructor takes ONLY keyword-only args (`*,`). Stores `.tool`, `.code`, `.message`, `.raw` on self. Calls `super().__init__(self._format_default())`. `_format_default()` returns `f"[{self.code}] {self.message}"` when `self.code` is truthy, else just `self.message`.
6. `def _extract_code_message(raw: CallToolResult) -> tuple[str | None, str]` — VERBATIM algorithm from 18-PATTERNS.md lines 196-222. Three steps:
   - Step 1: `sc = getattr(raw, "structuredContent", None); if isinstance(sc, dict):` — read `code` and `message` keys. Only return when `isinstance(message, str)` is True. Coerce code via `str(code) if code is not None else None`.
   - Step 2: Iterate `raw.content` with `for block in raw.content:` — `if isinstance(block, TextContent):` (NEVER `getattr(block, "text")` — Pitfall 7 for heterogeneous content types `ImageContent`/`AudioContent`/`ResourceLink`/`EmbeddedResource`). `try: parsed = json.loads(block.text) except (json.JSONDecodeError, ValueError): parsed = None`. If `isinstance(parsed, dict)` AND `isinstance(message, str)`, return. CRITICAL: `break` after first TextContent — do NOT iterate further looking for parseable JSON. Only inspect the first TextContent block.
   - Step 3: `concat = "".join(b.text for b in raw.content if isinstance(b, TextContent))`. Return `(None, concat)`.

Do NOT add docstrings with `>>>` doctest examples; do NOT add `code` synonym recognition; do NOT add a recursive walk into nested dicts; do NOT subclass anything other than `Exception`.

Module exports both `ToolCallError` and `_extract_code_message` (the leading underscore is intentional — `_extract_code_message` is internal-but-importable for `_tool_factory.py` and tests; only `ToolCallError` is re-exported through `sdet/__init__.py` in Plan 18-04).
  </action>
  <verify>
    <automated>uv run python -c "from mcp_test_framework.sdet.errors import ToolCallError, _extract_code_message; e = ToolCallError(tool='t', code='X', message='m', raw=None); assert str(e) == '[X] m'; e2 = ToolCallError(tool='t', code=None, message='m', raw=None); assert str(e2) == 'm'; assert isinstance(e, Exception); assert not hasattr(e, 'model_dump'); print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - File exists: `src/mcp_test_framework/sdet/errors.py`
    - `grep -c "class ToolCallError(Exception)" src/mcp_test_framework/sdet/errors.py` returns 1
    - `grep -c "def _extract_code_message" src/mcp_test_framework/sdet/errors.py` returns 1
    - `grep -c "from mcp.types import CallToolResult, TextContent" src/mcp_test_framework/sdet/errors.py` returns 1
    - `grep -c "isinstance(block, TextContent)" src/mcp_test_framework/sdet/errors.py` returns at least 1 (Pitfall 7 filter)
    - `grep -c "isinstance(b, TextContent)" src/mcp_test_framework/sdet/errors.py` returns at least 1 (step 3 concat filter)
    - `grep -c "break" src/mcp_test_framework/sdet/errors.py` returns at least 1 (step 2 early termination after first TextContent)
    - `grep -cE 'errorCode|detail|reason|"error"' src/mcp_test_framework/sdet/errors.py` returns 0 (D-08 strict key set — no synonyms)
    - `grep -c "BaseModel" src/mcp_test_framework/sdet/errors.py` returns 0 (D-07 plain Exception, not Pydantic)
    - `grep -cE "str\(code\)" src/mcp_test_framework/sdet/errors.py` returns at least 1 (non-string code coercion)
    - `grep -cE "f.\[\{self\.code\}\] \{self\.message\}." src/mcp_test_framework/sdet/errors.py` returns 1 (D-07 format string verbatim)
    - `uv run python -c "from mcp_test_framework.sdet.errors import ToolCallError; print('OK')"` exits 0 and prints `OK`
  </acceptance_criteria>
  <done>
    `src/mcp_test_framework/sdet/errors.py` is importable, `ToolCallError` matches D-07 verbatim, `_extract_code_message` matches D-08's three-step strict chain with TextContent filter on every iteration, only `code`/`message` keys recognized.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| MCP server -> framework | Untrusted server payload (`structuredContent`, `TextContent.text`) crosses into Python exception construction. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-18-01 | T (Tampering) | `_extract_code_message` step 2 (`json.loads(block.text)`) | mitigate | Wrap in `try/except (json.JSONDecodeError, ValueError)`; fall through to step 3 on any parse failure. Never re-raise. |
| T-18-02 | D (DoS) | `_extract_code_message` step 3 concat | accept | Concat is bounded by MCP CallToolResult size (server-side limit); no recursion; O(N) over content blocks where N is typically ≤ 5. |
| T-18-03 | I (Info Disclosure) | `.raw` attribute | accept | `.raw` is the full CallToolResult including any server-provided diagnostic info; this is intentional — SDETs writing tests need full visibility. `--debug` appendix (Plan 18-06) deliberately surfaces it. |
| T-18-04 | E (Elevation) | None | accept | Pure data extraction; no privileged operations. |
</threat_model>

<verification>
- `uv run pytest tests/framework/unit/test_tool_call_error.py -x` passes (pinning tests in Plan 18-08).
- `uv run python -c "from mcp_test_framework.sdet.errors import ToolCallError, _extract_code_message"` exits 0.
- Module is pyright-strict-clean (Phase 17 CODEGEN-04 D-04 pattern): `uv run pyright src/mcp_test_framework/sdet/errors.py` returns 0 errors.
</verification>

<success_criteria>
- `ToolCallError` is a plain `Exception` subclass with `.tool` / `.code` / `.message` / `.raw` attributes.
- `str(ToolCallError(...))` matches D-07's `_format_default` shape exactly.
- `_extract_code_message` implements the D-08 three-step strict chain with TextContent filter throughout.
- No synonyms for `code` / `message` are recognized at any step.
- File is importable from `mcp_test_framework.sdet.errors`.
</success_criteria>

<output>
After completion, create `.planning/phases/18-sdet-test-surface-typed-errors/18-01-SUMMARY.md` documenting what was built, decisions referenced (D-07, D-08), and what downstream plans (18-02, 18-04, 18-05, 18-07) now have a stable import target.
</output>
