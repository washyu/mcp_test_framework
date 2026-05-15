---
phase: 17-schema-driven-codegen-surface
plan: 03
subsystem: sdet-factory
tags: [factory, seam, phase18-handoff, codegen-05]
requirements: [CODEGEN-05]
status: complete
dependency_graph:
  requires:
    - "17-01 (ToolResponse base — TypeVar R bound)"
  provides:
    - "tool(name) factory + ToolWrapper[P, R] Generic (CODEGEN-05 seam)"
    - "_REGISTRIES + _ACTIVE_SLUG module-level slots (Phase 18 hook point)"
  affects:
    - "Phase 17-04 emitter consumer (generated _REGISTRY entries now have a typed home)"
    - "Phase 18 mcp_session fixture (slots ready to populate; .call() body deferred)"
tech-stack:
  added:
    - "typing.Generic + TypeVar (PEP 484 generic class)"
  patterns:
    - "Lazy registry — no import-time coupling to sdet/generated/"
    - "Module-level state seam with save/restore teardown discipline (autouse pytest fixture)"
    - "Stringly-typed lookup mirroring ToolNotFoundError shape (mcp_client.py:51-65)"
key-files:
  created:
    - "src/mcp_test_framework/sdet/_tool_factory.py"
    - "tests/framework/unit/test_tool_factory.py"
  modified: []
decisions:
  - "D-09 stringly-typed `tool(name).call(params)` surface (no attribute-namespace)"
  - "Ship the seam in Phase 17; defer wire body to Phase 18"
metrics:
  duration: "≈12 minutes (TDD RED → GREEN, no REFACTOR needed)"
  completed: "2026-05-13"
  tasks: 1
  files_created: 2
  tests_added: 8
---

# Phase 17 Plan 03: tool() Factory + ToolWrapper Seam Summary

One-liner: Shipped CODEGEN-05 seam — stringly-typed `tool(name)` returns a `ToolWrapper[P, R]` Generic whose `.call()` raises `NotImplementedError` pointing at Phase 18; module-level `_REGISTRIES` / `_ACTIVE_SLUG` slots locked as the Phase 18 `mcp_session` hook point.

## What Shipped

`src/mcp_test_framework/sdet/_tool_factory.py` — 115 lines:

- `class ToolWrapper(Generic[P, R])` where `P = TypeVar("P", bound=BaseModel)` and `R = TypeVar("R", bound=ToolResponse)`.
- `ToolWrapper.__init__(name, params_cls, response_cls)` stores the three introspection attributes.
- `ToolWrapper.call(params)` is `async` and raises `NotImplementedError` whose message names **`Phase 18`** and **`mcp_session`** and points at `REQUIREMENTS.md SDET-03`.
- `def tool(name: str) -> ToolWrapper` looks up the registered `(params_cls, response_cls)` tuple in `_REGISTRIES[_ACTIVE_SLUG]`.
- Module-level slots: `_REGISTRIES: dict[str, dict[str, tuple[type[BaseModel], type[ToolResponse]]]] = {}` and `_ACTIVE_SLUG: str | None = None`.

`tests/framework/unit/test_tool_factory.py` — 8 tests, all passing:

1. `test_imports_succeed` — guard for import-cycle regressions.
2. `test_tool_raises_when_no_active_registry` — `RuntimeError` mentions `mcp_session`.
3. `test_tool_returns_wrapper_for_registered_name` — `.name`, `.params_cls`, `.response_cls` exposed.
4. `test_tool_raises_with_candidate_list_on_unknown_name` — `KeyError` carries unknown name, all candidates, slug, and `gen-sdet-classes` remediation hint.
5. `test_call_raises_not_implemented_with_phase18_reference` — `NotImplementedError` mentions `Phase 18` AND `mcp_session`.
6. `test_tool_wrapper_is_generic` — `ToolWrapper[_FakeParams, _FakeResponse]` is subscriptable.
7. `test_state_resets_between_tests_part_a` / `part_b` — pin the autouse save/restore fixture discipline that Phase 18 must mirror.

## Phase 17 → Phase 18 Seam Mechanics

The seam is **module-level mutable state** with **autouse save/restore** as the test contract:

```python
# _tool_factory.py — Phase 17 ships these defaults.
_REGISTRIES: dict[str, dict[str, tuple[type[BaseModel], type[ToolResponse]]]] = {}
_ACTIVE_SLUG: str | None = None
```

Phase 18's `mcp_session` fixture sketch (forward-look, NOT implemented in this plan):

```python
# Phase 18 — sketch only; do not ship in this plan.
import importlib
import pytest

from mcp_test_framework.sdet import _tool_factory as tf


@pytest.fixture(scope="session")
async def mcp_session(config, mcp_client):
    slug = config.mcp_server.slug  # e.g. "homelab_mcp"
    # 1. Import the generated module — its top-level _REGISTRY dict is the source of truth.
    mod = importlib.import_module(f"mcp_test_framework.sdet.generated.{slug}")
    saved_slug = tf._ACTIVE_SLUG
    saved_reg = tf._REGISTRIES.get(slug)
    tf._REGISTRIES[slug] = mod._REGISTRY  # type: ignore[attr-defined]
    tf._ACTIVE_SLUG = slug
    try:
        # Phase 18 will also monkey-patch ToolWrapper.call to wire ClientSession.call_tool.
        yield mcp_client
    finally:
        tf._ACTIVE_SLUG = saved_slug
        if saved_reg is not None:
            tf._REGISTRIES[slug] = saved_reg
        else:
            tf._REGISTRIES.pop(slug, None)
```

The teardown discipline pinned by `test_state_resets_between_tests_part_a/b` is the **exact pattern Phase 18 must follow** to avoid the T-17.03-01 threat (stale registry bleed across sessions).

## tool() Factory Contract (LOCKED)

| Caller state | Outcome |
| --- | --- |
| `_ACTIVE_SLUG is None` | `RuntimeError("no MCP server registry is active... `mcp_session` fixture (Phase 18) is what activates a registry...")` |
| `_ACTIVE_SLUG = "<slug>"`, name **in** registry | Returns `ToolWrapper(name, params_cls, response_cls)`; `.call()` still raises `NotImplementedError` until Phase 18. |
| `_ACTIVE_SLUG = "<slug>"`, name **not in** registry | `KeyError(f"tool {name!r} is not in the generated registry for server {slug!r}. Available tools: [...sorted...]. Re-run `mcp-test-framework gen-sdet-classes`...")` |

Error-message shape mirrors `ToolNotFoundError` at `src/mcp_test_framework/mcp_client.py:51-65` (in-repo precedent for "lookup failure carries the candidate list").

## Deviations from Plan

None — plan executed exactly as written. RED gate failed with the expected `ImportError`; GREEN gate passed all 8 tests on first run. No REFACTOR needed.

## TDD Gate Compliance

- **RED gate:** commit `7e97911` — `test(17-03): add failing tests for tool() factory + ToolWrapper seam` (ImportError, 0 tests collected).
- **GREEN gate:** commit `8840f46` — `feat(17-03): ship tool() factory + ToolWrapper Generic for CODEGEN-05 seam` (8/8 tests passing).
- **REFACTOR gate:** N/A — no cleanup needed; the implementation matches the planned shape verbatim.

## Verification (per plan)

```
$ MCPTF_CONFIG_FILE=…/config.yaml uv run pytest tests/framework/unit/test_tool_factory.py -v
============================== 8 passed in 3.59s ==============================

$ uv run python -c "from mcp_test_framework.sdet._tool_factory import tool, ToolWrapper, _REGISTRIES, _ACTIVE_SLUG; print('OK', _ACTIVE_SLUG, len(_REGISTRIES))"
OK None 0

$ rg -c 'from mcp_test_framework.sdet.generated' src/mcp_test_framework/sdet/_tool_factory.py
(no matches — lazy registry confirmed; no import-time coupling)
```

## Threat Flags

None — no new trust boundaries beyond those declared in `<threat_model>`. The `KeyError` candidate-list disclosure (T-17.03-02) was already `accept`-dispositioned by the plan; the autouse-fixture pattern that mitigates T-17.03-01 is shipped + pinned by `test_state_resets_between_tests_part_a/b`.

## Known Stubs

`ToolWrapper.call()` is **intentionally** an `NotImplementedError`-raising stub — this is the Phase 17 → Phase 18 seam by design (per `<planner_authority_limits>` and the plan's `<objective>`). The error message points at `REQUIREMENTS.md SDET-03 (Phase 18)` so the operator knows exactly what is missing. This stub will be wired by Phase 18's `mcp_session` fixture; no other plan is required.

Not a "code wired to empty data" stub — the dispatch shape is fully functional and pyright-clean; only the wire body is deferred.

## Phase 17 → Phase 18 Handoff Checklist

Phase 18 will need to do **only** these things to this module:

1. Replace `ToolWrapper.call`'s body with a call to `ClientSession.call_tool(self.name, params.model_dump(mode="python"))` followed by `return self.response_cls(raw=<result>)`.
2. Ship the `mcp_session` fixture per the sketch above (save/restore `_ACTIVE_SLUG` + `_REGISTRIES[slug]`).
3. Add `tool` and `mcp_session` to `src/mcp_test_framework/sdet/__init__.py`'s `__all__` (Phase 17's `__init__.py` exports only `ToolResponse` per Plan 17-01).

The dispatch shape, error messages, TypeVar bounds, and slot contract are **frozen** as of this plan.

## Commits

| Hash | Type | Subject |
| --- | --- | --- |
| `7e97911` | test | add failing tests for tool() factory + ToolWrapper seam |
| `8840f46` | feat | ship tool() factory + ToolWrapper Generic for CODEGEN-05 seam |

## Self-Check: PASSED

- `src/mcp_test_framework/sdet/_tool_factory.py` — FOUND
- `tests/framework/unit/test_tool_factory.py` — FOUND
- Commit `7e97911` — FOUND
- Commit `8840f46` — FOUND
- All 8 unit tests passing
- `_tool_factory.py` does NOT import from `sdet.generated` (lazy registry confirmed)
- Smoke import test prints `OK None 0` as required by acceptance criteria
