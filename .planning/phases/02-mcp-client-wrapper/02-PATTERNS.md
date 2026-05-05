# Phase 2: MCP Client Wrapper - Pattern Map

**Mapped:** 2026-05-04
**Files analyzed:** 7 (1 new src, 1 modify src, 2 new tests, 1 modify test, 3 modify config/docs)
**Analogs found:** 7 / 7 (all phase-1-derived; no greenfield-with-no-analog cases)

## File Classification

| New/Modified File | Status | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|--------|------|-----------|----------------|---------------|
| `src/mcp_test_framework/mcp_client.py` | NEW | service (async I/O wrapper) | request-response (stdio JSON-RPC + custom exception) | `src/mcp_test_framework/schema_validator.py` (domain-local exception convention) + `src/mcp_test_framework/config.py` (module docstring + custom-source CM-style class) | role-match (no async analog yet); pure-data analog for naming/exception conventions |
| `src/mcp_test_framework/models.py` | MODIFY | model (pydantic config sub-model) | CRUD (in-memory data) | `src/mcp_test_framework/models.py` `OllamaConfig.timeout_seconds` (lines 38-42) | exact (verbatim shape per D-05) |
| `tests/smoke/__init__.py` | NEW (empty) | test package marker | n/a | `tests/unit/__init__.py` (empty) | exact |
| `tests/smoke/test_smoke_homelab_mcp.py` | NEW | test (async live integration) | event-driven (subprocess + stdio) | none in repo (first async test); structural analog: `tests/unit/test_schema_validator.py` (header docstring + helper-then-tests layout) | partial (no async analog); naming/header pattern from schema_validator test |
| `tests/unit/test_mcp_client.py` | NEW | test (sync unit) | CRUD (pure-data exception-shape assertions) | `tests/unit/test_schema_validator.py` (helper + per-check tests, severity/path invariants) | role-exact (sync unit, mock-friendly only) |
| `tests/unit/test_config.py` | MODIFY | test (sync unit) | CRUD (config precedence) | `tests/unit/test_config.py` itself (lines 50-105 — `test_defaults`, `test_env_overrides_default`, `test_env_overrides_yaml`) | exact (extend existing precedence-test family) |
| `pyproject.toml` | MODIFY | config (build/tool) | n/a | `pyproject.toml` lines 29-36 (existing `[tool.pytest.ini_options]`) | exact (extend the same table) |
| `.env.example` | MODIFY | config (env doc) | n/a | `.env.example` lines 7-9 (`OLLAMA_TIMEOUT_SECONDS=120` line) | exact (sister env var) |
| `config.example.yaml` | MODIFY | config (YAML doc) | n/a | `config.example.yaml` lines 4-7 (`ollama:` block with `timeout_seconds`) | exact (sister sub-model) |

## Pattern Assignments

---

### `src/mcp_test_framework/mcp_client.py` (service, request-response — NEW)

**Primary analog (naming + exception convention):** `src/mcp_test_framework/schema_validator.py`
**Secondary analog (module docstring style + class-as-source pattern):** `src/mcp_test_framework/config.py`
**Reference skeleton:** RESEARCH.md §"Code Examples > Lifecycle pattern" (lines 285-391) — verbatim, sourced from `mcp 1.27.0` source inspection.

**Module docstring pattern** (copy shape from `schema_validator.py` lines 1-29):
```python
"""Async stdio MCP client wrapper around mcp.client.stdio.stdio_client + ClientSession.

Implements the McpTestClient interface from
docs/mcp_test_framework_mvp_spec.md §mcp_client.py:

    __init__(command, args, timeout_seconds), __aenter__/__aexit__,
    list_tools(), get_tool(name), call_tool(name, arguments).

Per CONTEXT.md decisions (D-05..D-08, plus Discretion items):
- Lifecycle owned via contextlib.AsyncExitStack inside __aenter__ so
  stdio_client + ClientSession enter/exit happen in the same task
  (Pitfall 1 mitigation).
- Every SDK call (initialize, list_tools, call_tool) wrapped in
  asyncio.timeout(self._timeout_seconds) -- same uniform ceiling (D-06).
- Server stderr captured via the SDK's errlog parameter and routed to
  a stdlib logger named "mcp_test_framework.mcp_client.stderr".
- ToolNotFoundError is domain-local (parallels ValidationIssue in
  schema_validator.py); raised by get_tool() when name not present.
- CallToolResult passed through unchanged; tests in Phase 4 assert shape.

Phase 4 fixture FIX-01 will consume this as:
    async with McpTestClient(cfg.mcp_server.command, cfg.mcp_server.args,
                              cfg.mcp_server.timeout_seconds) as client: ...
"""
from __future__ import annotations
```

**Imports pattern** (modeled after `schema_validator.py` lines 30-36 + RESEARCH.md lines 289-298):
```python
import asyncio
import io
import logging
import shutil
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import CallToolResult, Tool
```
- Note `from __future__ import annotations` — every Phase 1 src file uses this; do the same.
- Imports are stdlib-first, then third-party (mcp/pydantic), separated by a blank line — matches `schema_validator.py`.
- **Forbidden:** any `homelab_mcp` import (caught by ruff TID251 + `tests/conftest.py` `sys.modules` scan).

**Domain-local exception pattern** (mirrors `ValidationIssue` in `schema_validator.py` lines 39-50, with `LookupError` base instead of `BaseModel`):
```python
class ToolNotFoundError(LookupError):
    """Raised by McpTestClient.get_tool when the named tool is not registered.

    Carries the candidate tool list so Phase 4's target_tool fixture (FIX-03)
    can fail the run early with a useful diagnostic. Parallels ValidationIssue
    in schema_validator.py: domain-specific type living in its owning module
    rather than a cross-cutting models.py.
    """

    def __init__(self, tool_name: str, available: list[str]) -> None:
        self.tool_name = tool_name
        self.available = available
        super().__init__(
            f"Tool {tool_name!r} not found. Available tools: {available!r}"
        )
```
**Why these names:** RESEARCH.md "Discretion" decision and CONTEXT.md D-08 lock the public attributes (`tool_name`, `available`); the unit test in `tests/unit/test_mcp_client.py` will assert on both.

**Logger-adapter pattern** (RESEARCH.md "Code Examples > Lifecycle pattern" lines 303-325):
```python
_log = logging.getLogger("mcp_test_framework.mcp_client.stderr")


class _LoggerWriter(io.TextIOBase):
    """File-like adapter routing each written line to a stdlib logger at WARNING.

    The SDK's stdio_client(server, errlog=...) accepts any TextIO and passes
    it directly to anyio.open_process(stderr=...). The OS writes subprocess
    stderr bytes to write() on Windows and POSIX alike. The SDK does NOT close
    errlog -- caller owns the lifecycle (which is fine for a process-lifetime
    logger).
    """

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
```
- Underscore-prefixed (`_log`, `_LoggerWriter`) marks them private to the module — same convention as `_BareNameNestedEnvSource` in `config.py` (line 61).

**Lifecycle / `__aenter__` pattern** (RESEARCH.md "Code Examples > Lifecycle pattern" lines 337-372):
```python
class McpTestClient:
    def __init__(self, command: str, args: list[str], timeout_seconds: int) -> None:
        self._command = command
        self._args = list(args)  # defensive copy
        self._timeout_seconds = timeout_seconds
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def __aenter__(self) -> "McpTestClient":
        # Pitfall 14: friendlier early error than the SDK's [WinError 2].
        # The SDK's get_windows_executable_command does its own which() walk;
        # this is belt-and-suspenders for the missing-binary diagnostic.
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
        # Reverse-order unwind in the SAME task that did __aenter__ -- this
        # is the documented Pitfall-1 mitigation. Trust the SDK's
        # _terminate_process_tree (SIGTERM -> SIGKILL on a 2.0s timer; Job
        # Object on Windows). NO 5s force-kill belt -- stdio_client does not
        # expose Process (RESEARCH Q1 decision: Option A).
        stack = self._stack
        self._stack = None
        self._session = None
        if stack is not None:
            await stack.aclose()
```

**Belt-and-braces timeout pattern** (RESEARCH.md "Pattern 2"; verified against RESEARCH.md "Code Examples" lines 374-390):
```python
    async def list_tools(self) -> list[Tool]:
        assert self._session is not None, "McpTestClient not entered"
        async with asyncio.timeout(self._timeout_seconds):
            result = await self._session.list_tools()
        return list(result.tools)

    async def get_tool(self, name: str) -> Tool:
        # Re-fetches every call -- no in-process cache (CONTEXT Discretion).
        # Phase 4's session fixture means the round-trip happens once per
        # test session anyway.
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
- All three SDK call sites use the SAME `self._timeout_seconds` ceiling (D-06).
- `assert self._session is not None` matches the assertive style; in Phase 1 the equivalent guard would be `if not isinstance(schema, dict)` (`schema_validator.py` line 108) — both fail loudly rather than silently.
- `call_tool` returns the SDK's `CallToolResult` UNCHANGED (Discretion decision; Pitfall 12 — Phase 4 owns shape interpretation).

**No analog for these aspects (use RESEARCH.md only):**
- `AsyncExitStack` ownership pattern — pure RESEARCH/SDK source.
- `errlog`/`stderr` plumbing — pure RESEARCH/SDK source.
- `asyncio.timeout` (3.11+) usage — pure RESEARCH/SDK source.

---

### `src/mcp_test_framework/models.py` (model, CRUD — MODIFY)

**Analog:** `src/mcp_test_framework/models.py` line 38-42 (`OllamaConfig.timeout_seconds`).

**Field-add pattern** (verbatim shape per CONTEXT D-05; copy from existing `OllamaConfig.timeout_seconds`):
```python
class McpServerConfig(BaseModel):
    """MCP server subprocess configuration."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    command: str = Field(
        default="homelab-mcp",
        validation_alias=AliasChoices("MCP_SERVER_COMMAND", "command"),
    )
    args: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("MCP_SERVER_ARGS", "args"),
    )
    timeout_seconds: int = Field(  # NEW (D-05)
        default=30,
        ge=1,
        validation_alias=AliasChoices("MCP_SERVER_TIMEOUT_SECONDS", "timeout_seconds"),
    )
```

**Why this exact shape:**
- `default=30` per CONTEXT D-05 (30s ceiling, not target).
- `ge=1` — mirrors `OllamaConfig.timeout_seconds` (line 39); never accept 0/negative.
- `AliasChoices(<env name>, <field name>)` — Phase 1 LEARNINGS pattern "AliasChoices(<env>, <field>) + populate_by_name=True for dual routing". Both routes (env and YAML) MUST work.
- No new pattern in `config.py` — `_BareNameNestedEnvSource` (lines 61-92) auto-walks the new field's `AliasChoices` once it's declared (LEARNINGS lesson "EnvSettingsSource does not walk sub-model validation_alias" was the one-time fix; the source is general).

**Phase 1 LEARNINGS warning that applies:** "4/9 config tests failed initially due to silent default-fallback" — adding `MCP_SERVER_TIMEOUT_SECONDS` env handling without a precedence test in `tests/unit/test_config.py` would silently default-fallback with no exception trace. The precedence test (D-07) is non-negotiable.

---

### `tests/smoke/__init__.py` (test marker — NEW empty file)

**Analog:** `tests/unit/__init__.py` (empty).
**Pattern:** Create as a 0-byte file. Pytest does not require it for discovery, but the existing `tests/unit/__init__.py` keeps `tests/` as a regular Python package; `tests/smoke/__init__.py` keeps that convention.

---

### `tests/smoke/test_smoke_homelab_mcp.py` (test, event-driven — NEW)

**Structural analog (header + helper-then-tests layout):** `tests/unit/test_schema_validator.py` lines 1-30
**Reference skeleton:** RESEARCH.md "Code Examples > Smoke-test sketch" (lines 393-442).

**Header pattern** (modeled after `test_schema_validator.py` docstring style):
```python
"""Live integration smoke test against the real homelab-mcp binary.

Permanent live-marker pytest -- D-01 in CONTEXT.md (NOT a throwaway script).
Skipped by default via pyproject.toml `addopts = "-m 'not live_homelab'"`.
Opt in with `uv run pytest -m live_homelab`.

Falsifies BOTH Phase 2 success criteria (D-04):
  SC#1 -- raw stdio_client + ClientSession lists target tool with non-empty schema.
  SC#2 -- McpTestClient.call_tool returns isError=False with non-empty content
          or structuredContent.

Pre-req: `homelab-mcp` binary must be on PATH. Missing -> the test fails fast
inside the test body via FileNotFoundError (D-02), NOT at collection time.
"""
from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from mcp_test_framework.config import Config
from mcp_test_framework.mcp_client import McpTestClient
```

**Marker + loop-scope pattern** (RESEARCH.md line 407 + Phase 1 LEARNINGS pattern "Pytest-asyncio strict mode + session-scoped fixture loop"):
```python
pytestmark = [
    pytest.mark.live_homelab,
    pytest.mark.asyncio(loop_scope="session"),
]
```
- `pytestmark` at module level applies the markers to every test in the file — the simplest way to honor CONTEXT D-04 ("BOTH success criteria… falsifiable in the test file").
- `loop_scope="session"` matches `asyncio_default_fixture_loop_scope = "session"` already locked in `pyproject.toml` line 35. Phase 4's session-scoped fixtures will share the same loop.

**Test bodies** (RESEARCH.md "Code Examples > Smoke-test sketch" lines 410-441 — verbatim, with names locked by D-04):
```python
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
- Note SC#1 uses RAW `stdio_client + ClientSession` (proves the framework can drive the SDK directly, no homelab_mcp import); SC#2 uses the WRAPPER (proves Phase 2's deliverable). Two separate functions per D-04.
- `Config()` instantiation matches the no-arg pattern from `tests/unit/test_config.py` line 54.
- `assert ..., f"..."` failure messages mirror the `test_schema_validator.py` style (e.g., line 98).

**Why no new env-var-clearing fixture:** Smoke tests intentionally USE the developer's environment (so `MCP_SERVER_COMMAND` overrides the default if set). Unlike `tests/unit/test_config.py` which calls `_clear_env(monkeypatch)`, this test wants the live env.

---

### `tests/unit/test_mcp_client.py` (test, CRUD — NEW)

**Analog:** `tests/unit/test_schema_validator.py` (helper-then-tests layout, severity/path invariants).

**Header pattern** (modeled after `test_schema_validator.py` lines 1-18):
```python
"""Unit tests for mcp_test_framework.mcp_client (mock-friendly slices only).

Live subprocess / timeout behavior is exercised by tests/smoke/test_smoke_homelab_mcp.py;
mocking stdio_client to assert "timeout fires" is high-cost / low-signal
(CONTEXT.md "Phase 2 unit tests scope").

Coverage in this file:
  - ToolNotFoundError payload shape (tool_name, available, message)
  - _LoggerWriter line-buffering and flushing behavior

All tests are synchronous -- no @pytest.mark.asyncio.
"""
from __future__ import annotations

import logging

import pytest

from mcp_test_framework.mcp_client import ToolNotFoundError, _LoggerWriter
```

**Test pattern (exception payload):** Modeled after the per-check tests in `test_schema_validator.py` lines 90-115 (focused, one assertion per attribute):
```python
def test_tool_not_found_carries_name_and_available() -> None:
    """ToolNotFoundError payload exposes tool_name and available for FIX-03 diagnostic."""
    err = ToolNotFoundError("missing_tool", available=["a", "b"])
    assert err.tool_name == "missing_tool"
    assert err.available == ["a", "b"]


def test_tool_not_found_message_includes_name_and_candidates() -> None:
    """str(ToolNotFoundError) contains the missing name and the candidate list."""
    err = ToolNotFoundError("missing_tool", available=["a", "b"])
    msg = str(err)
    assert "missing_tool" in msg
    assert "['a', 'b']" in msg or '"a", "b"' in msg  # repr of list


def test_tool_not_found_is_lookup_error() -> None:
    """ToolNotFoundError subclasses LookupError so callers can catch it generically."""
    err = ToolNotFoundError("x", available=[])
    assert isinstance(err, LookupError)
```

**Test pattern (logger adapter):** Use `caplog` (pytest stdlib log capture) — analog: none in repo, but documented project-wide via Phase 4's `--log-cli-level=WARNING` story:
```python
def test_logger_writer_emits_complete_lines(caplog: pytest.LogCaptureFixture) -> None:
    """_LoggerWriter buffers partial writes and emits on newline."""
    logger = logging.getLogger("mcp_test_framework.mcp_client.stderr")
    writer = _LoggerWriter(logger)
    with caplog.at_level(logging.WARNING, logger=logger.name):
        writer.write("hello ")  # no newline yet -> nothing emitted
        assert not caplog.records
        writer.write("world\n")  # newline -> one record
    assert len(caplog.records) == 1
    assert caplog.records[0].message == "hello world"
    assert caplog.records[0].levelno == logging.WARNING


def test_logger_writer_flush_emits_buffered_partial(caplog: pytest.LogCaptureFixture) -> None:
    """_LoggerWriter.flush() emits any unterminated buffered text."""
    logger = logging.getLogger("mcp_test_framework.mcp_client.stderr")
    writer = _LoggerWriter(logger)
    with caplog.at_level(logging.WARNING, logger=logger.name):
        writer.write("partial line without newline")
        assert not caplog.records
        writer.flush()
    assert len(caplog.records) == 1
    assert caplog.records[0].message == "partial line without newline"
```
- These cover Assumption A3 in RESEARCH.md ("line-buffering acceptable; partial line at process kill may be lost"). The flush test makes the contract explicit.
- Sync tests, no `@pytest.mark.asyncio` — matches `test_schema_validator.py` and the project-wide convention "synchronous tests don't get the asyncio marker" (RESEARCH anti-pattern note in `test_config.py` line 12).

---

### `tests/unit/test_config.py` (test, CRUD — MODIFY)

**Analog:** itself, lines 50-105 — `test_defaults`, `test_env_overrides_default`, `test_env_overrides_yaml`.

**Two changes required:**

**1. Extend `_SPEC_ENV_VARS` tuple** (line 27):
```python
_SPEC_ENV_VARS: tuple[str, ...] = (
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "OLLAMA_TIMEOUT_SECONDS",
    "MCP_SERVER_COMMAND",
    "MCP_SERVER_ARGS",
    "MCP_SERVER_TIMEOUT_SECONDS",  # NEW (Phase 2 D-05)
    "TARGET_TOOL_NAME",
    "JUDGE_TIMEOUT_SECONDS",
    "MCPTF_CONFIG_FILE",
)
```
- Critical: missing this addition would let a developer's shell `MCP_SERVER_TIMEOUT_SECONDS=99` leak into other tests' `Config()` calls and silently flip assertions.

**2. Extend default + add precedence test** — copy the shape of `test_defaults` (line 50) and `test_env_overrides_default` (line 65):
```python
def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """No env, no YAML -> every field is its declared default."""
    _clear_env(monkeypatch)

    cfg = Config()

    assert cfg.ollama.base_url == "http://127.0.0.1:11434"
    assert cfg.ollama.model == "qwen3.6:latest"
    assert cfg.ollama.timeout_seconds == 120
    assert cfg.mcp_server.command == "homelab-mcp"
    assert cfg.mcp_server.args == []
    assert cfg.mcp_server.timeout_seconds == 30  # NEW assertion (Phase 2 D-05)
    assert cfg.target.tool_name == "list_registered_servers"
    assert cfg.judge_timeout_seconds == 120


def test_mcp_server_timeout_seconds_env_overrides_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MCP_SERVER_TIMEOUT_SECONDS env var routes through _BareNameNestedEnvSource.

    Phase 1 LEARNINGS lesson "EnvSettingsSource does not walk sub-model validation_alias"
    means a missing precedence test would let the field silently default-fallback
    with no exception trace. This is the regression guard required by D-07.
    """
    _clear_env(monkeypatch)
    monkeypatch.setenv("MCP_SERVER_TIMEOUT_SECONDS", "5")

    cfg = Config()

    assert cfg.mcp_server.timeout_seconds == 5
```
- Both tests follow the existing pattern: `_clear_env(monkeypatch)`, then `monkeypatch.setenv(...)`, then construct `Config()`, then assert.
- `monkeypatch.setenv` value is `"5"` (string) — pydantic coerces to `int` per the field annotation.
- Optional belt-and-suspenders test for YAML routing (mirroring `test_yaml_overrides_default` at line 75) is desirable but not required by D-07.

---

### `pyproject.toml` (config — MODIFY)

**Analog:** itself, lines 29-36 (existing `[tool.pytest.ini_options]` table).

**Modification pattern** (CONTEXT D-03, RESEARCH.md "Code Examples > pyproject.toml marker registration" line 457-467):
```toml
[tool.pytest.ini_options]
asyncio_mode = "strict"
asyncio_default_fixture_loop_scope = "session"
testpaths = ["tests"]
markers = [
  "live_homelab: requires live homelab-mcp on PATH",
]
addopts = "-m 'not live_homelab'"
```
- Add `markers = [...]` (new) and `addopts = "-m 'not live_homelab'"` (new) to the existing table; do NOT create a second `[tool.pytest.ini_options]` table.
- Marker description string MUST mention "live homelab-mcp on PATH" so `pytest --markers` output is self-documenting.
- `addopts` quoting: TOML strings — single quotes inside double-quoted value (`"-m 'not live_homelab'"`), exactly as in CONTEXT D-03.
- Default `uv run pytest` skips the live test; `uv run pytest -m live_homelab` runs only it; `uv run pytest -m ''` overrides to run everything.

**No other `pyproject.toml` edits needed for Phase 2.** No new top-level deps (`mcp 1.27.0` already pinned at `mcp>=1.27` line 8).

---

### `.env.example` (config doc — MODIFY)

**Analog:** itself, lines 7-9 (`OLLAMA_TIMEOUT_SECONDS=120` block).

**Insertion pattern:**
```
MCP_SERVER_COMMAND=homelab-mcp
MCP_SERVER_ARGS=
MCP_SERVER_TIMEOUT_SECONDS=30   # NEW (Phase 2 D-07)
```
- Insert immediately after `MCP_SERVER_ARGS=` (line 12), keeping `mcp_server` env vars grouped, mirroring how `OLLAMA_TIMEOUT_SECONDS` sits with the other `OLLAMA_*` vars.
- Value `30` matches the `default=30` in `models.py`.
- No comment needed — the file's top-of-file comment (lines 1-5) already documents the convention.

---

### `config.example.yaml` (config doc — MODIFY)

**Analog:** itself, lines 9-11 (existing `mcp_server:` block) + lines 4-7 (`ollama:` block with `timeout_seconds`).

**Insertion pattern:**
```yaml
mcp_server:
  command: homelab-mcp
  args: []
  timeout_seconds: 30   # NEW (Phase 2 D-07)
```
- Add the field at the bottom of the `mcp_server:` block; matches how `ollama:` (lines 4-7) declares `timeout_seconds` last in its block.
- Value `30` matches `default=30` in `models.py` and the `.env.example` line above.
- Two-space indentation — matches existing YAML style.

---

## Shared Patterns

### Async-everywhere with `asyncio.timeout`

**Source:** RESEARCH.md "Pattern 2" + CONTEXT D-06 + CLAUDE.md §"Architecture Notes" ("`asyncio.timeout` (3.11+) wraps every subprocess/HTTP op").

**Apply to:** Every method on `McpTestClient` that calls into the SDK — `__aenter__` (around `initialize`), `list_tools`, `call_tool`. NOT `get_tool` directly (it delegates to `list_tools` which is already wrapped).

```python
async with asyncio.timeout(self._timeout_seconds):
    return await self._session.<sdk_method>(...)
```

The same `self._timeout_seconds` ceiling applies uniformly (D-06). The Phase 1 analog is `Config`'s `judge_timeout_seconds` (separate knob for Ollama) — Phase 2's pattern adds `mcp_server.timeout_seconds` in the parallel slot.

---

### Domain-local exceptions in their owning module

**Source:** Phase 1 LEARNINGS pattern + `schema_validator.py` line 39-50 (`ValidationIssue`).

**Apply to:** `ToolNotFoundError` in `mcp_client.py` — NOT in a shared `models.py` or `errors.py`. Mirrors the precedent set by `ValidationIssue`.

```python
class ToolNotFoundError(LookupError):
    def __init__(self, tool_name: str, available: list[str]) -> None: ...
```

The exception base (`LookupError`) is chosen so callers can `except LookupError:` generically — matches how `ValidationIssue` is a `BaseModel` so callers can construct/serialize it without importing it specifically.

---

### `from __future__ import annotations` at the top of every src file

**Source:** Every Phase 1 src file: `models.py:20`, `config.py:28`, `schema_validator.py:30`.

**Apply to:** `src/mcp_test_framework/mcp_client.py` and both new test files (`tests/smoke/test_smoke_homelab_mcp.py`, `tests/unit/test_mcp_client.py`).

```python
from __future__ import annotations
```

Even though Python 3.14 is the runtime, the project's convention (Phase 1) is to keep this header for forward compat and consistent annotation evaluation.

---

### `AliasChoices(<env name>, <field name>)` + `populate_by_name=True` for any new env-routed field

**Source:** Phase 1 LEARNINGS pattern; verified in `models.py` lines 25-68.

**Apply to:** The new `McpServerConfig.timeout_seconds` field. The sub-model already has `populate_by_name=True` in its `model_config` (line 48), so only the field-level `validation_alias` is new.

```python
timeout_seconds: int = Field(
    default=30,
    ge=1,
    validation_alias=AliasChoices("MCP_SERVER_TIMEOUT_SECONDS", "timeout_seconds"),
)
```

**Why both alias choices are non-negotiable:** Phase 1 LEARNINGS lesson "Single-arg `AliasChoices` breaks YAML overlay routing" — single-arg would silently break `config.example.yaml` overlay routing for `mcp_server.timeout_seconds`. The two-element form keeps both env and YAML pathways live.

---

### Black-box guard (no homelab_mcp imports)

**Source:** Phase 1 LEARNINGS pattern "Black-box defense in depth — lint + runtime" (`pyproject.toml` line 51-52 + `tests/conftest.py` line 13-38).

**Apply to:** All Phase 2 deliverables. No new measures required — Phase 1's two layers (ruff TID251 + `sys.modules` scan) catch any accidental import mechanically. The smoke test specifically uses `mcp.client.stdio.stdio_client` directly (NOT a homelab_mcp helper) — that is the SC#1 contract.

---

### Pytest-asyncio strict mode + `loop_scope="session"`

**Source:** Phase 1 LEARNINGS pattern "Pytest-asyncio strict mode + session-scoped fixture loop, configured at the build layer" (`pyproject.toml` lines 34-35).

**Apply to:** `tests/smoke/test_smoke_homelab_mcp.py` — opt into the session loop via `pytest.mark.asyncio(loop_scope="session")` so Phase 4's session-scoped fixtures (when they consume `McpTestClient`) inherit the same loop and don't trigger Pitfall 1.

```python
pytestmark = [pytest.mark.live_homelab, pytest.mark.asyncio(loop_scope="session")]
```

Sync unit tests (`test_mcp_client.py`, `test_config.py`) get NO marker — strict mode tolerates sync tests without markers; adding `@pytest.mark.asyncio` to a sync test is the documented anti-pattern (`test_config.py` line 12).

---

## No Analog Found

| File / Concern | Reason | Source for Pattern |
|----------------|--------|--------------------|
| Async lifecycle / `AsyncExitStack` ownership | Phase 1 ships zero async code; Phase 2 is the first | RESEARCH.md "Pattern 1" + "Code Examples > Lifecycle pattern" lines 285-391 (verbatim from SDK source inspection) |
| `errlog` -> stdlib logger adapter (`_LoggerWriter`) | First TextIO->logger bridge in the project | RESEARCH.md "Pattern 3" + "Code Examples > Lifecycle pattern" lines 303-325 |
| `pytestmark` module-level marker tuple | First time the project uses module-level markers | Pytest docs (standard pattern); CONTEXT D-02/D-04 |
| `caplog` fixture usage | First test that asserts on log records | Pytest stdlib (`pytest.LogCaptureFixture`) |
| Live integration smoke harness directory (`tests/smoke/`) | New convention introduced by D-01 | CONTEXT D-01 / RESEARCH.md "Pattern 4" |

For all the above, RESEARCH.md provides verified-from-source patterns; the planner should cite those sections directly rather than searching for non-existent codebase analogs.

---

## Metadata

**Analog search scope:** `src/mcp_test_framework/`, `tests/`, `pyproject.toml`, `.env.example`, `config.example.yaml`.
**Files scanned:** 11 (4 src, 4 test, 3 config/doc).
**Pattern extraction date:** 2026-05-04
**Phase 1 LEARNINGS sections drawn on:** Decisions (frozen sub-models, AliasChoices+populate_by_name, ValidationIssue convention), Lessons (silent default-fallback, EnvSettingsSource gap), Patterns (per-sub-model frozen, dual routing, async strict mode + session loop, black-box defense in depth).

## PATTERN MAPPING COMPLETE
