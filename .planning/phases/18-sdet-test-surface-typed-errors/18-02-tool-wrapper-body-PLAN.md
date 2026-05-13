---
phase: 18-sdet-test-surface-typed-errors
plan: 02
type: execute
wave: 2
depends_on: [18-01]
files_modified:
  - src/mcp_test_framework/sdet/_tool_factory.py
autonomous: true
requirements: [SDET-03, UI-02]
must_haves:
  truths:
    - "ToolWrapper.call() performs the live MCP wire call via the active McpTestClient"
    - "ToolWrapper.call() raises ToolCallError when result.isError is True"
    - "ToolWrapper.call() returns response_cls(raw=result) when result.isError is False"
    - "Calling tool().call() without an active mcp_session fixture raises RuntimeError naming the missing fixture"
    - "_ACTIVE_CLIENT module slot is added alongside _ACTIVE_SLUG and _REGISTRIES"
    - "params are serialized via params.model_dump(mode='json') (wire-safe JSON)"
  artifacts:
    - path: "src/mcp_test_framework/sdet/_tool_factory.py"
      provides: "Filled .call() body (replaces NotImplementedError) + _ACTIVE_CLIENT slot"
      contains: "_ACTIVE_CLIENT, result.isError, ToolCallError, _extract_code_message"
  key_links:
    - from: "_tool_factory.py:ToolWrapper.call"
      to: "sdet/errors.py:ToolCallError + _extract_code_message"
      via: "from mcp_test_framework.sdet.errors import ToolCallError, _extract_code_message"
      pattern: "raise ToolCallError\\(tool=.*, code=code, message=message, raw=result\\)"
    - from: "_tool_factory.py:ToolWrapper.call"
      to: "McpTestClient.call_tool"
      via: "await _ACTIVE_CLIENT.call_tool(self.name, arguments)"
      pattern: "_ACTIVE_CLIENT.call_tool"
---

<objective>
Fill the `ToolWrapper.call()` body at `_tool_factory.py:70-82` (currently raises `NotImplementedError` with a Phase 18 reference) with the actual MCP wire call + typed-error raise + typed-response wrap. Add a new module-state slot `_ACTIVE_CLIENT: McpTestClient | None = None` alongside `_ACTIVE_SLUG` and `_REGISTRIES` — this slot is set/cleared by the `mcp_session` fixture (Plan 18-03).

The slot contract + `tool(name)` factory shape at lines 85-115 stay LOCKED — only the `.call()` body and the new `_ACTIVE_CLIENT` slot change. Per CONTEXT D-08 + 18-PATTERNS.md: serialize params via `model_dump(mode="json")` (Claude's-discretion default for wire safety).

Purpose: Closes the Phase 17 seam. After this plan, `ToolWrapper.call()` does real work — the `mcp_session` fixture (Plan 18-03) wires `_ACTIVE_CLIENT` so calls succeed end-to-end.

Output: One modified file (`src/mcp_test_framework/sdet/_tool_factory.py`).
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
@.planning/phases/18-sdet-test-surface-typed-errors/18-01-SUMMARY.md
@src/mcp_test_framework/sdet/_tool_factory.py
@src/mcp_test_framework/sdet/errors.py
@src/mcp_test_framework/mcp_client.py

<interfaces>
<!-- The McpTestClient.call_tool wire-shape mirror — pattern locked at
     src/mcp_test_framework/mcp_client.py:207-210 -->

```python
async def call_tool(self, name: str, arguments: dict[str, Any]) -> CallToolResult:
    assert self._session is not None, "McpTestClient not entered"
    async with asyncio.timeout(self._timeout):
        return await self._session.call_tool(name, arguments)
```

<!-- Phase 18 .call() body (target) — from 18-PATTERNS.md lines 92-118 -->
```python
async def call(self, params: P) -> R:
    if _ACTIVE_CLIENT is None:
        raise RuntimeError(
            "no active MCP client. tool().call() requires the `mcp_session` "
            "fixture (Phase 18). Use it in an SDET test under `tests/sdet/`."
        )
    arguments = params.model_dump(mode="json")
    result = await _ACTIVE_CLIENT.call_tool(self.name, arguments)
    if result.isError:
        from mcp_test_framework.sdet.errors import ToolCallError, _extract_code_message
        code, message = _extract_code_message(result)
        raise ToolCallError(tool=self.name, code=code, message=message, raw=result)
    return self.response_cls(raw=result)
```

<!-- New module slot — added alongside _REGISTRIES (line 38) + _ACTIVE_SLUG (line 39) -->
```python
_ACTIVE_CLIENT: "McpTestClient | None" = None  # set by mcp_session fixture body
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Replace NotImplementedError body + add _ACTIVE_CLIENT slot</name>
  <files>src/mcp_test_framework/sdet/_tool_factory.py</files>
  <read_first>
    - src/mcp_test_framework/sdet/_tool_factory.py (current file in full — lines 1-115, especially lines 38-39 for slot location, lines 70-82 for the body to replace)
    - src/mcp_test_framework/sdet/errors.py (Plan 18-01 output — verify ToolCallError + _extract_code_message symbols are present)
    - src/mcp_test_framework/mcp_client.py (call_tool wire-shape pattern at lines 207-210; .McpTestClient class signature for the TYPE_CHECKING import)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-CONTEXT.md (D-07 lines 79-99; D-08 lines 102-107; Claude's discretion on `mode="json"` lines 140-141)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-PATTERNS.md (assembled body lines 92-118; slot to add line 122)
  </read_first>
  <behavior>
    - Test: calling `wrapper.call(params)` when `_ACTIVE_CLIENT is None` raises `RuntimeError` whose message contains "no active MCP client" AND "mcp_session" AND "Phase 18" AND "tests/sdet/".
    - Test: with `_ACTIVE_CLIENT` set to a mock whose `call_tool` returns a `CallToolResult(isError=False, content=[TextContent(type='text', text='ok')])` (and structuredContent appropriate), `await wrapper.call(params)` returns an instance of `wrapper.response_cls`.
    - Test: with mock `call_tool` returning `CallToolResult(isError=True, structuredContent={"code": "X", "message": "Y"}, content=[])`, `await wrapper.call(params)` raises `ToolCallError` with `.tool == wrapper.name`, `.code == "X"`, `.message == "Y"`, `.raw is the_result`.
    - Test: `params.model_dump` is called with `mode="json"` (use mock spy on params to assert kwargs).
    - Test: the result.isError-False path passes `raw=result` to `self.response_cls(raw=result)`.
    - Test: `_ACTIVE_CLIENT` module attribute exists and defaults to `None`.
  </behavior>
  <action>
Modify `src/mcp_test_framework/sdet/_tool_factory.py`. THREE changes only — do NOT touch the `tool(name)` factory at lines 85-115 or the `ToolWrapper.__init__` at lines 65-68.

**Change 1 — Add TYPE_CHECKING import block at module top (after the existing imports block, before line 37's blank line):**

Add a `from typing import TYPE_CHECKING` and a `TYPE_CHECKING` block importing `McpTestClient` for the slot annotation. Required structure:

```python
from typing import Generic, TYPE_CHECKING, TypeVar

# ... existing imports ...

if TYPE_CHECKING:
    from mcp_test_framework.mcp_client import McpTestClient
```

Rationale: avoids a runtime circular import (fixtures.py → mcp_client.py → ... → _tool_factory.py paths). The slot's annotation is a forward-string already.

**Change 2 — Add the `_ACTIVE_CLIENT` module slot at line 40 (immediately after `_ACTIVE_SLUG: str | None = None`):**

```python
# Phase 18 SDET-03: active McpTestClient injected by the mcp_session fixture.
# Mutated ONLY by mcp_session in src/mcp_test_framework/sdet/session.py.
_ACTIVE_CLIENT: "McpTestClient | None" = None
```

Use the forward-string annotation `"McpTestClient | None"` (not the unquoted form) so the slot is importable at runtime without resolving the TYPE_CHECKING import.

**Change 3 — Replace the entire `.call()` method body (current lines 70-82, the NotImplementedError block) with the wired body:**

```python
async def call(self, params: P) -> R:
    """Make the MCP wire call; raise ToolCallError on isError; else return response_cls.

    Phase 18 SDET-03 + UI-02 wiring:
      - Resolves the active McpTestClient via the module-level _ACTIVE_CLIENT
        slot (set/cleared by the mcp_session fixture). Raises RuntimeError if
        unset (naming the missing fixture so the operator can fix it).
      - Serializes `params` via Pydantic with mode="json" (MCP wire format
        expects JSON-serializable dicts; preserves int/str/list/None as-is).
      - Awaits McpTestClient.call_tool (which already enforces asyncio.timeout
        per mcp_client.py:207-210).
      - On result.isError=True: extracts code+message via the D-08 strict
        heuristic chain and raises ToolCallError(tool, code, message, raw).
      - On result.isError=False: constructs self.response_cls(raw=result) per
        CODEGEN-04's uniform .raw/.data/.text/.is_error contract.
    """
    if _ACTIVE_CLIENT is None:
        raise RuntimeError(
            "no active MCP client. tool().call() requires the `mcp_session` "
            "fixture (Phase 18). Use it in an SDET test under `tests/sdet/`."
        )
    arguments = params.model_dump(mode="json")
    result = await _ACTIVE_CLIENT.call_tool(self.name, arguments)
    if result.isError:
        from mcp_test_framework.sdet.errors import (
            ToolCallError,
            _extract_code_message,
        )
        code, message = _extract_code_message(result)
        raise ToolCallError(
            tool=self.name,
            code=code,
            message=message,
            raw=result,
        )
    return self.response_cls(raw=result)
```

Notes:
- The `from mcp_test_framework.sdet.errors import ...` is INSIDE the `if result.isError:` branch deliberately (lazy import — avoids paying the import cost in the success path and avoids any future circular-import risk between `errors.py` and `_tool_factory.py`). Pattern matches the 18-PATTERNS.md body lines 113-115 exactly.
- Use `params.model_dump(mode="json")` — NOT `mode="python"`. MCP wire format expects JSON-serializable dicts. Pin this in a test (Plan 18-08).
- The `RuntimeError` message must contain all four signal phrases: "no active MCP client", "mcp_session", "Phase 18", "tests/sdet/" — operator scans for these.

Do NOT remove the existing `_REGISTRIES`, `_ACTIVE_SLUG`, `P`, `R`, or `ToolWrapper.__init__` definitions. Do NOT change the signature `async def call(self, params: P) -> R`. Do NOT change the docstring style on the `tool(name)` function at lines 85-115.
  </action>
  <verify>
    <automated>uv run python -c "from mcp_test_framework.sdet._tool_factory import _ACTIVE_CLIENT, _ACTIVE_SLUG, _REGISTRIES; assert _ACTIVE_CLIENT is None; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "_ACTIVE_CLIENT" src/mcp_test_framework/sdet/_tool_factory.py` returns at least 3 (slot declaration + at-least-two references in `.call`)
    - `grep -c "NotImplementedError" src/mcp_test_framework/sdet/_tool_factory.py` returns 0 (body fully replaced)
    - `grep -c "if TYPE_CHECKING:" src/mcp_test_framework/sdet/_tool_factory.py` returns 1
    - `grep -c "from mcp_test_framework.sdet.errors import" src/mcp_test_framework/sdet/_tool_factory.py` returns 1 (lazy-import inside isError branch)
    - `grep -c 'params.model_dump(mode="json")' src/mcp_test_framework/sdet/_tool_factory.py` returns 1
    - `grep -c "_ACTIVE_CLIENT.call_tool" src/mcp_test_framework/sdet/_tool_factory.py` returns 1
    - `grep -c "raise ToolCallError" src/mcp_test_framework/sdet/_tool_factory.py` returns 1
    - `grep -c "self.response_cls(raw=result)" src/mcp_test_framework/sdet/_tool_factory.py` returns 1
    - `grep -cE 'mode="python"' src/mcp_test_framework/sdet/_tool_factory.py` returns 0 (wire-safe JSON only)
    - `grep -c "no active MCP client" src/mcp_test_framework/sdet/_tool_factory.py` returns 1 (operator-readable error)
    - `uv run python -c "from mcp_test_framework.sdet._tool_factory import _ACTIVE_CLIENT, _ACTIVE_SLUG, _REGISTRIES, ToolWrapper, tool; print('OK')"` exits 0
    - `uv run pyright src/mcp_test_framework/sdet/_tool_factory.py` returns 0 errors
  </acceptance_criteria>
  <done>
    `.call()` body fully replaced; `_ACTIVE_CLIENT` slot added; the three locked invariants (slot contract, `tool(name)` factory, ToolWrapper.__init__) untouched; module imports cleanly with no circular references.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| MCP server -> framework | `result.isError` boolean + `CallToolResult` content originates from the server-under-test. |
| Test code -> framework | `params: P` Pydantic model constructed by the SDET; Pydantic validates at construction. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-18-05 | T (Tampering) | `params.model_dump(mode="json")` | mitigate | Pydantic v2 with `extra="forbid"` (Phase 17 CODEGEN-04 convention on Params classes) rejects unknown fields at construction time — long before this `.call()` body runs. |
| T-18-06 | D (DoS) | `McpTestClient.call_tool` timeout | mitigate | `McpTestClient.call_tool` already wraps in `asyncio.timeout(self._timeout)` per mcp_client.py:207-210; this plan inherits that guard. |
| T-18-07 | E (Elevation) | Module-state slot `_ACTIVE_CLIENT` | accept | Module state is process-local; only `mcp_session` fixture mutates it; cancel-scope invariant preserved (sync write, no await around mutation). |
</threat_model>

<verification>
- `uv run pytest tests/framework/unit/test_tool_factory.py -x` passes (existing test that pins NotImplementedError WILL fail and must be updated or removed in this plan — Plan 18-08 introduces the replacement test_sdet_fixtures.py / test_tool_call_error.py tests).
- The single existing test at `tests/framework/unit/test_tool_factory.py:84-96` (`test_call_raises_not_implemented_with_phase18_reference`) MUST be deleted or updated as part of this plan — it now violates the contract. Replace with a test that confirms `.call()` raises RuntimeError naming the missing fixture when `_ACTIVE_CLIENT is None`.
</verification>

<success_criteria>
- `.call()` body fully replaced; no `NotImplementedError` remains in the module.
- `_ACTIVE_CLIENT` slot exists and defaults to `None`.
- Calling `.call()` without an active client raises `RuntimeError` naming `mcp_session` + `Phase 18` + `tests/sdet/`.
- `params.model_dump(mode="json")` is the wire serialization (NOT `mode="python"`).
- `result.isError=True` path raises `ToolCallError` with `.tool`/`.code`/`.message`/`.raw` populated via `_extract_code_message`.
- `result.isError=False` path returns `self.response_cls(raw=result)`.
- Module is pyright-strict-clean.
</success_criteria>

<output>
After completion, create `.planning/phases/18-sdet-test-surface-typed-errors/18-02-SUMMARY.md` documenting: the body replacement, the new `_ACTIVE_CLIENT` slot, the existing `test_tool_factory.py:84-96` test deletion/update, and the dependency Plan 18-03 inherits (the fixture must set `_ACTIVE_CLIENT`).
</output>
