---
phase: 18-sdet-test-surface-typed-errors
plan: 04
type: execute
wave: 4
depends_on: [18-01, 18-02, 18-03]
files_modified:
  - src/mcp_test_framework/sdet/__init__.py
autonomous: true
requirements: [SDET-03, SDET-04, UI-02]
must_haves:
  truths:
    - "from mcp_test_framework.sdet import mcp_session, tool, ToolCallError, ToolResponse works"
    - "__all__ lists exactly the four operator-facing names"
    - "Underscore-prefixed internals (_tool_factory, _slugs) stay internal — not re-exported"
    - "Header docstring updates to reflect Phase 18 surface"
  artifacts:
    - path: "src/mcp_test_framework/sdet/__init__.py"
      provides: "Public SDET surface: mcp_session, tool, ToolCallError, ToolResponse"
      exports: ["mcp_session", "tool", "ToolCallError", "ToolResponse"]
  key_links:
    - from: "sdet/__init__.py"
      to: "errors.py + _tool_factory.py + session.py + response.py"
      via: "barrel re-export"
      pattern: "from mcp_test_framework.sdet.(errors|_tool_factory|session|response) import"
---

<objective>
Extend `src/mcp_test_framework/sdet/__init__.py` to re-export the Phase 18 public surface: `mcp_session` (from `session.py`), `tool` (from `_tool_factory.py`), `ToolCallError` (from `errors.py`), alongside the existing `ToolResponse`. Update `__all__` and the module docstring to reflect the new state.

Underscore-prefixed internals (`_tool_factory`, `_slugs`, `_codegen`) stay internal — the public name `tool` is what re-exports.

Purpose: This is the operator-facing seam. SDETs write `from mcp_test_framework.sdet import mcp_session, tool, ToolCallError` — Phase 17 already shipped `ToolResponse`; this plan rounds out the surface.

Output: One modified file (`src/mcp_test_framework/sdet/__init__.py`).
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
@.planning/phases/18-sdet-test-surface-typed-errors/18-01-SUMMARY.md
@.planning/phases/18-sdet-test-surface-typed-errors/18-02-SUMMARY.md
@.planning/phases/18-sdet-test-surface-typed-errors/18-03-SUMMARY.md
@src/mcp_test_framework/sdet/__init__.py

<interfaces>
<!-- Current file (verbatim from 18-PATTERNS.md lines 34-49) -->
```python
"""mcp_test_framework.sdet -- SDET test surface (Phase 17 onwards).

Phase 17 (CODEGEN-01..06) ships:
  - ToolResponse: uniform .raw / .data / .text / .is_error base class
    that every generated <Tool>Response inherits from (CODEGEN-04, D-07).

Phases 18-20 will extend this re-export with `mcp_session`, `tool`,
`requires_homelab`. Do not add those here -- they are out of scope per
CONTEXT.md "Out of scope (deliberate)".
"""
from __future__ import annotations

from mcp_test_framework.sdet.response import ToolResponse

__all__ = ["ToolResponse"]
```

<!-- Target shape — from 18-PATTERNS.md lines 53-60 -->
```python
from mcp_test_framework.sdet.response import ToolResponse
from mcp_test_framework.sdet._tool_factory import tool
from mcp_test_framework.sdet.errors import ToolCallError
from mcp_test_framework.sdet.session import mcp_session

__all__ = ["ToolResponse", "tool", "ToolCallError", "mcp_session"]
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update sdet/__init__.py with Phase 18 re-exports</name>
  <files>src/mcp_test_framework/sdet/__init__.py</files>
  <read_first>
    - src/mcp_test_framework/sdet/__init__.py (current full content — preserve future-import and the response.py re-export verbatim style)
    - src/mcp_test_framework/sdet/errors.py (Plan 18-01 output — confirm `ToolCallError` symbol)
    - src/mcp_test_framework/sdet/_tool_factory.py (verify `tool` is the public name; `tool(name)` factory at lines 85-115)
    - src/mcp_test_framework/sdet/session.py (Plan 18-03 output — confirm `mcp_session` symbol)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-CONTEXT.md (Phase 18 in-scope items lines 11-15)
  </read_first>
  <action>
Replace `src/mcp_test_framework/sdet/__init__.py` with the following content (preserving the existing convention: from-future-import + sibling-module barrel re-exports + `__all__`):

```python
"""mcp_test_framework.sdet -- SDET test surface (Phase 17 + 18).

Phase 17 (CODEGEN-01..06) ships:
  - ToolResponse: uniform .raw / .data / .text / .is_error base class
    that every generated <Tool>Response inherits from (CODEGEN-04, D-07).

Phase 18 (SDET-01..04, UI-02) adds:
  - mcp_session: session-scoped pytest-asyncio fixture wrapping McpTestClient
    and activating the per-server generated registry (D-01/D-02/D-03).
  - tool(name): typed call wrapper factory; `tool("create_vm").call(params)`
    performs the wire call and returns a typed CreateVmResponse on success
    (CODEGEN-05 contract; .call() body wired in Phase 18).
  - ToolCallError: plain Exception subclass with .tool / .code / .message /
    .raw fields; raised by tool().call() when result.isError is True
    (UI-02; surfaced into the em-dash FAIL row + --debug appendix).

Phase 20 (PREFLIGHT-01..02) will add `requires_homelab`. Do not add it here
until Phase 20 lands — keep this barrel narrow.
"""
from __future__ import annotations

from mcp_test_framework.sdet.errors import ToolCallError
from mcp_test_framework.sdet.response import ToolResponse
from mcp_test_framework.sdet.session import mcp_session
from mcp_test_framework.sdet._tool_factory import tool

__all__ = ["ToolCallError", "ToolResponse", "mcp_session", "tool"]
```

**Critical notes:**
- Import order: alphabetical by symbol name within their groups (`ToolCallError`, `ToolResponse`, `mcp_session`, `tool`) — matches ruff's default isort behavior so we don't fight the linter.
- The `_tool_factory` import keeps the underscore (it's an internal module); the re-exported NAME `tool` is public.
- `__all__` lists exactly four items — the four operator-facing names. Do NOT add `_extract_code_message`, `_tool_factory`, `_slugs`, `_codegen`, or any underscore-prefixed name.
- The future-import (`from __future__ import annotations`) stays at the top, before any other imports.
- The header docstring's "Phase 20 (PREFLIGHT-01..02) will add `requires_homelab`" sentence is the new scope-discipline anchor (matching the existing convention of saying what's deferred so future PRs don't add it speculatively).

Do NOT:
- Re-export `_extract_code_message` (D-08 helper is internal to `_tool_factory` and tests).
- Re-export `_REGISTRIES`, `_ACTIVE_SLUG`, `_ACTIVE_CLIENT` (module state slots — internal).
- Re-export `server_slug` (slugify helper — internal).
- Re-export `ToolWrapper` directly (operators call `tool(name)`; the wrapper class is a return-type detail).
- Add any tests, classes, or functions to this file — it's a barrel.
  </action>
  <verify>
    <automated>uv run python -c "from mcp_test_framework.sdet import mcp_session, tool, ToolCallError, ToolResponse; from mcp_test_framework.sdet import __all__; assert set(__all__) == {'ToolCallError', 'ToolResponse', 'mcp_session', 'tool'}, __all__; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "from mcp_test_framework.sdet.errors import ToolCallError" src/mcp_test_framework/sdet/__init__.py` returns 1
    - `grep -c "from mcp_test_framework.sdet.response import ToolResponse" src/mcp_test_framework/sdet/__init__.py` returns 1
    - `grep -c "from mcp_test_framework.sdet.session import mcp_session" src/mcp_test_framework/sdet/__init__.py` returns 1
    - `grep -c "from mcp_test_framework.sdet._tool_factory import tool" src/mcp_test_framework/sdet/__init__.py` returns 1
    - `grep -cE '__all__\s*=\s*\["ToolCallError", "ToolResponse", "mcp_session", "tool"\]' src/mcp_test_framework/sdet/__init__.py` returns 1
    - `grep -cE "_extract_code_message|_REGISTRIES|_ACTIVE_SLUG|_ACTIVE_CLIENT|server_slug|ToolWrapper" src/mcp_test_framework/sdet/__init__.py` returns 0 (no internal symbols re-exported)
    - `grep -c "from __future__ import annotations" src/mcp_test_framework/sdet/__init__.py` returns 1
    - `uv run python -c "from mcp_test_framework.sdet import mcp_session, tool, ToolCallError, ToolResponse; print('OK')"` exits 0 and prints `OK`
    - `uv run pyright src/mcp_test_framework/sdet/__init__.py` returns 0 errors
  </acceptance_criteria>
  <done>
    `mcp_test_framework.sdet` re-exports exactly four public names: `ToolCallError`, `ToolResponse`, `mcp_session`, `tool`. `__all__` matches. Underscore internals are not surfaced. Header docstring reflects Phase 17+18 state with a forward note about Phase 20's `requires_homelab`.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

None new — barrel re-export only. All threats are inherited from the underlying modules (Plans 18-01, 18-02, 18-03).
</threat_model>

<verification>
- `uv run python -c "from mcp_test_framework.sdet import mcp_session, tool, ToolCallError, ToolResponse"` exits 0.
- `uv run pytest tests/framework/unit/test_sdet_fixtures.py::test_public_surface -x` passes (Plan 18-08 pins the `__all__` contract).
- Module is pyright-strict-clean.
</verification>

<success_criteria>
- All four operator-facing names re-export cleanly.
- `__all__` is exact; no extra symbols leak.
- Header docstring carries scope-discipline forward note about `requires_homelab` (Phase 20 boundary).
</success_criteria>

<output>
After completion, create `.planning/phases/18-sdet-test-surface-typed-errors/18-04-SUMMARY.md` documenting: the four public exports, the explicit non-exports (internal symbols), and confirmation that Plans 18-07 (sanity test) + 18-08 (framework self-tests) can now import from the canonical public surface.
</output>
