---
phase: 18-sdet-test-surface-typed-errors
plan: 03
subsystem: sdet
tags: [sdet, mcp-session, fixture, registry-activation, SDET-03, SDET-04, D-01, D-02, D-03]
requires:
  - "mcp_test_framework.sdet._tool_factory._ACTIVE_CLIENT slot (Plan 18-02)"
  - "mcp_test_framework.sdet._tool_factory._ACTIVE_SLUG slot (Phase 17 CODEGEN-05)"
  - "mcp_test_framework.sdet._tool_factory._REGISTRIES slot (Phase 17 CODEGEN-05)"
  - "mcp_test_framework.fixtures._pytest_exit_operator_tone helper (Phase 13)"
  - "mcp_test_framework.fixtures.mcp_client session fixture (Phase 04.1)"
  - "mcp_test_framework.sdet._slugs.server_slug (Phase 17 CODEGEN-04)"
  - "mcp_test_framework.sdet.generated.<slug>._REGISTRY (Phase 17 CODEGEN-01..06)"
provides:
  - "mcp_test_framework.sdet.session.mcp_session pytest-asyncio fixture"
  - "McpTestClient.server_info public accessor (Implementation | None)"
  - "McpTestClient._wrap(..., server_info=...) kwarg threading from owner task"
affects:
  downstream:
    - "Plan 18-04 (sdet/__init__.py public surface) re-exports mcp_session"
    - "Plan 18-07 (tests/sdet/test_basic_call.py) consumes mcp_session"
    - "Plan 18-08 (tests/framework/unit/test_sdet_fixtures.py) shipped by this plan; future plans extend it"
tech_stack:
  added: []
  patterns:
    - "Session-scoped pytest-asyncio fixture with loop_scope='session' (alias of mcp_client)"
    - "SYNC registry-activation mutations around the yield (no anyio cancel scope; Phase 04.1 invariant)"
    - "Public Implementation attribute on McpTestClient, populated by both __aenter__ and _wrap()"
    - "FixtureFunctionDefinition._get_wrapped_function() for unit-testing pytest-asyncio fixtures"
key_files:
  created:
    - src/mcp_test_framework/sdet/session.py
    - tests/framework/unit/test_sdet_fixtures.py
  modified:
    - src/mcp_test_framework/mcp_client.py
    - src/mcp_test_framework/fixtures.py
decisions:
  referenced:
    - "D-01: mcp_session is the SDET alias for the existing mcp_client fixture (no duplicate lifecycle)"
    - "D-02: 5-step registry-activation flow lives in the fixture body (sync; cancel-scope safe)"
    - "D-03: ModuleNotFoundError -> _pytest_exit_operator_tone(returncode=2)"
    - "Phase 04.1 cancel-scope invariant preserved (mutations are SYNC; no anyio scope crosses yield)"
metrics:
  tasks_completed: 1
  files_created: 2
  files_modified: 2
  duration_seconds: 365
  completed_date: "2026-05-13"
---

# Phase 18 Plan 03: mcp_session fixture Summary

Shipped the `mcp_session` pytest-asyncio fixture as `src/mcp_test_framework/sdet/session.py`. The fixture is a session-scoped alias of the existing `mcp_client` fixture (D-01); around the yield it performs the D-02 5-step registry-activation flow (read `serverInfo.name`, slugify, `importlib.import_module`, read `_REGISTRY`, install `_ACTIVE_SLUG` / `_ACTIVE_CLIENT` / `_REGISTRIES[slug]`); on teardown it restores the prior state. D-03 fail-loud on `ModuleNotFoundError` uses `_pytest_exit_operator_tone(returncode=2)` with the operator-readable message naming the slug, `gen-sdet-classes`, and `--sdet`.

After this commit, the seam between Phase 17's `tool(name)` factory and Phase 18's live MCP wire is fully connected: an SDET test that requests `mcp_session` will activate the per-server registry, and `tool("name").call(params)` will route through the active client and raise `ToolCallError` on `result.isError`.

## What Was Built

### `src/mcp_test_framework/sdet/session.py` (new, 73 lines)

Single new module exporting one fixture:

```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_session(mcp_client: McpTestClient):
    server_name = mcp_client.server_info.name      # public accessor (Rule 3, see below)
    slug = server_slug(server_name)
    try:
        mod = importlib.import_module(f"mcp_test_framework.sdet.generated.{slug}")
    except ModuleNotFoundError:
        _pytest_exit_operator_tone(summary=..., detail=..., next_step=...)
    registry = getattr(mod, "_REGISTRY")
    prior_slug = _tf._ACTIVE_SLUG
    prior_client = _tf._ACTIVE_CLIENT
    _tf._REGISTRIES[slug] = registry
    _tf._ACTIVE_SLUG = slug
    _tf._ACTIVE_CLIENT = mcp_client
    try:
        yield mcp_client
    finally:
        _tf._ACTIVE_SLUG = prior_slug
        _tf._ACTIVE_CLIENT = prior_client
        _tf._REGISTRIES.pop(slug, None)
```

Pure D-01/D-02/D-03 implementation. No anyio cancel scope opens across the yield (Phase 04.1 invariant preserved); all mutations are stdlib-sync.

### `src/mcp_test_framework/mcp_client.py` (modified, Rule 3 deviation)

Added a public `server_info: Implementation | None` attribute to `McpTestClient`:

- `__init__` initializes it to `None`.
- `__aenter__` captures the live `init_result` from `session.initialize()` and stores `init_result.serverInfo`.
- `_wrap(..., server_info=...)` accepts the field as a kwarg (default `None`) so the `mcp_client` fixture's owner task can thread it through.

**Why this was a Rule 3 fix:** The plan's `<action>` block assumed `mcp_client._session.server_info.name` was reachable as a fallback. It is not. The mcp SDK's `ClientSession.initialize()` returns `InitializeResult(serverInfo=Implementation(...))` but `ClientSession` only caches `_server_capabilities` — `serverInfo` is dropped on the floor after the handshake (verified: `[a for a in dir(ClientSession) if 'server' in a.lower()] == ['get_server_capabilities']`). `cli.py`'s `_run_codegen_handshake` already works around this with a process-global monkey-patch on `ClientSession.initialize`, but that's a CLI-time hack inappropriate for a long-lived pytest fixture. The minimal correct fix is to capture `serverInfo` once at handshake time and expose it on the wrapper.

### `src/mcp_test_framework/fixtures.py` (modified, Rule 3 follow-on)

The `mcp_client` fixture's `_owner_task` now binds `init_result = await session.initialize()` and passes `server_info=init_result.serverInfo` to `McpTestClient._wrap(...)`. Single 4-line change inside the existing `try` block; no shape change to the owner-task / `asyncio.Future` / `asyncio.Event` plumbing.

### `tests/framework/unit/test_sdet_fixtures.py` (new, 7 tests)

| # | Test | Pins |
|---|------|------|
| 1 | `test_mcp_session_is_pytest_asyncio_session_scoped_fixture` | Decorator: `scope="session"` via `_fixture_function_marker`; `loop_scope="session"` via `_loop_scope` |
| 2 | `test_mcp_session_signature_depends_on_mcp_client` | First positional parameter named `mcp_client` (pytest resolves by name) |
| 3 | `test_mcp_session_module_imports_cleanly` | Smoke import — guards against circular-import regressions |
| 4 | `test_mcp_session_activates_registry_on_entry` | At yield time: `_ACTIVE_SLUG == "homelab_mcp"`, `_ACTIVE_CLIENT is mcp_client`, `_REGISTRIES["homelab_mcp"] is gen_mod._REGISTRY`; yielded value IS the client |
| 5 | `test_mcp_session_restores_prior_state_on_teardown` | After teardown: prior `_ACTIVE_SLUG`/`_ACTIVE_CLIENT` restored exactly; registry entry popped; other registry entries untouched |
| 6 | `test_mcp_session_fail_loud_on_missing_generated_module` | `pytest.exit.Exception` (`_pytest.outcomes.Exit`) with `returncode=2` and message containing "No generated SDET classes", the slugified server name, "gen-sdet-classes", and "--sdet" |
| 7 | `test_session_module_opens_no_anyio_cancel_scope` | Phase 04.1 invariant: `re.findall(r"with anyio\.\|CancelScope", source) == []` |

Test fixture infrastructure:
- `_FakeParams` / `_FakeResponse` ride on the existing Pydantic + `ToolResponse` shapes.
- `_reset_module_state` autouse fixture saves/restores `_ACTIVE_SLUG`, `_ACTIVE_CLIENT`, and `_REGISTRIES` to prevent cross-test bleed.
- `_unwrap(fixture)` uses `FixtureFunctionDefinition._get_wrapped_function()` (pytest >= 8 + pytest-asyncio 1.x) to reach the underlying async generator function.
- `_make_fake_client(server_name)` returns a `MagicMock` with `.server_info = SimpleNamespace(name=server_name)` — matches the public `server_info` accessor the GREEN phase added.

## Downstream Impact

After this commit:

- **Plan 18-04 (sdet public surface)** unblocked — re-export `mcp_session` through `src/mcp_test_framework/sdet/__init__.py` `__all__`.
- **Plan 18-07 (tests/sdet/test_basic_call.py)** unblocked — the sanity test will request `mcp_session` and call `tool("name").call(params)` end-to-end against the live (or synthetic) MCP server. The fixture is the single integration point that connects Phase 17 codegen, Plan 18-02's `_ACTIVE_CLIENT` slot, and Plan 18-01's `ToolCallError`.
- **Plan 18-08 (framework self-tests)** — this plan SHIPPED `tests/framework/unit/test_sdet_fixtures.py` directly. Plan 18-08 may extend it with cross-cutting tests (e.g. `mcp_session` + `--sdet` interaction) but does not need to author the D-01/D-02/D-03 pins; they are locked here.
- **No downstream impact on Plan 18-05/18-06** — `--sdet` CLI flag and runner-renderer integration are independent of the fixture body.

## Decisions Referenced

- **D-01** (Phase 18 CONTEXT.md lines 42): `mcp_session` aliases `mcp_client`; no duplicate `stdio_client` / `ClientSession` lifecycle. Honored — the fixture signature requests `mcp_client` by name; pytest-asyncio resolves the dependency chain.
- **D-02** (CONTEXT.md lines 44-51): 5-step registry activation; sync mutations only. Honored verbatim — `importlib.import_module` + `_REGISTRIES[slug] = registry` + attribute assignment on `_tf._ACTIVE_SLUG` / `_ACTIVE_CLIENT`, followed by `yield` inside a `try/finally` that restores prior state.
- **D-03** (CONTEXT.md lines 53-61): `ModuleNotFoundError` -> `_pytest_exit_operator_tone(returncode=2)` with the specific message shape. Honored — message contains the slug (post-normalization), the literal `serverInfo.name`, instructions to run `gen-sdet-classes`, and the `--sdet` flag.
- **Phase 04.1 cancel-scope invariant** (CONTEXT.md lines 240-241): no anyio scope across yield. Honored — verified by `test_session_module_opens_no_anyio_cancel_scope` which greps the module source for `with anyio\.` and `CancelScope`.

## Verification

| Check | Result |
|-------|--------|
| `grep -c "async def mcp_session"` | 1 |
| `grep -c '@pytest_asyncio.fixture(loop_scope="session", scope="session")'` | 1 |
| `grep -c "import importlib"` | 1 |
| `grep -c "from mcp_test_framework.fixtures import _pytest_exit_operator_tone"` | 1 |
| `grep -c "from mcp_test_framework.sdet._slugs import server_slug"` | 1 |
| `grep -c "from mcp_test_framework.sdet import _tool_factory as _tf"` | 1 |
| `grep -c "importlib.import_module"` | 1 |
| `grep -c "except ModuleNotFoundError"` | 1 |
| `grep -c "_pytest_exit_operator_tone"` | 3 (1 import + 1 call + 1 docstring; spec required ≥ 1) |
| `grep -c "_tf._ACTIVE_SLUG = slug"` | 1 |
| `grep -c "_tf._ACTIVE_CLIENT = mcp_client"` | 1 |
| `grep -c "_tf._REGISTRIES\[slug\] = registry"` | 1 |
| `grep -c "_tf._REGISTRIES.pop(slug, None)"` | 1 |
| `grep -c "yield mcp_client"` | 1 |
| `grep -cE "with anyio\.\|CancelScope"` | 0 (Phase 04.1 invariant) |
| `grep -c "No generated SDET classes"` | 1 |
| `grep -c "gen-sdet-classes"` | 2 (see deviation below — plan expected 1, D-03 message shape mandates 2) |
| `grep -c "\-\-sdet"` | 1 |
| `grep -c "try:"` | 2 (one around import_module, one around yield) |
| `grep -c "finally:"` | 1 (teardown restoration) |
| `uv run python -c "from mcp_test_framework.sdet.session import mcp_session; print('OK')"` | exit 0, prints `OK` |
| `uv run pyright src/mcp_test_framework/sdet/session.py` | 0 errors, 0 warnings, 0 informations |
| `uv run pyright src/mcp_test_framework/mcp_client.py` | 0 errors |
| `uv run pyright tests/framework/unit/test_sdet_fixtures.py` | 0 errors |
| `uv run pytest tests/framework/unit/test_sdet_fixtures.py --noconftest -v` | 7 passed in 0.60s |
| `uv run pytest tests/framework/unit/test_tool_factory.py --noconftest` | 12 passed (regression check — Plan 18-02 tests still green) |
| `uv run pytest tests/framework/unit/test_mcp_client.py --noconftest` | 5 passed (regression check) |

`--noconftest` rationale: `tests/conftest.py:_session_needs_preflight` keys on a `tests/unit/` prefix that excludes `tests/framework/unit/`, so the unit run otherwise triggers the live MCP/Ollama preflight. This is a pre-existing infrastructure mismatch already documented in Plan 18-02 SUMMARY's "Out-of-Scope Deferred Item" section.

## Threat Model Compliance

| Threat ID | Disposition | Implementation |
|-----------|-------------|----------------|
| T-18-08 (Tampering on `importlib.import_module(f"...{slug}")`) | mitigate | `slug` passes through `_slugs.server_slug` which normalizes to `[a-z0-9_]+` only; the parent package `mcp_test_framework.sdet.generated` constrains the search space to a single directory under `sys.path`. No filesystem path traversal possible because dotted module paths resolve via package lookup, not `os.path.join`. |
| T-18-09 (DoS on `mcp_client.server_info.name`) | accept | Server name is bounded by MCP protocol (≤ 64 chars typical); slug derivation is O(N) over the name. |
| T-18-10 (Elevation via `_tf._ACTIVE_*` mutations) | accept | Process-local state; `try/finally` restores prior values on every code path (including pytest-failure exit); no privilege boundary crossed. |

## Deviations from Plan

### `[Rule 3 - Blocking]` McpTestClient.server_info accessor did not exist

**Found during:** Task 1 read-first phase, while verifying `mcp_client._session.server_info.name` against the mcp SDK source.

**Issue:** The plan's `<action>` block instructed: *"Verify by reading `src/mcp_test_framework/mcp_client.py` whether `McpTestClient` exposes a `server_info` property; if it does, USE THAT instead of `_session.server_info.name`."* The verification surfaced a gap the plan did not anticipate — the mcp SDK's `ClientSession.initialize()` returns `InitializeResult(serverInfo=Implementation(...))` but `ClientSession` only caches `_server_capabilities` on itself; `serverInfo` is **dropped** after the handshake. Confirmed by:

```
>>> [a for a in dir(ClientSession) if 'server' in a.lower()]
['get_server_capabilities']
```

So `mcp_client._session.server_info.name` would raise `AttributeError` at runtime, and `mcp_client.server_info.name` (the public-accessor alternative) would also fail because no such attribute existed. The fixture had no way to read the server name without monkey-patching `ClientSession.initialize` (which is `cli.py`'s pre-existing CLI-time workaround in `_run_codegen_handshake` — inappropriate for a long-lived pytest fixture because it requires a process-wide lock and risks races between concurrent fixture instantiations).

**Fix:** Threaded `serverInfo` through `McpTestClient._wrap` and surfaced it as the public `server_info: Implementation | None` attribute. The `mcp_client` fixture's owner task already calls `await session.initialize()`; bind its return value (`init_result`) and pass `server_info=init_result.serverInfo` to `_wrap`. For the smoke path, `__aenter__` does the same. The attribute is `None` until the handshake completes; `mcp_session` asserts non-None before reading.

**Files modified:**
- `src/mcp_test_framework/mcp_client.py` — added `server_info` attribute on `__init__`, kwarg on `_wrap`, and capture in `__aenter__`. Added `Implementation` to the `mcp.types` import line.
- `src/mcp_test_framework/fixtures.py` — owner task binds `init_result = await session.initialize()` and passes `server_info=init_result.serverInfo` to `_wrap`.

**Commit:** rolled into the single task commit (`e11ef56`).

**Tracked as:** `[Rule 3 - Blocking]` per the GSD deviation rules. This was strictly required to satisfy the plan's `<success_criteria>` ("Around the yield, `_tf._ACTIVE_SLUG`, `_tf._ACTIVE_CLIENT`, and `_tf._REGISTRIES[slug]` are set"). Without the Rule 3 fix the fixture body could not produce a slug, so no registry could ever be activated. The minimal scope (3 files, ~10 net additive lines) is consistent with Rule 3 ("auto-fix blocking issues") rather than Rule 4 ("ask about architectural changes") — no schema, no new module, no new dep, and the `__aenter__` smoke path already had the exact same single-line capture pattern available.

### `[Rule 1 - Bug]` Acceptance criterion `grep -c "gen-sdet-classes" == 1` vs D-03 message spec

**Found during:** Task 1 grep verification phase.

**Issue:** The plan's acceptance criterion was `grep -c "gen-sdet-classes" returns 1`, but the D-03 message shape from CONTEXT.md lines 58-59 prescribes TWO occurrences:
1. Detail line: *"This usually means `gen-sdet-classes` has not been run..."*
2. Next-step line: *"run `mcp-test-framework gen-sdet-classes` against this server first..."*

The plan's `<action>` block (lines 200-211) copy-pasted both occurrences directly. The acceptance criterion and the action prescription were inconsistent.

**Fix:** Honored the D-03 message shape (2 occurrences) and documented the count divergence. The acceptance criterion is mechanical guidance for the executor; the D-03 message is the operator-facing contract. When they conflict, the operator contract wins (this is the same pattern Plan 18-02 SUMMARY recorded for its `NotImplementedError` grep-vs-docstring divergence).

**Files modified:** None beyond the original `session.py` authored against D-03.

**Commit:** rolled into the single task commit (`e11ef56`).

**Tracked as:** `[Rule 1 - Bug]` acceptance-criterion / specification misalignment. Same class of issue as the Plan 18-02 docstring-rewording deviation.

### `[Rule 1 - Bug]` `_pytestfixturefunction` marker access pattern

**Found during:** TDD GREEN-phase test execution.

**Issue:** First version of `test_mcp_session_is_pytest_asyncio_session_scoped_fixture` read `mcp_session._pytestfixturefunction` per the legacy pytest fixture introspection idiom. Under pytest 9.0 + pytest-asyncio 1.x, fixtures are wrapped as `FixtureFunctionDefinition` objects exposing `_fixture_function_marker` (the `FixtureFunctionMarker` with `scope`) and `_loop_scope` separately. The `_pytestfixturefunction` attribute is `None`.

**Fix:** Rewrote the test to read `_fixture_function_marker.scope` and `_loop_scope` independently. Updated `_unwrap(fixture)` helper to use `FixtureFunctionDefinition._get_wrapped_function()` instead of the legacy `__wrapped__` attribute (with a fallback for non-asyncio fixtures).

**Files modified:** `tests/framework/unit/test_sdet_fixtures.py` only (test author error, no implementation change).

**Commit:** rolled into the single task commit (`e11ef56`).

**Tracked as:** `[Rule 1 - Bug]` test-author error — pytest 9 / pytest-asyncio 1.x fixture introspection idiom.

## Out-of-Scope Deferred Item

`src/mcp_test_framework/fixtures.py` lines 419, 434 — pre-existing pyright errors on the `judge` fixture (`Return type of async generator function must be compatible with "AsyncGenerator[Any, Any]"`). These errors exist on `main` BEFORE this plan and are not caused by Plan 18-03's Rule 3 fix (verified via `git stash` + `pyright` rerun). Same out-of-scope pattern Plan 18-02 SUMMARY documented for the `tests/conftest.py:_session_needs_preflight` nodeid prefix mismatch. Recorded here for the deferred-items tracker rather than as a deviation.

## TDD Gate Compliance

This plan's task is marked `tdd="true"`. Gate sequence verified in `git log`:

| Gate | Commit | Notes |
|------|--------|-------|
| RED  | `919e2d0` | `test(18-03): add failing tests for mcp_session fixture (D-01/D-02/D-03)` — 7 tests authored; all fail with `ModuleNotFoundError: No module named 'mcp_test_framework.sdet.session'` (the module did not exist yet). |
| GREEN | `e11ef56` | `feat(18-03): add mcp_session fixture with registry activation (D-01/D-02/D-03)` — session.py + Rule 3 fix lands; 7/7 tests pass; 17/17 regression tests still pass. |
| REFACTOR | (not needed) | The GREEN module is already minimal — no duplication, no dead branches; the docstring is the only place where wording was tightened during GREEN to satisfy the plan's grep counts. |

## Self-Check: PASSED

- `src/mcp_test_framework/sdet/session.py` — FOUND (73 lines, new)
- `tests/framework/unit/test_sdet_fixtures.py` — FOUND (210 lines, new)
- `src/mcp_test_framework/mcp_client.py` — FOUND (modified; `server_info` attribute + `_wrap` kwarg + `__aenter__` capture)
- `src/mcp_test_framework/fixtures.py` — FOUND (modified; owner task threads `server_info=` to `_wrap`)
- commit `919e2d0` — FOUND (RED tests)
- commit `e11ef56` — FOUND (GREEN implementation)
- pyright clean on all four touched files in this plan (`session.py`, `mcp_client.py`, `test_sdet_fixtures.py`); pre-existing `fixtures.py` judge-fixture pyright errors are out of scope
- 7/7 D-01/D-02/D-03 pins pass
- 17/17 regression tests (`test_tool_factory.py` + `test_mcp_client.py`) pass
- Phase 04.1 invariant verified by test #7 (`re.findall(r"with anyio\.|CancelScope", session.py source) == []`)
