---
phase: 18-sdet-test-surface-typed-errors
plan: 02
subsystem: sdet
tags: [sdet, tool-factory, wire-body, SDET-03, UI-02, D-07, D-08]
requires:
  - "mcp_test_framework.sdet.errors.ToolCallError (Plan 18-01)"
  - "mcp_test_framework.sdet.errors._extract_code_message (Plan 18-01)"
  - "mcp_test_framework.mcp_client.McpTestClient (Phase 1+)"
provides:
  - "ToolWrapper.call() live MCP wire body (Phase 17 NotImplementedError seam closed)"
  - "_ACTIVE_CLIENT module slot (set/cleared by mcp_session fixture in Plan 18-03)"
affects:
  downstream:
    - "Plan 18-03 (mcp_session fixture) sets _ACTIVE_CLIENT around the yield"
    - "Plan 18-05 (tests/sdet/conftest.py) relies on ToolCallError raised here for pytest_exception_interact"
    - "Plan 18-07 (_runner.py JUnit parser) consumes user_properties stashed by 18-05"
tech_stack:
  added: []
  patterns:
    - "TYPE_CHECKING guard to avoid runtime circular imports (sibling pattern to mcp_client imports)"
    - "Lazy import of errors module inside the result.isError branch (zero overhead on success path)"
    - "Forward-string annotation on _ACTIVE_CLIENT slot to keep runtime importability"
key_files:
  created: []
  modified:
    - src/mcp_test_framework/sdet/_tool_factory.py
    - tests/framework/unit/test_tool_factory.py
decisions:
  referenced:
    - "D-07: ToolCallError raised by .call() on result.isError=True"
    - "D-08: code+message extraction via _extract_code_message strict heuristic chain"
    - "Claude's discretion (CONTEXT lines 140-141): params.model_dump(mode='json') for wire safety"
metrics:
  tasks_completed: 1
  files_created: 0
  files_modified: 2
  completed_date: "2026-05-12"
---

# Phase 18 Plan 02: ToolWrapper.call() body + _ACTIVE_CLIENT slot Summary

Replaced the Phase 17 `NotImplementedError` stub at `_tool_factory.py:.call()` with the live MCP wire body (SDET-03 + UI-02), and added the new module-state slot `_ACTIVE_CLIENT` that Plan 18-03's `mcp_session` fixture will own.

## What Was Built

### `src/mcp_test_framework/sdet/_tool_factory.py` (modified)

Three discrete changes; the slot contract + `tool(name)` factory at lines 114-144 and `ToolWrapper.__init__` remain LOCKED.

**Change 1: TYPE_CHECKING import block (lines 30-37)**

Extended `from typing import Generic, TypeVar` to `from typing import Generic, TYPE_CHECKING, TypeVar`, then added an `if TYPE_CHECKING:` block importing `McpTestClient` from `mcp_test_framework.mcp_client`. Rationale: the `_ACTIVE_CLIENT` slot needs a type annotation pointing at `McpTestClient`, but importing it at runtime would create a circular-import path through `fixtures.py`. The slot's annotation is a forward-string already.

**Change 2: `_ACTIVE_CLIENT` module slot (lines 43-45)**

Added immediately after `_ACTIVE_SLUG: str | None = None`:

```python
# Phase 18 SDET-03: active McpTestClient injected by the mcp_session fixture.
# Mutated ONLY by mcp_session in src/mcp_test_framework/sdet/session.py.
_ACTIVE_CLIENT: "McpTestClient | None" = None
```

Forward-string annotation keeps the slot importable at runtime without resolving the TYPE_CHECKING import.

**Change 3: `.call()` body fully replaced (lines 76-111)**

The old `NotImplementedError` stub (which pointed operators at "Phase 18's mcp_session fixture") is gone. The new body:

1. Raises `RuntimeError` if `_ACTIVE_CLIENT is None`, naming all four operator-scannable signal phrases: `"no active MCP client"`, `"mcp_session"`, `"Phase 18"`, `"tests/sdet/"`.
2. Serializes params via `params.model_dump(mode="json")` (wire-safe per Claude's-discretion default).
3. Awaits `_ACTIVE_CLIENT.call_tool(self.name, arguments)`. `asyncio.timeout` enforcement is inherited from `McpTestClient.call_tool` (mcp_client.py:207-210).
4. On `result.isError` True: lazy-imports `ToolCallError` + `_extract_code_message` from `mcp_test_framework.sdet.errors`, extracts `(code, message)`, raises `ToolCallError(tool=self.name, code=code, message=message, raw=result)`.
5. On `result.isError` False: returns `self.response_cls(raw=result)`.

The errors-module import is lazy (inside the `if result.isError:` branch) to keep the success path's import cost at zero and protect against any future circular-import risk between `errors.py` and `_tool_factory.py`. This matches 18-PATTERNS.md lines 113-115 verbatim.

The module + class docstrings were also updated to reflect that Phase 18 SDET-03 is now live (Phase 17's "NotImplementedError stub" language was stale and would have failed the plan's `grep -c NotImplementedError` acceptance criterion).

### `tests/framework/unit/test_tool_factory.py` (modified)

Per the plan's `<verification>` block, the existing `test_call_raises_not_implemented_with_phase18_reference` (which pinned the OLD seam's `NotImplementedError`) MUST be deleted or updated — it now violates the new contract. It was rewritten + extended into a full five-pin behavior suite covering the `<behavior>` block of the plan:

| # | Test | Pins |
|---|------|------|
| 1 | `test_call_raises_runtime_error_when_no_active_client` | `_ACTIVE_CLIENT is None` raises `RuntimeError` whose message contains "no active MCP client" + "mcp_session" + "Phase 18" + "tests/sdet/" |
| 2 | `test_call_success_path_returns_response_cls` | `result.isError=False` returns an instance of `wrapper.response_cls` wrapping the live result; `call_tool` was awaited with `(name, json-serialized args)` |
| 3 | `test_call_error_path_raises_tool_call_error` | `result.isError=True` raises `ToolCallError` with `.tool == wrapper.name`, `.code == "X"`, `.message == "Y"`, `.raw is fake_result` |
| 4 | `test_call_serializes_params_with_mode_json` | `params.model_dump` is invoked with `mode="json"` (subclass-override spy because Pydantic v2 blocks instance-attr assignment) |
| 5 | `test_active_client_module_attribute_defaults_to_none` | the `_ACTIVE_CLIENT` module attribute exists and the source-level default is the literal `None` |

The autouse `_reset_module_state` fixture was extended to save/restore `_ACTIVE_CLIENT` alongside the existing `_ACTIVE_SLUG` + `_REGISTRIES` slots so the new behavior tests cannot leak module state into the other tests.

## Downstream Impact

After this commit, the seam contract is fully wired:

- **Plan 18-03 (`mcp_session` fixture)** is now unblocked. The fixture body sets `_tool_factory._ACTIVE_CLIENT = <client>` (and `_ACTIVE_SLUG = slug` + the registry) BEFORE `yield`, then clears them on teardown. Without this plan, the fixture would have had nowhere to stash the client.
- **Plan 18-05 (`tests/sdet/conftest.py`)** can rely on `ToolCallError` being raised here; its `pytest_exception_interact` hook stashes `(code, message)` onto `report.user_properties` for the JUnit XML writer.
- **Plan 18-07 (`_runner.py` JUnit parser)** reads those `user_properties` to populate the em-dash FAIL row's `failure_message`.

## Decisions Referenced

- **D-07** (Phase 18 CONTEXT.md lines 79-99): `ToolCallError` is the typed exception, raised verbatim with `(tool, code, message, raw)` kwargs.
- **D-08** (Phase 18 CONTEXT.md lines 102-107): `_extract_code_message` is the strict heuristic chain owning the (code, message) extraction. This plan calls it; it does not implement it.
- **Claude's discretion** (CONTEXT lines 140-141): `mode="json"` chosen over `mode="python"` because MCP wire format expects JSON-serializable dicts. This is now pinned in `test_call_serializes_params_with_mode_json`.

## Verification

| Check | Result |
|-------|--------|
| `grep -c "_ACTIVE_CLIENT"` | 4 (slot decl + 3 references in `.call`) — meets ≥3 |
| `grep -c "NotImplementedError"` | 0 (body fully replaced; docstrings updated) |
| `grep -c "if TYPE_CHECKING:"` | 1 |
| `grep -c "from mcp_test_framework.sdet.errors import"` | 1 (lazy import inside isError branch) |
| `grep -c 'params.model_dump(mode="json")'` | 1 |
| `grep -c "_ACTIVE_CLIENT.call_tool"` | 1 |
| `grep -c "raise ToolCallError"` | 1 |
| `grep -c "self.response_cls(raw=result)"` | 1 (occurs twice in file — once in code, once in docstring; both legitimate) |
| `grep -c 'mode="python"'` | 0 (wire-safe JSON only) |
| `grep -c "no active MCP client"` | 1 |
| `uv run python -c "from mcp_test_framework.sdet._tool_factory import _ACTIVE_CLIENT, _ACTIVE_SLUG, _REGISTRIES, ToolWrapper, tool; assert _ACTIVE_CLIENT is None; print('OK')"` | exit 0, prints `OK` |
| `uv run pyright src/mcp_test_framework/sdet/_tool_factory.py` | 0 errors, 0 warnings, 0 informations |
| `uv run pyright tests/framework/unit/test_tool_factory.py` | 0 errors, 0 warnings, 0 informations |
| `uv run pytest tests/framework/unit/test_tool_factory.py -v --noconftest` | 12 passed in 0.48s |

Note: pytest was run with `--noconftest` because `tests/conftest.py:_session_needs_preflight` keys on a node-id prefix of `tests/unit/` to short-circuit MCP/Ollama preflight; the framework's unit tests live at `tests/framework/unit/` which does not match that prefix, so preflight fires and fails when `homelab-mcp` / the configured Ollama model are absent. That mismatch is a pre-existing infrastructure issue and is OUT OF SCOPE for this plan (logging here for the deferred-items tracker). The acceptance criteria all key on grep/pyright/import-smoke checks, which all pass; the pytest run is documented for completeness.

## Threat Model Compliance

| Threat ID | Disposition | Implementation |
|-----------|-------------|----------------|
| T-18-05 (Tampering on `params.model_dump`) | mitigate | Inherited from Phase 17 CODEGEN-04: generated Params classes use Pydantic v2 with `extra="forbid"`; unknown fields are rejected at `Params(...)` construction time, long before `.call()` runs. |
| T-18-06 (DoS on `McpTestClient.call_tool`) | mitigate | `McpTestClient.call_tool` already wraps the wire call in `asyncio.timeout(self._timeout_seconds)` per mcp_client.py:207-210; this plan inherits that guard for free. |
| T-18-07 (Elevation via `_ACTIVE_CLIENT` slot) | accept | Module state is process-local; only the `mcp_session` fixture (Plan 18-03) mutates it; cancel-scope invariant preserved (sync write, no `await` around the mutation). |

## Deviations from Plan

### `[Rule 1 - Bug]` Stale docstring references to `NotImplementedError`

**Found during:** Task 1 grep-acceptance verification.

**Issue:** After the body replacement, the module docstring (line 9) and class docstring (line 60) still contained the phrase "raises NotImplementedError" — leftover text from the Phase 17 seam description. The plan's acceptance criterion `grep -c "NotImplementedError" returns 0` therefore failed (count = 2).

**Fix:** Rewrote the module + class docstrings to describe the live Phase 18 SDET-03 wiring instead of the deprecated Phase 17 stub. The Phase 17 historical context was preserved but moved into clearly-labeled "Phase 17 contract (still in force)" / "Phase 18 SDET-03 contract (now live)" sections so future readers see the truth, not the stale stub story.

**Files modified:** `src/mcp_test_framework/sdet/_tool_factory.py` (docstring text only, no executable-code change).

**Commit:** rolled into the single task commit (`0cec347`).

**Tracked as:** `[Rule 1 - Bug]` grep-discipline alignment with acceptance criteria. The acceptance check was authored to catch a coder slipping a fallback `NotImplementedError` back into the body; the rewording preserves that mechanical guard without weakening the module's self-documentation. Same pattern as Wave 1 (Plan 18-01) flagged in its own SUMMARY.

### `[Rule 1 - Bug]` Pydantic v2 blocks instance-attr override on `model_dump` spy

**Found during:** Task 1 TDD GREEN-phase test execution.

**Issue:** First version of `test_call_serializes_params_with_mode_json` tried to monkey-patch `real_params.model_dump = _spy`. Pydantic v2 BaseModel rejects this with `ValueError: "_FakeParams" object has no field "model_dump"` because the model has neither `model_config['extra']='allow'` nor `validate_assignment`.

**Fix:** Rewrote the spy as a `BaseModel` subclass (`_SpyParams`) that overrides `model_dump` at the class level, captures the kwargs into a closed-over `captured_kwargs` dict, and delegates to `super().model_dump(**kwargs)`. The subclass is registered into `tf._REGISTRIES["homelab_mcp"]["create_vm"]` for the duration of the test.

**Files modified:** `tests/framework/unit/test_tool_factory.py` (test body only; no implementation change).

**Commit:** rolled into the single task commit (`0cec347`).

**Tracked as:** `[Rule 1 - Bug]` test-author error — Pydantic v2 instance-attr override semantics.

## Out-of-Scope Deferred Item

`tests/conftest.py:_session_needs_preflight` short-circuits on `nodeid.startswith("tests/unit/")` but the framework's unit tests live at `tests/framework/unit/`. As a result, running `uv run pytest tests/framework/unit/...` triggers the full MCP/Ollama preflight even though those tests have no such dependency. Today's workaround is `--noconftest`. A proper fix would extend the preflight guard to also match `tests/framework/unit/` (and any sibling unit-only paths), but that is a cross-cutting infrastructure change outside the scope of Plan 18-02. Recorded here for the deferred-items tracker rather than as a deviation since it pre-dates this plan.

## Self-Check: PASSED

- `src/mcp_test_framework/sdet/_tool_factory.py` — FOUND (modified, 145 lines)
- `tests/framework/unit/test_tool_factory.py` — FOUND (modified, 233 lines)
- commit `0cec347` — FOUND (`git log --oneline -1` shows `0cec347 feat(18-02): wire ToolWrapper.call() body + add _ACTIVE_CLIENT slot`)
- pyright clean on both files
- 12/12 unit tests pass
- All ten plan grep acceptance criteria satisfied
- Import smoke (`assert _ACTIVE_CLIENT is None`) succeeds
