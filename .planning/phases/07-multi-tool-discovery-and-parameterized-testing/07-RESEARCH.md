# Phase 07: Multi-tool discovery & parameterized testing - Research

**Researched:** 2026-05-07
**Domain:** pytest collection-time hooks + indirect parametrize + a third stdio_client spawn site bound to the Phase 06 isolation contract
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Default behavior with `target.tool_name` unset (or empty/None) — discover and test every tool the server advertises. Existing v1.0 single-tool config keeps working.
- **D-02:** `Config.target.tool_name` field type `str` → `str | None`. Default flips from `"list_registered_servers"` to `None`. `AliasChoices("TARGET_TOOL_NAME", "tool_name")` unchanged. Empty string treated equivalently to None at parametrize time.
- **D-03:** `mcp-test-framework list-tools` is the verify step. **No new CLI in Phase 07.**
- **D-04:** Starter-config generator deferred to Phase 08.
- **D-05:** Test IDs **always** render as `<test_name>[<tool_name>]` — including with a single-tool config (single-item parametrize list).
- **D-06:** Tools with non-empty `inputSchema.required` produce `isError=True` and **fail TEST-08 visibly**. NO auto-skip in Phase 07 — that's Phase 08's TOOLCFG-07.
- **D-07:** Same fail-visibly stance for TEST-10 (non-JSON prose output).
- **D-08:** **Accept slow runtime** (10 tests × N tools × 3 LLM judge calls). No default cap, no warning, no `target.allow_all_tools` opt-in. Caps are Phase 08's territory.
- **D-09:** Expected-runtime documentation is Phase 10 (DOC-04/DOC-05).
- **D-10:** Tool discovery happens at **collection time** via a sync `pytest_generate_tests` (or equivalent) calling `asyncio.run(...)` on a brief MCP session. MUST use a per-discovery `tempfile.TemporaryDirectory` + `_build_isolated_env`.
- **D-11:** Discovery is a **third spawn site** (after `_preflight` and `mcp_client._owner_task`). It MUST inject `_build_isolated_env(<discovery tempdir>)`.
- **D-12:** Discovery result is cached so the long-lived `mcp_client` session-fixture does NOT double-spawn. Cache: module-level dict OR `pytest.StashKey`.
- **D-13:** **Indirect parametrize** via the `target_tool` fixture. Fixture body takes `request.param` and returns `await mcp_client.get_tool(request.param)`. Test bodies (TEST-01..TEST-10) keep their `target_tool` parameter unchanged.
- **D-14:** Test-module-level parametrize via `pytestmark` augmentation: `pytest.mark.parametrize("target_tool", <discovered names>, indirect=True, ids=<tool-name list>)`. Module-level uniform default.
- **D-15:** When `target.tool_name` is None, `_preflight` drops the membership assertion at fixtures.py:156-162. MCP handshake + Ollama checks remain.
- **D-16:** `_preflight`'s `list_tools()` and the discovery hook's `list_tools()` may both call independently; sharing is optional (CD-02).
- **D-17:** `tests/test_homelab_list_registered_servers.py` is **renamed** to a tool-agnostic name (suggested: `tests/test_mcp_tool_contract.py`).

### Claude's Discretion

- **CD-01:** Cache mechanism — module-level dict, `pytest.StashKey`, or `pytest.Config.cache`. Pick whichever is readable and survives re-collection cleanly.
- **CD-02:** Whether to share `list_tools()` between `_preflight` and the discovery hook (savings: one subprocess spawn per session). Pick simpler.
- **CD-03:** Where to place `pytest.mark.parametrize` — module-level `pytestmark`, per-test decorator stack, or `pytest_generate_tests` hook in `conftest.py`. Hook approach gives most flexibility.
- **CD-04:** New module name for the renamed test file. `test_mcp_tool_contract.py` suggested but not locked.
- **CD-05:** Whether the discovery hook short-circuits when `target.tool_name` is set (single-item parametrize list, no spawn). Tradeoff: simpler if always-spawn; less work if short-circuit.
- **CD-06:** Order of plans. Discovery seam + `target_tool` fixture rewrite must land together to avoid a transient broken state.

### Deferred Ideas (OUT OF SCOPE)

- Starter-config generator — Phase 08.
- Up-front runtime estimate at collection time — post-v1.2 if needed.
- Soft cap on tool count with `target.allow_all_tools=true` opt-in — rejected.
- Auto-skip for required-args tools — Phase 08 (TOOLCFG-07).
- Process-parallel execution (xdist), warm-up — v1.2 (SEED-002).
- Sharing `list_tools()` across `_preflight` + discovery hook — Claude's discretion (CD-02).

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MULTI-01 | Framework discovers all tools from connected MCP server at session startup; `target_tool` generalizes to "tool list" | Discovery hook design (§Architecture Pattern 1); reuse of `_preflight` brief-session shape with `_build_isolated_env`; `McpTestClient.list_tools()` is the existing seam |
| MULTI-02 | Tests parametrize over discovered tool list at collection time via `pytest.mark.parametrize` (no codegen) | `pytest_generate_tests` hook in conftest.py with `metafunc.parametrize("target_tool", names, indirect=True, ids=names)` (§Pattern 1, §Code Examples) — verified in pytest 9.x docs |
| MULTI-03 | Test IDs render as `<test_name>[<tool_name>]` in pytest terminal AND JUnit XML | pytest's default `[<id>]` bracket-suffix renders identically in `-v` output and JUnit `testcase[@name]`; tool names like `list_registered_servers` are pytest-id safe (§Pattern 2) |
| MULTI-04 | Backward-compat: `target.tool_name` set → only that tool runs; unset → all discovered (modulo skip-list) | `Config.target.tool_name: str \| None` (D-02) + discovery hook reads `config.target.tool_name`: if set, emits single-item list; if None/empty, emits full discovered list (§Code Examples) |

</phase_requirements>

## Summary

Phase 07 is a small but load-bearing surgical change: replace the `target_tool` fixture's direct-`config.target.tool_name` resolution with **indirect parametrize** driven by a tool list discovered at collection time. The discovery happens in a single new sync hook (`pytest_generate_tests` in `tests/conftest.py`) that calls `asyncio.run(_discover_tools(config))` on a one-shot `McpTestClient` session. This hook is a **third spawn site** under the Phase 06 isolation contract — it MUST inject `_build_isolated_env(<discovery tempdir>)` into `StdioServerParameters(env=...)`.

The biggest risk areas — all addressable: (1) `Config.target.tool_name` going from required `str` to `str | None` interacts with the project's custom `_BareNameNestedEnvSource` in a non-obvious way (an env var `TARGET_TOOL_NAME=""` lands as `""`, NOT `None`; a normalization step is required); (2) the existing ISOL-03 hash-equality test does **not** automatically cover the new spawn site — the test asserts the user's real `~/.homelab_mcp/` is unchanged after running the v1.1 tool surface in-process via `mcp_client`, but the discovery spawn happens at **collection time**, BEFORE `mcp_client` runs. ISOL-03 still implicitly guards correctness because the discovery spawn writes into its own per-discovery tempdir which is then discarded — but a planner who wants explicit coverage should add a small assertion that the collection-time hook also goes through `_build_isolated_env`.

**Primary recommendation:** Land the discovery hook + indirect parametrize + fixture rewrite + `_preflight` membership-check branch + module rename in **one cohesive plan**. The intermediate state where the fixture exists but the hook doesn't (or vice versa) breaks every integration test. Rename and parametrize together.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Tool discovery (read tool list from server) | pytest collection hook (sync, top-level conftest) | — | Must run BEFORE `pytest_generate_tests` produces parameter sets, which is before any fixture loop exists |
| Per-test tool resolution | `target_tool` fixture (session-scoped, async) | `mcp_client.get_tool` | Fixture takes `request.param` (a name) and resolves via the long-lived session |
| Tool-name → test ID rendering | `pytest.mark.parametrize(ids=...)` | — | Plain pytest mechanism; runs at collection time, no test code involvement |
| Subprocess isolation for discovery spawn | `_build_isolated_env(<per-discovery tempdir>)` | `tempfile.TemporaryDirectory` | Enforces Phase 06 ISOL-02/04/07 contract on every spawn site |
| Brief MCP session for discovery | `McpTestClient.__aenter__` (reused as-is) | — | Already isolation-aware as of Phase 06 D-16; no new entry point needed |

## Standard Stack

### Core (already in project)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.0+ (declared `>=9.0`) | Test runner; `pytest_generate_tests` hook host | Already in use; only library that exposes the metafunc collection-time API [VERIFIED: pyproject.toml:25] |
| pytest-asyncio | 1.3+ | Strict-mode async test markers; session-scoped event loop | Already in use; matches `asyncio_default_fixture_loop_scope = "session"` [VERIFIED: pyproject.toml:26, :36] |
| mcp (SDK) | 1.27+ | `stdio_client`, `ClientSession`, `Tool` model | Only authoritative MCP client; black-box rule binds us to it [VERIFIED: pyproject.toml:11] |
| pydantic + pydantic-settings | 2.13+ / 2.14+ | `Config.target.tool_name: str \| None` field type change | Already the config layer [VERIFIED: pyproject.toml:12-13] |

### No new dependencies

Phase 07 introduces **zero new third-party libraries**. Everything required is already in the project's deptree. The new code is ~100 LOC across `tests/conftest.py` + `src/mcp_test_framework/fixtures.py` + `src/mcp_test_framework/models.py` + a renamed test module.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pytest_generate_tests` hook in conftest.py | `pytest_collection_modifyitems` | Both are collection-time and both have access to `metafunc.config` (parametrize-via-modify-items requires more boilerplate to inject params; not standard for this case). `pytest_generate_tests` is the canonical pytest seam for parametrize injection [CITED: pytest docs `how-to/parametrize.rst`]. **Recommendation: `pytest_generate_tests`.** |
| Module-level `pytestmark` parametrize | Per-test `@pytest.mark.parametrize` decorators | Module-level requires the tool list to be available at module import time — it isn't (we don't want to spawn at import time). The `pytest_generate_tests` hook IS the correct seam because it runs after import + collection-discovery and has access to a populated `metafunc`. Module-level `pytestmark` augmentation only works if the tool list is computed at import time — undesirable. **Recommendation: hook-driven.** |
| `pytest.StashKey` for discovery cache | Module-level dict in conftest.py | StashKey is the typed-cache pytest idiom; module-level dict is simpler. Either works; D-12 says planner picks. For ~10 tools cached once per session, simplicity wins. **Recommendation: module-level dict in conftest.py with a clear name like `_DISCOVERED_TOOL_NAMES`.** |
| `asyncio.run(...)` from sync hook | Reuse the session loop | Cannot — there is no session loop yet at collection time. `pytest_generate_tests` runs BEFORE pytest-asyncio installs its session-scoped loop [VERIFIED via pytest-asyncio docs: loop_scope is honored on test/fixture markers, not on collection hooks]. `asyncio.run(...)` creates and tears down a fresh loop in the hook — the **correct** pattern (and identical to how `_preflight`'s pattern would behave if forced into sync context). |

## Architecture Patterns

### System Architecture Diagram

```
                  [pytest invocation]
                          │
                          ▼
    ┌─────────────────────────────────────────────────┐
    │  pytest_generate_tests(metafunc) in conftest.py  │  (sync, runs once per test fn)
    │     • check "target_tool" in metafunc.fixturenames│
    │     • read Config()                              │
    │     • if config.target.tool_name set:            │
    │         tool_names = [config.target.tool_name]   │
    │     • else:                                      │
    │         tool_names = _discover_or_cache(config)  │
    │     • metafunc.parametrize(                      │
    │         "target_tool", tool_names,               │
    │         indirect=True, ids=tool_names)           │
    └─────────────────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────┐
    │  _discover_or_cache(config) — cached after first call │
    │   asyncio.run(_discover(config)):                │
    │     with tempfile.TemporaryDirectory(...) as td: │
    │       async with McpTestClient(...) as cli:     │
    │         tools = await cli.list_tools()           │
    │       return [t.name for t in tools]            │
    │   (subprocess spawned via stdio_client uses    │
    │    _build_isolated_env(td) — Phase 06 contract)  │
    └─────────────────────────────────────────────────┘
                          │
        cached tool names ▼
                          │
                          ▼
    ┌─────────────────────────────────────────────────┐
    │  pytest creates N test instances per test fn    │
    │   test_id format: test_<name>[<tool_name>]      │
    └─────────────────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────┐
    │  Session fixtures spin up (loop_scope="session"):│
    │   _preflight (autouse, membership-check skipped  │
    │     when config.target.tool_name is None)        │
    │   _isolated_home → mcp_client (long-lived)       │
    │   judge, rubrics                                  │
    └─────────────────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────┐
    │  Per-test execution:                             │
    │   target_tool fixture (now indirect-aware):      │
    │     name = request.param                         │
    │     return await mcp_client.get_tool(name)       │
    └─────────────────────────────────────────────────┘
```

**Key flow property:** The discovery hook's `asyncio.run(...)` opens a loop, spawns the MCP subprocess, lists tools, tears down the loop completely, AND deletes the discovery tempdir BEFORE pytest-asyncio's session-scoped loop is created for the long-lived `mcp_client` fixture. **Zero overlap** — no Phase 04.1 invariant violation.

### Recommended Project Structure

No new directories. Three files touched + one rename:

```
src/mcp_test_framework/
  fixtures.py     # MODIFY: target_tool fixture body (indirect param-aware);
                  #         _preflight conditional membership check (D-15)
  models.py       # MODIFY: TargetConfig.tool_name type → str | None,
                  #         default → None, plus empty-string normalizer
  config.py       # POSSIBLY MODIFY: review _BareNameNestedEnvSource
                  #         empty-string handling (Pitfall 2)
tests/
  conftest.py     # ADD: pytest_generate_tests hook + _discover() helper
  test_mcp_tool_contract.py   # RENAMED from test_homelab_list_registered_servers.py;
                              # bodies unchanged except 3 tests use config.target.tool_name
                              # directly — see Pattern 3
```

### Pattern 1: Discovery hook (canonical implementation)

**What:** A sync `pytest_generate_tests` hook in `tests/conftest.py` that, the first time it sees a test function requesting `target_tool`, discovers the tool list via a one-shot `asyncio.run(...)` and caches the result.

**When to use:** This is the only correct seam for late-bound parametrize lists in pytest. [CITED: pytest `how-to/parametrize.rst` "Implement pytest_generate_tests for Dynamic Parametrization"]

**Implementation sketch (verified against existing `_preflight` shape at fixtures.py:142-154):**

```python
# tests/conftest.py
from __future__ import annotations
import asyncio
import tempfile
from pathlib import Path
from typing import Optional

import pytest

from mcp_test_framework.config import Config
from mcp_test_framework.mcp_client import McpTestClient
# Note: discovery uses McpTestClient.__aenter__ which is already
# isolation-aware (Phase 06 D-16) — it builds its own per-instance
# tempdir + _build_isolated_env env block. Discovery does NOT need to
# manage the tempdir manually.

pytest_plugins = ["mcp_test_framework.fixtures"]  # existing

# Module-level cache (CD-01: dict over StashKey for simplicity)
_DISCOVERED_TOOL_NAMES: Optional[list[str]] = None


async def _discover_tools(config: Config) -> list[str]:
    """Brief MCP handshake → list_tools → tool names. Mirrors _preflight."""
    async with McpTestClient(
        config.mcp_server.command,
        config.mcp_server.args,
        config.mcp_server.timeout_seconds,
    ) as client:
        tools = await client.list_tools()
    return [t.name for t in tools]


def _resolve_tool_names(config: Config) -> list[str]:
    """Single-item list if config.target.tool_name is set; discovered list otherwise."""
    global _DISCOVERED_TOOL_NAMES
    explicit = config.target.tool_name
    if explicit:  # non-None and non-empty
        return [explicit]
    if _DISCOVERED_TOOL_NAMES is None:
        _DISCOVERED_TOOL_NAMES = asyncio.run(_discover_tools(config))
    return _DISCOVERED_TOOL_NAMES


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Inject indirect parametrize on `target_tool` for tests that request it.

    Discovery happens lazily — first test function that needs it triggers
    the (cached) one-shot subprocess spawn. The McpTestClient's
    __aenter__ uses _build_isolated_env (Phase 06 D-16) so the discovery
    spawn cannot leak state to ~/.homelab_mcp/ (ISOL-03 contract preserved).
    """
    if "target_tool" not in metafunc.fixturenames:
        return
    # Skip for unit/ — they don't use target_tool but if any sneaks in
    # we wouldn't want to spawn the MCP server.
    if metafunc.module.__name__.startswith("tests.unit."):
        return
    config = Config()
    names = _resolve_tool_names(config)
    metafunc.parametrize("target_tool", names, indirect=True, ids=names)
```

**Notes:**
- Calling `Config()` inside `pytest_generate_tests` is fine — the config layer is sync.
- The `metafunc.module.__name__.startswith("tests.unit.")` guard is **not** strictly required (no unit test requests `target_tool` today, verified via grep) but is cheap defense-in-depth.
- The hook does NOT swallow exceptions from `_discover_tools`. If discovery raises (handshake failure, bad config), the test session aborts at collection time with a stack trace — the same behavior as if `_preflight` failed, just earlier. Decision is consistent with `_preflight`'s `pytest.exit(returncode=2)` pattern, though here we let pytest's default exception handling do the job at collection time. [VERIFIED: pytest collection errors produce exit code 2 by default.]

### Pattern 2: `target_tool` fixture rewrite (indirect-aware)

**What:** Fixture takes `request.param` (a tool name) and resolves via the long-lived `mcp_client` session.

**When to use:** Always — this is the new contract.

```python
# src/mcp_test_framework/fixtures.py (replaces target_tool at line 330-338)

@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def target_tool(
    request: pytest.FixtureRequest,
    mcp_client: McpTestClient,
    _preflight,
):
    """Resolve target tool by name (parametrized indirectly).

    The parametrize layer (in tests/conftest.py via pytest_generate_tests)
    populates request.param with each discovered tool name. Test IDs
    render as test_<name>[<tool_name>] uniformly — including when
    config.target.tool_name is set (single-item parametrize list per D-05).

    Defense in depth: get_tool raises ToolNotFoundError if the parametrize
    list and the live server's tool list disagree (race window: a tool was
    advertised at discovery but un-advertised by the time mcp_client's
    session asks for it — vanishingly unlikely with stdio + a single server,
    but the existing error path is preserved).
    """
    return await mcp_client.get_tool(request.param)
```

**Note:** The fixture **MUST be session-scoped to match `mcp_client`'s scope** (pytest-asyncio with `loop_scope="session"` on both ensures they share a loop). With indirect parametrize, pytest creates one fixture instance **per parameter value** — but since the scope is `session`, the same `target_tool` value is reused across the 10 tests for that tool name. **VERIFIED via** [pytest docs `how-to/parametrize.rst` "Defer setup of parametrized resources with indirect parametrization"]: indirect parametrize respects fixture scope correctly; one instance per `request.param` value within scope. [HIGH confidence; cited.]

### Pattern 3: Tests that don't currently use `target_tool` need light surgery

**Reading `tests/test_homelab_list_registered_servers.py`:** All 10 tests have `pytestmark = [pytest.mark.asyncio(loop_scope="session")]` (single marker). Of the 10:

| # | Test | Uses target_tool? | Uses mcp_client + config.target.tool_name? | Action |
|---|------|-------------------|--------------------------------------------|--------|
| TEST-01 | test_target_tool_exists | ✓ | — | None — fixture-driven |
| TEST-02 | test_schema_passes_structural_checks | ✓ | — | None |
| TEST-03 | test_description_min_length | ✓ | — | None |
| TEST-04 | test_every_parameter_has_description_and_type | ✓ | — | None |
| TEST-05 | test_description_clarity | ✓ + judge + rubric_clarity | — | None |
| TEST-06 | test_description_disambiguation | ✓ + judge + rubric_disambiguation | — | None |
| TEST-07 | test_parameters_self_explanatory | ✓ + judge + rubric_parameters | — | None |
| TEST-08 | test_empty_args_call_returns_non_error | ✗ | ✓ (line 170: `config.target.tool_name`) | **Add `target_tool` parameter; replace `config.target.tool_name` → `target_tool.name`** |
| TEST-09 | test_result_has_content_or_structured | ✗ | ✓ (line 179) | **Same** |
| TEST-10 | test_text_content_parses_as_json | ✓ + mcp_client | ✓ (line 195) | **Replace `config.target.tool_name` → `target_tool.name`** (already takes target_tool) |

**Critical detail flagged by code reading:** TEST-08 and TEST-09 do NOT currently take `target_tool` — they call `mcp_client.call_tool(config.target.tool_name, {})` directly. To benefit from parametrize, they must take `target_tool` and use `target_tool.name`. This is a **mechanical, three-tests rewrite**. The rewrite makes them parametrize-driven exactly like the others.

**This is a discovery the planner needs to know — the diff is not "just add parametrize markers"; it touches the bodies of TEST-08, TEST-09, and TEST-10.** Diff per test is small (~3 lines each), but plan-checker should catch it if missed.

### Pattern 4: `Config.target.tool_name: str | None` semantics

**What:** Field type change with an empty-string-coerces-to-None normalization.

```python
# src/mcp_test_framework/models.py — replaces TargetConfig

from typing import Optional
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class TargetConfig(BaseModel):
    """Target tool to run tests against. None = discover all tools (Phase 07 D-01)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    tool_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("TARGET_TOOL_NAME", "tool_name"),
    )

    @field_validator("tool_name", mode="before")
    @classmethod
    def _empty_to_none(cls, v):
        """Empty string from env → None (Phase 07 D-02 'empty equivalent to None')."""
        if isinstance(v, str) and v.strip() == "":
            return None
        return v
```

**Why the validator is required (Pitfall 2 below):** The project's custom `_BareNameNestedEnvSource` (config.py:91-146) only sets `sub_data[sub_name]` when an env var is **present** in the environment. An empty `TARGET_TOOL_NAME=""` IS present — its value is `""` — and Pydantic v2 will accept `""` as a valid `str` in an `Optional[str]` field. Without `_empty_to_none`, `config.target.tool_name == ""` (not `None`) when the user has `TARGET_TOOL_NAME=` (no value) in `.env`. The discovery hook's `if explicit:` check (Pattern 1) handles `""` correctly via Python truthiness — but this is fragile. Better: normalize at the model boundary so downstream code can simply check `is None`.

[VERIFIED: pydantic-settings docs — `field_validator(mode="before")` is the canonical way to coerce raw env values before type validation.]
[VERIFIED via code reading: `_BareNameNestedEnvSource.__call__` at config.py:127-146 — the `if env_name in env` check is membership-only, not truthiness.]

### Anti-Patterns to Avoid

- **Computing the tool list at module import time.** Importing `tests/test_mcp_tool_contract.py` triggers an MCP subprocess spawn = slow + side effects in lint/IDE/static-analysis tools. **Always** defer to `pytest_generate_tests`.
- **Using `pytest_collection_modifyitems` to inject parametrize.** Possible, but you have to construct `MarkDecorator` objects manually; `metafunc.parametrize(...)` in `pytest_generate_tests` is the canonical seam.
- **Trying to share the discovery loop with the session fixture loop.** They run at different lifecycle phases — collection vs test execution. Don't try to be clever.
- **Letting the discovery hook fail silently.** A spawn failure at collection time should abort the run with a useful stack trace, not produce zero parametrized tests (which would silently appear to pass).
- **Caching the discovery list across test sessions in the same process.** A module-level dict in conftest.py is fine within one pytest invocation; cross-process caching (e.g., `pytest.Config.cache`) is overkill at v1.1's scale and adds a stale-cache class of bugs.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Collection-time parameter generation | A custom plugin or `pytest_collection_modifyitems` parameter injection | `pytest_generate_tests(metafunc)` + `metafunc.parametrize(...)` | Canonical pytest seam; `metafunc` exposes `fixturenames`, `config`, `module` cleanly |
| Indirect-parametrize fixture wiring | Manually iterating `request.param` in test bodies | `indirect=True` + `request.param` inside the fixture | The test body stays oblivious; only the fixture sees the param |
| Test ID rendering | Slugifying tool names yourself | `ids=tool_names` (list of bare strings) | pytest accepts arbitrary printable strings as ids; `list_registered_servers` is already pytest- and JUnit-XML-safe |
| Per-discovery tempdir lifecycle | Manually creating + deleting via try/finally | `McpTestClient.__aenter__` already does it (mcp_client.py:156-160 — Phase 06 D-16) | Reuse the existing isolation seam — single source of truth for spawn isolation |
| Empty-string-to-None coercion in env layer | Custom logic in the `_BareNameNestedEnvSource` | `field_validator(mode="before")` on `TargetConfig.tool_name` | Pydantic v2 idiom; localized; doesn't touch the config source plumbing |

**Key insight:** Phase 07 is a **glue phase** — it composes existing primitives (`McpTestClient.__aenter__`, `_build_isolated_env`, `_preflight` brief-session pattern, indirect parametrize). The temptation to build a "discovery framework" should be resisted; the right answer is ~50 lines of conftest.py.

## Runtime State Inventory

> Phase 07 is a partial rename + behavior change phase. Inventory below answers the canonical question: *after every file in the repo is updated, what runtime systems still have the old string cached, stored, or registered?*

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — verified: the framework treats homelab-mcp as a black box; there is no persistent state owned by `mcp_test_framework` itself. The user's `~/.homelab_mcp/` state is what Phase 06 protects, and Phase 07 doesn't touch it. | None |
| Live service config | None — verified: no external service is configured by name. The CLI script entry point (`mcp-test-framework = "mcp_test_framework.cli:app"` at pyproject.toml:18) is unaffected by the test-module rename. | None |
| OS-registered state | None — verified: no Task Scheduler / launchd / systemd / pm2 entry references `test_homelab_list_registered_servers.py`. The renamed file is discovered by pytest via testpath `tests/` (pyproject.toml:37). | None |
| Secrets / env vars | `TARGET_TOOL_NAME` env var name is unchanged. `.env` files containing `TARGET_TOOL_NAME=list_registered_servers` continue to work with the new `Optional[str]` field — the value is set, so the user's existing single-tool behavior is preserved (D-01, MULTI-04). | None — backward compat preserved by D-02 keeping the alias unchanged |
| Build artifacts / installed packages | None — verified: `src/mcp_test_framework.egg-info/` is git-ignored (the project uses uv + hatchling, not egg-info). `uv sync` rebuilds. The renamed test module is not packaged (it's under `tests/`, not `src/`). | None |

**The canonical answer for Phase 07:** No runtime state outside the repo holds references to `test_homelab_list_registered_servers.py`. The rename is **purely a code-edit** (D-17), not a data migration. The `TARGET_TOOL_NAME` env var is unchanged in name; only the field type widens to accept None.

## Common Pitfalls

### Pitfall 1: ISOL-03 hash-equality test does NOT automatically cover the discovery spawn

**What goes wrong:** Phase 06's `tests/test_isolation.py::test_real_state_unchanged` (lines 90-151) is the regression guard for "real `~/.homelab_mcp/` not mutated by the run". It does its work **inside** the test body via `mcp_client.call_tool(...)` for two specific v1.1 tools. **The discovery spawn happens at collection time, BEFORE this test body runs** — and ISOL-03 captures the pre-state at the start of its test body, AFTER the discovery spawn already completed.

**Why it happens:** Pytest collection runs before any test body. The `before` hash-snapshot at line 124 (`before = {p: _sha256_of(p) for p in REAL_FILES}`) happens after the discovery hook already spawned + tore down its subprocess.

**Implication:** The existing ISOL-03 test still passes correctly because the discovery spawn — using `_build_isolated_env(<discovery tempdir>)` via `McpTestClient.__aenter__` — does not touch the user's real state regardless of whether ISOL-03 measures it. ISOL-03 is structurally measuring "does the v1.1 tool surface, run via the long-lived mcp_client, mutate state?" not "does any subprocess this test session spawned mutate state?" — and that's by design.

**How to avoid:** Two options for the planner —
1. **(Cheap, defensible)** Document explicitly in the discovery hook's docstring + `_isolation.py:33-36` ("DO NOT widen") that the discovery hook is now a third spawn site enrolled in the contract, and lean on code review.
2. **(Stronger, but ~10 LOC)** Add a tiny new assertion to `tests/test_isolation.py` (or a new test next to it): take the hash snapshot at module import / session-start time (before collection completes is already too late — better to use a `pytest_sessionstart` hook to record `before_hashes` into a stash and compare in the existing test). This requires the snapshot to be recorded BEFORE `pytest_generate_tests` fires — which means a `pytest_configure` or the very first action in `pytest_sessionstart`.

**Warning signs:** A future developer adds a fourth spawn site that bypasses `_build_isolated_env`, ISOL-03 still passes, and host state gets mutated silently.

**Recommendation:** The planner should prefer **option (1)** for scope reasons — Phase 07's surface is parametrize/discovery, not isolation testing. Phase 10 DOC-07 is the right venue for the "spawn-site list" documentation in EXTENDING.md. **Flag option (2) as a deferred-to-v1.1.x enhancement if the team wants belt-and-suspenders.** It is NOT a blocker for Phase 07 closure.

### Pitfall 2: `TARGET_TOOL_NAME=""` in `.env` does NOT collapse to `None` automatically

**What goes wrong:** A user expecting "unset = discover all tools" might write `TARGET_TOOL_NAME=` in `.env` (intending "empty = unset"). The custom `_BareNameNestedEnvSource` reads `""` as a present value and feeds it to Pydantic. Without normalization, `config.target.tool_name == ""` — and the discovery hook's `if explicit:` short-circuit treats `""` as falsy (so it discovers — correct behavior!). BUT downstream `_preflight` membership checks would fail in confusing ways if anyone writes `if config.target.tool_name is None:` instead of `if config.target.tool_name:`.

**Why it happens:** The pydantic-settings env-variable layer sees membership, not truthiness. `os.environ` doesn't distinguish "unset" from "empty" reliably across shells (POSIX `export TARGET_TOOL_NAME=` differs from `unset TARGET_TOOL_NAME`).

**How to avoid:** Add a `field_validator(mode="before")` on `TargetConfig.tool_name` that maps `""` → `None`. This is small (~5 LOC) and idiomatic Pydantic v2. See Pattern 4.

**Warning signs:** A test adds `if config.target.tool_name is None:` somewhere (instead of `if not config.target.tool_name`) and silently doesn't trigger when the user has `TARGET_TOOL_NAME=`.

### Pitfall 3: Tests that don't currently take `target_tool` (TEST-08, TEST-09) get NOT parametrized

**What goes wrong:** If the planner only adds a `pytestmark = [..., pytest.mark.parametrize(...)]` line to the test module without changing test bodies, TEST-08 and TEST-09 (which use `mcp_client` + `config.target.tool_name` directly) would still run **once** — not parametrized — because they don't take the `target_tool` fixture. With `config.target.tool_name = None` (the new default), they would crash trying to call `mcp_client.call_tool(None, {})`.

**Why it happens:** Indirect parametrize **only** affects tests that consume the parametrized fixture. TEST-08 and TEST-09 don't.

**How to avoid:** Rewrite TEST-08, TEST-09, and TEST-10's body to take `target_tool` and call `mcp_client.call_tool(target_tool.name, {})` instead of `config.target.tool_name`. This is a 3-line change per test (Pattern 3 above).

**Warning signs:** Plan checker should catch a mismatch between "10 tests parametrized" expectation and the actual count of tests taking `target_tool`. If the plan says "module-level parametrize over `target_tool`", every test must have `target_tool` in its parameter list.

### Pitfall 4: Tool names with special characters (forward-looking)

**What goes wrong:** Today, all `homelab-mcp` tool names are snake_case (`list_registered_servers`, `list_keyring_credentials`). Pytest accepts these as parametrize ids without sanitization. **Future MCP servers might advertise tools with names like `tools/list_things` or `core:list_things`** — pytest's id parser will mostly accept them, but `[` `]` `:` characters in the id can confuse pytest's `-k` filter and JUnit XML readers.

**Why it happens:** Pytest test IDs are bracket-delimited; `[` in the id collides with the bracket syntax.

**How to avoid:** Use the bare tool name as the id (no sanitization) — matches D-05's spec. **If a tool name contains characters that break pytest's id model**, the failure is loud (pytest emits a warning at collection time); not silent. The failure mode is "test does not run" rather than "test runs against wrong tool". A note in the docstring + a deferred-to-Phase-08 sanitization helper is sufficient.

**Warning signs:** A real homelab-mcp release advertises a tool with `:` or `/` in its name. Phase 07 punts; Phase 08 (TOOLCFG-01) — when per-tool config maps tool names to config keys — is the right venue for a documented sanitization rule.

### Pitfall 5: Discovery happens BEFORE `_preflight` — failure modes diverge

**What goes wrong:** `_preflight` is an `autouse` session fixture (fixtures.py:85-168) — it runs at the START of test execution, AFTER collection. The discovery hook runs at collection. So if `homelab-mcp` is not on PATH or fails to spawn:
- **Old (v1.0) behavior:** `_preflight` calls `pytest.exit("MCP command 'homelab-mcp' not found on PATH", returncode=2)` — clean signaled failure.
- **New (Phase 07) behavior with discovery hook:** `asyncio.run(_discover_tools(config))` raises `FileNotFoundError` (from `McpTestClient.__aenter__`'s `shutil.which` check at mcp_client.py:143) → pytest collection error → exit code 2 (also clean, but the error message comes from a different code path, lacking the structured one-line diagnostic).

**Why it happens:** Two failure paths now exist for "MCP server not on PATH" — the discovery hook (fails at collection) and `_preflight` (fails after collection if the user has `target.tool_name` set, which short-circuits discovery via Pattern 1's `_resolve_tool_names`).

**How to avoid:** The discovery hook should produce the **same diagnostic style** as `_preflight`. Wrap `_discover_tools` exceptions and call `pytest.exit("MCP handshake with 'homelab-mcp' failed: ...", returncode=2)` mirroring fixtures.py:150-153 — for exit-code parity with v1.0.

**Recommendation:** The discovery hook should `try/except` around `asyncio.run(...)` and emit the same `pytest.exit(...)` style as `_preflight`. Diff is ~5 lines in the conftest hook. Catches: `FileNotFoundError` (binary not on PATH), `asyncio.TimeoutError` (handshake too slow), generic `Exception` (anything else from the SDK).

**Warning signs:** CI gets a stack trace at collection time instead of a clean preflight diagnostic. Symptom-not-cause failure modes confuse new contributors.

## Code Examples

### Code Example 1: Verified `pytest_generate_tests` + indirect parametrize pattern

[CITED: pytest docs `doc/en/example/parametrize.rst` — "Defer setup of parametrized resources with indirect parametrization"]

```python
# verbatim from pytest docs:
def pytest_generate_tests(metafunc):
    if "db" in metafunc.fixturenames:
        metafunc.parametrize("db", ["d1", "d2"], indirect=True)


@pytest.fixture
def db(request):
    if request.param == "d1":
        return DB1()
    elif request.param == "d2":
        return DB2()
```

**Mapped onto Phase 07:** `db` → `target_tool`; `["d1", "d2"]` → `<discovered tool names>`; the fixture body becomes `await mcp_client.get_tool(request.param)`.

### Code Example 2: Verified ids passing for bracketed test names

[CITED: pytest docs `doc/en/example/parametrize.rst` — "Parametrize with explicit string test IDs"]

```python
@pytest.mark.parametrize("a,b,expected", testdata, ids=["forward", "backward"])
def test_timedistance_v1(a, b, expected): ...
# Test IDs render as: test_timedistance_v1[forward], test_timedistance_v1[backward]
```

**Mapped onto Phase 07:** `ids=tool_names` produces `test_schema_passes_structural_checks[list_keyring_credentials]`, `test_schema_passes_structural_checks[list_registered_servers]`, etc. — **exactly D-05's spec**.

### Code Example 3: Reused `_preflight` brief-session pattern (already in repo)

[VERIFIED: src/mcp_test_framework/fixtures.py:142-154]

```python
# existing _preflight pattern — discovery hook is a near-clone:
async with McpTestClient(
    config.mcp_server.command,
    config.mcp_server.args,
    config.mcp_server.timeout_seconds,
) as brief_client:
    tools = await brief_client.list_tools()
```

The McpTestClient context manager already calls `_build_isolated_env(...)` at mcp_client.py:164 inside its `__aenter__` (Phase 06 D-16) — so **the discovery hook gets isolation for free** simply by reusing this pattern via `async with McpTestClient(...) as cli:`. This is the strongest argument for not open-coding a new `stdio_client` block in the hook.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single hardcoded `target.tool_name` resolved by `target_tool` fixture | Indirect parametrize over discovered tool list | Phase 07 (this phase) | All test IDs become `[<tool_name>]`-suffixed; CI dashboards filter per-tool |
| `pytest_collection_modifyitems` parameter injection (older idiom, pre-pytest 4) | `pytest_generate_tests(metafunc).parametrize(...)` | Pytest 4.x+; current 9.x | Canonical seam, type-safe, readable |
| Class-scoped event-loop (pytest-asyncio 0.x) | `loop_scope="session"` per-marker (pytest-asyncio 1.x) | pytest-asyncio 1.0+ | Already adopted in this project (pyproject.toml:36) |

**Deprecated/outdated:**
- `pytest-asyncio` `auto` mode — explicitly forbidden per project's `asyncio_mode = "strict"` (pyproject.toml:34). Strict mode is the default in 1.x.
- Module-level eager-import parametrize lists — replaced by hook-driven dynamic parametrize. Still seen in tutorials online, but hook-driven is the canonical 2026 approach.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Calling `Config()` inside `pytest_generate_tests` is safe — config-loading is pure-sync. | Pattern 1 | LOW — `Config(BaseSettings)` is a pure-sync Pydantic load (verified via reading `config.py`); there's no async config source in the repo. |
| A2 | `asyncio.run(...)` from a sync `pytest_generate_tests` hook completes + tears down its own loop fully BEFORE pytest-asyncio's session-scoped loop is created. | Pattern 1, §Pitfall 5 | LOW — `asyncio.run()` documented to create+close a fresh loop; the session-scoped pytest-asyncio loop is created **per test**, not at collection time. [Verified via pytest-asyncio docs.] If wrong, symptoms would be loud (RuntimeError about already-running loop). |
| A3 | Indirect parametrize on a session-scoped fixture results in **one fixture instance per `request.param` value** within session scope (i.e., we do NOT re-spawn `mcp_client` per tool — `target_tool` reuses `mcp_client` for all tools). | Pattern 2 | LOW — pytest docs explicitly support this with `metafunc.parametrize(..., scope="session")` style; in our case the fixture itself is session-scoped via the decorator, and `target_tool` does not own its own external resource. The dependency `mcp_client` is also session-scoped → ONE long-lived MCP session, regardless of N. |
| A4 | The renamed module name (`test_mcp_tool_contract.py`) does not collide with any existing pytest collection rule, marker, or pyproject.toml `testpaths` entry. | Pattern §Recommended Project Structure | LOW — verified via reading pyproject.toml (`testpaths = ["tests"]`, no module-name-specific rules) and grepping the repo for old name references. |
| A5 [ASSUMED] | Once-per-collection `_DISCOVERED_TOOL_NAMES` cache survives pytest's `--collect-only` followed by a real run in the same process. | Pattern 1 | LOW — `--collect-only` runs in a single pytest invocation; module-level state persists. If user runs `--collect-only` then a separate invocation, each gets its own cache (correct behavior, mirrors v1.0 _preflight re-runs per CONTEXT specifics). |
| A6 [ASSUMED] | Pytest 9.x's `metafunc.parametrize(...)` accepts `ids=<list>` where each id contains underscores and is bracketed safely; no escaping required for snake_case names. | Pattern §Pitfall 4 | LOW — verified by reading pytest docs cited above. |
| A7 [ASSUMED] | The `_BareNameNestedEnvSource` does not need any change to handle `Optional[str]` — Pydantic's type validation accepts `None` and string values for `Optional[str]` fields. | Pattern 4 | LOW — Pydantic v2 `Optional[str]` semantics are well-documented; the validator handles "" → None coercion before type validation. |

**No high-risk assumptions.** Phase 07 sits on solid, well-documented pytest + pytest-asyncio + Pydantic v2 mechanics.

## Open Questions

1. **CD-02 outcome — share `list_tools()` between `_preflight` and discovery hook?**
   - What we know: The savings is one subprocess spawn per session. The discovery hook is `asyncio.run(...)` from collection; `_preflight` is async from the session loop. They cannot share a loop.
   - What's unclear: Whether the discovery hook should populate a stash that `_preflight` reads to skip its `list_tools` round-trip (or vice versa). 
   - Recommendation: **Don't share.** They run in different lifecycle phases; coupling them makes failure modes harder to reason about. Two sub-second `list_tools` calls per session is not a perf concern at v1.1 scale (D-08 explicitly accepts slow runtime). **Recommendation: hook spawns; `_preflight` runs unchanged (modulo D-15 membership-check branch).**

2. **CD-03 outcome — module-level pytestmark vs hook for parametrize injection?**
   - What we know: Module-level pytestmark requires the tool list at module import time. Hook does not.
   - What's unclear: Whether the planner wants the parametrize call expressed in the test module (more visible to test authors) vs in conftest.py (more centralized).
   - Recommendation: **Hook in conftest.py.** Test author readability is preserved by the test bodies still taking `target_tool`. The parametrize machinery is plumbing — belongs in conftest.py.

3. **CD-05 outcome — short-circuit when `target.tool_name` is set?**
   - What we know: Short-circuit saves one subprocess spawn at collection time. Always-spawn is simpler code (~5 fewer LOC).
   - What's unclear: Whether v1.0 backward-compat users (with `TARGET_TOOL_NAME` set) experience a regression from the extra collection-time spawn.
   - Recommendation: **Short-circuit.** v1.0 backward-compat is a feature surface (D-01, MULTI-04); making it strictly equivalent in startup cost is a quality detail. ~5 LOC delta.

## Environment Availability

> Phase 07 is purely a code/test-config change. External dependencies (homelab-mcp on PATH, Ollama at `127.0.0.1:11434`) are unchanged from v1.0 and verified by `_preflight`.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 | Build/run | ✓ | (pinned in `.python-version`, `pyproject.toml:7`) | — |
| pytest 9.x + pytest-asyncio 1.3+ | Test runner | ✓ | (declared in pyproject.toml:25-26) | — |
| mcp SDK 1.27+ | stdio_client + ClientSession | ✓ | (declared) | — |
| `homelab-mcp` on PATH (or `MCP_SERVER_COMMAND` set) | Discovery hook + tests | Depends on host | Unchanged from v1.0 | None — discovery hook fails loudly at collection time, mirroring `_preflight` (Pitfall 5) |
| Ollama at `127.0.0.1:11434` with `qwen3.6:latest` | Judge tests (TEST-05/06/07) | Depends on host | Unchanged from v1.0 | None — `_preflight` already gates this |

**No new dependencies introduced.** No fallback gaps.

## Project Constraints (from CLAUDE.md)

These directives bind Phase 07 implementation. Listed here so the planner can verify each plan complies:

- **Python 3.14 + uv only.** Locked via `.python-version` and `pyproject.toml`.
- **MCP transport stdio only via `stdio_client`.** No raw `subprocess.Popen`. The discovery hook reuses `McpTestClient.__aenter__` which uses `stdio_client` internally — compliant.
- **Black-box rule (mechanical).** The discovery hook MUST NOT import `homelab_mcp` or any submodule. Tools are read by name from `list_tools()` only. Enforced by `ruff TID251` + `tests/conftest.py:32-42` sys.modules guard. The new `pytest_generate_tests` hook in `tests/conftest.py` adds NO `homelab_mcp` imports.
- **Async timeouts.** All async ops use `asyncio.timeout` (3.11+). The discovery hook delegates to `McpTestClient.list_tools` which already wraps in `asyncio.timeout(self._timeout_seconds)` (mcp_client.py:193). No new timeout sites needed.
- **`pytest-asyncio` strict mode.** All async tests MUST carry `@pytest.mark.asyncio` markers. The renamed test module's existing `pytestmark = [pytest.mark.asyncio(loop_scope="session")]` covers all 10 tests; the parametrize marker is additive, not a replacement.
- **Session-scoped fixtures.** `target_tool`'s `loop_scope="session", scope="session"` is unchanged (pattern preserved per Pattern 2).
- **GSD workflow enforcement.** All edits must go through `/gsd-execute-phase` after this research → plan → discuss-phase loop.

## Validation Architecture

> `nyquist_validation: false` in `.planning/config.json:23` — section omitted per the research template's skip condition.

## Sources

### Primary (HIGH confidence)
- Context7 `/pytest-dev/pytest` (v9.0.0) — `pytest_generate_tests`, indirect parametrize, `metafunc.parametrize`, `ids=` lists
- Context7 `/pytest-dev/pytest-asyncio` — `loop_scope="session"`, strict mode default, marker semantics
- Context7 `/pydantic/pydantic` — `Optional[str]` field semantics, `field_validator(mode="before")`, `validation_alias` + `AliasChoices`
- Repo source (verified via reading): `src/mcp_test_framework/fixtures.py`, `src/mcp_test_framework/mcp_client.py`, `src/mcp_test_framework/_isolation.py`, `src/mcp_test_framework/models.py`, `src/mcp_test_framework/config.py`, `tests/conftest.py`, `tests/test_homelab_list_registered_servers.py`, `tests/test_isolation.py`, `pyproject.toml`
- `.planning/phases/07-multi-tool-discovery-and-parameterized-testing/07-CONTEXT.md` — locked decisions D-01..D-17, CD-01..CD-06
- `.planning/phases/06-per-session-host-state-isolation/06-VERIFICATION.md` — ISOL-03 + ISOL-06 evidence; spawn-site enumeration

### Secondary (MEDIUM confidence)
- pytest official docs (via Context7 `/pytest-dev/pytest`): `doc/en/how-to/parametrize.rst`, `doc/en/example/parametrize.rst`
- pytest-asyncio official docs: `docs/reference/markers/index.md`

### Tertiary (LOW confidence)
- None. All findings traced to authoritative sources or repo code.

## Metadata

**Confidence breakdown:**
- pytest hook seam (`pytest_generate_tests`): HIGH — canonical pytest API, multiple verified docs examples
- Indirect parametrize id rendering: HIGH — verified docs + already shipping pytest 9.x
- Reuse of `McpTestClient.__aenter__` for discovery: HIGH — code reading confirms Phase 06 D-16 isolation already in place
- `Optional[str]` env empty-string normalization: HIGH — Pydantic v2 idiom; verified via reading project's custom `_BareNameNestedEnvSource`
- Pitfall 1 (ISOL-03 doesn't auto-cover discovery): HIGH — verified by reading `tests/test_isolation.py` body line 124
- Pitfall 3 (TEST-08/TEST-09 need body rewrite): HIGH — verified by reading the test module
- Pitfall 5 (failure-mode parity with `_preflight`): HIGH — verified by reading `_preflight` body
- Test module rename has no other repercussions: HIGH — verified via grep for old name references in pyproject.toml, conftest.py, README, docs
- POSIX `USER` allowlist gap (carried over from Phase 06 G-03): not Phase 07's surface — flagged for awareness

**Research date:** 2026-05-07
**Valid until:** 2026-06-07 (30 days; pytest + pytest-asyncio + mcp SDK are stable lines; nothing in scope is fast-moving)
