# Authoring SDET scenarios for your MCP server

This doc walks an SDET through authoring a scenario test file under
`tests/sdet/test_<name>.py` against a connected MCP server. The flow covers
codegen regeneration, importing typed `Params` / `Response` classes, writing
the first wire call, sharing state across tests with a module-scope yield
fixture, ordering tests across files, and skipping cleanly when a dependency
is unreachable. The SDET persona is distinct from the operator's contract
pass: operators run the schema/judge/output sweep against every discovered
tool; SDETs author targeted lifecycle scenarios that exercise stateful tool
sequences end-to-end.

## Prerequisites

- A configured MCP server (a working `config.yaml`; see `docs/EXTENDING.md`
  for the bootstrap flow).
- `mcp-test-framework` installed in the project's `uv` environment
  (`uv sync` once, then `uv run mcp-test-framework --help`).
- A `tests/sdet/` directory at the repo root. The framework's runner
  discovers SDET scenarios from this scope only.
- Tests are async-only under `pytest-asyncio` strict mode. Every SDET test
  carries an explicit `@pytest.mark.asyncio(loop_scope="session")` marker —
  the session-scoped `mcp_session` fixture requires its consumers to share
  the session loop, and a bare `@pytest.mark.asyncio` will hang at the wire
  boundary.

## Regenerating codegen

Regenerate the typed `Params` / `Response` classes whenever the MCP server's
declared tool schemas change upstream. The classes are derived from the
server's live `inputSchema` / `outputSchema` at gen time, so a server-side
field rename or type change shows up as drift in the regenerated module the
moment you re-run the generator.

```bash
uv run mcp-test-framework gen-sdet-classes
```

The generator overwrites ONLY the
`src/mcp_test_framework/sdet/generated/<server_slug>/` tree — nothing else in
the working tree is touched. Every generated file carries a `do not
hand-edit` header at the top; if you need to extend a generated class with a
helper, subclass it in your own scenario file rather than editing the
generated source.

The change-detection signal is your type checker. After a regen, run
`mypy` or `pyright` over `tests/sdet/`. Drift between your scenario code and
the regenerated classes surfaces as a type error at the call site that needs
updating — `CreateProxmoxVmParams(...)` rejects a removed field, or a
renamed `.data["vmid"]` access fails on the new response shape. The
typecheck failure tells you exactly where the contract moved.

The import surface is the stable contract across regens. Import paths
(`from mcp_test_framework.sdet.generated.<server_slug> import <ClassName>`)
do not change when the schema underneath does; only the internal field set
of each class changes. Pin your imports against the import surface, and let
the type checker tell you which call sites need adjustment.

## Importing generated Params and Response classes

The SDET surface is two namespaces. The first is
`mcp_test_framework.sdet`, which exposes the runtime symbols
(`mcp_session`, `tool`, `ToolCallError`). The second is the per-server
generated module under `mcp_test_framework.sdet.generated.<server_slug>`,
which exposes one `Params` and one `Response` class per discovered tool.

```python
from mcp_test_framework.sdet import mcp_session, tool, ToolCallError
from mcp_test_framework.sdet.generated.homelab_mcp import (
    CreateProxmoxVmParams,
    CreateProxmoxVmResponse,
)
```

`<ToolName>Params` is a Pydantic `BaseModel` whose fields are derived from
the tool's live `inputSchema`. Constructing one
(`CreateProxmoxVmParams(node="pve", name="...", ...)`) validates the
arguments against the server's declared contract before any wire call is
made — missing required fields and wrong-type values are caught as
`ValidationError` at construction, not as an error response from the
server.

`<ToolName>Response` is a `ToolResponse` subclass that exposes a uniform
attribute set regardless of whether the tool declared an `outputSchema`:

- `.raw` — the live `mcp.types.CallToolResult`.
- `.data` — `.raw.structuredContent` as a dict when present, else `{}`.
- `.text` — concatenated `TextContent.text` blocks from `.raw.content`.
- `.is_error` — `.raw.isError`.

Tools without an `outputSchema` get a stub `Response` class with the same
uniform attributes — the SDET-side access pattern (`response.data["vmid"]`)
does not need to know whether the underlying tool declared an output shape.

## Writing your first test

Start with one async test that calls a tool and asserts the result is not an
error. The two load-bearing pieces are the `mcp_session` fixture (which
brings up the stdio MCP server, completes the handshake, and activates the
generated registry) and the `tool("name")` factory (which returns a typed
`ToolWrapper` whose `.call()` validates inputs and routes the wire call).

```python
import pytest
from mcp_test_framework.sdet import mcp_session, tool
from mcp_test_framework.sdet.generated.homelab_mcp import CreateProxmoxVmParams


@pytest.mark.asyncio(loop_scope="session")
async def test_create_returns_pending_vm(mcp_session):
    params = CreateProxmoxVmParams(
        node="pve",
        name="mcptf-dogfood-first-test",
        cores=1,
        memory=512,
    )
    response = await tool("create_proxmox_vm").call(params)
    assert response.is_error is False
    print(response.data.get("vmid"))
```

The `loop_scope="session"` argument on `@pytest.mark.asyncio` is required.
`mcp_session` is session-scoped, and pytest-asyncio's strict mode pins
fixtures to a specific event loop — a bare `@pytest.mark.asyncio` marker
binds the test to a new loop that cannot share streams with the session
fixture, and the wire call hangs at the first `await`.

## Sharing state across tests with a module-scope yield fixture

When a scenario spans multiple tests (create a resource, modify it, delete
it), the canonical pattern is a module-scope async yield fixture that owns a
typed state dataclass. The fixture creates the resource at setup,
`yield`s the state object to its consumers, and runs teardown in a
`finally:` block. Cleanup-on-failure is pytest-native: if any test
consuming the fixture raises, the `finally` still executes.

```python
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from mcp_test_framework.sdet import mcp_session, tool
from mcp_test_framework.sdet.generated.homelab_mcp import (
    CreateProxmoxVmParams,
    CreateProxmoxVmResponse,
    DeleteProxmoxVmParams,
    ManageProxmoxVmParams,
    ManageProxmoxVmResponse,
)


@dataclass
class ProxmoxVmLifecycleState:
    """Per-module scenario state threaded across the three lifecycle tests."""
    created: CreateProxmoxVmResponse
    modified: ManageProxmoxVmResponse | None = None


@pytest_asyncio.fixture(scope="module", loop_scope="session")
async def proxmox_vm_lifecycle(mcp_session):
    """Create a VM at setup, yield the state, delete at teardown."""
    name = f"mcptf-dogfood-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    created = await tool("create_proxmox_vm").call(
        CreateProxmoxVmParams(node="pve", name=name, cores=1, memory=512)
    )
    state = ProxmoxVmLifecycleState(created=created)
    try:
        yield state
    finally:
        vmid = state.created.data.get("vmid")
        if vmid is not None:
            try:
                await tool("delete_proxmox_vm").call(
                    DeleteProxmoxVmParams(node="pve", vmid=vmid)
                )
            except Exception:
                # best-effort cleanup; a real-test failure still surfaces.
                pass
```

The three tests below run top-to-bottom in file order. Within a single
module, pytest collects tests in source order and does not require ordering
markers; the create / modify / delete sequence is implicit in the file
layout.

```python
@pytest.mark.asyncio(loop_scope="session")
async def test_create_returns_pending_vm(proxmox_vm_lifecycle):
    state = proxmox_vm_lifecycle
    assert state.created.is_error is False
    assert state.created.data.get("vmid") is not None


@pytest.mark.asyncio(loop_scope="session")
async def test_modify_accepts_cpu_increase(proxmox_vm_lifecycle):
    state = proxmox_vm_lifecycle
    vmid = state.created.data["vmid"]
    state.modified = await tool("manage_proxmox_vm").call(
        _CpuBumpManageVmParams(node="pve", vmid=vmid, action={"type": "config", "cores": 2})
    )
    assert state.modified.is_error is False


@pytest.mark.asyncio(loop_scope="session")
async def test_delete_returns_ok(proxmox_vm_lifecycle):
    state = proxmox_vm_lifecycle
    vmid = state.created.data["vmid"]
    response = await tool("delete_proxmox_vm").call(
        DeleteProxmoxVmParams(node="pve", vmid=vmid)
    )
    assert response.is_error is False
```

The `state.created` field is set at fixture setup and visible to every
consuming test; `state.modified` is written by `test_modify_accepts_cpu_increase`
and read (transitively) by the teardown path. The module-scope of the
fixture means all three tests see the same `state` instance — that is the
mechanism by which intermediate values flow between tests in the same
file.

## The inputSchema workaround (and why the framework does not mask it)

The `_CpuBumpManageVmParams` subclass referenced in
`test_modify_accepts_cpu_increase` above is a deliberate escape hatch. Some
upstream MCP servers (homelab-mcp 1.7.0 included) declare an
`inputSchema` that is self-contradictory: optional fields declared
`type: "string"` (without `"null"`) AND defaulted to `null` in the same
schema. The framework's Pydantic-generated `ManageProxmoxVmParams` is
`extra="forbid"` (matching the declared schema), which prevents transporting
an action payload like `{"type": "config", "cores": 2}` through the wire.

The escape hatch is a per-scenario subclass with `extra="allow"`:

```python
from pydantic import ConfigDict
from mcp_test_framework.sdet.generated.homelab_mcp import ManageProxmoxVmParams


class _CpuBumpManageVmParams(ManageProxmoxVmParams):
    """Local override for the homelab-mcp inputSchema contradiction.

    Upstream homelab-mcp declares optional fields as type:string (without
    "null") but defaults them to null in the same schema -- self-contradictory.
    The base ManageProxmoxVmParams is extra="forbid" per the declared schema
    and rejects the action payload below; this subclass relaxes that one
    constraint without leaking outside this scenario.
    """
    model_config = ConfigDict(extra="allow")
```

Three observations on this pattern:

1. **Upstream is the bug.** The server should either declare
   `type: ["string", "null"]` for the optional fields, or strip null-valued
   keys from its inbound payload before its own jsonschema check. The
   framework correctly reflects the server's declared `extra="forbid"` shape
   — the workaround belongs to the scenario, not to the framework.

2. **The framework does not paper over upstream bugs.** Adding
   `exclude_none=True` to `tool().call()` would silently drop null fields
   and mask the upstream contradiction — and it would also prevent SDETs
   from testing the server's null-handling edge cases when they want to.
   This is the SEED-022 principle: framework primitives; SDET owns safety.
   The framework wraps tool calls; the SDET decides which payloads to send.
   See the in-repo memory file
   `project_framework_primitives_sdet_safety_principle.md` for the full
   statement of the principle.

3. **The escape hatch lives in the scenario file.** A `_CpuBump*` subclass
   in `tests/sdet/test_proxmox_vm_lifecycle.py` is local to the workaround
   it enables. The framework's role is to surface upstream contract
   violations as test failures; the SDET's role is to decide whether to
   work around an upstream bug, file it, or fail loudly. Both are valid
   choices, and both stay visible at the scenario boundary.

## Ordering across files

The framework ships no custom cross-file ordering mechanism. Single-file
scenarios (the canonical idiom) rely on pytest's file-order collection:
tests run top-to-bottom within one module without any markers.

If your scenario spans multiple files (e.g., a provision step in one
file and a drive step in another), add `pytest-order` to YOUR project's
dev dependencies (NOT this framework's) and annotate tests with
`@pytest.mark.order(N)`.

### Worked example

```python
# tests/sdet/test_provision.py
import pytest
import pytest_asyncio

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def provisioned_vm(mcp_session):
    # ... create VM, yield handle, teardown ...
    yield {"vmid": 9990}

@pytest.mark.order(1)
@pytest.mark.asyncio(loop_scope="session")
async def test_provision(provisioned_vm):
    assert provisioned_vm["vmid"] is not None
```

```python
# tests/sdet/test_drive.py
import pytest

@pytest.mark.order(2)
@pytest.mark.asyncio(loop_scope="session")
async def test_drive(provisioned_vm):
    # provisioned_vm is the same session-scoped instance from test_provision.
    # @pytest.mark.order(2) guarantees this runs AFTER test_provision even
    # though it lives in a different file.
    assert provisioned_vm["vmid"] is not None
```

### Why this is not framework-internal

- The framework itself ships no SDET scenarios, so the framework's own
  dependencies never include `pytest-order`.
- Promoting this recipe to a project dep is an opt-in operator decision.

## Skipping when dependencies are unreachable

The framework owns no probe primitives. Whether a scenario should run
against the current environment is the SDET's call, not the framework's:
the author defines a `_probe()` callable, wires it into
`@pytest.mark.skipif`, and the scenario SKIPs when the probe returns
`False`. This is the SEED-022 principle — framework primitives; SDET owns
safety — recorded in the in-repo memory file
`project_framework_primitives_sdet_safety_principle.md`. A framework that
shipped reachability helpers for "proxmox", "ollama", or "ssh" would have
to keep growing to match every SDET's infrastructure; keeping `_probe()`
author-defined keeps that pressure where it belongs.

The canonical recipe is an env-var-gated TCP reachability probe:

```python
import os
import socket
import pytest

def _probe() -> bool:
    """Return True iff Proxmox is reachable, else False."""
    host = os.environ.get("MCPTF_DOGFOOD_PROXMOX_HOST")
    if not host:
        return False
    try:
        with socket.create_connection((host, 22), timeout=2):
            return True
    except OSError:
        return False

@pytest.mark.skipif(
    not _probe(),
    reason="Proxmox host unreachable (set MCPTF_DOGFOOD_PROXMOX_HOST)",
)
@pytest.mark.asyncio(loop_scope="session")
async def test_create_returns_pending_vm(proxmox_vm_lifecycle):
    ...
```

### Reason-string convention

Reason strings MUST name the missing dependency in operator-domain terms
AND the env var the operator sets to enable the test. SKIP rows under the
framework's default operator output (`_render_per_tool_rows`) surface the
reason string directly — consistent phrasing keeps the operator-facing
output readable across many scenarios in the same suite. Two examples:

- `reason="Proxmox host unreachable (set MCPTF_DOGFOOD_PROXMOX_HOST)"`
- `reason="Ollama judge offline (set MCPTF_OLLAMA_HOST and start the daemon)"`

Both name the dependency in operator language ("Proxmox host", "Ollama
judge") and the env var to set, so an operator reading the SKIP row in the
test summary knows exactly what to change to opt in.

### Other probe shapes

For tools where the wire call itself is cheap (no slow handshake, no
expensive setup), an env-var presence check is enough — skip the TCP probe
entirely:

```python
def _probe() -> bool:
    return bool(os.environ.get("MCPTF_DOGFOOD_PROXMOX_HOST"))
```

If you want to gate on whether the MCP server itself advertises the tool
you intend to call (the server may have stopped exposing it across
versions), probe the live capability surface via `mcp_session`:

```python
async def _probe(mcp_session) -> bool:
    """Skip unless the target MCP server actually advertises the tool."""
    tools = await mcp_session.list_tools()
    return any(t.name == "create_proxmox_vm" for t in tools)
```

This shape does not wire directly into `@pytest.mark.skipif`, because the
marker evaluates at collection time — before `mcp_session` has been set
up. The practical pattern is to call the capability probe inside fixture
setup and `pytest.skip(reason=...)` from there:

```python
@pytest_asyncio.fixture(scope="module", loop_scope="session")
async def proxmox_vm_lifecycle(mcp_session):
    if not await _probe(mcp_session):
        pytest.skip("create_proxmox_vm not advertised by the server")
    # ... rest of fixture ...
```

The hello-world MCP server fixture planned in the next section will let
many of today's infrastructure-bound scenarios run unconditionally in CI,
which means fewer `_probe()` callables overall. Until then,
author-defined probes are the canonical way to keep scenarios honest in
both live and CI environments.

## Failure handling: ToolCallError

When the MCP server returns `result.isError = True`, `tool().call()` raises
`ToolCallError` instead of returning a `Response`. The exception exposes
four attributes:

- `.tool` — the MCP tool name (string).
- `.code` — the server-supplied error code, or `None` if absent.
- `.message` — a human-readable error message extracted from the result.
- `.raw` — the live `mcp.types.CallToolResult` (not a Pydantic clone).

Under the framework's default operator output, FAIL rows surface
`.code` / `.message` via the em-dash detail pattern established in Phase 16
(`FAIL test_name — [CODE] message`). Under `--debug`, the raw
`CallToolResult` payload lands in the appendix block for the failing test.

The wiring that surfaces `ToolCallError` fields into the JUnit XML is
already in place: `tests/sdet/conftest.py` ships a `pytest_exception_interact`
hook that writes the four attributes into the test's
`user_properties` on the JUnit node. SDETs do not modify this file — the
hook is framework infrastructure that every authored scenario inherits.

## Future: CI-runnable scenarios

Scenarios that depend on live operator infrastructure (a Proxmox cluster, a
reachable SSH host, an Ollama daemon) currently SKIP in CI. A future v1.x
phase will ship a small hello-world MCP server fixture inside this repo —
hand-crafted to cover the surface dimensions every codegen-generated
wrapper has to handle (required and optional params, scalars and arrays,
declared and undeclared `outputSchema`) — as the canonical home for
CI-runnable scenarios that exercise the full SDET wiring without operator
infrastructure. Until that fixture ships, the canonical pattern for keeping
infrastructure-bound scenarios honest in CI is the conditional skip recipe
in the section above.

## Further reading

- `docs/EXTENDING.md` — operator-side knobs (rubrics, judge backend, env passthrough).
- `README.md` — operator quickstart and the `## SDET scenarios` sample.
- Generated module: `src/mcp_test_framework/sdet/generated/<server_slug>/`.
