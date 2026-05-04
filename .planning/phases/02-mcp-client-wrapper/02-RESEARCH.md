# Phase 2: MCP Client Wrapper - Research

**Researched:** 2026-05-04
**Domain:** Async MCP stdio client wrapper around the official Python SDK (`mcp 1.27.0`)
**Confidence:** HIGH

## Summary

Phase 2 ships `src/mcp_test_framework/mcp_client.py` -- a thin async lifecycle wrapper around `mcp.client.stdio.stdio_client` + `mcp.ClientSession` exposing the spec interface (`__aenter__`/`__aexit__`, `list_tools`, `get_tool`, `call_tool`). The SDK already does most of the dangerous work correctly: Windows command resolution via `shutil.which` with `PATHEXT` walk, Job-Object-backed subprocess for child-process cleanup on Windows, graceful stdin-close-then-SIGTERM-then-SIGKILL escalation on teardown, and an internal `anyio.fail_after` per request honored via `read_timeout_seconds`. The wrapper's job is therefore narrow: own the `AsyncExitStack` so `stdio_client` and `ClientSession` enter and exit in the same task (Pitfall 1 mitigation), wrap every SDK call in `asyncio.timeout(self._timeout_seconds)` (Pitfall 5 belt that runs alongside the SDK's internal one), route the `errlog` TextIO to a stdlib logger, surface a domain `ToolNotFoundError`, and normalize Windows command resolution before handing the command string to `StdioServerParameters`.

A second deliverable is a permanent live-marker pytest at `tests/smoke/test_smoke_homelab_mcp.py` (D-01) that doubles as Phase 2's success criteria #1 and #2 falsifier. The marker `live_homelab` is registered in `pyproject.toml` and added to `addopts = "-m 'not live_homelab'"` so default `uv run pytest` skips it (D-03).

**One critical CONTEXT.md correction surfaced by source inspection:** CONTEXT.md "Subprocess cleanup belt" claims `stdio_client exposes the Process reference` so the wrapper can `process.kill()` from a finalizer. This is false in `mcp 1.27.0`: `stdio_client` yields only `(read_stream, write_stream)` and the underlying `Process` is held inside an internal `anyio.create_task_group()` -- callers cannot reach it. See **Open Questions Q1** -- the planner needs a decision on whether the 5s belt is dropped, replaced with a different mechanism (Windows-only `taskkill /F` shell-out keyed off `MCP_SERVER_COMMAND`), or accepted as redundant given the SDK already runs SIGTERM->SIGKILL on a 2.0s timer via `_terminate_process_tree` (`PROCESS_TERMINATION_TIMEOUT = 2.0`).

**Primary recommendation:** Implement the wrapper as ~80 LOC: `__aenter__` builds `StdioServerParameters`, opens the SDK contexts via `AsyncExitStack`, runs `initialize` under `asyncio.timeout`; `list_tools`/`get_tool`/`call_tool` are one-line wrappers each adding `async with asyncio.timeout(self._timeout_seconds)`; `errlog` is a small file-like adapter that writes lines to `logging.getLogger("mcp_test_framework.mcp_client.stderr").warning(...)`. Drop the 5s force-kill belt (or convert to the Windows-only `taskkill` fallback) once Q1 is resolved.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Smoke harness lives as a permanent live-marker pytest test**
- **D-01:** The Phase-2 smoke harness is a real pytest test at `tests/smoke/test_smoke_homelab_mcp.py` -- NOT a throwaway script under `scripts/`. It is committed and re-runnable indefinitely as part of the project's live-integration smoke pack.
- **D-02:** Marker convention: `@pytest.mark.live_homelab`. Any test using this marker requires the `homelab-mcp` binary on `PATH` and a reachable subprocess; missing -> test fails fast inside the test body, not at collection.
- **D-03:** Default-skip mechanism: pure pytest `addopts`, no env var, no conftest hook. Locked into `[tool.pytest.ini_options]` in `pyproject.toml`:
  ```toml
  markers = [
    "live_homelab: requires live homelab-mcp on PATH",
  ]
  addopts = "-m 'not live_homelab'"
  ```
  - `uv run pytest` skips live tests (default for unit/CI runs)
  - `uv run pytest -m live_homelab` runs live tests only
  - `uv run pytest -m ''` overrides to run everything
- **D-04:** The smoke test must cover BOTH Phase 2 success criteria #1 and #2:
  - SC#1: a function that uses raw `stdio_client` + `ClientSession` directly, lists tools, and asserts `list_registered_servers` is present with a non-empty schema (matches roadmap wording "without ever importing homelab_mcp")
  - SC#2: a function that drives `McpTestClient` (the wrapper this phase is shipping), calls `call_tool("list_registered_servers", {})`, and asserts `not result.isError` and that `content` or `structuredContent` is non-empty
  Whether these are one or two test functions is a planner detail; both criteria must be falsifiable in the test file.

**Single timeout knob on McpServerConfig**
- **D-05:** Add ONE new field to `McpServerConfig`:
  ```python
  timeout_seconds: int = Field(
      default=30,
      ge=1,
      validation_alias=AliasChoices("MCP_SERVER_TIMEOUT_SECONDS", "timeout_seconds"),
  )
  ```
  Mirrors `OllamaConfig.timeout_seconds` shape. Frozen sub-model + `populate_by_name=True` already locked at the class level -- no new pattern.
- **D-06:** The same `timeout_seconds` ceiling wraps all three SDK call sites (`session.initialize`, `session.list_tools`, `session.call_tool`). 30s default is a ceiling, not a minimum -- fast paths complete quickly; pathological hangs surface as `TimeoutError` after 30s rather than indefinitely. Per-call separate knobs are deferred.
- **D-07:** Documentation/examples updated to support D-05:
  - `.env.example` adds `MCP_SERVER_TIMEOUT_SECONDS=30`
  - `config.example.yaml` adds `mcp_server.timeout_seconds: 30` (next to `command` / `args`)
  - At least one Phase 1-style precedence test in `tests/unit/test_config.py` MUST exercise `MCP_SERVER_TIMEOUT_SECONDS` env routing through `_BareNameNestedEnvSource` -- Phase 1 lesson "EnvSettingsSource does not walk sub-model validation_alias" applies; the new field needs the same coverage shape as `OLLAMA_TIMEOUT_SECONDS`.
- **D-08:** `McpTestClient.__init__` signature: `__init__(self, command: str, args: list[str], timeout_seconds: int)` -- additive over the spec's `(command, args)` wording; smallest-diff change. Phase 4 fixture wires it as `McpTestClient(cfg.mcp_server.command, cfg.mcp_server.args, cfg.mcp_server.timeout_seconds)`.

### Claude's Discretion
- **Error semantics on `CallToolResult.isError=true`:** Pass-through. Tests in Phase 4 assert `not result.isError`.
- **Error semantics on `get_tool(name)` not found:** Raise a custom `ToolNotFoundError(tool_name, available=[...])` exception, defined in `mcp_client.py`.
- **Stderr capture target:** Plumb the SDK's `errlog` parameter to a stdlib logger named `mcp_test_framework.mcp_client.stderr` at `WARNING` level. No handlers attached by the wrapper -- pytest's log capture decides where the lines surface.
- **Subprocess cleanup belt:** `__aexit__` lets `AsyncExitStack` unwind in reverse order in the same task. Add a defensive 5-second guard that, on `__aexit__` not completing cleanly, force-kills the underlying subprocess. **NOTE: Q1 below documents that the SDK does NOT expose the Process reference -- this constraint as written cannot be implemented as described and needs planner re-decision.**
- **`get_tool` implementation:** Re-fetches via `list_tools()` each call -- no in-process cache.
- **Phase 2 unit tests scope:** `tests/unit/test_mcp_client.py` covers `ToolNotFoundError` payload shape; `tests/unit/test_config.py` adds the `MCP_SERVER_TIMEOUT_SECONDS` precedence test. Live timeout/subprocess behavior is exercised by `tests/smoke/test_smoke_homelab_mcp.py` only -- mocking `stdio_client` to assert "timeout fires" is high-cost / low-signal.
- **`shutil.which` resolution (Pitfall 14):** `McpTestClient.__aenter__` resolves `command` via `shutil.which()` before passing to `stdio_client`. If `which` returns `None`, raise a precise `FileNotFoundError("MCP server command not on PATH: <name>")`. **NOTE: The SDK already does this internally (see `get_windows_executable_command` in Code Examples) -- the wrapper's `which()` is now belt-and-suspenders, not strictly required. Decision logged here so the planner doesn't accidentally drop it.**
- **No `homelab_mcp` import anywhere in this phase's deliverables:** Phase 1's two-layer guard (ruff TID251 + `tests/conftest.py` `sys.modules` scan) catches violations mechanically. No additional measures needed.

### Deferred Ideas (OUT OF SCOPE)
- **Per-call timeout knobs (init / list / call separately).**
- **Smoke script as throwaway `scripts/` entry.**
- **`MCPTF_LIVE` env var gating** (marker-only via `addopts` is v1.0).
- **Custom CallToolResult validator wrapping** (`assert_successful(result) -> None` helper -- defer to Phase 4 if needed).
- **`McpTestClient(config: McpServerConfig)` constructor variant** -- keep positional `(command, args, timeout_seconds)`; add `from_config` classmethod later only if Phase 4 friction warrants.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CORE-03 | `mcp_client.py` exposes an async `McpTestClient` wrapping the official `mcp` SDK's `stdio_client` + `ClientSession` with `list_tools`, `get_tool`, and `call_tool`; every SDK call is wrapped in `asyncio.timeout()`; defensive handling of `CallToolResult.isError` and the `content` vs `structuredContent` shape variance | Standard Stack (mcp 1.27.0 verified-installed); Architecture Patterns (AsyncExitStack ownership, errlog adapter, asyncio.timeout coverage); Code Examples §"Lifecycle pattern", §"errlog adapter", §"call_tool with timeout"; Pitfalls §1, §4, §5, §12 covered. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Subprocess lifecycle (spawn/kill) | mcp SDK (`stdio_client` + `_terminate_process_tree`) | `McpTestClient.__aexit__` | SDK owns the Process via internal task group; wrapper only owns the `AsyncExitStack` that drives the SDK's CMs in the right task. |
| Windows command resolution (PATHEXT walk) | mcp SDK (`get_windows_executable_command`) | `McpTestClient.__aenter__` (belt) | SDK already does `shutil.which` with `.cmd/.bat/.exe/.ps1` extensions; wrapper's pre-`which` check is a friendlier early-error surface for missing binaries. |
| MCP handshake (initialize) | mcp SDK (`ClientSession.initialize`) | `McpTestClient.__aenter__` (timeout wrap) | SDK does the JSON-RPC dance; wrapper adds `asyncio.timeout` ceiling. |
| Per-RPC read timeout | mcp SDK (`anyio.fail_after` inside `send_request`) | `McpTestClient` (`asyncio.timeout` outer wrap) | SDK times out via `read_timeout_seconds`; wrapper's `asyncio.timeout` is the documented Pitfall-5 belt that catches stalls outside the SDK's request loop (e.g., during subprocess teardown races). |
| stderr routing | mcp SDK (`errlog: TextIO` parameter) | `McpTestClient` (TextIO->logger adapter) | SDK accepts any TextIO; wrapper supplies a thin `io.TextIOBase` subclass that flushes lines into a stdlib logger. |
| `CallToolResult` shape interpretation | Phase 4 tests (FIX-03, TEST-08, TEST-09) | `McpTestClient.call_tool` (pass-through) | Wrapper returns SDK's `CallToolResult` unchanged per Discretion decision; tests own shape assertions. |
| Tool-not-found diagnostic | `McpTestClient.get_tool` | Phase 4 `target_tool` fixture | Wrapper raises `ToolNotFoundError(name, available=[...])`; fixture catches for early-fail diagnostic. |
| Frozen config + env routing | Phase 1 `Config` / `_BareNameNestedEnvSource` | `McpServerConfig.timeout_seconds` (new field) | Phase 1 mechanism handles bare-name routing; new field plugs in via `AliasChoices`. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mcp | 1.27.0 | Official MCP Python SDK | The only authoritative MCP client for Python; already installed (verified `uv pip show mcp` -> 1.27.0); `requires-python >=3.10`, runs on 3.14 with no observed wheel issues; ships `stdio_client`, `ClientSession`, `StdioServerParameters`, full `mcp.types` model tree. [VERIFIED: `uv pip show mcp`, PyPI metadata 2026-05-04] |
| pytest-asyncio | >=1.3 (Phase 1 lock) | Strict-mode async test integration | Already configured `asyncio_mode = "strict"` + `asyncio_default_fixture_loop_scope = "session"` in `pyproject.toml` -- the smoke test inherits these defaults. [VERIFIED: pyproject.toml] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| anyio | transitive via mcp | task-group + memory streams | Do NOT import directly; the SDK uses it internally. The wrapper interacts with it only indirectly through `stdio_client`. [VERIFIED: source inspection of `stdio_client`] |
| pydantic | >=2.13,<3 (Phase 1 lock) | New `McpServerConfig.timeout_seconds` field | Same `Field(...) + AliasChoices` pattern as `OllamaConfig.timeout_seconds`. [VERIFIED: existing `models.py`] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `mcp` SDK `stdio_client` | Raw `asyncio.create_subprocess_exec` + hand-rolled JSON-RPC framing | Loses MCP handshake, capability negotiation, stdio framing, error mapping, Windows Job Object cleanup, and PATHEXT resolution. **Forbidden by spec.** [CITED: `docs/mcp_test_framework_mvp_spec.md` §Implementation Notes for Claude Code] |
| `asyncio.timeout()` (3.11+) | `asyncio.wait_for(...)` | `asyncio.timeout` is the modern context-manager API and the spec's explicit instruction. `wait_for` is the older callable form -- equivalent in semantics but less ergonomic and not what the spec prescribes. [CITED: spec §Implementation Notes; CLAUDE.md §Architecture Notes] |
| Wrapper with cached `list_tools` result | Re-fetch on every `get_tool` | One stdio round-trip per call vs cache invalidation complexity. **Discretion decision: re-fetch.** Phase 4's session fixture caches at the test layer anyway. |

### Verified Versions

```bash
$ uv pip show mcp
Name: mcp
Version: 1.27.0
```
Confirmed against PyPI: latest is 1.27.0, released 2026-04-02 (per https://pypi.org/pypi/mcp/json -- fetched 2026-05-04). `requires-python >=3.10`. Already locked in Phase 1 `pyproject.toml` as `mcp>=1.27`.

## Architecture Patterns

### System Architecture Diagram

```
+---------------------------------------------------------------+
|  Phase 4 fixture (FIX-01, session-scoped)                     |
|    async with McpTestClient(cmd, args, timeout) as client:    |
|      ...                                                      |
+--------------------------+------------------------------------+
                           | (entered in pytest session loop task)
                           v
+---------------------------------------------------------------+
|  McpTestClient.__aenter__   (this Phase)                      |
|                                                               |
|  AsyncExitStack owned by THIS task                            |
|    1. shutil.which(command) -> resolved path or FileNotFound  |
|    2. enter stdio_client(StdioServerParameters, errlog=adptr) |
|       -> (read_stream, write_stream)                          |
|    3. enter ClientSession(read, write)                        |
|    4. async with asyncio.timeout(timeout_seconds):            |
|         await session.initialize()                            |
|    5. yield self                                              |
+----+----------------------+-----------------------------------+
     |                      |
     | stdio (pipes)        | TextIO writes -> logger.warning
     v                      v
+----------------+   +-------------------------------------+
| homelab-mcp    |   | logging.getLogger(                  |
| subprocess     |   |   "mcp_test_framework.mcp_client    |
| (Job Object on |   |    .stderr")                        |
|  Windows)      |   +-------------------------------------+
+----------------+

McpTestClient.list_tools() / get_tool(name) / call_tool(name, args):
  async with asyncio.timeout(self._timeout_seconds):
      return await self._session.<method>(...)

McpTestClient.__aexit__:
  AsyncExitStack unwinds in reverse:
    - ClientSession (no special teardown beyond CM exit)
    - stdio_client: closes stdin -> waits 2.0s -> SIGTERM -> SIGKILL
                    (this is _terminate_process_tree's escalation;
                     on Windows it uses Job Objects, on POSIX killpg)
```

### Recommended Project Structure
```
src/mcp_test_framework/
├── mcp_client.py        # NEW Phase 2 — McpTestClient + ToolNotFoundError + _LoggerWriter
├── models.py            # MODIFY — add McpServerConfig.timeout_seconds field
├── config.py            # NO CHANGE — _BareNameNestedEnvSource picks up the new field automatically
├── schema_validator.py  # NO CHANGE
└── __init__.py          # NO CHANGE

tests/
├── conftest.py          # NO CHANGE
├── _fixtures/           # NO CHANGE
├── unit/
│   ├── test_config.py   # MODIFY — add MCP_SERVER_TIMEOUT_SECONDS precedence test
│   ├── test_mcp_client.py  # NEW — ToolNotFoundError payload + adapter unit tests (mock-friendly only)
│   └── ...
└── smoke/                  # NEW directory
    ├── __init__.py         # empty (or omit; pytest discovers .py files regardless)
    └── test_smoke_homelab_mcp.py   # NEW — D-01/D-04 live smoke (live_homelab marker)

pyproject.toml           # MODIFY — register live_homelab marker; addopts = "-m 'not live_homelab'"
.env.example             # MODIFY — add MCP_SERVER_TIMEOUT_SECONDS=30 (D-07)
config.example.yaml      # MODIFY — add mcp_server.timeout_seconds: 30 (D-07)
```

### Pattern 1: AsyncExitStack-owned lifecycle in the same task
**What:** `McpTestClient.__aenter__` builds an `AsyncExitStack`, enters both `stdio_client(...)` and `ClientSession(...)` into it, runs `initialize()`, and stores the stack on `self`. `__aexit__` calls `await self._stack.aclose()`. Both enter and exit happen in the same task (the one that runs `async with McpTestClient(...) as client:`), which is what anyio cancel scopes require.
**When to use:** Always, for this wrapper. It is the documented mitigation for Pitfall 1 (anyio cancel-scope error) until PEP 789 lands.
**Example:** see Code Examples §"Lifecycle pattern" below.

### Pattern 2: Belt-and-braces timeout (wrapper outer + SDK inner)
**What:** Every wrapper method does `async with asyncio.timeout(self._timeout_seconds): ...`. The SDK's `ClientSession.send_request` ALSO times out via `anyio.fail_after(read_timeout_seconds)` if you pass `read_timeout_seconds=timedelta(seconds=N)`. We do not pass `read_timeout_seconds` (CONTEXT.md does not call for it), so the SDK relies entirely on our outer `asyncio.timeout`.
**When to use:** Every method that calls into the SDK -- `initialize`, `list_tools`, `call_tool`. Use the same `self._timeout_seconds` ceiling for all three (D-06).
**Why both layers exist:** Pitfall 5 (server termination undetected -- `modelcontextprotocol/python-sdk#396`). The SDK's `anyio.fail_after` only fires once a request has been sent and is waiting for a response; if the wrapper itself stalls before the request reaches the wire, only the outer `asyncio.timeout` saves us.

### Pattern 3: TextIO -> logger adapter for `errlog`
**What:** `stdio_client(server, errlog=...)` accepts any `TextIO`. Subclass `io.TextIOBase` (only `write` and `flush` need real implementations) and route each line to `logging.getLogger("mcp_test_framework.mcp_client.stderr").warning(...)`. The SDK uses this `errlog` as the subprocess's stderr destination via `stderr=errlog` kwarg to `anyio.open_process` -- the OS writes the bytes directly to your file-like object's `write()`.
**When to use:** Always for this wrapper. Default `errlog=sys.stderr` would pollute pytest output and bypass capture/log-filtering.

### Pattern 4: Permanent live-marker smoke pytest
**What:** A real pytest at `tests/smoke/test_smoke_homelab_mcp.py` decorated with `@pytest.mark.live_homelab` and `@pytest.mark.asyncio(loop_scope="session")`. Skipped by default via `addopts = "-m 'not live_homelab'"`; opt-in via `uv run pytest -m live_homelab`.
**When to use:** Phase-2 acceptance verification AND any future hand-runnable smoke check against the live binary. Replaces the throwaway `scripts/smoke_*.py` pattern (D-01).

### Anti-Patterns to Avoid
- **`subprocess.Popen(['homelab-mcp', ...])`**: bypasses MCP handshake, framing, Windows Job Object lifecycle, and graceful shutdown. Forbidden by spec.
- **Storing `stdio_client(...)` CM on `self` and entering/exiting from different methods.** Pitfall 1 is the inevitable result. The wrapper's `AsyncExitStack` must enter and aclose in the same task.
- **Calling `session.call_tool(...)` without an outer `asyncio.timeout`.** Hangs forever on undetected server termination (Pitfall 5).
- **Naively asserting `len(result.content) > 0`.** Some servers populate only `structuredContent`. The wrapper MUST pass `CallToolResult` through unchanged; tests check `result.isError` first, then `content OR structuredContent` (Pitfall 12).
- **Importing `homelab_mcp` even for type hints.** Pitfall 8. The wrapper has no reason to -- it returns SDK types only.
- **Setting `errlog=open(somefile, 'w')` synchronously without closing.** Use the logger adapter or pass `sys.stderr`. The SDK does not own the lifecycle of the TextIO you give it.
- **Auto-resolving the YAML config path or auto-loading `.env` in the wrapper.** Phase 1 owns that via `Config.load()`; the wrapper takes `(command, args, timeout_seconds)` straight.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Subprocess spawn over stdio | `asyncio.create_subprocess_exec` + hand-rolled framing | `mcp.client.stdio.stdio_client` | MCP handshake, JSON-RPC framing, capability negotiation, error mapping, and Windows Job Object cleanup are all delivered by the SDK. [CITED: source inspection of `stdio_client`] |
| Windows command resolution | Custom PATHEXT walker | SDK's `get_windows_executable_command` (called by `_get_executable_command`) | Already walks `.cmd/.bat/.exe/.ps1`. Our wrapper's `shutil.which` is a friendlier pre-flight check, not a replacement. [VERIFIED: source `mcp.client.stdio.get_windows_executable_command`] |
| Subprocess force-kill / process-tree teardown | `os.kill`, `process.terminate()` ladder | SDK's `_terminate_process_tree` (Job Object on Windows, `killpg` on POSIX) | Already runs the SIGTERM->SIGKILL escalation on a 2.0s timer (`PROCESS_TERMINATION_TIMEOUT = 2.0`). [VERIFIED: source inspection] |
| Per-RPC timeout | Hand-rolled timer + cancellation | `asyncio.timeout(seconds)` (3.11+) outer + (optionally) SDK's `read_timeout_seconds=timedelta(...)` inner | Spec mandates `asyncio.timeout`; SDK already plumbs `anyio.fail_after` internally. [CITED: spec §Implementation Notes] |
| MCP types (Tool, CallToolResult, TextContent, ...) | Re-declare or wrap | Import from `mcp.types` | They are pydantic BaseModels with full discriminator unions. Wrapping adds friction with no benefit. |
| Loading `.env` and YAML | python-dotenv, hand-rolled YAML overlay | `Config` from Phase 1 (already loads everything) | The wrapper takes raw `(command, args, timeout_seconds)`; the fixture in Phase 4 reads them off `cfg.mcp_server`. |

**Key insight:** The SDK does ~95% of the dangerous work correctly. The wrapper's value is the *lifecycle ownership shape* -- ensuring `AsyncExitStack` enters and exits in the same task, layering `asyncio.timeout` over every call site, and routing `errlog` to a stdlib logger. Anything beyond that is duplication.

## Runtime State Inventory

> Phase 2 adds new code (`mcp_client.py`) and one new field (`McpServerConfig.timeout_seconds`). It is not a rename or migration phase. The relevant runtime state additions are:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None -- the wrapper holds no persistent state. | None. |
| Live service config | None at the framework layer. The `homelab-mcp` server itself may have its own state, but the framework treats it as a black-box subprocess (Pitfall 8). | None. |
| OS-registered state | Subprocess processes spawned by `stdio_client`. On Windows these are wrapped in a Job Object so OS cleanup happens automatically when the parent process exits even if `__aexit__` doesn't run. On POSIX they get a new session (`start_new_session=True`) so `killpg` reaps the whole tree. | The wrapper relies on the SDK's lifecycle -- no extra registration. |
| Secrets/env vars | New env var: `MCP_SERVER_TIMEOUT_SECONDS` (D-05). Picked up by Phase 1's `_BareNameNestedEnvSource` automatically once `AliasChoices` is set on the new `McpServerConfig.timeout_seconds` field. **No `config.py` change required**, only `models.py`. | Add `.env.example` line + `config.example.yaml` line per D-07; add precedence test per D-07. |
| Build artifacts / installed packages | New module file `src/mcp_test_framework/mcp_client.py`. No new packages -- `mcp 1.27.0` is already in deps. New tests directory `tests/smoke/`. | None beyond standard add-and-commit. |

## Common Pitfalls

(Subset of `.planning/research/PITFALLS.md` directly relevant to Phase 2 -- Pitfalls 1, 4, 5, 12, 14 from that document.)

### Pitfall 1: anyio cancel-scope on stdio_client teardown
**What goes wrong:** `RuntimeError: Attempted to exit cancel scope in a different task than it was entered in` during teardown. Most commonly when `mcp_client` fixture uses one loop scope and a test uses another, OR when the wrapper stores a CM on `self` and exits it from a different method.
**Why it happens:** `stdio_client` and `ClientSession` yield inside an `anyio.create_task_group()` cancel scope. anyio enforces same-task entry/exit.
**How to avoid:** `AsyncExitStack` owned by the same task that consumes the client. Pin loop scope at the build layer (Phase 1 already did: `asyncio_default_fixture_loop_scope = "session"`). Wrap `initialize()` in `asyncio.timeout`.
**Warning signs:** Test passes but `RuntimeError: Attempted to exit cancel scope...` appears in teardown output. `homelab-mcp.exe` still alive in Task Manager after pytest exits 0.

### Pitfall 4: Windows ProactorEventLoop subprocess cleanup races
**What goes wrong:** On Windows, the loop can close mid-teardown before the subprocess exits cleanly, leaking `homelab-mcp.exe`.
**Why it happens:** ProactorEventLoop uses IOCP; closing the loop mid-`__aexit__` strands subprocess termination IO.
**How to avoid:** Session-scoped event loop (already locked Phase 1) so the loop survives the entire test session. Trust the SDK's Job Object on Windows -- it kills the process tree even if Python doesn't explicitly call `kill()`. Document the manual recovery: `taskkill /F /IM homelab-mcp.exe`.
**Warning signs:** "Event loop is closed" in teardown traceback; first test of a re-run fails because something is "still holding port/pipe".

### Pitfall 5: Server termination undetected -- hangs forever
**What goes wrong:** If `homelab-mcp` crashes mid-`call_tool`, `await session.call_tool(...)` hangs indefinitely. Documented in `modelcontextprotocol/python-sdk#396`.
**How to avoid:** Mandatory `asyncio.timeout()` around every SDK call. Treat timeout as a test FAILURE, not a hang. Plumb stderr via `errlog` so the server's crash trace appears in test output.
**Warning signs:** Pytest progress dots stop with no output; manual Ctrl+C required.

### Pitfall 12: CallToolResult shape variance
**What goes wrong:** Tests that assume `result.content` is non-empty break against servers that populate only `structuredContent` (and vice versa). Tests that ignore `result.isError` miss tool-level failures.
**How to avoid:** Wrapper passes `CallToolResult` through unchanged (CONTEXT Discretion); tests check `not result.isError` first, then `content OR structuredContent`.
**Warning signs:** False-pass on a tool whose RPC succeeded but whose body was empty; assertions on `.content[0].text` against a server that uses structured content only.

### Pitfall 14: Windows path / extension handling
**What goes wrong:** `MCP_SERVER_COMMAND=homelab-mcp` (no extension) historically did not resolve via `asyncio.create_subprocess_exec` because PATHEXT wasn't consulted.
**How to avoid:** **Already handled by the SDK** as of `mcp 1.27.0` -- `get_windows_executable_command` does `shutil.which(command)` then walks `.cmd/.bat/.exe/.ps1`. The wrapper's pre-`which()` check is a friendlier early-error surface for the missing-binary case (returns `FileNotFoundError` with the bare name in the message vs the SDK's `[WinError 2] The system cannot find the file specified`).
**Warning signs:** Cryptic `[WinError 2]` instead of "MCP server command not on PATH: homelab-mcp".

## Code Examples

Verified patterns from official sources and source inspection of `mcp 1.27.0`.

### Lifecycle pattern (`McpTestClient.__aenter__` skeleton)
```python
# Source: source inspection of mcp.client.stdio.stdio_client (mcp 1.27.0)
# + Pitfall 1 mitigation pattern from .planning/research/PITFALLS.md

import asyncio
import io
import logging
import shutil
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import CallToolResult, Tool

_log = logging.getLogger("mcp_test_framework.mcp_client.stderr")


class _LoggerWriter(io.TextIOBase):
    """File-like adapter routing each written line to a stdlib logger at WARNING."""

    def __init__(self, logger: logging.Logger, level: int = logging.WARNING) -> None:
        self._logger = logger
        self._level = level
        self._buffer = ""

    def writable(self) -> bool:
        return True

    def write(self, s: str) -> int:
        self._buffer += s
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line.strip():
                self._logger.log(self._level, line.rstrip())
        return len(s)

    def flush(self) -> None:
        if self._buffer.strip():
            self._logger.log(self._level, self._buffer.rstrip())
            self._buffer = ""


class ToolNotFoundError(LookupError):
    def __init__(self, tool_name: str, available: list[str]) -> None:
        self.tool_name = tool_name
        self.available = available
        super().__init__(
            f"Tool {tool_name!r} not found. Available tools: {available!r}"
        )


class McpTestClient:
    def __init__(self, command: str, args: list[str], timeout_seconds: int) -> None:
        self._command = command
        self._args = list(args)
        self._timeout_seconds = timeout_seconds
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def __aenter__(self) -> "McpTestClient":
        # Pre-flight: friendly error for missing binary (belt over SDK's own which()).
        if shutil.which(self._command) is None:
            raise FileNotFoundError(
                f"MCP server command not on PATH: {self._command!r}"
            )
        params = StdioServerParameters(command=self._command, args=self._args)
        stack = AsyncExitStack()
        try:
            read, write = await stack.enter_async_context(
                stdio_client(params, errlog=_LoggerWriter(_log))
            )
            session = await stack.enter_async_context(ClientSession(read, write))
            async with asyncio.timeout(self._timeout_seconds):
                await session.initialize()
        except BaseException:
            await stack.aclose()
            raise
        self._stack = stack
        self._session = session
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        stack = self._stack
        self._stack = None
        self._session = None
        if stack is not None:
            await stack.aclose()

    async def list_tools(self) -> list[Tool]:
        assert self._session is not None, "McpTestClient not entered"
        async with asyncio.timeout(self._timeout_seconds):
            result = await self._session.list_tools()
        return list(result.tools)

    async def get_tool(self, name: str) -> Tool:
        tools = await self.list_tools()
        for tool in tools:
            if tool.name == name:
                return tool
        raise ToolNotFoundError(name, [t.name for t in tools])

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> CallToolResult:
        assert self._session is not None, "McpTestClient not entered"
        async with asyncio.timeout(self._timeout_seconds):
            return await self._session.call_tool(name, arguments)
```

### Smoke-test sketch (`tests/smoke/test_smoke_homelab_mcp.py`)
```python
# Source: D-01/D-04 in CONTEXT.md + Phase 2 success criteria #1 and #2

import asyncio
from contextlib import AsyncExitStack

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from mcp_test_framework.config import Config
from mcp_test_framework.mcp_client import McpTestClient

pytestmark = [pytest.mark.live_homelab, pytest.mark.asyncio(loop_scope="session")]


async def test_raw_stdio_lists_target_tool() -> None:
    """SC#1: raw stdio_client + ClientSession lists target tool with non-empty schema."""
    cfg = Config()
    params = StdioServerParameters(command=cfg.mcp_server.command, args=cfg.mcp_server.args)
    async with AsyncExitStack() as stack:
        read, write = await stack.enter_async_context(stdio_client(params))
        session = await stack.enter_async_context(ClientSession(read, write))
        async with asyncio.timeout(cfg.mcp_server.timeout_seconds):
            await session.initialize()
            result = await session.list_tools()
    target = cfg.target.tool_name
    names = [t.name for t in result.tools]
    assert target in names, f"{target!r} missing from {names!r}"
    target_tool = next(t for t in result.tools if t.name == target)
    assert isinstance(target_tool.inputSchema, dict) and target_tool.inputSchema, (
        f"{target!r} has empty inputSchema"
    )


async def test_wrapper_call_tool_returns_non_error_with_content() -> None:
    """SC#2: McpTestClient.call_tool returns isError=False with content/structuredContent."""
    cfg = Config()
    async with McpTestClient(
        cfg.mcp_server.command,
        cfg.mcp_server.args,
        cfg.mcp_server.timeout_seconds,
    ) as client:
        result = await client.call_tool(cfg.target.tool_name, {})
    assert not result.isError, f"call_tool returned isError=True: {result!r}"
    assert result.content or result.structuredContent, (
        f"both content and structuredContent empty: {result!r}"
    )
```

### `errlog` parameter wiring (verified from SDK source)
```python
# Source: mcp.client.stdio.stdio_client signature -- verified 2026-05-04
# def stdio_client(server: StdioServerParameters, errlog: TextIO = sys.stderr): ...
#
# The SDK passes errlog directly to anyio.open_process(stderr=errlog). The OS writes
# subprocess stderr bytes to errlog.write(...) on Windows and POSIX alike. The SDK does
# not close errlog -- caller owns the lifecycle.
#
# Therefore _LoggerWriter (above) only needs write() and flush() to be functional.
```

### `pyproject.toml` marker registration (D-03)
```toml
# Source: CONTEXT.md D-03 (locked)
[tool.pytest.ini_options]
asyncio_mode = "strict"
asyncio_default_fixture_loop_scope = "session"
testpaths = ["tests"]
markers = [
  "live_homelab: requires live homelab-mcp on PATH",
]
addopts = "-m 'not live_homelab'"
```

### `McpServerConfig.timeout_seconds` field addition (D-05)
```python
# Source: CONTEXT.md D-05 + Phase 1 OllamaConfig.timeout_seconds pattern (verbatim shape)
class McpServerConfig(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    command: str = Field(
        default="homelab-mcp",
        validation_alias=AliasChoices("MCP_SERVER_COMMAND", "command"),
    )
    args: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("MCP_SERVER_ARGS", "args"),
    )
    timeout_seconds: int = Field(  # NEW
        default=30,
        ge=1,
        validation_alias=AliasChoices("MCP_SERVER_TIMEOUT_SECONDS", "timeout_seconds"),
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `subprocess.Popen` + hand-framed JSON-RPC | `mcp.client.stdio.stdio_client` + `ClientSession` | mcp 0.x onward | Spec-mandated; non-negotiable. |
| `asyncio.wait_for(coro, timeout=...)` | `async with asyncio.timeout(timeout): coro` | Python 3.11+ | Spec uses `asyncio.timeout`; consistent across all wrappers. |
| Hand-rolled Windows command resolution | SDK's `get_windows_executable_command` (since well before 1.27) | mcp pre-1.20 | Wrapper's `shutil.which` becomes a UX upgrade only -- friendlier error message, not a correctness fix. |
| Per-test event loop in pytest-asyncio 0.x | Session-scoped event loop in pytest-asyncio 1.x | pytest-asyncio 1.0 (May 2025) | Already locked in Phase 1 `pyproject.toml`. The smoke test inherits via `loop_scope="session"`. |
| Hand-rolled `<think>` strip / format-mode handling | (out of scope -- Phase 3) | -- | -- |

**Deprecated/outdated:**
- `jsonschema.RefResolver` -- replaced by `referencing` (Pitfall 16). Phase 2 doesn't touch jsonschema directly, but the SDK's own `_validate_tool_result` uses `jsonschema.validate` via the `referencing` path on 4.18+.
- pytest-asyncio `event_loop` fixture -- removed in 1.0. Don't copy old StackOverflow snippets.
- pytest-asyncio `asyncio_mode = "auto"` -- the project is locked on `strict` (Phase 1).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The SDK's internal `PROCESS_TERMINATION_TIMEOUT = 2.0` is sufficient for `homelab-mcp` to shut down gracefully on stdin-close. | Pattern 1 / Architecture diagram | If `homelab-mcp` ignores stdin EOF and takes >2s to die, the SDK escalates to SIGKILL/Job-Object kill. Worst case is a 2s teardown delay -- well under the wrapper's `timeout_seconds` ceiling. Low risk. |
| A2 | Phase 4's session-scoped fixture using `loop_scope="session"` will not trip Pitfall 1 once paired with the AsyncExitStack ownership pattern shown above. | Pattern 1 | Validated indirectly by the smoke test running the full enter/exit cycle in one task. Phase 4 risk, not Phase 2. |
| A3 | `_LoggerWriter`'s line-buffering is acceptable -- subprocess stderr writes don't need to be flushed in real-time during tests, only by session end. | Code Examples §"Lifecycle pattern" | If a smoke test fails fast and the buffer holds a partial line at process kill, that final line may be lost. Low signal loss; acceptable. |
| A4 | The SDK's `call_tool` auto-validates `structuredContent` against the tool's `outputSchema` (verified in `_validate_tool_result` source). For Phase 2's smoke test, `list_registered_servers` either has no `outputSchema` or returns conformant structured content, so the smoke `call_tool` does not raise `RuntimeError("Invalid structured content...")`. | Architecture diagram | If `list_registered_servers` declares an `outputSchema` and returns non-conformant content, the smoke test fails with `RuntimeError`, not `assert not result.isError`. Either outcome falsifies the live binary's contract -- acceptable signal. Flagged for Phase 4 awareness. |

**If this table is empty:** N/A -- 4 assumptions logged above; none change Phase 2 deliverables.

## Open Questions

1. **CONTEXT.md "Subprocess cleanup belt" cannot be implemented as written.**
   - **What we know:** CONTEXT.md says: *"`stdio_client` exposes the `Process` reference -- capture it inside `__aenter__` and use `process.kill()` from a synchronous finalizer if needed"*. Source inspection of `mcp.client.stdio.stdio_client` (mcp 1.27.0) confirms `stdio_client` yields ONLY `(read_stream, write_stream)` -- the `Process` is held inside an internal `anyio.create_task_group()` and is not exposed to callers.
   - **What's unclear:** Three viable options for the planner to pick from:
     - **Option A:** Drop the 5s force-kill belt entirely. Trust the SDK's `_terminate_process_tree` (Job Object on Windows, `killpg` on POSIX, `PROCESS_TERMINATION_TIMEOUT = 2.0`). This is the simplest path and matches Phase 1's "trust the SDK" posture.
     - **Option B:** Keep the *intent* of the belt but reimplement it as a Windows-only `taskkill /F /IM <command>` shell-out gated by `if sys.platform == "win32"`. Bluntly kills any orphan process matching the command name -- effective but not surgical (could kill an unrelated `homelab-mcp` started in a different terminal).
     - **Option C:** Submit an upstream PR to expose the `Process` from `stdio_client`. Out of scope for this phase; mention as a SEED.
   - **Recommendation:** Option A. The SDK's existing escalation is documented and tested. The 5s belt was conceived for the case where `__aexit__` itself never returns; that scenario is already mitigated by the `asyncio.timeout` ceiling around `initialize()` (the only `__aenter__` call) and by the SDK's bounded `PROCESS_TERMINATION_TIMEOUT`. Add a Phase 5 README troubleshooting note documenting `taskkill /F /IM homelab-mcp.exe` as the manual recovery (already in the Discussion's spirit). Surface Option B as a fallback if a Phase 4 smoke run reveals real-world leaks.

2. **Is `homelab-mcp` actually on PATH on the dev machine that will run the live smoke?**
   - **What we know:** Right now, `shutil.which("homelab-mcp")` returns `None` on this developer's Windows 11 machine (verified 2026-05-04 via `uv run python -c "import shutil; print(shutil.which('homelab-mcp'))"`). A live smoke test will fail-fast inside the test body with `FileNotFoundError("MCP server command not on PATH: 'homelab-mcp'")`. This is the D-02 design ("missing -> test fails fast inside the test body, not at collection") so behaviorally correct -- but it means **`uv run pytest -m live_homelab` will fail on this machine until `homelab-mcp` is installed on PATH.**
   - **What's unclear:** Is `homelab-mcp` installed somewhere not on PATH (e.g., another venv), or is it not installed at all? Is there a planned `pipx install homelab-mcp` step that should be in the README?
   - **Recommendation:** Plan should include a Phase-2 README appendix or a `## Live smoke prerequisites` section documenting how to install `homelab-mcp` on PATH. Phase 5's full README will subsume this. The smoke test's `FileNotFoundError` message is already self-documenting; no extra error UX needed.

3. **`structuredContent` vs `content` for `list_registered_servers` -- which does the live tool actually use?**
   - **What we know:** Phase 2's SC#2 wording ("`content` or `structuredContent` is non-empty") accepts either. The wrapper passes both through.
   - **What's unclear:** If the live tool returns `structuredContent` only, the wrapper's `call_tool` triggers SDK auto-validation against `outputSchema` (per `_validate_tool_result`). If the schema is strict and the response shape drifts, the smoke fails with `RuntimeError`, not `result.isError=True`. Phase 4's TEST-09/TEST-10 will hit this surface harder.
   - **Recommendation:** Phase 2 doesn't need to predict; the smoke test simply needs to assert what's there. Phase 4 should re-research with the actual tool output in hand.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 | All deliverables | Yes | 3.14.3 | -- |
| uv | Install + run | Yes (project already uses it) | -- | -- |
| `mcp` package | Wrapper | Yes (installed) | 1.27.0 | -- |
| `pytest-asyncio` | Smoke test | Yes (Phase 1 dev dep) | per uv.lock | -- |
| `homelab-mcp` binary on PATH | Live smoke test (D-02) | **No** -- `shutil.which("homelab-mcp")` returns `None` on this dev machine | -- | Smoke test fails fast inside test body per D-02; default `uv run pytest` skips via `addopts = "-m 'not live_homelab'"`. Unit tests do NOT depend on this. |
| Windows 11 (target OS) | Subprocess lifecycle (Pitfall 4) | Yes | Windows 11 Home 26200 | -- |
| Console color / no extras | -- | -- | -- | -- |

**Missing dependencies with no fallback:** None for unit-test deliverables. `homelab-mcp` binary is missing for live smoke -- but D-02 explicitly designs around this (skip-by-default + fail-fast on opt-in). See Open Question Q2.

**Missing dependencies with fallback:** `homelab-mcp` -- fallback is "default-skip" via `addopts`.

## Project Constraints (from CLAUDE.md)

The CLAUDE.md "Architecture Notes" section restates invariants that bound Phase 2:

- **MCP transport is stdio only.** Use `stdio_client`, never raw `subprocess.Popen`. Phase 2 honors this -- the wrapper composes the SDK CMs.
- **`homelab-mcp` is a black box.** No imports from `homelab_mcp.*` anywhere in `src/` or `tests/`. Belt-and-suspenders: ruff TID251 + `tests/conftest.py` `sys.modules` scan (Phase 1 ships both).
- **Async-first; `asyncio.timeout` (3.11+) wraps every subprocess/HTTP op.** Phase 2's wrapper does this for all three SDK call sites with the same `self._timeout_seconds` ceiling (D-06).
- **Fixtures are session-scoped.** Phase 2 doesn't ship fixtures (Phase 4 does), but the wrapper must be compatible -- the AsyncExitStack ownership pattern is precisely what enables session-scoped use.
- **GSD workflow enforcement:** all file edits go through GSD execute. Phase 2 deliverables ship via `/gsd-execute-phase`.
- **Python 3.14 + `uv` (pinned).** Phase 2 adds no new top-level deps; only a new field in `models.py`.

These directives are mutually consistent with CONTEXT.md decisions D-01..D-08. No contradictions.

## Sources

### Primary (HIGH confidence -- source inspection of installed `mcp 1.27.0`)
- `mcp.client.stdio.stdio_client` source -- yields `(read_stream, write_stream)`; accepts `errlog: TextIO = sys.stderr`; uses internal `anyio.create_task_group()` and `process` CM with `_terminate_process_tree(process)` on stdin-close timeout (`PROCESS_TERMINATION_TIMEOUT = 2.0`).
- `mcp.client.stdio.get_windows_executable_command` source -- does `shutil.which` then walks `.cmd/.bat/.exe/.ps1`.
- `mcp.client.stdio._terminate_process_tree` source -- delegates to `terminate_windows_process_tree` (Job Object) or `terminate_posix_process_tree` (`killpg`).
- `mcp.ClientSession.__init__` signature -- `read_timeout_seconds: timedelta | None = None`; supports per-session and per-request timeouts via `read_timeout_seconds` (used internally by `BaseSession.send_request` -> `anyio.fail_after`).
- `mcp.ClientSession.call_tool` source -- runs `_validate_tool_result` against the tool's `outputSchema` after non-error responses; raises `RuntimeError("Invalid structured content returned by tool ...")` on mismatch.
- `mcp.types.CallToolResult` model fields -- `content: list[TextContent | ImageContent | AudioContent | ResourceLink | EmbeddedResource]` (required), `structuredContent: dict | None = None`, `isError: bool = False`, `meta: dict | None`.
- `mcp.types.Tool` (verified Phase 1) -- pydantic validator rejects `inputSchema=None` at construction.

### Primary (HIGH confidence -- official sources)
- PyPI metadata for `mcp` -- latest `1.27.0` released 2026-04-02; `requires-python >=3.10`; classifies through 3.13 (no observed issues on 3.14, confirmed by Phase 1 `uv sync`). [VERIFIED: https://pypi.org/pypi/mcp/json fetched 2026-05-04]
- `.planning/research/PITFALLS.md` Pitfalls 1, 4, 5, 12, 14 -- canonical references; cited by CONTEXT.md Canonical References. [CITED]

### Secondary (MEDIUM confidence -- WebFetch verified)
- GitHub mcp/python-sdk releases page -- no public-interface changes to `stdio_client`/`ClientSession`/`errlog` between 1.20 and 1.27 (per WebFetch summary 2026-05-04). [VERIFIED via WebFetch]

### Tertiary (LOW confidence -- not used)
- None. All Phase 2 claims are sourced from installed-SDK inspection or the locked Phase 1 + CONTEXT.md decisions.

## Validation Architecture

> Skipped: `.planning/config.json` has `workflow.nyquist_validation: false`. The project's existing pytest infrastructure (Phase 1) is the test layer; Phase 2 adds `tests/unit/test_mcp_client.py` and `tests/smoke/test_smoke_homelab_mcp.py` plus one test in `tests/unit/test_config.py`. No formal test-mapping table required by config.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- mcp 1.27.0 verified installed; all signatures source-inspected.
- Architecture: HIGH -- AsyncExitStack pattern is the documented Pitfall-1 mitigation; `_LoggerWriter` adapter is straightforward; SDK already does the dangerous Windows work.
- Pitfalls: HIGH -- existing PITFALLS.md document is comprehensive; one CONTEXT.md misstatement caught (Q1).

**Research date:** 2026-05-04
**Valid until:** ~2026-06-04 (mcp SDK is stable but moves; revalidate if a new minor lands before Phase 2 ships)

## RESEARCH COMPLETE

Phase 2 wrapper design is fully sourced from the installed `mcp 1.27.0` SDK; one CONTEXT.md misstatement (Q1: stdio_client does not expose Process) needs a planner decision before implementation -- recommend Option A (drop the 5s belt; trust SDK's `_terminate_process_tree`).
