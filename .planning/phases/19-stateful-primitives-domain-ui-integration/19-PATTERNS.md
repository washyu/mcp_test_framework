# Phase 19: Stateful primitives + domain UI integration - Pattern Map

**Mapped:** 2026-05-13
**Files analyzed:** 5 (1 dogfood scenario + 1 self-test + 2 src/ modifications + 1 example-config addition)
**Analogs found:** 4 / 5 (one genuinely new pattern: cleanup-on-failure self-test using `xfail(strict=True)` + module global counter)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tests/sdet/test_proxmox_vm_lifecycle.py` (NEW) | integration test / dogfood scenario | request-response + module-scope state | `tests/sdet/test_basic_call.py` (loop_scope idiom) + `src/mcp_test_framework/fixtures.py:444-460` (judge AsyncExitStack pattern) | role-match (no existing module-scope yield fixture in repo) |
| `tests/framework/unit/test_state_cleanup_on_failure.py` (NEW) | unit test (pytest-native semantics pin) | event-driven (fixture finalizer) | `tests/framework/test_tool_config.py:218` (xfail decorator shape, `strict=False`) | partial — no existing `xfail(strict=True)` analog; D-06 supplies the verbatim shape |
| `src/mcp_test_framework/_runner.py` (MODIFY — `parse_junit_xml` ~line 489) | XML parser | transform | itself (`parse_junit_xml` lines 489-563) — existing `_extract_tool_name` parametrize-id extraction is the inversion analog for SDET classname extraction | exact (extend in place) |
| `src/mcp_test_framework/_runner.py` (MODIFY — `_render_per_tool_rows` ~line 973) | renderer | transform | itself (`_render_per_tool_rows` lines 973-1024) — unchanged if parser populates `per_tool[scenario_group]` with synthetic `[test_function_name]` entries | exact (parser-side change only; renderer is data-driven) |
| `src/mcp_test_framework/models.py` (MODIFY — add `HomelabProxmoxConfig`) | config sub-model | data model | `src/mcp_test_framework/models.py:36-73` (OllamaConfig + McpServerConfig — frozen Pydantic v2 sub-models) | exact |
| `src/mcp_test_framework/config.py` (MODIFY — add `homelab:` field) | config root | data model | `src/mcp_test_framework/config.py:53-54` (`ollama`/`mcp_server` field declaration) | exact |
| `examples/homelab-mcp.yaml` (MODIFY — add `homelab.proxmox.dogfood_vmid_range`) | example config | static / YAML | `examples/homelab-mcp.yaml:12-15` (`mcp_server:` block style) | exact |

---

## Pattern Assignments

---

### `tests/sdet/test_proxmox_vm_lifecycle.py` (NEW — dogfood scenario, request-response + module state)

**Analogs:**
- **A — `loop_scope` / async-marker idiom:** `tests/sdet/test_basic_call.py` (Phase 18 Plan 07; the only existing `tests/sdet/` test).
- **B — AsyncExitStack-based fixture body for live-resource lifecycle:** `src/mcp_test_framework/fixtures.py:444-460` (`judge` fixture).
- **C — `mcp_session` consumption + `tool().call()` ergonomics:** `tests/sdet/test_basic_call.py:42-53`.

**Critical lock from Plan 18-07 SUMMARY:** Every async test under `tests/sdet/` MUST use `@pytest.mark.asyncio(loop_scope="session")`. Bare `@pytest.mark.asyncio` hangs at the wire boundary because `mcp_session` is session-scoped. The dogfood fixture is `scope="module"` (per D-04) and STILL needs `loop_scope="session"` on the decorator — the loop is session-pinned even if the fixture scope is narrower.

**Existing async-test header pattern (test_basic_call.py:1-39 — copy structure verbatim):**
```python
"""Phase 19 SDET dogfood: VM lifecycle scenario (STATE-01..04 + UI-01).
...
# tool: create_proxmox_vm / manage_proxmox_vm / delete_proxmox_vm / get_proxmox_vm_status
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from dataclasses import dataclass

from mcp_test_framework.sdet import mcp_session, tool  # noqa: F401
from mcp_test_framework.sdet.generated.homelab_mcp import (
    CreateProxmoxVmParams, CreateProxmoxVmResponse,
    ManageProxmoxVmParams, ManageProxmoxVmResponse,
    DeleteProxmoxVmParams,
    GetProxmoxVmStatusParams,
)
```

The `# tool: ...` header lock from Plan 18-07 Warning-4 (line 32 of test_basic_call.py) carries forward — pin the tool choices so a re-plan can't silently re-decide.

**Async marker pattern from test_basic_call.py:42 + :56:**
```python
@pytest.mark.asyncio(loop_scope="session")
async def test_basic_tool_round_trip(mcp_session) -> None:
```

**Module-scope yield fixture shape (NO direct analog — assembled from CONTEXT D-04 + Plan 18-07 loop_scope pitfall + fixtures.py:444-460 AsyncExitStack idiom):**

The codebase has zero `scope="module"` async fixtures. The closest shape is the session-scoped `judge` fixture body, which is also async-yield and owns a live network resource. Use it as the structural model — only the scope changes:

`fixtures.py:444-460` (judge — analog for "fixture body owns live resource + yields + teardown"):
```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def judge(config: Config, _preflight) -> Judge:
    """Long-lived OllamaJudge instance, exposed to tests as Judge Protocol.
    ...
    """
    async with AsyncExitStack() as stack:
        instance = await stack.enter_async_context(
            OllamaJudge(
                config.ollama.base_url,
                config.ollama.model,
                config.ollama.timeout_seconds,
            )
        )
        yield instance
```

**Phase 19 dogfood fixture (CONTEXT.md `<specifics>` lines 136-148 verbatim, plus the loop_scope lock):**
```python
@dataclass
class ProxmoxVmLifecycleState:
    """STATE-03: typed state shape per scenario. NOT a base class -- each
    scenario module owns its own dataclass (CONTEXT.md D-04).
    """
    created: CreateProxmoxVmResponse
    modified: ManageProxmoxVmResponse | None = None
    # delete result is observed via assertion; no need to retain.


@pytest_asyncio.fixture(scope="module", loop_scope="session")
async def proxmox_vm_lifecycle(mcp_session):
    """STATE-01/02/03: module-scope yield fixture; teardown always runs.

    CONTEXT.md D-03: VMID isolation -- reserved range from config
    (homelab.proxmox.dogfood_vmid_range, default [9990, 9999]) + timestamped
    name prefix. Module-scope teardown sweeps stranded mcptf-dogfood-*
    VMs from prior crashed runs (best-effort; log on failure).
    """
    # Best-effort sweep of prior-crash strays before allocation. Failures
    # logged but do NOT fail setup -- CONTEXT.md D-03 "best-effort sweep".
    # ... sweep ...

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"mcptf-dogfood-{timestamp}"
    vmid = _next_free_dogfood_vmid(...)  # within configured range

    created = await tool("create_proxmox_vm").call(
        CreateProxmoxVmParams(vmid=vmid, name=name, cores=1, ...)
    )
    state = ProxmoxVmLifecycleState(created=created)
    try:
        yield state
    finally:
        # STATE-01/02: teardown ALWAYS runs, even if an intervening test
        # failed. Standard pytest yield finalizer is the locked pattern
        # (Phase 04.1 invariant: NO anyio CancelScope across the yield).
        await tool("delete_proxmox_vm").call(DeleteProxmoxVmParams(vmid=vmid))
```

**Cancel-scope invariant (Phase 04.1 lock, fixtures.py:324-410 header):**
> "The fixture body holds NO anyio cancel scopes across the yield. ..."

Phase 19's module-scope fixture mirrors this. `await tool(...).call(...)` operates inside the already-active `mcp_session` fixture's session loop; no new anyio cancel scope is opened. Standard `try: yield ... finally:` is the safe shape.

**Test body shape (CONTEXT.md `<specifics>` lines 150-173 — copy verbatim):**
```python
@pytest.mark.asyncio(loop_scope="session")
async def test_create_returns_pending_vm(proxmox_vm_lifecycle):
    state = proxmox_vm_lifecycle
    assert state.created.data["vmid"] == ...   # via generated response


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

**ToolCallError propagation:** No new error-routing code needed. Phase 18 `tests/sdet/conftest.py:pytest_exception_interact` (LOCKED — do not modify) already converts any `ToolCallError` raised inside a `tests/sdet/` test into `mcptf_error_*` JUnit properties consumed by the renderer. The dogfood scenario inherits this for free.

---

### `tests/framework/unit/test_state_cleanup_on_failure.py` (NEW — pytest-native semantics pin)

**Analog (partial):** `tests/framework/test_tool_config.py:218-229` — the only `@pytest.mark.xfail` in the codebase. Note `strict=False` there; Phase 19 needs `strict=True` to make the suite green when teardown runs.

**Existing xfail decorator shape (test_tool_config.py:218-229):**
```python
@pytest.mark.xfail(
    strict=False,
    reason=(
        "Phase 13 v2-schema rework dropped the `target:` block "
        "(extra_forbidden). The v1.1.1 SAFE-01 explicit-override "
        "semantics need a v2 equivalent before this test can be "
        "retargeted -- tracked under Phase 13 verification follow-up "
        ...
    ),
)
def test_resolve_tool_names_explicit_target_overrides_skip_true(self) -> None:
```

**Phase 19 STATE-02 self-test (CONTEXT.md D-06 verbatim, with `strict=True` so the suite goes green when both tests pass):**

```python
"""Phase 19 STATE-02: cleanup-on-failure self-test.

Pins the pytest-native semantics that a yield-fixture's teardown body
runs even when an intervening test fails. The fixture below increments
a module-global counter on teardown; the consumer test is marked
xfail(strict=True) so its deliberate failure flips green in pytest's
accounting, and the trailing test asserts the teardown counter == 1.

NO MCP, no subprocess, no pytester. <100 ms. Self-contained regression
guard. CONTEXT.md D-06 / D-07: one self-test file -- subprocess +
JUnit-XML assertion variant rejected (50x cost for the same proof).
"""
from __future__ import annotations

import pytest

_teardown_count = 0


@pytest.fixture
def stateful_resource():
    yield "resource"
    global _teardown_count
    _teardown_count += 1


@pytest.mark.xfail(strict=True, reason="STATE-02: deliberate failure to trigger teardown path")
def test_consumer_fails_deliberately(stateful_resource):
    assert False, "intentional failure to trigger teardown path"


def test_teardown_ran_despite_failure():
    # Ordered AFTER the failing test (pytest collects in file order).
    # If teardown did NOT run on failure, this assertion fires and the
    # whole suite goes red -- catching a pytest-semantics regression
    # the moment it lands.
    assert _teardown_count == 1
```

**`strict=True` rationale (CONTEXT.md D-06 + pytest docs):**
- `strict=True` + the test failing as expected → reported as `XFAIL` (green-equivalent).
- `strict=True` + the test passing → reported as `XPASS` → **fails the suite** (the desired regression guard: if pytest ever started letting the test pass, we'd want to know).
- The codebase has no prior `strict=True` example. This is new. The shape comes from D-06 verbatim.

**Module-global counter pattern (no existing analog in repo).** Search confirms no existing test uses a module-global mutable counter as a fixture-side-effect probe. The shape is novel but minimal: 3 LOC (`_teardown_count = 0` + `global _teardown_count; _teardown_count += 1`).

**No async, no MCP, no pytest_plugins changes.** The file works under the existing `tests/framework/unit/` conftest inheritance (parent `tests/conftest.py` carries `pytest_plugins = ["mcp_test_framework.fixtures"]`, but this test consumes no framework fixtures).

---

### `src/mcp_test_framework/_runner.py` — `parse_junit_xml` extension (~line 489) — MODIFY

**Analog A — itself:** `parse_junit_xml` at lines 489-563. The existing loop reads `<testcase name="...">` and routes through `_extract_tool_name` (lines 335-347) which extracts the parametrize suffix `[<tool>]`. SDET tests have NO parametrize bracket (they are hand-authored, see Phase 18 D-09 + Plan 18-07 — `tests/sdet/conftest.py` does NOT declare `pytest_generate_tests`). So `_extract_tool_name` currently returns `None` for SDET testcases (line 492: `if tool is None: continue`), meaning **SDET rows are currently filtered OUT of the per-tool bucket** entirely. Phase 19's parser extension changes this.

**Existing `_extract_tool_name` (lines 335-347):**
```python
def _extract_tool_name(nodeid_or_name: str) -> str | None:
    """Return tool name from `[<tool>]` parametrize suffix, or None.
    ...
    """
    if "[" not in nodeid_or_name or not nodeid_or_name.endswith("]"):
        return None
    return nodeid_or_name[nodeid_or_name.rindex("[") + 1 : -1]
```

**Existing parser loop entry (lines 489-497):**
```python
for tc in suite.iter("testcase"):
    name = tc.get("name", "")
    tool = _extract_tool_name(name)
    if tool is None:
        continue  # D-09: testcases without [<tool>] suffix excluded.

    bucket = run.per_tool.setdefault(
        tool, ToolVerdict(name=tool, verdict="PASS")
    )
```

**Phase 19 D-08 derivation logic:** JUnit XML emits `<testcase classname="tests.sdet.test_proxmox_vm_lifecycle" name="test_create_returns_pending_vm">`. The renderer (`_render_per_tool_rows`) is data-driven — it groups by `per_tool` dict key. So the parser needs to:

1. When `_extract_tool_name(name)` returns `None`, check `tc.get("classname", "")`.
2. If `classname.startswith("tests.sdet.test_")` (or any `.test_*` stem under a `tests.sdet` prefix), derive `scenario_group = classname.rsplit(".", 1)[-1].removeprefix("test_")`.
3. Derive `row_label = name.removeprefix("test_")` (D-09).
4. Populate `bucket = run.per_tool.setdefault(scenario_group, ToolVerdict(name=scenario_group, verdict="PASS"))` with the SAME PASS/FAIL/SKIP rule logic the existing loop uses (lines 504-561), but the row identity is `(scenario_group, row_label)` instead of just `scenario_group`.

**Per-test row visibility — the existing `ToolVerdict` is aggregate, not per-case.** This is the genuinely tricky shape. Two options for the planner:

- **Option α (extend `ToolVerdict`):** add `per_case: list[tuple[str, Verdict]] = field(default_factory=list)` to `ToolVerdict` so scenario groups can carry their per-test rows. Renderer extension reads this and emits nested rows under the group header. Existing contract tools leave `per_case=[]` and the renderer falls through to the current single-row shape.
- **Option β (synthetic parametrize id):** emit one `ToolVerdict` entry per `(scenario_group, row_label)` pair, using key like `proxmox_vm_lifecycle::create_returns_pending_vm` (literal `::` delimiter, NOT brackets — keeps `_extract_tool_name` un-confused). Renderer splits on `::` and emits nested rows. **Lower-risk: zero dataclass churn**, matches Phase 18 Plan 06's "Strategy 1 — second-pass over data rather than dataclass extension" pattern (18-06 SUMMARY line 47-49). Planner picks; α is cleaner but extends the parser→renderer contract.

**Reference for the "Strategy 1 — no dataclass churn" pattern (Plan 18-06 SUMMARY):**
> Strategy 1 (no ToolVerdict extension): D-11 appendix re-parses JUnit XML rather than adding tool_call_error_* fields to ToolVerdict. Keeps the parser→renderer dataclass surface frozen.

Mirrors here: extending `ToolVerdict` ripples through the existing 30 parser-regression tests; using a synthetic key keeps the surface stable.

**`ToolVerdict` dataclass (lines 391-413) — to keep stable OR extend (planner picks):**
```python
@dataclass
class ToolVerdict:
    name: str
    verdict: Verdict
    failure_message: str | None = None
    failure_body: str | None = None
    skip_reasons: list[str] = field(default_factory=list)
    case_count: int = 0
    duration: float = 0.0
```

**Sticky-verdict rules from existing loop (lines 504-561) — REUSE VERBATIM for SDET rows:**

The Phase 19 SDET extension uses the same FAIL-sticky / PASS-dominates / SKIP rules. The D-09 JUnit-property hook (lines 521-535) for `mcptf_error_code` / `mcptf_error_message` already fires for SDET testcases — no parser change there. Inheriting Phase 18 D-09/D-10 means SDET failures get `[code] message` em-dash rendering for free.

**JUnit `classname` is set automatically by pytest.** Confirmed by structure: pytest's JUnit XML writer uses `classname = test_module_path.replace("/", ".").removesuffix(".py")` so `tests/sdet/test_proxmox_vm_lifecycle.py` → `classname="tests.sdet.test_proxmox_vm_lifecycle"`. No test-side wiring required.

---

### `src/mcp_test_framework/_runner.py` — `_render_per_tool_rows` extension (~line 973) — MODIFY

**Analog:** itself (lines 973-1024). The function is data-driven: groups by verdict, sorts alphabetically, prints `{tool}  ✓ PASS` / `{tool}  ✗ FAIL — {msg}` / `{tool}  – SKIP — {reasons}`.

**Existing render loop (lines 994-1024):**
```python
if fails:
    print("failures:", file=file)
    for tool in fails:
        v = parsed.per_tool[tool]
        tag = _red("FAIL", file)
        if v.failure_message:
            # U+2014 em-dash; matches Phase 09 SC-3 (locked separator).
            print(f"  {tool.ljust(name_width)}  ✗ {tag} — {v.failure_message}", file=file)
        else:
            print(f"  {tool.ljust(name_width)}  ✗ {tag}", file=file)

if all_skips:
    print("skipped:", file=file)
    for tool in all_skips:
        ...
        tag = _dim("SKIP", file)
        if reasons_text:
            print(f"  {tool.ljust(name_width)}  – {tag} — {reasons_text}", file=file)
        else:
            print(f"  {tool.ljust(name_width)}  – {tag}", file=file)

if passes:
    print("passing:", file=file)
    for tool in passes:
        tag = _green("PASS", file)
        print(f"  {tool.ljust(name_width)}  ✓ {tag}", file=file)
```

**Phase 19 UI-01 expected output (CONTEXT.md lines 178-183):**
```
proxmox_vm_lifecycle
  ✓ create_returns_pending_vm
  ✓ modify_accepts_cpu_increase
  ✓ delete_returns_ok
```

**Note the layout difference:** contract rows render as one line per tool `{tool}  ✓ PASS`; scenario rows render as a **group header line** (`proxmox_vm_lifecycle`) followed by per-test rows (`  ✓ create_returns_pending_vm`). Two layout shapes coexist.

**Renderer extension — assembled from Option β (synthetic key) shape:**

If the parser populates `per_tool` with synthetic keys like `proxmox_vm_lifecycle::create_returns_pending_vm`, the renderer detects them and groups:

```python
# Split per_tool into contract entries (no '::') and scenario entries.
contract_entries = {k: v for k, v in parsed.per_tool.items() if "::" not in k}
scenario_entries: dict[str, list[tuple[str, ToolVerdict]]] = {}  # group -> [(row_label, v), ...]
for k, v in parsed.per_tool.items():
    if "::" not in k:
        continue
    group, _, row_label = k.partition("::")
    scenario_entries.setdefault(group, []).append((row_label, v))

# Existing per-verdict bucketing logic operates over contract_entries
# unchanged. (Lines 985-1023 above.)

# NEW: scenario blocks (Phase 19 UI-01).
for group in sorted(scenario_entries):
    print(group, file=file)   # bare group header, NOT "passing:"/"failures:"
    for row_label, v in sorted(scenario_entries[group]):  # file-order via name? planner picks
        if v.verdict == "PASS":
            tag = _green("PASS", file)
            print(f"  ✓ {row_label}", file=file)
        elif v.verdict == "FAIL":
            tag = _red("FAIL", file)
            if v.failure_message:
                print(f"  ✗ {row_label} — {v.failure_message}", file=file)
            else:
                print(f"  ✗ {row_label}", file=file)
        else:  # SKIP
            reasons_text = _format_skip_reasons(v.skip_reasons)
            if reasons_text:
                print(f"  – {row_label} — {reasons_text}", file=file)
            else:
                print(f"  – {row_label}", file=file)
```

**CONTEXT.md UI-01 row glyph note:** lines 180-182 show `  ✓ create_returns_pending_vm` (single leading space + glyph + space + label). The existing contract-row format is `  {tool.ljust(width)}  ✓ PASS` (two-space indent + ljust-name + double-space + glyph + " PASS"). The UI-01 sample drops the "PASS"/"FAIL"/"SKIP" word and the alignment column — rows are tight. Planner pins exact whitespace.

**Em-dash separator (U+2014, line 1002):** reused verbatim. The em-dash literal is locked at `_runner.py:537` and `:1002`. Pin both call sites in tests.

---

### `src/mcp_test_framework/models.py` — add `HomelabProxmoxConfig` sub-model — MODIFY

**Analog:** `models.py:36-73` (`OllamaConfig` + `McpServerConfig`).

**Existing sub-model pattern (models.py:36-53):**
```python
class OllamaConfig(BaseModel):
    """Ollama judge configuration."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    base_url: str = Field(
        default="http://127.0.0.1:11434",
        validation_alias=AliasChoices("OLLAMA_BASE_URL", "base_url"),
    )
    model: str = Field(
        default="qwen3.6:latest",
        validation_alias=AliasChoices("OLLAMA_MODEL", "model"),
    )
```

**Phase 19 sub-model shape (CONTEXT D-03: `homelab.proxmox.dogfood_vmid_range: [9990, 9999]`):**

Two-level nesting — `Config.homelab.proxmox.dogfood_vmid_range`. Mirrors `mcp_server.timeout_seconds` depth.

```python
class HomelabProxmoxConfig(BaseModel):
    """Phase 19 STATE-04: dogfood scenario Proxmox isolation knobs."""

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")

    dogfood_vmid_range: tuple[int, int] = Field(
        default=(9990, 9999),
        description=(
            "Reserved VMID range for mcptf-dogfood-* VMs. Default avoids "
            "collision with typical operator-owned ranges."
        ),
    )


class HomelabConfig(BaseModel):
    """Phase 19: homelab-specific scenario knobs (extension point for future
    homelab.* domains; v1.3 ships only `proxmox`).
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")

    proxmox: HomelabProxmoxConfig = Field(default_factory=HomelabProxmoxConfig)
```

**Key invariants from `OllamaConfig` / `McpServerConfig` / `ToolConfig` (all 3 sub-models in models.py):**
- `model_config = ConfigDict(frozen=True, populate_by_name=True, ...)` — frozen on every sub-model (A5 from 01-RESEARCH.md: parent BaseSettings frozen does NOT propagate).
- `extra="forbid"` — `ToolConfig` (line 93) uses this; copy verbatim for `HomelabProxmoxConfig` and `HomelabConfig` so typos like `dogfood_vmd_range` (missing `i`) fail loudly at load time. Note that `OllamaConfig`/`McpServerConfig` do NOT use `extra="forbid"` — they're env-routable; Phase 19's homelab block is NOT env-routable.
- **NO `validation_alias=AliasChoices(...)`** — Phase 13 D-07 retired env routing for new fields. `ToolConfig` already drops it (models.py:91-93 docstring). Homelab block follows.

**Validator pattern (models.py:65-74 `_validate_version` for range/scalar invariants):**
```python
@field_validator("version", mode="after")
@classmethod
def _validate_version(cls, v: int) -> int:
    if v != 2:
        raise ValueError(...)
    return v
```

Phase 19 should add an equivalent `_validate_dogfood_vmid_range`:
```python
@field_validator("dogfood_vmid_range", mode="after")
@classmethod
def _validate_dogfood_vmid_range(cls, v: tuple[int, int]) -> tuple[int, int]:
    lo, hi = v
    if lo > hi or lo < 100 or hi > 999_999_999:
        raise ValueError(
            f"dogfood_vmid_range {v!r} must be (lo, hi) with lo <= hi "
            f"and both within Proxmox VMID bounds [100, 999999999]"
        )
    return v
```

(Bounds are Proxmox-cluster-typical; planner verifies actual Proxmox VMID range.)

---

### `src/mcp_test_framework/config.py` — add `homelab:` field on `Config` — MODIFY

**Analog:** `config.py:53-54` (existing `ollama` / `mcp_server` field declarations on `Config`).

**Existing pattern (config.py:53-54):**
```python
ollama: OllamaConfig = Field(default_factory=OllamaConfig)
mcp_server: McpServerConfig = Field(default_factory=McpServerConfig)
```

**Phase 19 extension (one-line addition adjacent to lines 53-54):**
```python
homelab: HomelabConfig = Field(default_factory=HomelabConfig)
```

Plus the import at the top of `config.py:38-42`:
```python
from mcp_test_framework.models import (
    HomelabConfig,    # NEW
    McpServerConfig,
    OllamaConfig,
    ToolConfig,
)
```

**No `settings_customise_sources` change.** The new field flows through the existing init_kwargs → YAML → defaults pipeline (config.py:77-113). Operators set `homelab.proxmox.dogfood_vmid_range: [9990, 9999]` in `config.yaml` and it lands on `Config.homelab.proxmox.dogfood_vmid_range` automatically.

**Frozen invariant preserved:** `Config.model_config = SettingsConfigDict(frozen=True, extra="forbid")` (config.py:48-51); the new `homelab` field is frozen too (HomelabConfig has its own `frozen=True`).

---

### `examples/homelab-mcp.yaml` — add `homelab.proxmox.dogfood_vmid_range` — MODIFY

**Analog:** `examples/homelab-mcp.yaml:12-15` (mcp_server: block style).

**Existing block style (lines 12-15):**
```yaml
mcp_server:
  command: uvx
  args: [homelab-mcp]
  timeout_seconds: 30
```

**Phase 19 addition (after `judge_timeout_seconds: 120` line ~17, before `version: 2`):**
```yaml
# Phase 19 STATE-04: dogfood scenario uses a pinned VMID range to avoid
# colliding with operator-owned VMs. Override if your cluster reserves
# 9990-9999 for something else; the framework only creates/deletes VMs
# within this range. Names are `mcptf-dogfood-<ISO8601-timestamp>`.
homelab:
  proxmox:
    dogfood_vmid_range: [9990, 9999]
```

**Critical: do NOT add this block to `config.example.yaml`.** That file is the generic starter template (line 1-2: "starter template with placeholder tool names"); `homelab.*` is homelab-mcp-specific and belongs only in the worked reference. CONTEXT D-03 says the range is "configurable via a `homelab.proxmox.dogfood_vmid_range` block in `config.yaml`; default = `[9990, 9999]`" — the default lives in `HomelabProxmoxConfig.dogfood_vmid_range` so operators who never touch the YAML still get the right range.

---

## Shared Patterns

### `loop_scope="session"` on every async marker / fixture
**Source:** `tests/sdet/test_basic_call.py:42, :56` + Plan 18-07 SUMMARY "Deviations [Rule 1]" (lines 144-150)
**Apply to:** every `@pytest.mark.asyncio(...)` AND `@pytest_asyncio.fixture(...)` in `tests/sdet/test_proxmox_vm_lifecycle.py`. Bare `@pytest.mark.asyncio` hangs.
```python
@pytest.mark.asyncio(loop_scope="session")
async def test_x(...): ...

@pytest_asyncio.fixture(scope="module", loop_scope="session")
async def proxmox_vm_lifecycle(mcp_session): ...
```
Phase 21 will document this in DOC-SDET; Phase 19 must not regress it.

### Phase 04.1 cancel-scope invariant — no anyio CancelScope across yield
**Source:** `src/mcp_test_framework/fixtures.py:324-410` docstring + Phase 18 CONTEXT line 34
**Apply to:** `tests/sdet/test_proxmox_vm_lifecycle.py` module-scope fixture body
Standard `try: yield ... finally: ...` is the locked shape. `await tool(...).call(...)` rides inside `mcp_session`'s already-active loop and opens no new cancel scope. AsyncExitStack is acceptable IF needed for additional resources (sweep helpers, etc.), but the dogfood fixture as specified doesn't need one.

### One module per concern
**Source:** Plan 18-02/03/04 module split (`errors.py`, `session.py`, `_tool_factory.py`)
**Apply to:** Phase 19 keeps the scenario in ONE file (`test_proxmox_vm_lifecycle.py`). Helpers like `_next_free_dogfood_vmid` / `_sweep_stranded_dogfood_vms` live in the same file as private (`_` prefix) module-level functions, NOT in `src/mcp_test_framework/sdet/`. STATE-01..04 is a PATTERN, not a framework primitive (CONTEXT D-04: "Pattern — not a base class — each scenario owns its state shape; the framework ships no abstract `ScenarioState` superclass"). Locked.

### Em-dash separator U+2014
**Source:** `_runner.py:537` (parser failure-message format) + `_runner.py:1002` (renderer FAIL row)
**Apply to:** Phase 19's scenario FAIL row rendering. The em-dash literal `—` must survive the new code path. Pin in tests.

### Pydantic v2 frozen sub-model with `extra="forbid"`
**Source:** `src/mcp_test_framework/models.py:93` (`ToolConfig.model_config`)
**Apply to:** `HomelabProxmoxConfig` and `HomelabConfig` in `models.py`. `extra="forbid"` is critical so typos in operator YAML (`dogfood_vmd_range`) fail loudly at config load. Mirrors v1.1 TOOLCFG-05 / D-15 lock.

### Generated-class imports come from `mcp_test_framework.sdet.generated.<slug>`
**Source:** `tests/sdet/test_basic_call.py:39` (Phase 17 codegen import surface)
**Apply to:** `tests/sdet/test_proxmox_vm_lifecycle.py`. Use:
```python
from mcp_test_framework.sdet.generated.homelab_mcp import (
    CreateProxmoxVmParams, ...
)
```
Black-box rule (CONTEXT line 35): the dogfood NEVER imports from `homelab-mcp` source.

### Phase 18 `pytest_exception_interact` hook is consumed AS-IS
**Source:** `tests/sdet/conftest.py:22-46` (Phase 18 D-09 hook)
**Apply to:** Phase 19 does NOT modify this file. Any `ToolCallError` raised by `tool(...).call(...)` inside the dogfood is automatically converted to `mcptf_error_*` JUnit properties → consumed by the renderer for em-dash `[code] message` rows. No additional wiring needed.

### `# tool: ...` Warning-4 lock comment
**Source:** `tests/sdet/test_basic_call.py:32` (Plan 18-07 SUMMARY Decision)
**Apply to:** `tests/sdet/test_proxmox_vm_lifecycle.py` file-header docstring. Pin the four Proxmox tool choices so a re-plan can't silently re-decide:
```python
"""...
# tool: create_proxmox_vm (D-01 -- live VM creation)
# tool: manage_proxmox_vm (D-02 -- CPU 1 -> 2 modify step)
# tool: delete_proxmox_vm (D-01 -- live VM teardown)
# tool: get_proxmox_vm_status (D-02 -- verification re-read)
"""
```

---

## No Analog Found

| File / Pattern | Gap | Mitigation |
|----------------|-----|------------|
| Module-scope async yield fixture | No `scope="module"` async fixture exists anywhere in the repo. All async fixtures are `scope="session"` (`mcp_client`, `judge`, `mcp_session`). | Assemble from CONTEXT D-04 verbatim shape + session-scoped `judge` body (`fixtures.py:444-460`) as the structural model. Phase 04.1 cancel-scope invariant + Plan 18-07 `loop_scope="session"` lock together fully constrain the shape. |
| `xfail(strict=True)` | No existing `strict=True` usage. `test_tool_config.py:218` uses `strict=False`. | CONTEXT D-06 supplies the verbatim shape. pytest docs are authoritative for the semantic (`strict=True` + xpass → suite fails). |
| Module-global counter as fixture-teardown probe | No prior usage in repo. | Trivial pattern (3 LOC); CONTEXT D-06 supplies the verbatim shape. |
| Group-header row layout (`group:\n  ✓ row1\n  ✓ row2`) | No prior renderer code emits a bare group header — existing `_render_per_tool_rows` only emits `failures:` / `skipped:` / `passing:` section headers + a single line per tool. | CONTEXT lines 178-183 supply the exact expected output. Renderer extension is small; pin layout in tests with byte-comparison fixtures. |
| `homelab.*` config block | No existing `homelab.*` field on `Config`. | Mirror `OllamaConfig` + `McpServerConfig` shape (models.py:36-73). Sub-model nesting is one level deeper (`Config.homelab.proxmox.dogfood_vmid_range`), but Pydantic v2 handles arbitrary nesting via `default_factory` per level. |
| Dogfood-style live-integration test | First of its kind. `tests/sdet/test_basic_call.py` is a read-only smoke; this is the first stateful live scenario. | CONTEXT.md `<specifics>` lines 110-174 supply the verbatim shape. Test runs against live Proxmox; until Phase 20 ships `requires_homelab`, failure on unreachable Proxmox is a loud crash (CONTEXT D-01). |

---

## Metadata

**Analog search scope:**
- `tests/sdet/` (test_basic_call.py, conftest.py — Phase 18 Plan 07 deliverables)
- `tests/framework/unit/` (xfail occurrences, fixture-state-reset patterns)
- `src/mcp_test_framework/fixtures.py` (session-scoped fixtures, AsyncExitStack idiom, cancel-scope invariant)
- `src/mcp_test_framework/_runner.py` (`parse_junit_xml`, `_render_per_tool_rows`, `_extract_tool_name`, `ToolVerdict`)
- `src/mcp_test_framework/models.py` (Pydantic v2 sub-model conventions)
- `src/mcp_test_framework/config.py` (root config + `settings_customise_sources`)
- `examples/homelab-mcp.yaml` + `config.example.yaml` (YAML block style)
- `src/mcp_test_framework/sdet/generated/homelab_mcp/__init__.py` (Proxmox tool import surface)

**Files scanned:** 12 source / 4 test / 3 config + 18-PATTERNS.md (carried-forward analogs)

**Pattern extraction date:** 2026-05-13

**Carry-forward from Phase 18 patterns (still valid for Phase 19):**
- `tests/sdet/conftest.py` `pytest_exception_interact` hook — consumed AS-IS, not modified
- `_render_scenario_pre_run_digest` (line 849) — Phase 19 does not modify; the digest already buckets on scenario MODULE names (CONTEXT line 30: "Phase 18 D-06 scenario digest in `_runner.py` already keys on scenario MODULE names. Phase 19's `_render_per_tool_rows` extension reuses the same module-name derivation so digest and rows agree.")
- `_collect_sdet_scenarios` (line 904) — signature has unused `ctx` parameter; Phase 19's preflight extension (deferred to Phase 20) will read scenario-skip state through it. No Phase 19 change.
- Em-dash U+2014 separator — Phase 09 SC-3 lock, Phase 14/16/18 reuse, Phase 19 reuses for FAIL rows.
