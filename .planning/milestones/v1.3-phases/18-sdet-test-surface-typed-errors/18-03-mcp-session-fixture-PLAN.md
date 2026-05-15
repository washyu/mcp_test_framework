---
phase: 18-sdet-test-surface-typed-errors
plan: 03
type: execute
wave: 3
depends_on: [18-02]
files_modified:
  - src/mcp_test_framework/sdet/session.py
autonomous: true
requirements: [SDET-03, SDET-04]
must_haves:
  truths:
    - "mcp_session is a pytest-asyncio session-scoped fixture (loop_scope='session', scope='session')"
    - "mcp_session yields the existing McpTestClient (D-01 alias — no duplicate stdio_client/ClientSession lifecycle)"
    - "On entry, mcp_session activates the per-server generated registry (D-02 5-step flow)"
    - "On teardown, mcp_session restores prior _ACTIVE_SLUG / _ACTIVE_CLIENT and pops the registry entry"
    - "ModuleNotFoundError on import_module triggers _pytest_exit_operator_tone with returncode=2 (D-03)"
    - "No anyio CancelScope is opened across the yield (Phase 04.1 invariant preserved)"
  artifacts:
    - path: "src/mcp_test_framework/sdet/session.py"
      provides: "mcp_session async fixture; D-02 registry activation; D-03 fail-loud"
      exports: ["mcp_session"]
  key_links:
    - from: "session.py:mcp_session"
      to: "fixtures.py:mcp_client + _pytest_exit_operator_tone"
      via: "import + dependency-injected fixture parameter"
      pattern: "from mcp_test_framework.fixtures import.*mcp_client.*_pytest_exit_operator_tone"
    - from: "session.py:mcp_session"
      to: "_tool_factory._ACTIVE_SLUG / _ACTIVE_CLIENT / _REGISTRIES"
      via: "module-attribute mutation around yield"
      pattern: "_tf\\._ACTIVE_(SLUG|CLIENT)\\s*="
    - from: "session.py:mcp_session"
      to: "_slugs.server_slug"
      via: "slug derivation from serverInfo.name"
      pattern: "from mcp_test_framework.sdet._slugs import server_slug"
---

<objective>
Ship the `mcp_session` fixture as a new module `src/mcp_test_framework/sdet/session.py`. The fixture is a pytest-asyncio session-scoped wrapper around the existing `mcp_client` fixture (D-01 alias / re-export — NO duplicate `stdio_client` / `ClientSession` lifecycle introduced). Around the yield it performs the D-02 registry-activation flow (5 steps: read `serverInfo.name`, slugify, `importlib.import_module`, read `_REGISTRY`, install into `_REGISTRIES[slug]` + set `_ACTIVE_SLUG` + set `_ACTIVE_CLIENT`). On teardown it restores prior state and pops the registry entry. On `ModuleNotFoundError` it fails loud via `_pytest_exit_operator_tone` with the D-03 message shape and `returncode=2`.

Critical invariant (Phase 04.1): The D-02 mutations are SYNC (`importlib.import_module` + dict mutation + attribute assignment), so NO new anyio cancel scope is opened across the yield.

Purpose: This is the runtime piece that activates the Phase 17 codegen seam. After this plan, `tool(name).call(params)` works end-to-end inside an SDET test that requests the `mcp_session` fixture.

Output: One new file (`src/mcp_test_framework/sdet/session.py`).
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
@.planning/phases/18-sdet-test-surface-typed-errors/18-PATTERNS.md
@.planning/phases/18-sdet-test-surface-typed-errors/18-02-SUMMARY.md
@src/mcp_test_framework/sdet/_tool_factory.py
@src/mcp_test_framework/sdet/_slugs.py
@src/mcp_test_framework/fixtures.py

<interfaces>
<!-- D-03 fail-loud helper signature — fixtures.py:57-81 -->
```python
def _pytest_exit_operator_tone(
    summary: str,
    detail: list[str],
    next_step: str,
    *,
    returncode: int = 2,
) -> typing.NoReturn: ...
```

<!-- mcp_client fixture signature — fixtures.py:324 -->
```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_client(config: Config, _preflight, _isolated_home: Path) -> AsyncIterator[McpTestClient]: ...
```

<!-- _slugs.server_slug signature -->
```python
def server_slug(server_name: str) -> str: ...
# e.g. "homelab-mcp" -> "homelab_mcp"
```

<!-- Phase 18 mcp_session target — from 18-PATTERNS.md lines 298-344 -->
```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_session(mcp_client: McpTestClient):
    server_name = mcp_client._session.server_info.name
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
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create sdet/session.py with mcp_session fixture (D-01/D-02/D-03)</name>
  <files>src/mcp_test_framework/sdet/session.py</files>
  <read_first>
    - src/mcp_test_framework/fixtures.py lines 57-81 (_pytest_exit_operator_tone helper — signature, parts-assembly shape, mirroring cli._emit_operator_error)
    - src/mcp_test_framework/fixtures.py lines 324-410 (mcp_client fixture — decorator, signature, anyio-owner-task plumbing, NoReturn yield shape, cancel-scope invariant note)
    - src/mcp_test_framework/sdet/_slugs.py (server_slug function — single source of truth for serverInfo.name -> slug)
    - src/mcp_test_framework/sdet/_tool_factory.py (verify _ACTIVE_CLIENT slot exists from Plan 18-02; the slot names this fixture mutates)
    - src/mcp_test_framework/sdet/generated/homelab_mcp/__init__.py (verify the `_REGISTRY: dict[str, tuple[type[BaseModel], type[ToolResponse]]]` attribute shape this fixture reads)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-CONTEXT.md (D-01 lines 42; D-02 lines 44-51; D-03 lines 53-61; cancel-scope invariant lines 240-241)
    - .planning/phases/18-sdet-test-surface-typed-errors/18-PATTERNS.md (target body lines 298-344; the lock notes at lines 346-349)
  </read_first>
  <behavior>
    - Test: `mcp_session` is decorated with `@pytest_asyncio.fixture(loop_scope="session", scope="session")` (introspect `_pytestfixturefunction` marker).
    - Test: signature is `async def mcp_session(mcp_client: McpTestClient)` (depends on `mcp_client` fixture by name; pytest-asyncio resolves the chain).
    - Test: when `mcp_client._session.server_info.name == "homelab-mcp"`, the fixture body slugifies to `"homelab_mcp"` and calls `importlib.import_module("mcp_test_framework.sdet.generated.homelab_mcp")`.
    - Test: with that import succeeding (real generated module exists in repo), after entering the fixture body `_tf._ACTIVE_SLUG == "homelab_mcp"`, `_tf._ACTIVE_CLIENT is mcp_client`, AND `_tf._REGISTRIES["homelab_mcp"]` is the generated `_REGISTRY` dict.
    - Test: after exiting the fixture (teardown completes), `_tf._ACTIVE_SLUG` and `_tf._ACTIVE_CLIENT` are restored to their prior values, AND `_tf._REGISTRIES.pop("homelab_mcp", None)` was called (registry entry gone).
    - Test: when `importlib.import_module` raises `ModuleNotFoundError` (mocked), the fixture calls `pytest.exit` (via `_pytest_exit_operator_tone`) with `returncode=2` and the message contains ALL of: "No generated SDET classes", the slug, `gen-sdet-classes`, AND `--sdet`.
    - Test: the fixture yields `mcp_client` (so tests can `async def test_x(mcp_session): await mcp_session.call_tool(...)`).
  </behavior>
  <action>
Create `src/mcp_test_framework/sdet/session.py` with the exact shape from 18-PATTERNS.md lines 298-344. Module structure:

**1. Module docstring** referencing Phase 18 decisions:
- D-01: alias / re-export of session-scoped `mcp_client` (NO duplicate stdio_client/ClientSession lifecycle).
- D-02: registry activation lives in fixture body. 5 steps: read `serverInfo.name` from the live session, slugify via `_slugs.server_slug`, `importlib.import_module("mcp_test_framework.sdet.generated.<slug>")`, read `_REGISTRY` attribute, install into `_REGISTRIES[slug]` + set `_ACTIVE_SLUG` + set `_ACTIVE_CLIENT`. Yield. On teardown, restore prior state.
- D-03: ModuleNotFoundError -> `_pytest_exit_operator_tone` with returncode=2.
- Phase 04.1 invariant: D-02 mutations are SYNC (`importlib.import_module` + dict + attribute assignment). NO new anyio cancel scope opened across the yield.

**2. Imports (in this order):**
```python
from __future__ import annotations

import importlib

import pytest_asyncio

from mcp_test_framework.fixtures import _pytest_exit_operator_tone
from mcp_test_framework.mcp_client import McpTestClient
from mcp_test_framework.sdet import _tool_factory as _tf
from mcp_test_framework.sdet._slugs import server_slug
```

Do NOT import `mcp_client` (the fixture function) at the top — pytest-asyncio resolves the dependency by parameter name, not by import.

**3. The fixture body — VERBATIM from 18-PATTERNS.md lines 298-344:**

```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_session(mcp_client: McpTestClient):
    """Live ClientSession driver + active SDET registry (D-01/D-02/D-03).

    D-01: This fixture is the SDET surface's alias for the framework-wide
    `mcp_client` fixture. Tests under tests/sdet/ depend on `mcp_session`
    (operator-readable name); under the hood it IS `mcp_client` plus the
    D-02 registry activation. No duplicate stdio_client / ClientSession
    lifecycle is introduced.

    D-02: Around the yield this fixture performs the 5-step registry
    activation. The mutations are SYNC (importlib.import_module + dict
    mutation + attribute assignment). NO anyio cancel scope is opened
    across the yield — Phase 04.1 invariant preserved.

    D-03: ModuleNotFoundError raises `pytest.exit` via the operator-tone
    helper with returncode=2 (CI distinguishes from test failures). The
    message names the missing slug, the gen-sdet-classes command, and the
    --sdet flag — operator scans for these.
    """
    # Step 1+2: server name -> slug (single source of truth: _slugs.server_slug).
    server_name = mcp_client._session.server_info.name
    slug = server_slug(server_name)

    # Step 3+4: import the generated module; D-03 fail-loud on ModuleNotFoundError.
    try:
        mod = importlib.import_module(
            f"mcp_test_framework.sdet.generated.{slug}"
        )
    except ModuleNotFoundError:
        _pytest_exit_operator_tone(
            summary=(
                f"No generated SDET classes found for server {slug!r} "
                f"(from serverInfo.name={server_name!r})."
            ),
            detail=[
                f"  The fixture tried to `import "
                f"mcp_test_framework.sdet.generated.{slug}` and the module "
                "does not exist.",
                "  This usually means `gen-sdet-classes` has not been run "
                "for this server, or the server's name changed.",
            ],
            next_step=(
                "run `mcp-test-framework gen-sdet-classes` against this "
                "server first, then re-run with --sdet"
            ),
        )

    # Step 5: install registry + active slug + active client. Save priors.
    registry = getattr(mod, "_REGISTRY")
    prior_slug = _tf._ACTIVE_SLUG
    prior_client = _tf._ACTIVE_CLIENT
    _tf._REGISTRIES[slug] = registry
    _tf._ACTIVE_SLUG = slug
    _tf._ACTIVE_CLIENT = mcp_client

    try:
        yield mcp_client
    finally:
        # Step 7: restore prior state. Pop registry only if we installed it.
        _tf._ACTIVE_SLUG = prior_slug
        _tf._ACTIVE_CLIENT = prior_client
        _tf._REGISTRIES.pop(slug, None)
```

**Critical access pattern:** `mcp_client._session.server_info.name` — `McpTestClient._session` is the live `mcp.ClientSession`, and `ClientSession.server_info` is set after the initialize handshake completes. If the wrapper exposes a public accessor (e.g. `mcp_client.server_info`), prefer that; if not, use the underscore-prefixed `_session` directly (the wrapper itself exposes `_session` for transport-level reuse — see `_tool_factory.py:Phase 18 wire body` which uses `_ACTIVE_CLIENT.call_tool` going through the public method).

Verify by reading `src/mcp_test_framework/mcp_client.py` whether `McpTestClient` exposes a `server_info` property; if it does, USE THAT instead of `_session.server_info.name`. Document the chosen accessor in the docstring.

**Do NOT:**
- Open a new anyio CancelScope (Phase 04.1 invariant).
- Re-implement stdio_client / ClientSession lifecycle.
- Re-implement slug rules (use `_slugs.server_slug` only).
- Make this fixture `autouse=True` (it's depended on explicitly by SDET tests).
- Catch any exception other than `ModuleNotFoundError` during the import step (the other steps' errors should propagate so test failures are visible).
- Pop the registry on failure paths where you DIDN'T install it (the `try/finally` correctly only runs the cleanup after the install succeeded — keep the structure verbatim).
  </action>
  <verify>
    <automated>uv run python -c "import inspect; from mcp_test_framework.sdet.session import mcp_session; sig = inspect.signature(mcp_session.__wrapped__ if hasattr(mcp_session, '__wrapped__') else mcp_session); assert 'mcp_client' in sig.parameters, sig.parameters; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - File exists: `src/mcp_test_framework/sdet/session.py`
    - `grep -c "async def mcp_session" src/mcp_test_framework/sdet/session.py` returns 1
    - `grep -c "@pytest_asyncio.fixture(loop_scope=.session., scope=.session.)" src/mcp_test_framework/sdet/session.py` returns 1
    - `grep -c "import importlib" src/mcp_test_framework/sdet/session.py` returns 1
    - `grep -c "from mcp_test_framework.fixtures import _pytest_exit_operator_tone" src/mcp_test_framework/sdet/session.py` returns 1
    - `grep -c "from mcp_test_framework.sdet._slugs import server_slug" src/mcp_test_framework/sdet/session.py` returns 1
    - `grep -c "from mcp_test_framework.sdet import _tool_factory as _tf" src/mcp_test_framework/sdet/session.py` returns 1
    - `grep -c "importlib.import_module" src/mcp_test_framework/sdet/session.py` returns 1
    - `grep -c "except ModuleNotFoundError" src/mcp_test_framework/sdet/session.py` returns 1
    - `grep -c "_pytest_exit_operator_tone" src/mcp_test_framework/sdet/session.py` returns at least 1
    - `grep -c "_tf._ACTIVE_SLUG = slug" src/mcp_test_framework/sdet/session.py` returns 1
    - `grep -c "_tf._ACTIVE_CLIENT = mcp_client" src/mcp_test_framework/sdet/session.py` returns 1
    - `grep -c "_tf._REGISTRIES\\[slug\\] = registry" src/mcp_test_framework/sdet/session.py` returns 1
    - `grep -c "_tf._REGISTRIES.pop(slug, None)" src/mcp_test_framework/sdet/session.py` returns 1
    - `grep -c "yield mcp_client" src/mcp_test_framework/sdet/session.py` returns 1
    - `grep -cE "with anyio\\.|CancelScope" src/mcp_test_framework/sdet/session.py` returns 0 (Phase 04.1 invariant — no new cancel scope)
    - `grep -c "No generated SDET classes" src/mcp_test_framework/sdet/session.py` returns 1
    - `grep -c "gen-sdet-classes" src/mcp_test_framework/sdet/session.py` returns 1
    - `grep -c "\\-\\-sdet" src/mcp_test_framework/sdet/session.py` returns 1
    - `grep -c "try:" src/mcp_test_framework/sdet/session.py` returns 2 (one around import_module, one around yield)
    - `grep -c "finally:" src/mcp_test_framework/sdet/session.py` returns 1 (teardown restoration)
    - `uv run python -c "from mcp_test_framework.sdet.session import mcp_session; print('OK')"` exits 0
    - `uv run pyright src/mcp_test_framework/sdet/session.py` returns 0 errors
  </acceptance_criteria>
  <done>
    `src/mcp_test_framework/sdet/session.py` exists, the `mcp_session` fixture matches D-01/D-02/D-03 verbatim, mutates `_tf._ACTIVE_SLUG`/`_ACTIVE_CLIENT`/`_REGISTRIES` correctly around the yield, fails loud on ModuleNotFoundError with returncode=2, and opens NO new anyio cancel scope.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| MCP server -> framework | `serverInfo.name` originates from the server-under-test; flows into `importlib.import_module(f"...{slug}")`. |
| Generated code -> framework | `_REGISTRY` attribute of the generated module is `dict[str, tuple[type[BaseModel], type[ToolResponse]]]`; produced by `gen-sdet-classes`. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-18-08 | T (Tampering) | `importlib.import_module(f"mcp_test_framework.sdet.generated.{slug}")` | mitigate | `slug` passes through `_slugs.server_slug` which normalizes to `[a-z0-9_]+` only (single source of truth); no path traversal possible because dotted module paths in `import_module` resolve via `sys.path` packages, not filesystem paths; the parent package `mcp_test_framework.sdet.generated` constrains the search space to a single directory. |
| T-18-09 | D (DoS) | `mcp_client._session.server_info.name` | accept | Server name is bounded by MCP protocol (typically ≤ 64 chars); slug derivation is O(N) over the name. |
| T-18-10 | E (Elevation) | Module-state mutations on `_tf._ACTIVE_*` | accept | Process-local state; `try/finally` ensures restoration on test-failure paths; no privilege boundary crossed. |
</threat_model>

<verification>
- `uv run pytest tests/framework/unit/test_sdet_fixtures.py -x` passes (Plan 18-08 pins D-01/D-02/D-03 in this file).
- `uv run pytest tests/sdet/test_basic_call.py -x` passes after Plan 18-07 ships the sanity test (verifies end-to-end registry activation against the real generated `homelab_mcp` module).
- Module is pyright-strict-clean.
</verification>

<success_criteria>
- `from mcp_test_framework.sdet.session import mcp_session` resolves.
- `mcp_session` is a `pytest_asyncio.fixture(loop_scope="session", scope="session")`.
- Around the yield, `_tf._ACTIVE_SLUG`, `_tf._ACTIVE_CLIENT`, and `_tf._REGISTRIES[slug]` are set; on teardown, all three are restored / popped.
- ModuleNotFoundError on the import step triggers `pytest.exit` with returncode=2 and the operator-readable message shape.
- No new anyio CancelScope is opened across the yield.
</success_criteria>

<output>
After completion, create `.planning/phases/18-sdet-test-surface-typed-errors/18-03-SUMMARY.md` documenting: the fixture shape, the chosen `serverInfo.name` access path (public accessor vs `_session.server_info.name`), the 5-step activation flow, and the dependency Plan 18-04 inherits (re-export `mcp_session` through `sdet/__init__.py`).
</output>
