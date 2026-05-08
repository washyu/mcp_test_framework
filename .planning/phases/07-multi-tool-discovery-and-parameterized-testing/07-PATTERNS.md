# Phase 07: Multi-tool discovery & parameterized testing - Pattern Map

**Mapped:** 2026-05-07
**Files analyzed:** 4 (1 new behavior in existing file, 3 modify, 1 of which is also a rename)
**Analogs found:** 4 / 4 (all in-repo; this is a glue phase by design)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tests/conftest.py` (ADD `pytest_generate_tests` hook + `_discover_tools` helper + `_resolve_tool_names` helper + module-level cache) | pytest collection-time plugin (sync hook + async helper) | request-response (one-shot subprocess spawn → tool name list) | `src/mcp_test_framework/fixtures.py` `_preflight` brief-session block (lines 142-154) | role-match — both wrap `McpTestClient` for a brief `list_tools()`, but `_preflight` is async/session-fixture-shaped while the discovery hook is sync-collection + `asyncio.run(...)` |
| `src/mcp_test_framework/fixtures.py` (MODIFY `target_tool` line 330-338 → indirect-parametrize-aware; MODIFY `_preflight` lines 156-162 → drop membership check when `tool_name is None`) | session-scoped pytest-asyncio fixture | request-response (per-test tool resolution) | existing `target_tool` body at fixtures.py:330-338 itself; existing `_preflight` membership-check branch | exact (in-place rewrite of the same fixture; one-line conditional added to existing branch) |
| `src/mcp_test_framework/models.py` (MODIFY `TargetConfig.tool_name` line 70-73 → `Optional[str]`, default `None`, add `field_validator(mode="before")` empty-string→None coercion) | Pydantic v2 BaseModel field (cross-cutting config) | transform (env var → typed config) | existing `OllamaConfig.timeout_seconds` Field+AliasChoices pattern at models.py:38-42 (validator part has no analog — new pattern, but pydantic v2 idiomatic) | role-match for the Field shape; no analog for the validator (new pattern, Phase 07 introduces it) |
| `tests/test_homelab_list_registered_servers.py` → `tests/test_mcp_tool_contract.py` (RENAME + edit TEST-08 line 165-171, TEST-09 line 174-182, TEST-10 line 185-224 to take `target_tool` and use `target_tool.name`) | pytest async integration test module | request-response (per-tool MCP `call_tool({})` + assertions) | existing TEST-01..TEST-07 in the same module (lines 51-157) — already take `target_tool` as fixture parameter | exact — TEST-01..TEST-07 are the canonical shape; TEST-08..TEST-10 must be rewritten to match it |

## Pattern Assignments

### `tests/conftest.py` — ADD `pytest_generate_tests` hook + discovery helpers

**Analog 1 (brief-session shape):** `src/mcp_test_framework/fixtures.py` lines 142-154 (`_preflight`'s MCP brief-handshake block)

**Analog 2 (existing conftest shape):** `tests/conftest.py` (entire file, currently lines 1-42) — preserves `pytest_plugins` registration and the `pytest_configure` sys.modules black-box guard.

**Imports pattern** (mirrors `fixtures.py:22-47` — `from __future__ import annotations` first, stdlib next, third-party next, local last; absolute imports via `mcp_test_framework.<submodule>`):
```python
# tests/conftest.py — augmented import block
from __future__ import annotations

import asyncio  # NEW — discovery hook calls asyncio.run()
import sys  # already present (line 14)
from typing import Optional  # NEW

import pytest  # NEW — for Metafunc type hint and pytest.exit()

from mcp_test_framework.config import Config  # NEW
from mcp_test_framework.mcp_client import McpTestClient  # NEW
```

**Existing seam to PRESERVE (lines 12, 17-42):**
```python
pytest_plugins = ["mcp_test_framework.fixtures"]  # MUST stay top-level

def pytest_configure(config) -> None:
    """Fail-fast if anything importable from homelab_mcp leaks into the test process."""
    leaked = [name for name in sys.modules
              if name == "homelab_mcp" or name.startswith("homelab_mcp.")]
    if leaked:
        raise RuntimeError(...)
```
The new code MUST NOT import `homelab_mcp` or any submodule (would trip the guard). Black-box rule: tools are read by name from `list_tools()` only.

**Core discovery pattern** — copy the `async with McpTestClient(...) as <name>: tools = await <name>.list_tools()` shape verbatim from `fixtures.py:142-148` (`_preflight` Check 3 + 4):
```python
# fixtures.py:142-148 — VERBATIM analog for _discover_tools body:
async with McpTestClient(
    config.mcp_server.command,
    config.mcp_server.args,
    config.mcp_server.timeout_seconds,
) as brief_client:
    tools = await brief_client.list_tools()
```
The discovery hook reuses this exact shape inside an `async def _discover_tools(config) -> list[str]` and returns `[t.name for t in tools]`. Per `mcp_client.py:139-177` (`McpTestClient.__aenter__`), this entry point already builds its own per-instance tempdir + `_build_isolated_env(...)` — discovery gets isolation **for free** (Phase 06 D-16; discovery does NOT need to manage a tempdir manually).

**Sync hook + asyncio.run pattern** (NO direct analog in repo — pytest 9.x canonical seam, verified in RESEARCH §Pattern 1):
```python
def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "target_tool" not in metafunc.fixturenames:
        return
    config = Config()
    names = _resolve_tool_names(config)  # cached module-level
    metafunc.parametrize("target_tool", names, indirect=True, ids=names)
```

**Failure-mode parity pattern** (RESEARCH Pitfall 5) — mirror the `_preflight` exit style at `fixtures.py:149-154` so collection-time failures emit the same diagnostic shape as v1.0:
```python
# fixtures.py:149-154 — analog for discovery-hook exception handling:
except Exception as exc:
    pytest.exit(
        f"MCP handshake with {config.mcp_server.command!r} failed: "
        f"{exc.__class__.__name__}: {exc}",
        returncode=2,
    )
```
Discovery hook should `try/except` around `asyncio.run(...)` and call `pytest.exit(..., returncode=2)` with the same f-string shape.

**Cache pattern** (CD-01 — pick simpler; module-level dict over `pytest.StashKey` per RESEARCH recommendation):
```python
# Module-level cache — CD-01 chooses dict-style for simplicity
_DISCOVERED_TOOL_NAMES: Optional[list[str]] = None

def _resolve_tool_names(config: Config) -> list[str]:
    global _DISCOVERED_TOOL_NAMES
    explicit = config.target.tool_name
    if explicit:  # non-None and non-empty (validator already coerced "" -> None)
        return [explicit]  # CD-05 short-circuit — no spawn when tool_name set
    if _DISCOVERED_TOOL_NAMES is None:
        _DISCOVERED_TOOL_NAMES = asyncio.run(_discover_tools(config))
    return _DISCOVERED_TOOL_NAMES
```

---

### `src/mcp_test_framework/fixtures.py` — MODIFY `target_tool` (lines 330-338) + `_preflight` (lines 156-162)

**Analog (in-place rewrite):** the existing `target_tool` body itself at `fixtures.py:330-338`. The new shape preserves all decorators, scope, and the `mcp_client + _preflight` dependency declarations; only the body changes.

**Existing imports to PRESERVE (lines 22-47):** all stay. No new imports needed (`pytest.FixtureRequest` is already implicitly available through `pytest_asyncio.fixture` + the `request` parameter — but if the planner wants a type hint, add `import pytest` is already in scope at line 33).

**Existing fixture decorators to PRESERVE (line 330):**
```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def target_tool(...):
```
Per RESEARCH §Pattern 2 + Assumption A3: indirect parametrize on a session-scoped fixture creates one fixture instance per `request.param` value within session scope. `target_tool`'s dependency on `mcp_client` (also session-scoped) is preserved — ONE long-lived MCP session, regardless of N tools.

**Old body** (lines 330-338, to be replaced):
```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def target_tool(config: Config, mcp_client: McpTestClient, _preflight):
    """Resolve target tool by name; raises ToolNotFoundError if absent."""
    return await mcp_client.get_tool(config.target.tool_name)
```

**New body** (D-13: indirect parametrize via `request.param`):
```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def target_tool(
    request: pytest.FixtureRequest,
    mcp_client: McpTestClient,
    _preflight,
):
    """Resolve target tool by name (parametrized indirectly via tests/conftest.py)."""
    return await mcp_client.get_tool(request.param)
```
Note: `config: Config` parameter is REMOVED (no longer needed; the parametrize layer in conftest.py now owns the name source). `mcp_client.get_tool` (`mcp_client.py:197-205`) preserves its `ToolNotFoundError` raise on race-condition mismatches.

**`_preflight` membership-check pattern (D-15)** — wrap the existing assertion at `fixtures.py:156-162` in a conditional:

**Existing block** (lines 156-162, to be made conditional):
```python
tool_names = [t.name for t in tools]
if config.target.tool_name not in tool_names:
    pytest.exit(
        f"target tool {config.target.tool_name!r} not in MCP server tool list "
        f"(available: {tool_names!r})",
        returncode=2,
    )
```

**New shape** (D-15: skip when `tool_name is None`, keep when set; `field_validator` in models.py guarantees `""` → `None`):
```python
if config.target.tool_name is not None:
    tool_names = [t.name for t in tools]
    if config.target.tool_name not in tool_names:
        pytest.exit(
            f"target tool {config.target.tool_name!r} not in MCP server tool list "
            f"(available: {tool_names!r})",
            returncode=2,
        )
```
Other `_preflight` checks (Check 1: PATH; Check 2: Ollama; Check 3: handshake) stay verbatim.

---

### `src/mcp_test_framework/models.py` — MODIFY `TargetConfig` (lines 65-73)

**Analog (existing pattern in same file):** `OllamaConfig.timeout_seconds` at `models.py:38-42` and the `model_config = ConfigDict(frozen=True, populate_by_name=True)` pattern at `models.py:28, 48, 68`.

**Existing imports to PRESERVE (line 22):**
```python
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
```

**Imports to ADD:**
```python
from typing import Optional
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator  # add field_validator
```

**Existing `model_config` pattern** (lines 68, identical at 28, 48):
```python
model_config = ConfigDict(frozen=True, populate_by_name=True)
```
PRESERVE verbatim.

**Existing `Field` + `AliasChoices` pattern** (analog at `models.py:30-33`, `OllamaConfig.base_url`):
```python
base_url: str = Field(
    default="http://127.0.0.1:11434",
    validation_alias=AliasChoices("OLLAMA_BASE_URL", "base_url"),
)
```

**Old `TargetConfig.tool_name`** (lines 70-73, to be replaced):
```python
tool_name: str = Field(
    default="list_registered_servers",
    validation_alias=AliasChoices("TARGET_TOOL_NAME", "tool_name"),
)
```

**New `TargetConfig.tool_name`** (D-02: type → `Optional[str]`, default → `None`; AliasChoices unchanged):
```python
tool_name: Optional[str] = Field(
    default=None,
    validation_alias=AliasChoices("TARGET_TOOL_NAME", "tool_name"),
)

@field_validator("tool_name", mode="before")
@classmethod
def _empty_to_none(cls, v):
    """Empty string from env → None (D-02 'empty equivalent to None')."""
    if isinstance(v, str) and v.strip() == "":
        return None
    return v
```
**No analog for the validator** — this is a new pattern in this file. RESEARCH Pitfall 2 explains why: the project's custom `_BareNameNestedEnvSource` reads `""` as a present value, so `TARGET_TOOL_NAME=` in `.env` would yield `""` (not `None`) without explicit coercion.

**Update docstring** (line 66) from:
```python
"""Target tool to run all tests against."""
```
to:
```python
"""Target tool to run all tests against. None = discover all tools (Phase 07 D-01)."""
```

---

### `tests/test_homelab_list_registered_servers.py` → `tests/test_mcp_tool_contract.py` (RENAME + body edits)

**Analog 1 (canonical test shape):** TEST-01 at `test_homelab_list_registered_servers.py:51-59` and TEST-02..TEST-07 (lines 62-157) — all already take `target_tool` as a fixture parameter. TEST-08..TEST-10 must be rewritten to match.

**Existing imports to PRESERVE (lines 31-39):**
```python
import json
import pytest
from jsonschema.validators import Draft202012Validator
from mcp_test_framework.config import Config
from mcp_test_framework.judge_protocol import Judge
from mcp_test_framework.mcp_client import McpTestClient
from mcp_test_framework.schema_validator import validate_tool_schema
```
After the TEST-08..TEST-10 rewrite, `Config` import is no longer used (the tests stop reading `config.target.tool_name`). Either remove the unused import or keep it — planner's call. **Recommendation:** remove unused `Config` import to keep ruff happy.

**Existing `pytestmark` pattern** (line 43):
```python
pytestmark = [pytest.mark.asyncio(loop_scope="session")]
```
PRESERVE verbatim. Per RESEARCH §CD-03 + D-14: parametrize injection lives in `conftest.py` `pytest_generate_tests`, NOT module-level pytestmark. The pytestmark line stays single-marker.

**Canonical test-body pattern** (analog: TEST-01 at lines 51-59, TEST-02 at 62-65 — fixture-driven, takes `target_tool`, uses `target_tool.<attr>`):
```python
# Canonical fixture-driven test shape (analog: TEST-01..TEST-07):
async def test_target_tool_exists(target_tool) -> None:
    """TEST-01: configured TARGET_TOOL_NAME present in server tool list."""
    assert target_tool.name, f"target_tool.name is empty: {target_tool!r}"

async def test_schema_passes_structural_checks(target_tool) -> None:
    issues = validate_tool_schema(target_tool)
    assert issues == [], f"schema issues found: {issues!r}"
```

**TEST-08 OLD body** (lines 165-171):
```python
async def test_empty_args_call_returns_non_error(
    mcp_client: McpTestClient,
    config: Config,
) -> None:
    """TEST-08: call_tool with {} returns isError=False."""
    result = await mcp_client.call_tool(config.target.tool_name, {})
    assert not result.isError, f"call_tool returned isError=True: {result!r}"
```

**TEST-08 NEW body** (Pitfall 3 — add `target_tool` parameter, use `target_tool.name`):
```python
async def test_empty_args_call_returns_non_error(
    mcp_client: McpTestClient,
    target_tool,
) -> None:
    """TEST-08: call_tool with {} returns isError=False."""
    result = await mcp_client.call_tool(target_tool.name, {})
    assert not result.isError, f"call_tool returned isError=True: {result!r}"
```

**TEST-09 OLD body** (lines 174-182): same shape as TEST-08; same fix — drop `config: Config`, add `target_tool`, replace `config.target.tool_name` → `target_tool.name`.

**TEST-10 OLD body** (lines 185-224): already takes `target_tool`. Single-line change at line 195 — replace `config.target.tool_name` → `target_tool.name`. Drop `config: Config` parameter at line 188.

**Test-ID rendering pattern** (D-05: uniform `[<tool_name>]` suffix). Driven by `ids=tool_names` in conftest.py's `metafunc.parametrize` call. No test-body change needed for ID rendering; pytest produces `test_schema_passes_structural_checks[list_registered_servers]` automatically.

**Module-rename mechanics:** This is `git mv tests/test_homelab_list_registered_servers.py tests/test_mcp_tool_contract.py` (CD-04). Verified by RESEARCH §A4: `pyproject.toml`'s `testpaths = ["tests"]` (no module-name-specific rules); no other repo files reference the old name in pyproject.toml, conftest.py, README, or docs. **Update the module docstring** (lines 1-28) to drop the "Phase 4 integration tests against live homelab-mcp / list_registered_servers" framing and note that the module is now tool-agnostic (parametrized over discovered tools).

---

## Shared Patterns

### Subprocess Isolation (Phase 06 contract — applies to ALL spawn sites)

**Source:** `src/mcp_test_framework/_isolation.py:80-107` (`_build_isolated_env`)

**Apply to:** Every spawn site that constructs `StdioServerParameters`. Three sites total in v1.1:
1. `_preflight` brief session (`fixtures.py:142-148`) — uses `McpTestClient.__aenter__` which builds its own tempdir + `_build_isolated_env` at `mcp_client.py:156-164`.
2. `mcp_client._owner_task` long-lived session (`fixtures.py:244-249`) — uses session-scoped `_isolated_home` fixture + `_build_isolated_env(_isolated_home)`.
3. **NEW**: discovery hook (`tests/conftest.py`) — reuses `McpTestClient.__aenter__`, gets isolation for free.

**Concrete excerpt (mcp_client.py:156-165):**
```python
isolated_home = Path(
    stack.enter_context(
        tempfile.TemporaryDirectory(prefix="mcp-test-fw-cli-")
    )
)
params = StdioServerParameters(
    command=self._command,
    args=self._args,
    env=_build_isolated_env(isolated_home),  # ISOL-02 / D-16 / D-17
)
```
The discovery hook MUST go through `McpTestClient.__aenter__` to inherit this. Do NOT open-code a new `stdio_client(...)` block — that would bypass `_build_isolated_env` and create a fourth (broken) spawn site.

**Black-box rule reference:** `tests/conftest.py:32-42` `pytest_configure` sys.modules guard. Discovery code MUST NOT import any `homelab_mcp` symbol.

### Failure-mode parity (collection-time vs preflight-time)

**Source:** `src/mcp_test_framework/fixtures.py:111-114, 127-131, 134-139, 149-154, 158-162` (all five `pytest.exit(..., returncode=2)` sites in `_preflight`)

**Apply to:** Discovery hook in `tests/conftest.py`. Wrap `asyncio.run(_discover_tools(config))` in a `try/except` that emits the same f-string + `returncode=2` shape so collection-time failures look like preflight failures.

**Concrete excerpt (fixtures.py:149-154):**
```python
except Exception as exc:
    pytest.exit(
        f"MCP handshake with {config.mcp_server.command!r} failed: "
        f"{exc.__class__.__name__}: {exc}",
        returncode=2,
    )
```

### Pytest-asyncio session-loop fixture pattern

**Source:** `src/mcp_test_framework/fixtures.py:85-86, 177-178, 212-213, 306-307, 330-331` (every async fixture in the module)

**Apply to:** the rewritten `target_tool` fixture. Decorator stays:
```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def target_tool(...):
```
Matches `asyncio_default_fixture_loop_scope = "session"` in `pyproject.toml:36`. Per RESEARCH Assumption A3: indirect parametrize creates one fixture instance per `request.param` value within session scope; `mcp_client` (also session-scoped) is shared across all instances — ONE long-lived MCP session.

### Pydantic v2 frozen+populate_by_name model pattern

**Source:** `src/mcp_test_framework/models.py:28, 48, 68`

**Apply to:** `TargetConfig` rewrite. PRESERVE the existing `model_config` line and the `Field(default=..., validation_alias=AliasChoices(...))` shape; only widen the type and add the validator.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `pytest_generate_tests` hook in `tests/conftest.py` | pytest collection plugin (sync hook) | request-response | First collection-time hook in the repo. The brief-session shape is borrowed from `_preflight`, but the sync-hook + `asyncio.run(...)` invocation pattern is new. RESEARCH §Pattern 1 + pytest docs `how-to/parametrize.rst` cited as authoritative. |
| `field_validator(mode="before")` on `TargetConfig.tool_name` | Pydantic v2 model validator | transform | First field validator in `models.py`. Pattern is pydantic v2 idiomatic (RESEARCH Pattern 4); planner should reference RESEARCH §Pitfall 2 for the rationale (custom `_BareNameNestedEnvSource` reads `""` as present, not absent). |

## Metadata

**Analog search scope:** `src/mcp_test_framework/`, `tests/`
**Files scanned:** 6 (fixtures.py, mcp_client.py, _isolation.py, models.py, tests/conftest.py, tests/test_homelab_list_registered_servers.py)
**Pattern extraction date:** 2026-05-07

**Key insight (from RESEARCH "Don't Hand-Roll"):** Phase 07 is a **glue phase** — every primitive needed already exists in the repo (McpTestClient.__aenter__ Phase-06-isolation-aware; _preflight brief-session shape; pytestmark + indirect-parametrize machinery; Pydantic v2 field_validator). The diff is pure composition: ~50 LOC in conftest.py + ~5 LOC in fixtures.py + ~10 LOC in models.py + ~10 LOC of test-body edits + a `git mv`. No new patterns are invented; the planner's job is to wire existing primitives in the canonical pytest seam.
