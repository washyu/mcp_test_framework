---
phase: 07-multi-tool-discovery-and-parameterized-testing
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/mcp_test_framework/models.py
  - src/mcp_test_framework/fixtures.py
  - tests/conftest.py
  - tests/test_homelab_list_registered_servers.py  # renamed -> tests/test_mcp_tool_contract.py
  - tests/test_mcp_tool_contract.py                # renamed target
autonomous: true
requirements: [MULTI-01, MULTI-02, MULTI-03, MULTI-04]

must_haves:
  truths:
    - "With TARGET_TOOL_NAME unset, `uv run pytest --collect-only -q` discovers all server-advertised tools and produces N test instances per test function (one per tool)."
    - "Test IDs render as `<test_name>[<tool_name>]` (e.g. `test_schema_passes_structural_checks[list_registered_servers]`) in pytest terminal output."
    - "With TARGET_TOOL_NAME=list_registered_servers, the run is restricted to that tool only — full v1.0 behavior preserved."
    - "Discovery happens at pytest collection time via `pytest_generate_tests` — no codegen, no eager-import spawn."
    - "The discovery subprocess spawn does NOT mutate `~/.homelab_mcp/credential_registry.json`, `~/.homelab_mcp/known_hosts`, or `~/.homelab_mcp/migration_state.json` (Phase 06 ISOL-03 contract preserved at the third spawn site)."
    - "The renamed test module `tests/test_mcp_tool_contract.py` exists; the old name `tests/test_homelab_list_registered_servers.py` is deleted from git."
  artifacts:
    - path: "tests/conftest.py"
      provides: "pytest_generate_tests hook + _discover_tools async helper + _resolve_tool_names cache + module-level _DISCOVERED_TOOL_NAMES"
      contains: "def pytest_generate_tests(metafunc"
    - path: "src/mcp_test_framework/models.py"
      provides: "TargetConfig.tool_name as Optional[str] with empty-string-to-None validator"
      contains: "tool_name: Optional[str]"
    - path: "src/mcp_test_framework/fixtures.py"
      provides: "target_tool fixture taking request.param; _preflight membership check conditional on tool_name is not None"
      contains: "request.param"
    - path: "tests/test_mcp_tool_contract.py"
      provides: "Renamed test module with TEST-08/09/10 body edits to take target_tool"
      exports: ["test_target_tool_exists", "test_schema_passes_structural_checks", "test_empty_args_call_returns_non_error"]
  key_links:
    - from: "tests/conftest.py"
      to: "src/mcp_test_framework/mcp_client.py:McpTestClient.__aenter__"
      via: "async with McpTestClient(...) as client: tools = await client.list_tools()"
      pattern: "async with McpTestClient"
    - from: "tests/conftest.py"
      to: "metafunc.parametrize"
      via: "indirect=True, ids=tool_names"
      pattern: "metafunc\\.parametrize\\(\"target_tool\""
    - from: "src/mcp_test_framework/fixtures.py:target_tool"
      to: "mcp_client.get_tool"
      via: "await mcp_client.get_tool(request.param)"
      pattern: "mcp_client\\.get_tool\\(request\\.param\\)"
    - from: "tests/test_mcp_tool_contract.py:TEST-08/09/10"
      to: "target_tool fixture"
      via: "target_tool.name passed to mcp_client.call_tool"
      pattern: "mcp_client\\.call_tool\\(target_tool\\.name"
---

<objective>
Generalize the v1.0 single-tool test loop to N-tools-per-run via collection-time tool discovery + indirect parametrize. The framework discovers tools from the live MCP server in a sync `pytest_generate_tests` hook (third spawn site, isolation-inherited from `McpTestClient.__aenter__`), parametrizes the `target_tool` fixture indirectly, and renames the test module to a tool-agnostic name. Closes MULTI-01..MULTI-04.

Purpose: A single test-suite invocation exercises all server-advertised tools; per-tool failures attribute via `[<tool_name>]` test IDs.

Output:
- New `pytest_generate_tests` hook + discovery helpers in `tests/conftest.py`
- `TargetConfig.tool_name: str | None` (D-02) with empty-string→None validator
- `target_tool` fixture rewritten to indirect parametrize (D-13)
- `_preflight` membership check made conditional on `tool_name is not None` (D-15)
- TEST-08/09/10 rewritten to take `target_tool` (Pitfall 3)
- Test module renamed to `tests/test_mcp_tool_contract.py` (D-17)
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/07-multi-tool-discovery-and-parameterized-testing/07-CONTEXT.md
@.planning/phases/07-multi-tool-discovery-and-parameterized-testing/07-RESEARCH.md
@.planning/phases/07-multi-tool-discovery-and-parameterized-testing/07-PATTERNS.md
@.planning/phases/06-per-session-host-state-isolation/06-VERIFICATION.md
@CLAUDE.md
@src/mcp_test_framework/_isolation.py
@src/mcp_test_framework/mcp_client.py
@src/mcp_test_framework/fixtures.py
@src/mcp_test_framework/models.py
@src/mcp_test_framework/config.py
@tests/conftest.py
@tests/test_homelab_list_registered_servers.py
@tests/test_isolation.py

<interfaces>
<!-- Key contracts the executor needs. Extracted from codebase + Phase 06 -->

From src/mcp_test_framework/_isolation.py (Phase 06):
```python
def _build_isolated_env(home: Path) -> dict[str, str]:
    """Build env dict for StdioServerParameters with HOME/USERPROFILE
    pointing at `home`, PYTHON_KEYRING_BACKEND=keyring.backends.null.Null,
    and the documented PATH/SYSTEMROOT/LANG/USERNAME/MCP_* allowlist."""
```

From src/mcp_test_framework/mcp_client.py (Phase 06 D-16 — already isolation-aware):
```python
class McpTestClient:
    def __init__(self, command: str, args: list[str], timeout_seconds: int) -> None: ...
    async def __aenter__(self) -> "McpTestClient":
        # Builds its own per-instance tempdir + StdioServerParameters(env=_build_isolated_env(td))
        ...
    async def list_tools(self) -> list[Tool]: ...
    async def get_tool(self, name: str) -> Tool: ...  # raises ToolNotFoundError on miss
    async def call_tool(self, name: str, arguments: dict) -> CallToolResult: ...
```

From src/mcp_test_framework/config.py:
```python
class Config(BaseSettings):
    mcp_server: McpServerConfig
    target: TargetConfig
    ollama: OllamaConfig
    # Loadable via plain Config()  -- pure-sync Pydantic load (RESEARCH A1)
```

From src/mcp_test_framework/fixtures.py (current):
```python
# _preflight membership check at lines 156-162 (to be made conditional)
# target_tool at lines 330-338 (to be rewritten to indirect)
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def target_tool(config: Config, mcp_client: McpTestClient, _preflight):
    return await mcp_client.get_tool(config.target.tool_name)
```

From src/mcp_test_framework/models.py (current TargetConfig at lines 65-73):
```python
class TargetConfig(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)
    tool_name: str = Field(
        default="list_registered_servers",
        validation_alias=AliasChoices("TARGET_TOOL_NAME", "tool_name"),
    )
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Widen TargetConfig.tool_name + add empty-string validator + drop _preflight membership when None</name>
  <files>
    - src/mcp_test_framework/models.py
    - src/mcp_test_framework/fixtures.py
  </files>
  <read_first>
    - src/mcp_test_framework/models.py (full)
    - src/mcp_test_framework/fixtures.py (lines 86-170, the _preflight body)
    - src/mcp_test_framework/config.py (skim _BareNameNestedEnvSource at lines 91-146 — confirms why the validator is needed; do NOT modify)
    - .planning/phases/07-multi-tool-discovery-and-parameterized-testing/07-RESEARCH.md (§Pattern 4, §Pitfall 2)
    - .planning/phases/07-multi-tool-discovery-and-parameterized-testing/07-PATTERNS.md (§"src/mcp_test_framework/models.py — MODIFY TargetConfig" + §"src/mcp_test_framework/fixtures.py — MODIFY _preflight")
  </read_first>
  <action>
**Edit 1: `src/mcp_test_framework/models.py` — TargetConfig (lines ~65-73).**

Update the import block at the top of the file:
```python
# add to existing pydantic import
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator
# add (or confirm exists) — Optional from typing
from typing import Optional
```

Replace the entire `TargetConfig` class body with:
```python
class TargetConfig(BaseModel):
    """Target tool to run all tests against. None = discover all tools (Phase 07 D-01)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    tool_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("TARGET_TOOL_NAME", "tool_name"),
    )

    @field_validator("tool_name", mode="before")
    @classmethod
    def _empty_to_none(cls, v):
        """Empty string from env -> None (Phase 07 D-02 'empty equivalent to None').

        The project's custom _BareNameNestedEnvSource (config.py:91-146) reads
        an env var as present when membership-check passes, regardless of value.
        TARGET_TOOL_NAME='' would land as '' (not None) without this coercion.
        See 07-RESEARCH §Pitfall 2.
        """
        if isinstance(v, str) and v.strip() == "":
            return None
        return v
```

DO NOT remove `AliasChoices("TARGET_TOOL_NAME", "tool_name")` — backward compat with v1.0 .env files (D-02).

**Edit 2: `src/mcp_test_framework/fixtures.py` — `_preflight` membership check (lines 156-162) per D-15.**

Locate the existing block in `_preflight` (around lines 156-162). The current shape is:
```python
tool_names = [t.name for t in tools]
if config.target.tool_name not in tool_names:
    pytest.exit(
        f"target tool {config.target.tool_name!r} not in MCP server tool list "
        f"(available: {tool_names!r})",
        returncode=2,
    )
```

Replace with the conditional shape (D-15: skip when `tool_name is None`, keep when set):
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

Other `_preflight` checks (PATH, Ollama handshake, MCP handshake, list_tools call) STAY VERBATIM. Do NOT touch lines 86-155 or 163-end of `_preflight` body.
  </action>
  <verify>
    <automated>uv run python -c "from mcp_test_framework.models import TargetConfig; m = TargetConfig(); assert m.tool_name is None; m2 = TargetConfig(tool_name=''); assert m2.tool_name is None; m3 = TargetConfig(tool_name='list_registered_servers'); assert m3.tool_name == 'list_registered_servers'; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -nE "tool_name:\s*Optional\[str\]" src/mcp_test_framework/models.py` returns at least one hit
    - `grep -nE 'default=None' src/mcp_test_framework/models.py` returns a hit on the `TargetConfig.tool_name` line
    - `grep -nE '@field_validator\("tool_name", mode="before"\)' src/mcp_test_framework/models.py` returns one hit
    - `grep -nE 'AliasChoices\("TARGET_TOOL_NAME"' src/mcp_test_framework/models.py` returns one hit (alias preserved)
    - `grep -c "if config.target.tool_name is not None:" src/mcp_test_framework/fixtures.py` returns at least 1
    - `grep -c 'AliasChoices("TARGET_TOOL_NAME"' src/mcp_test_framework/models.py` is 1 (no duplication)
    - `uv run python -c "from mcp_test_framework.config import Config; c = Config(); print(c.target.tool_name)"` runs without error (prints None or the configured value)
    - `uv run pytest --collect-only -q tests/test_isolation.py` still successfully collects (no syntax errors introduced)
  </acceptance_criteria>
  <done>
    - `TargetConfig.tool_name` is `Optional[str]` with default `None`; `AliasChoices("TARGET_TOOL_NAME", "tool_name")` preserved
    - `field_validator(mode="before")` coerces empty/whitespace strings to `None`
    - `_preflight` skips membership-check when `config.target.tool_name is None`; preserves it when set
    - Existing tests do NOT yet pass after this task in isolation (target_tool fixture still resolves None) — that's expected; Task 2 fixes it. The codebase compiles + imports cleanly.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Add pytest_generate_tests discovery hook + rewrite target_tool fixture to indirect parametrize</name>
  <files>
    - tests/conftest.py
    - src/mcp_test_framework/fixtures.py
  </files>
  <read_first>
    - tests/conftest.py (current — full file, 42 lines)
    - src/mcp_test_framework/fixtures.py (lines 86-170 for _preflight; lines 320-340 for current target_tool)
    - src/mcp_test_framework/mcp_client.py (lines 135-180 for __aenter__ — confirm it builds its own tempdir + _build_isolated_env, Phase 06 D-16)
    - .planning/phases/07-multi-tool-discovery-and-parameterized-testing/07-RESEARCH.md (§Pattern 1, §Pattern 2, §Pitfall 5, §Code Example 1)
    - .planning/phases/07-multi-tool-discovery-and-parameterized-testing/07-PATTERNS.md (§"tests/conftest.py — ADD" + §"src/mcp_test_framework/fixtures.py — MODIFY target_tool")
    - .planning/phases/06-per-session-host-state-isolation/06-VERIFICATION.md (ISOL-03 spawn-site enumeration; do NOT regress)
  </read_first>
  <action>
**Edit 1: `tests/conftest.py` — append discovery hook below the existing `pytest_configure`.**

PRESERVE the existing top of the file verbatim (the docstring, `pytest_plugins = ["mcp_test_framework.fixtures"]` at line 12, the `import sys`, and the `pytest_configure` body at lines 17-42).

Augment the import block right after the `from __future__ import annotations` line (line 10). The new imports must be added AFTER the `pytest_plugins` line if needed (or carry an `# noqa: E402` comment matching the existing `import sys` style at line 14):

```python
# After line 14 (`import sys  # noqa: E402 -- pytest_plugins must be a top-level statement`),
# add the following imports as a single block:
import asyncio  # noqa: E402
from typing import Optional  # noqa: E402

import pytest  # noqa: E402

from mcp_test_framework.config import Config  # noqa: E402
from mcp_test_framework.mcp_client import McpTestClient  # noqa: E402
```

DO NOT import anything from `homelab_mcp` (would trip the sys.modules guard). DO NOT import `stdio_client` directly — discovery MUST go through `McpTestClient.__aenter__` to inherit Phase 06 isolation (D-11, D-16). Open-coding `stdio_client(...)` here would create a fourth (broken) spawn site.

Append (after the existing `pytest_configure` body):

```python
# ---------------------------------------------------------------------------
# Phase 07 — Tool discovery hook (pytest_generate_tests)
#
# Third spawn site (after _preflight in fixtures.py and mcp_client._owner_task).
# This site MUST NOT open-code stdio_client(...) — McpTestClient.__aenter__ is
# already isolation-aware as of Phase 06 D-16 (it builds its own per-instance
# tempdir + _build_isolated_env env block). Re-using __aenter__ inherits the
# isolation contract for free; ISOL-03 hash-equality test in tests/test_isolation.py
# remains the regression guard.
#
# Cache (CD-01: module-level dict over StashKey for simplicity).
# ---------------------------------------------------------------------------

_DISCOVERED_TOOL_NAMES: Optional[list[str]] = None


async def _discover_tools(config: Config) -> list[str]:
    """Brief MCP handshake -> list_tools -> tool names. Mirrors fixtures.py:142-148.

    Reuses McpTestClient.__aenter__ (Phase 06 D-16) so the spawned subprocess
    receives _build_isolated_env(<per-instance tempdir>) — Phase 06 ISOL-02/04/07
    contract preserved at this third spawn site (Phase 07 D-11).
    """
    async with McpTestClient(
        config.mcp_server.command,
        config.mcp_server.args,
        config.mcp_server.timeout_seconds,
    ) as client:
        tools = await client.list_tools()
    return [t.name for t in tools]


def _resolve_tool_names(config: Config) -> list[str]:
    """Resolve the parametrize tool-name list.

    - If config.target.tool_name is set (truthy after empty-string-to-None
      validator coercion in models.py): single-item list, NO collection-time
      spawn (CD-05 short-circuit).
    - Otherwise: discovered list, cached module-level for this pytest invocation.
    """
    global _DISCOVERED_TOOL_NAMES
    explicit = config.target.tool_name
    if explicit:
        return [explicit]
    if _DISCOVERED_TOOL_NAMES is None:
        try:
            _DISCOVERED_TOOL_NAMES = asyncio.run(_discover_tools(config))
        except Exception as exc:  # noqa: BLE001 -- mirrors _preflight failure-mode parity
            # Match _preflight failure shape (fixtures.py:149-154) for exit-code parity.
            # See 07-RESEARCH §Pitfall 5.
            pytest.exit(
                f"Tool discovery via {config.mcp_server.command!r} failed: "
                f"{exc.__class__.__name__}: {exc}",
                returncode=2,
            )
    return _DISCOVERED_TOOL_NAMES


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Inject indirect parametrize on `target_tool` for tests that request it.

    Discovery happens lazily — first test function that needs target_tool
    triggers the (cached) one-shot subprocess spawn. McpTestClient.__aenter__
    uses _build_isolated_env (Phase 06 D-16) so this spawn cannot leak state
    to ~/.homelab_mcp/ (ISOL-03 contract preserved).
    """
    if "target_tool" not in metafunc.fixturenames:
        return
    config = Config()
    names = _resolve_tool_names(config)
    metafunc.parametrize("target_tool", names, indirect=True, ids=names)
```

**Edit 2: `src/mcp_test_framework/fixtures.py` — rewrite `target_tool` (lines ~330-338).**

Replace the existing `target_tool` definition with the indirect-parametrize-aware shape (D-13):

OLD:
```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def target_tool(config: Config, mcp_client: McpTestClient, _preflight):
    """Resolve target tool by name; raises ToolNotFoundError if absent."""
    return await mcp_client.get_tool(config.target.tool_name)
```

NEW:
```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def target_tool(
    request: pytest.FixtureRequest,
    mcp_client: McpTestClient,
    _preflight,
):
    """Resolve target tool by name (parametrized indirectly via tests/conftest.py).

    The pytest_generate_tests hook in tests/conftest.py populates request.param
    with each discovered tool name. Test IDs render as test_<name>[<tool_name>]
    uniformly — including when config.target.tool_name is set (single-item
    parametrize list per D-05). Indirect parametrize on a session-scoped fixture
    creates one fixture instance per request.param value within session scope;
    mcp_client (also session-scoped) is shared — ONE long-lived MCP session.
    """
    return await mcp_client.get_tool(request.param)
```

Drop the `config: Config` parameter — the parametrize layer in conftest.py now owns the name source. `mcp_client.get_tool` preserves its `ToolNotFoundError` raise on race-condition mismatches (defense in depth).

`pytest` is already imported in fixtures.py (line 33 per analog reference); confirm before touching imports.
  </action>
  <verify>
    <automated>uv run pytest --collect-only -q 2>&amp;1 | head -50</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def pytest_generate_tests(metafunc:" tests/conftest.py` returns 1
    - `grep -c "asyncio.run(_discover_tools" tests/conftest.py` returns 1
    - `grep -c "async with McpTestClient(" tests/conftest.py` returns 1
    - `grep -c "stdio_client(" tests/conftest.py` returns 0 (forbidden — must reuse McpTestClient.__aenter__)
    - `grep -c "from homelab_mcp" tests/conftest.py` returns 0 (black-box rule)
    - `grep -c "import homelab_mcp" tests/conftest.py` returns 0 (black-box rule)
    - `grep -c "metafunc.parametrize(\"target_tool\"" tests/conftest.py` returns 1
    - `grep -c "indirect=True" tests/conftest.py` returns 1
    - `grep -c "ids=names" tests/conftest.py` returns 1
    - `grep -c "pytest.exit(" tests/conftest.py` returns 1 (failure-mode parity)
    - `grep -c "returncode=2" tests/conftest.py` returns 1
    - `grep -c "pytest_plugins = " tests/conftest.py` returns 1 (existing seam preserved)
    - `grep -c 'pytest_configure' tests/conftest.py` returns at least 1 (existing sys.modules guard preserved)
    - `grep -c "request.param" src/mcp_test_framework/fixtures.py` returns at least 1
    - `grep -c "await mcp_client.get_tool(request.param)" src/mcp_test_framework/fixtures.py` returns 1
    - `grep -c "async def target_tool" src/mcp_test_framework/fixtures.py` returns 1 (single definition)
    - `uv run python -c "import tests.conftest"` runs without error (no import cycles)
  </acceptance_criteria>
  <done>
    - Discovery hook added in `tests/conftest.py`; reuses `McpTestClient.__aenter__` (no open-coded `stdio_client`); failure path mirrors `_preflight` style (`pytest.exit(..., returncode=2)`)
    - CD-05 short-circuit honored: when `config.target.tool_name` is truthy, single-item list, NO spawn
    - `target_tool` fixture takes `request.param`; `config: Config` parameter removed
    - `pytest --collect-only` succeeds (or fails loudly with a `pytest.exit` diagnostic if the MCP server isn't on PATH — that's expected on machines without homelab-mcp)
    - After Task 3, the test bodies will be ready; until then, TEST-08/09/10 may break because they still reference `config.target.tool_name` directly. That's a transient state inside this plan, resolved by Task 3.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Rename test module and rewrite TEST-08/09/10 bodies to take target_tool</name>
  <files>
    - tests/test_homelab_list_registered_servers.py  # to be removed via git mv
    - tests/test_mcp_tool_contract.py                # rename target + body edits
  </files>
  <read_first>
    - tests/test_homelab_list_registered_servers.py (full file — confirm test names, line numbers, current bodies of TEST-08/09/10)
    - .planning/phases/07-multi-tool-discovery-and-parameterized-testing/07-RESEARCH.md (§Pattern 3 — "Tests that don't currently use target_tool" + §Pitfall 3)
    - .planning/phases/07-multi-tool-discovery-and-parameterized-testing/07-PATTERNS.md (§"tests/test_homelab_list_registered_servers.py -> tests/test_mcp_tool_contract.py" — exact OLD/NEW snippets)
  </read_first>
  <action>
**Step 1: Rename the module.**

```
git mv tests/test_homelab_list_registered_servers.py tests/test_mcp_tool_contract.py
```

(Use the GSD-supplied bash; on Windows this still resolves via git's POSIX shim. If `git mv` fails on the worktree, fall back to a plain `git rm tests/test_homelab_list_registered_servers.py` + `Write tests/test_mcp_tool_contract.py` with the new content — but `git mv` is preferred for blame continuity.)

**Step 2: Edit the renamed module to update TEST-08, TEST-09, TEST-10 + drop unused `Config` import.**

After the rename, edit `tests/test_mcp_tool_contract.py`:

(a) **Module docstring at the top of the file** — update to drop the "homelab-mcp / list_registered_servers" framing. Example replacement (preserve any existing high-level structure; only edit prose):
```python
"""Phase 4 + Phase 7 integration tests against the live MCP server.

Tests are parametrized over the discovered tool list (Phase 07 MULTI-01..04)
via tests/conftest.py's pytest_generate_tests hook. Test IDs render as
test_<name>[<tool_name>] uniformly. With TARGET_TOOL_NAME set, the run is
restricted to that tool (single-item parametrize list).
"""
```

(b) **Imports** (around lines 31-39) — remove the now-unused `Config` import:
```python
# DELETE this line if it exists:
from mcp_test_framework.config import Config
```
Keep all other imports (`json`, `pytest`, `Draft202012Validator`, `Judge`, `McpTestClient`, `validate_tool_schema`, etc.) verbatim.

(c) **TEST-08 (`test_empty_args_call_returns_non_error`)** — locate the function (currently around lines 165-171). Replace the OLD body:
```python
async def test_empty_args_call_returns_non_error(
    mcp_client: McpTestClient,
    config: Config,
) -> None:
    """TEST-08: call_tool with {} returns isError=False."""
    result = await mcp_client.call_tool(config.target.tool_name, {})
    assert not result.isError, f"call_tool returned isError=True: {result!r}"
```
with the NEW body (Pitfall 3 — add `target_tool`, drop `config`, replace `config.target.tool_name` with `target_tool.name`):
```python
async def test_empty_args_call_returns_non_error(
    mcp_client: McpTestClient,
    target_tool,
) -> None:
    """TEST-08: call_tool with {} returns isError=False.

    Per Phase 07 D-06: tools whose inputSchema.required is non-empty produce
    isError=True and fail this test visibly. Phase 08 (TOOLCFG-07) ships the
    user-facing skip mechanism; Phase 07 ships no auto-skip.
    """
    result = await mcp_client.call_tool(target_tool.name, {})
    assert not result.isError, f"call_tool returned isError=True: {result!r}"
```

(d) **TEST-09 (`test_result_has_content_or_structured`)** — locate the function (currently around lines 174-182). Apply the same shape change:
- OLD signature: `async def test_result_has_content_or_structured(mcp_client: McpTestClient, config: Config) -> None:`
- NEW signature: `async def test_result_has_content_or_structured(mcp_client: McpTestClient, target_tool) -> None:`
- Replace EVERY occurrence of `config.target.tool_name` in the body with `target_tool.name`
- Preserve the rest of the body verbatim (assertion logic on `result.content` / `result.structuredContent`).

(e) **TEST-10 (`test_text_content_parses_as_json`)** — locate the function (currently around lines 185-224). Already takes `target_tool` per RESEARCH §Pattern 3 row "Test-10". Apply:
- OLD signature includes `config: Config` parameter — REMOVE it.
- Replace EVERY occurrence of `config.target.tool_name` in the body with `target_tool.name`
- Preserve the rest of the body verbatim (JSON parse + judge call logic).

(f) **Do NOT modify TEST-01..TEST-07** (already fixture-driven, take `target_tool`, use `target_tool.<attr>`). The `pytestmark = [pytest.mark.asyncio(loop_scope="session")]` line stays single-marker — DO NOT add a `pytest.mark.parametrize(...)` here; the parametrize injection lives in conftest.py per CD-03.

**Note on rename mechanics:** `pyproject.toml`'s `testpaths = ["tests"]` is module-name-agnostic; no edit needed. README/docs do not reference the old filename (verified by RESEARCH §A4); no edit needed.
  </action>
  <verify>
    <automated>uv run pytest --collect-only -q tests/test_mcp_tool_contract.py</automated>
  </verify>
  <acceptance_criteria>
    - `git ls-files tests/test_homelab_list_registered_servers.py` returns empty (file no longer tracked under old name)
    - `git ls-files tests/test_mcp_tool_contract.py` returns the new path (file tracked under new name)
    - `grep -c "def test_empty_args_call_returns_non_error" tests/test_mcp_tool_contract.py` returns 1
    - `grep -c "def test_result_has_content_or_structured" tests/test_mcp_tool_contract.py` returns 1
    - `grep -c "def test_text_content_parses_as_json" tests/test_mcp_tool_contract.py` returns 1
    - `grep -c "config.target.tool_name" tests/test_mcp_tool_contract.py` returns 0 (all reads replaced with target_tool.name)
    - `grep -c "target_tool.name" tests/test_mcp_tool_contract.py` returns at least 3 (TEST-08, TEST-09, TEST-10)
    - `grep -c "from mcp_test_framework.config import Config" tests/test_mcp_tool_contract.py` returns 0 (unused import removed)
    - `grep -c "config: Config" tests/test_mcp_tool_contract.py` returns 0 (parameter dropped from all rewritten tests)
    - `grep -cE "pytestmark = \[pytest\.mark\.asyncio\(loop_scope=\"session\"\)\]" tests/test_mcp_tool_contract.py` returns 1 (single-marker preserved; no module-level parametrize)
    - `grep -c "pytest.mark.parametrize" tests/test_mcp_tool_contract.py` returns 0 (parametrize lives in conftest.py only)
    - `uv run pytest --collect-only -q tests/test_mcp_tool_contract.py 2>&1 | grep -E "\\[list_registered_servers\\]"` returns at least one match (assumes homelab-mcp on PATH at execution time; if not, this acceptance check is replaced by a manual run)
    - `uv run pytest --collect-only -q tests/test_mcp_tool_contract.py 2>&1 | grep -c "test_target_tool_exists\\["` returns at least 1
    - `uv run ruff check src tests` returns 0 errors (no unused imports, no TID251 violations)
    - Phase 06 isolation regression guard: `uv run pytest tests/test_isolation.py -x` passes (ISOL-03 hash-equality still holds; the new third spawn site inherits `_build_isolated_env` via `McpTestClient.__aenter__`)
  </acceptance_criteria>
  <done>
    - Module renamed via `git mv`; old path removed from index; new path tracked
    - TEST-08, TEST-09, TEST-10 take `target_tool` and use `target_tool.name`; `config: Config` parameter dropped
    - TEST-01..TEST-07 unchanged (already fixture-driven)
    - Module-level `pytestmark` is single-marker; parametrize lives in conftest.py only (CD-03)
    - `uv run pytest --collect-only -q tests/test_mcp_tool_contract.py` produces test IDs of the form `<test_name>[<tool_name>]` for at least one tool name (e.g. `list_registered_servers`) — MULTI-03 verified
    - With `TARGET_TOOL_NAME=list_registered_servers` set in env, the same `--collect-only` produces only `[list_registered_servers]` — MULTI-04 verified
    - With `TARGET_TOOL_NAME` unset, the run discovers all server-advertised tools — MULTI-01 + MULTI-02 verified
    - Phase 06 ISOL-03 still passes — Phase 06 isolation contract preserved at the new spawn site
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| pytest collection -> stdio MCP subprocess (homelab-mcp) | The discovery hook spawns the MCP server via `McpTestClient.__aenter__` and reads `tools = await client.list_tools()`. The server is a black-box subprocess under test; tool name strings cross the trust boundary into pytest's parametrize id list and downstream into pytest test names + JUnit XML. |
| MCP subprocess HOME -> user's real `~/.homelab_mcp/` | Phase 06 contract: `_build_isolated_env(<tempdir>)` overrides HOME/USERPROFILE so the subprocess cannot reach the user's real state. The new third spawn site (discovery hook) MUST inherit this contract — verified by reusing `McpTestClient.__aenter__` (which already calls `_build_isolated_env` per Phase 06 D-16). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-07-01 | Tampering | Discovery hook (`tests/conftest.py:_discover_tools`) | accept | A hostile MCP server returning a tool whose name contains `[`, `]`, `:`, `/`, or control characters could disrupt pytest's bracket-delimited ID parser or JUnit XML readers. Mitigation: pytest emits a loud collection-time warning for malformed IDs (Pitfall 4 in RESEARCH); failure mode is "test does not run" not "wrong test runs". Phase 08 (TOOLCFG-01 — per-tool config keys) is the right venue for a documented sanitization rule; Phase 07 punts. **Risk = LOW** for the v1.1 surface (homelab-mcp tool names are all snake_case; verified). |
| T-07-02 | Information Disclosure | Discovery hook spawn site | mitigate | A new spawn site that bypasses `_build_isolated_env` would let the subprocess read/write the user's real `~/.homelab_mcp/` state. Mitigation: discovery hook MUST reuse `McpTestClient.__aenter__` (Phase 06 D-16, isolation-aware); acceptance criterion `grep -c "stdio_client(" tests/conftest.py` returns 0 enforces the contract at code-review time. Phase 06 ISOL-03 hash-equality test in `tests/test_isolation.py` is the runtime regression guard. |
| T-07-03 | Denial of Service | Discovery hook (`asyncio.run` at collection time) | accept | A slow / hung MCP server could stall pytest collection. Mitigation: `McpTestClient.list_tools()` already wraps in `asyncio.timeout(self._timeout_seconds)` per `mcp_client.py:193`; the discovery hook inherits this. Configurable via `MCP_SERVER_TIMEOUT_SECONDS`. **Risk = LOW**; existing v1.0 timeout contract carries forward. |
| T-07-04 | Repudiation | `_preflight` D-15 surgical edit | accept | Skipping the membership check when `tool_name is None` is intentional (D-15) — the discovery hook produces the parametrize list, so a "not in list" check at preflight would be redundant. When `tool_name` IS set, membership check is preserved. No new repudiation risk. |
| T-07-05 | Spoofing | `TargetConfig.tool_name` empty-string-to-None validator | accept | A user with `TARGET_TOOL_NAME=` (empty) in `.env` gets the discover-all behavior (D-01) — explicit by design. The validator coerces `""` to `None` so `is None` checks downstream are robust (Pitfall 2). No spoofing risk introduced; existing `AliasChoices("TARGET_TOOL_NAME", "tool_name")` semantics preserved. |
| T-07-06 | Elevation of Privilege | None | n/a | Phase 07 introduces no privilege boundary changes. The discovery subprocess runs at the same privilege as the test session (unchanged from v1.0). Phase 06 isolation already constrains its filesystem reach. |

**Benign findings note:** Per ASVS L1, the threat surface for Phase 07 is small. Most threats are accepted because mitigations are inherited from Phase 06 (isolation), pytest's existing collection-time error handling, and the v1.0 MCP timeout contract. The only mitigation-required threat is T-07-02 (preventing a fourth, broken spawn site that bypasses `_build_isolated_env`), enforced at code-review time via the `grep -c "stdio_client("` acceptance criterion in Task 2 + the existing `tests/test_isolation.py::test_real_state_unchanged` runtime guard.
</threat_model>

<verification>

## Phase-level checks

After all three tasks complete, run:

1. **Collection check (default — discover all):**
   ```
   uv run pytest --collect-only -q tests/test_mcp_tool_contract.py
   ```
   Expected: test IDs of the form `<test_name>[<tool_name>]` for every tool the MCP server advertises (e.g. `test_schema_passes_structural_checks[list_registered_servers]`, `test_schema_passes_structural_checks[list_keyring_credentials]`, …).

2. **Backward-compat check (single-tool restriction):**
   ```
   TARGET_TOOL_NAME=list_registered_servers uv run pytest --collect-only -q tests/test_mcp_tool_contract.py
   ```
   (PowerShell syntax: `$env:TARGET_TOOL_NAME='list_registered_servers'; uv run pytest --collect-only -q tests/test_mcp_tool_contract.py`)

   Expected: only `[list_registered_servers]` IDs appear; no other tool names.

3. **Phase 06 isolation regression guard:**
   ```
   uv run pytest tests/test_isolation.py -x
   ```
   Expected: passes. The new third spawn site (discovery hook) inherits `_build_isolated_env` via `McpTestClient.__aenter__`; user's real `~/.homelab_mcp/` is unchanged.

4. **Lint:**
   ```
   uv run ruff check src tests
   ```
   Expected: 0 errors. No unused `Config` import; no TID251 (homelab-mcp import) violations; no `stdio_client` open-coded in `tests/conftest.py`.

5. **Black-box rule:**
   ```
   grep -nE "^(import|from)\s+homelab_mcp" tests/conftest.py src/mcp_test_framework/fixtures.py src/mcp_test_framework/models.py
   ```
   Expected: no matches.

## Acceptance: ROADMAP Phase 07 success criteria

- ✅ Criterion 1: With no `target.tool_name` set, every advertised tool produces N test cases per test function — verified by collection check #1.
- ✅ Criterion 2: Test IDs render as `<test_name>[<tool_name>]` in pytest terminal — verified by collection check #1 (and Phase 09 will verify JUnit XML parity).
- ✅ Criterion 3: With `target.tool_name` set, run is restricted to that tool — verified by check #2.
- ✅ Criterion 4: Discovery happens at collection time via `pytest.mark.parametrize` (no codegen) — verified by code reading + check #1.

</verification>

<success_criteria>

Phase 07 plan complete when:

- [ ] `tests/conftest.py` contains `pytest_generate_tests`, `_discover_tools`, `_resolve_tool_names`, and a module-level `_DISCOVERED_TOOL_NAMES` cache
- [ ] Discovery hook does NOT contain `stdio_client(` (must reuse `McpTestClient.__aenter__`)
- [ ] Discovery hook does NOT import any `homelab_mcp` symbol (black-box rule)
- [ ] Discovery hook wraps `asyncio.run(...)` in `try/except` and calls `pytest.exit(..., returncode=2)` on failure (parity with `_preflight` style)
- [ ] CD-05 short-circuit: when `config.target.tool_name` is truthy, single-item list, no spawn
- [ ] `src/mcp_test_framework/models.py:TargetConfig.tool_name` is `Optional[str]` with default `None`; `field_validator(mode="before")` coerces empty/whitespace strings to `None`; `AliasChoices("TARGET_TOOL_NAME", "tool_name")` preserved
- [ ] `src/mcp_test_framework/fixtures.py:_preflight` membership check is conditional on `config.target.tool_name is not None`
- [ ] `src/mcp_test_framework/fixtures.py:target_tool` takes `request.param` and `mcp_client.get_tool(request.param)`; `config: Config` parameter removed
- [ ] `tests/test_homelab_list_registered_servers.py` is renamed to `tests/test_mcp_tool_contract.py` via `git mv`
- [ ] TEST-08, TEST-09, TEST-10 take `target_tool` and use `target_tool.name`; `config: Config` parameter dropped from all three; unused `Config` import removed
- [ ] TEST-01..TEST-07 unchanged
- [ ] `pytest --collect-only -q` produces `[<tool_name>]`-suffixed IDs (MULTI-03)
- [ ] With `TARGET_TOOL_NAME=list_registered_servers`, only `[list_registered_servers]` IDs appear (MULTI-04 backward-compat)
- [ ] With `TARGET_TOOL_NAME` unset, all advertised tools are parametrized (MULTI-01 + MULTI-02)
- [ ] `tests/test_isolation.py` still passes (ISOL-03 — Phase 06 invariant preserved at new spawn site)
- [ ] `uv run ruff check src tests` returns 0 errors

</success_criteria>

<output>

After completion, create `.planning/phases/07-multi-tool-discovery-and-parameterized-testing/07-01-SUMMARY.md` with:

- **affects**: `tests/conftest.py`, `src/mcp_test_framework/models.py`, `src/mcp_test_framework/fixtures.py`, `tests/test_mcp_tool_contract.py`
- **provides**: Multi-tool discovery + parametrize at collection time; `[<tool_name>]` test IDs; backward compat with `TARGET_TOOL_NAME` set
- **patterns**: `pytest_generate_tests` + indirect parametrize; reuse of `McpTestClient.__aenter__` for new spawn sites (inherits Phase 06 isolation contract); empty-string-to-None Pydantic v2 validator at the env-config boundary
- **decisions**: D-01..D-17 + CD-01 (module-level dict cache), CD-03 (hook in conftest.py, not module pytestmark), CD-04 (`test_mcp_tool_contract.py`), CD-05 (short-circuit when `tool_name` set), CD-06 (single cohesive plan)
- **gotchas**: TEST-08/09/10 needed body rewrite (Pitfall 3); empty-string env-var coercion (Pitfall 2); discovery is a third spawn site under Phase 06 contract (D-11)

</output>
