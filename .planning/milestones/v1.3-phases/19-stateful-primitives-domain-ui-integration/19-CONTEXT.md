# Phase 19: Stateful primitives + domain UI integration - Context

**Gathered:** 2026-05-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Turn Phase 18's runtime SDET surface (`mcp_session`, `tool()`, `ToolCallError`, `tests/sdet/` discovery scope, `_render_per_tool_rows` em-dash failure detail) into a stateful authoring idiom. Three deliverables:

1. **Module-scope yield-fixture pattern + cleanup-on-failure contract** — SDETs author a `scope="module"` fixture that yields a typed `ScenarioState` dataclass; tests within the module progressively mutate the state; teardown always runs even when an intervening test fails. Pattern is dogfooded by the framework's own VM-lifecycle scenario.
2. **VM-lifecycle dogfood (live Proxmox)** — `tests/sdet/test_proxmox_vm_lifecycle.py` exercises `create_proxmox_vm` → `manage_proxmox_vm` (CPU bump 1 → 2) → `delete_proxmox_vm` against the operator's live Proxmox cluster. Pinned VMID range 9990–9999, name prefix `mcptf-dogfood-{timestamp}`, teardown sweeps stranded prior-crash VMs.
3. **Domain-UI rendering for scenarios (UI-01)** — each scenario module renders as a per-tool group header (`proxmox_vm_lifecycle`); individual tests render as nested rows with `test_`-stripped function names (`create_returns_pending_vm`, `modify_accepts_cpu_increase`, `delete_returns_ok`); same PASS/✗/SKIP glyph vocabulary and em-dash failure-detail (Phase 16) the contract pass already uses.

**In scope:** STATE-01, STATE-02, STATE-03, STATE-04, UI-01 (5 requirements). Module-scope yield idiom + `ScenarioState` dataclass shape, cleanup-on-failure self-test, dogfood VM-lifecycle scenario with VMID isolation, `_render_per_tool_rows` extension for `tests/sdet/` nodeids, JUnit `classname`-based group key derivation, cross-file-ordering documented as a `pytest-order` recipe (no framework adoption).

**Out of scope (deliberate):**
- `requires_homelab(...)` preflight + reachability checks — Phase 20 (PREFLIGHT-01..02). Phase 19's dogfood fails loud on unreachable Proxmox; Phase 20 makes it skip cleanly.
- Authoring docs (`docs/SDET-AUTHORING.md`, README parity) — Phase 21 (DOC-SDET-01..03). The `pytest-order` cross-file recipe is captured as a decision here; the prose lands in Phase 21.
- Requirement-ID leak scrub in src/ — Phase 22 (SCRUB-SRC-01). Phase 19's new code must avoid requirement-ID docstrings from day one (no `STATE-01`/`UI-01`-style tags in operator-visible help text).
- `pytest-order` as a framework dependency — recipe only.
- Multi-server scenarios — single-server contract holds.
- Per-judge breakdown under `--debug` — Phase 16 D-11, deferred to v1.5.
- Mock MCP for the dogfood — violates the black-box principle; Phase 19 ships live or it doesn't ship.

**Hard dependencies (LOCKED — implement against):**
- Phase 18 `mcp_session` fixture (`src/mcp_test_framework/sdet/session.py`) — module-scope scenario fixtures consume `mcp_session` as the live MCP driver. Stays session-scoped; scenario fixtures depend on it.
- Phase 18 `tool(name).call(params)` factory (`src/mcp_test_framework/sdet/_tool_factory.py`) — the only mechanism for issuing the actual wire call in dogfood / scenario tests.
- Phase 18 `ToolCallError` (`src/mcp_test_framework/sdet/errors.py`) — scenario tests propagate `ToolCallError` to the renderer via the existing `pytest_exception_interact` hook in `tests/sdet/conftest.py` (Phase 18 D-09). No new error-routing needed.
- Phase 18 D-06 scenario digest in `_runner.py` (`_render_scenario_pre_run_digest`, `_collect_sdet_scenarios`) — already keys on scenario MODULE names. Phase 19's `_render_per_tool_rows` extension reuses the same module-name derivation so digest and rows agree.
- Phase 17 generated `<ToolName>Params` / `<ToolName>Response` classes — dogfood imports `CreateProxmoxVmParams`, `CreateProxmoxVmResponse`, `ManageProxmoxVmParams`, `ManageProxmoxVmResponse`, `DeleteProxmoxVmParams`, `DeleteProxmoxVmResponse`, `GetProxmoxVmStatusResponse` from `src/mcp_test_framework/sdet/generated/homelab_mcp/`.
- Phase 16 renderer surface (`_render_per_tool_rows`, em-dash separator U+2014, PASS/✗/SKIP glyph vocabulary) — extended (not reshaped) for `tests/sdet/` nodeids.
- Phase 15 test-surface split — dogfood lives under `tests/sdet/`; self-test for cleanup-on-failure lives under `tests/framework/unit/`.
- Phase 04.1 cancel-scope invariant (`fixtures.py:324-410`) — module-scope scenario fixtures must NOT introduce a CancelScope across the yield boundary. Standard `yield` + pytest finalizer is the locked pattern.
- Black-box rule — dogfood imports generated classes only; never reaches into `homelab-mcp` source. The `pytest-order` recipe is doc-only — no framework code uses it.

</domain>

<decisions>
## Implementation Decisions

### Dogfood scenario design

- **D-01: Live Proxmox, real VM.** The dogfood creates an actual VM on the operator's live Proxmox node, modifies it, deletes it. Preview/dry-run tools (`delete_proxmox_vm_preview`) are NOT used in the create/delete steps — the whole point of the dogfood is to exercise the cleanup-on-failure contract against real state. Mock MCP is explicitly rejected (violates Phase 04.1 black-box invariant). Until Phase 20 ships `requires_homelab`, the dogfood fails loud if Proxmox is unreachable.

- **D-02: Modify step = CPU core bump (1 → 2).** `manage_proxmox_vm` is called with `cores=2`. Verification re-reads via `get_proxmox_vm_status` and asserts `.data.cpus == 2`. Test function name: `test_modify_accepts_cpu_increase`. Idempotent enough that a stranded VM at 2 cores is the same shape as one at 1.

- **D-03: VMID isolation — reserved range + timestamped name prefix.** Dogfood pins VMID range 9990–9999 (configurable via a `homelab.proxmox.dogfood_vmid_range: [9990, 9999]` block in `config.yaml`; default = `[9990, 9999]`). Name prefix `mcptf-dogfood-{ISO8601-timestamp-second-precision}`. Module-scope teardown sweeps any stranded `mcptf-dogfood-*` VMs in the configured range from prior crashed runs (best-effort; logs sweep results; never fails teardown over a sweep miss). Configurable so a v2 operator can repoint at a non-default range without forking.

### Scenario state shape (STATE-03)

- **D-04: Module-scope fixture yields a per-scenario `ScenarioState` dataclass.** For the dogfood:
  ```python
  @dataclass
  class ProxmoxVmLifecycleState:
      created: CreateProxmoxVmResponse
      modified: ManageProxmoxVmResponse | None = None
      # delete result is observed via assertion only; no need to retain
  ```
  The fixture sets `created`; downstream tests mutate `state.modified = await tool("manage_proxmox_vm").call(...)`. Typed end-to-end via Phase 17 generated response classes. One dataclass per scenario module (~5–10 LOC each). Pattern (not a base class) — each scenario owns its state shape; the framework ships no abstract `ScenarioState` superclass.

- **D-05: Plain dict, `SimpleNamespace`, and tuple-unpacking patterns are rejected.** STATE-03 explicitly requires "typed via the response class"; untyped containers don't satisfy. Mutating a generated `Response` instance directly (option B in the discussion) is also rejected — the generated classes carry a "do not hand-edit" header and instance mutation blurs that contract.

### Cleanup-on-failure self-test (STATE-02)

- **D-06: Self-test = direct fixture with finalizer counter.** Lives at `tests/framework/unit/test_state_cleanup_on_failure.py`. Shape:
  ```python
  _teardown_count = 0

  @pytest.fixture
  def stateful_resource():
      yield "resource"
      global _teardown_count
      _teardown_count += 1

  def test_consumer_fails_deliberately(stateful_resource):
      assert False, "intentional failure to trigger teardown path"

  def test_teardown_ran_despite_failure():
      # Ordered AFTER the failing test (pytest collects in file order).
      assert _teardown_count == 1
  ```
  Uses `@pytest.mark.xfail(strict=True)` on `test_consumer_fails_deliberately` so the suite still reports green when both tests pass. No MCP, no subprocess, no `pytester`. <100 ms. Self-contained regression guard.

- **D-07: One self-test file, not subprocess + direct (the "both shapes" option is rejected).** STATE-02 is fully pinned by D-06's counter assertion; a subprocess JUnit-XML assertion would prove the same pytest-native behavior at 50× the cost. If the runner reporting integration breaks, Phase 19's UI-01 tests already catch that downstream.

### Renderer key (UI-01)

- **D-08: Scenario group key = JUnit `classname` with `test_` prefix and `.py` extension stripped.** `tests/sdet/test_proxmox_vm_lifecycle.py::test_create_returns_pending_vm` → JUnit `classname="tests.sdet.test_proxmox_vm_lifecycle"` → group key `proxmox_vm_lifecycle`. Renderer applies this transformation when `nodeid.startswith("tests/sdet/")`; `tests/contract/` keeps parametrize-id grouping unchanged. One scenario per module is enforced by convention (not by code); two scenarios in one module would collapse into one group header, which the operator would notice immediately.

- **D-09: Row label = test function name with `test_` stripped.** `test_create_returns_pending_vm` → `create_returns_pending_vm`. Matches the ROADMAP wording verbatim. Renderer applies this when emitting nested rows under an SDET group; existing PASS/✗/SKIP glyphs + em-dash failure-detail unchanged. Phase 18 D-06's scenario digest already uses the same module-name derivation, so digest line and per-tool rows agree.

- **D-10: Custom pytest markers, module-scope-fixture-name keying, and class-wrapped scenarios are rejected.** All three add SDET-facing API surface that Phase 21 would have to document and Phase 22 would have to keep ID-leak-free. Module filename is zero-API: the file you write IS the scenario name.

### Cross-file ordering (STATE-04)

- **D-11: `pytest-order` is recipe-only — not added as a project dep.** The dogfood is single-file by D-04, so the framework itself never needs cross-file ordering. STATE-04 ships as a documented pattern in Phase 21's `docs/SDET-AUTHORING.md`:
  > "If your scenario spans files, add `pytest-order` to YOUR project's dev deps and annotate tests with `@pytest.mark.order(N)`. The framework ships no custom ordering mechanism."

  Framework does not import, vendor, or transitively pull in `pytest-order`. Phase 19 plans MUST NOT add it to `pyproject.toml`.

### Open / inferred (planner decides)

- **Existing `_runner.py` parser changes.** Phase 18 D-09 hook reads `mcptf_error_*` JUnit properties for `ToolCallError` rendering. Phase 19's per-tool-rows extension reads `classname` instead (or in addition). Planner figures out whether to extend `parse_junit_xml` or add a sibling helper.
- **Module-scope fixture wiring detail.** Whether the scenario fixture depends on `mcp_session` directly (recommended — single source of truth) or re-derives via `_ACTIVE_CLIENT`. Planner picks based on which produces the cleanest type signatures.
- **Sweep failure handling.** D-03 says teardown sweep is best-effort. Whether sweep emits a warning, a log message, or silently soldiers on — planner decides based on what the existing `_pytest_exit_operator_tone` helper already supports.

</decisions>

<specifics>
## Specific Ideas

**Dogfood scenario file layout** (one module, function names match D-09 row-label policy):

```python
# tests/sdet/test_proxmox_vm_lifecycle.py

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from dataclasses import dataclass

from mcp_test_framework.sdet import mcp_session, tool
from mcp_test_framework.sdet.generated.homelab_mcp import (
    CreateProxmoxVmParams, CreateProxmoxVmResponse,
    ManageProxmoxVmParams, ManageProxmoxVmResponse,
    DeleteProxmoxVmParams,
    GetProxmoxVmStatusParams, GetProxmoxVmStatusResponse,
)

@dataclass
class ProxmoxVmLifecycleState:
    created: CreateProxmoxVmResponse
    modified: ManageProxmoxVmResponse | None = None

@pytest_asyncio.fixture(scope="module", loop_scope="session")
async def proxmox_vm_lifecycle(mcp_session):
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"mcptf-dogfood-{timestamp}"
    vmid = _next_free_dogfood_vmid(...)  # within configured range
    # ... sweep stranded mcptf-dogfood-* in range, best-effort ...
    created = await tool("create_proxmox_vm").call(
        CreateProxmoxVmParams(vmid=vmid, name=name, cores=1, ...)
    )
    state = ProxmoxVmLifecycleState(created=created)
    yield state
    # Teardown: always runs even if an intervening test failed.
    await tool("delete_proxmox_vm").call(DeleteProxmoxVmParams(vmid=vmid))

@pytest.mark.asyncio(loop_scope="session")
async def test_create_returns_pending_vm(proxmox_vm_lifecycle):
    state = proxmox_vm_lifecycle
    assert state.created.data["vmid"] == ...  # via generated response
    # ... assertion shape per generated Response schema ...

@pytest.mark.asyncio(loop_scope="session")
async def test_modify_accepts_cpu_increase(proxmox_vm_lifecycle):
    state = proxmox_vm_lifecycle
    state.modified = await tool("manage_proxmox_vm").call(
        ManageProxmoxVmParams(vmid=state.created.data["vmid"], cores=2)
    )
    status = await tool("get_proxmox_vm_status").call(
        GetProxmoxVmStatusParams(vmid=state.created.data["vmid"])
    )
    assert status.data["cpus"] == 2

@pytest.mark.asyncio(loop_scope="session")
async def test_delete_returns_ok(proxmox_vm_lifecycle):
    state = proxmox_vm_lifecycle
    result = await tool("delete_proxmox_vm").call(
        DeleteProxmoxVmParams(vmid=state.created.data["vmid"])
    )
    # ... assertion per generated DeleteProxmoxVmResponse ...
```

**Expected operator output (UI-01)** when the dogfood runs against a reachable Proxmox:

```
proxmox_vm_lifecycle
  ✓ create_returns_pending_vm
  ✓ modify_accepts_cpu_increase
  ✓ delete_returns_ok
```

**Phase 18 `@pytest.mark.asyncio(loop_scope="session")` lesson** carries forward — every `tests/sdet/` async test uses this marker form (not bare `@pytest.mark.asyncio`) because `mcp_session` is session-scoped. Phase 21 docs will absorb this pitfall (Phase 18 SUMMARY 18-07 already flagged it).

**STATE-02 self-test file template** (D-06): see decision block above for the verbatim shape.

</specifics>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` — Phase 19 entry (goal, requirements, success criteria, plans TBD)
- `.planning/REQUIREMENTS.md` — STATE-01..04, UI-01 definitions
- `.planning/PROJECT.md` — project boundaries, Key Decisions table, framework-primitives principle
- `.planning/STATE.md` — Phase 18 closure context, v1.3 milestone state
- `.planning/phases/18-sdet-test-surface-typed-errors/18-CONTEXT.md` — locks D-01..D-11 for Phase 18 (mcp_session, tool factory, ToolCallError, --sdet, renderer hookup). Phase 19 builds on these.
- `.planning/phases/18-sdet-test-surface-typed-errors/18-06-SUMMARY.md` — `_render_per_tool_rows` and JUnit parser current state; integration target for UI-01.
- `.planning/phases/18-sdet-test-surface-typed-errors/18-07-SUMMARY.md` — `tests/sdet/conftest.py` hook + `loop_scope="session"` pitfall.
- `src/mcp_test_framework/_runner.py` — `_render_per_tool_rows` (line ~973), `parse_junit_xml` (line ~480+), `_render_scenario_pre_run_digest` (line ~849).
- `src/mcp_test_framework/sdet/session.py` — `mcp_session` fixture (the dependency for scenario module-scope fixtures).
- `src/mcp_test_framework/sdet/generated/homelab_mcp/` — generated `<ToolName>Params/Response` classes for Proxmox VM tools.
- `tests/sdet/conftest.py` — `pytest_exception_interact` hook (Phase 18 D-09) — `ToolCallError` propagation to renderer; reused as-is.
- `tests/sdet/test_basic_call.py` — Phase 18 reference implementation for SDET test authoring style (loop_scope, async marker shape).
- Memory: [Framework primitives; SDET owns safety (SEED-022)](.) — locks the architectural principle that the framework provides primitives, the SDET decides what to call. Cited when proposals say "framework should auto-detect/skip destructive tools."

</canonical_refs>

<deferred>
## Deferred Ideas

None surfaced in this discussion. (User's earlier Phase 17/18 sessions captured most of the SDET-surface deferrals; the cross-file `pytest-order` choice landed as a recipe within Phase 19's scope, not a deferral.)

</deferred>
