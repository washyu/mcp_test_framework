---
phase: 18-sdet-test-surface-typed-errors
plan: 04
subsystem: sdet
tags: [sdet, barrel-export, public-surface, SDET-03, SDET-04, UI-02]
requires:
  - "mcp_test_framework.sdet.errors.ToolCallError (Plan 18-01)"
  - "mcp_test_framework.sdet._tool_factory.tool (Plan 18-02)"
  - "mcp_test_framework.sdet.session.mcp_session (Plan 18-03)"
  - "mcp_test_framework.sdet.response.ToolResponse (Phase 17 CODEGEN-04)"
provides:
  - "Canonical SDET public import surface: mcp_session, tool, ToolCallError, ToolResponse"
  - "Locked __all__ contract (exactly four operator-facing names)"
affects:
  downstream:
    - "Plan 18-07 (tests/sdet/test_basic_call.py) imports from canonical surface"
    - "Plan 18-08 (tests/framework/unit/test_sdet_fixtures.py) pins __all__ membership"
    - "Phase 19 (STATE) SDET scenarios import from this barrel"
    - "Phase 21 (DOC-SDET) documents this exact surface in README + sdet.md"
tech_stack:
  added: []
  patterns:
    - "Barrel re-export of sibling-module symbols via explicit `from ... import` lines"
    - "Underscore-prefixed modules (`_tool_factory`) retain underscore in import path; re-exported NAME is public"
    - "Scope-discipline forward note in docstring (Phase 20 `requires_homelab` deferral) to deter speculative additions"
key_files:
  created: []
  modified:
    - src/mcp_test_framework/sdet/__init__.py
decisions:
  referenced:
    - "Phase 17 D-07: ToolResponse is the uniform response base class"
    - "Plan 18-01: ToolCallError as plain Exception subclass with .tool/.code/.message/.raw"
    - "Plan 18-02: `tool(name)` factory returns ToolWrapper; ToolWrapper itself stays internal"
    - "Plan 18-03 D-01: mcp_session is the SDET alias for mcp_client (session-scoped fixture)"
    - "Phase 20 deferral: `requires_homelab` does not land here -- documented in barrel docstring"
metrics:
  tasks_completed: 1
  files_created: 0
  files_modified: 1
  duration_seconds: 51
  completed_date: "2026-05-13"
---

# Phase 18 Plan 04: SDET Public Surface Summary

Barrel-export Phase 18's three new SDET symbols (`mcp_session`, `tool`, `ToolCallError`) alongside the existing `ToolResponse`, locking `__all__` to exactly four operator-facing names so SDETs can write `from mcp_test_framework.sdet import mcp_session, tool, ToolCallError, ToolResponse`.

## What Shipped

**File modified:** `src/mcp_test_framework/sdet/__init__.py`

Now re-exports four symbols from sibling modules:

| Symbol         | Source module                                  | Phase / Plan         |
| -------------- | ---------------------------------------------- | -------------------- |
| `ToolCallError`| `mcp_test_framework.sdet.errors`               | Plan 18-01           |
| `ToolResponse` | `mcp_test_framework.sdet.response`             | Phase 17 (CODEGEN-04)|
| `mcp_session`  | `mcp_test_framework.sdet.session`              | Plan 18-03           |
| `tool`         | `mcp_test_framework.sdet._tool_factory`        | Plan 18-02           |

`__all__ = ["ToolCallError", "ToolResponse", "mcp_session", "tool"]` — exact, alphabetical.

## Explicit Non-Exports (Internal)

The following symbols exist in sibling modules but are deliberately NOT re-exported:

- `_extract_code_message` (errors.py) — internal helper for ToolCallError construction; consumed by `_tool_factory.ToolWrapper.call()` and unit-tested directly.
- `_REGISTRIES`, `_ACTIVE_SLUG`, `_ACTIVE_CLIENT` (`_tool_factory.py`) — module state slots mutated by `mcp_session` fixture; not for direct SDET access.
- `ToolWrapper` (`_tool_factory.py`) — return-type detail of `tool(name)`; operators call `tool("name").call(params)`, never instantiate it directly.
- `server_slug` (`_slugs.py`) — slugify helper; internal to codegen + registry-activation flow.
- `_codegen` module — Phase 17 generator; not runtime.

## Verification

- `uv run python -c "from mcp_test_framework.sdet import mcp_session, tool, ToolCallError, ToolResponse; ..."` exits 0, prints `OK`, and asserts `set(__all__) == {'ToolCallError','ToolResponse','mcp_session','tool'}`.
- `uv run pyright src/mcp_test_framework/sdet/__init__.py` returns `0 errors, 0 warnings, 0 informations`.
- All eight grep-based acceptance criteria from the plan pass (4 explicit re-export lines, exact `__all__` literal, 0 internal-symbol leaks, 1 future-import line).

## Deviations from Plan

None — plan executed exactly as written. Import order and docstring text match the plan body verbatim.

## Downstream Unblocking

This barrel is the canonical import seam:

- **Plan 18-07** (`tests/sdet/test_basic_call.py`) can now import its three target symbols from `mcp_test_framework.sdet` instead of reaching into `sdet.session` / `sdet._tool_factory` / `sdet.errors` directly.
- **Plan 18-08** (`tests/framework/unit/test_sdet_fixtures.py`) pins the `__all__` contract as a regression guard so future plans don't widen the surface speculatively.
- **Phase 19** (STATE + UI-01) and **Phase 20** (PREFLIGHT) author user-facing SDET tests against this exact surface.
- **Phase 21** (DOC-SDET-03 README) documents this barrel as the single import line.

## Self-Check: PASSED

- File `src/mcp_test_framework/sdet/__init__.py` exists and contains the four-symbol re-export with `__all__` literal matching the plan.
- Commit `2a94dc4` (`feat(18-04): expose Phase 18 SDET public surface`) recorded on `main`.
- Runtime import smoke (`uv run python -c "from mcp_test_framework.sdet import ..."`) returns `OK`.
- Pyright clean: `0 errors`.
