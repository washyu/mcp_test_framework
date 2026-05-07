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
- Server stderr inherited from the parent process (SDK errlog default);
  pytest captures it via its standard stderr capture. The named logger
  "mcp_test_framework.mcp_client.stderr" is preserved for future re-wiring
  (see 02.1 RESEARCH Option A) but receives no records from this version.
- ToolNotFoundError is domain-local (parallels ValidationIssue in
  schema_validator.py); raised by get_tool() when name not present.
- CallToolResult passed through unchanged; tests in Phase 4 assert shape.
- shutil.which() pre-flight surfaces a friendlier missing-binary error
  than the SDK's bare [WinError 2] (Pitfall 14 belt).
- NO 5s force-kill belt: stdio_client does not expose Process; trust the
  SDK's _terminate_process_tree (Q1 OPTION A; CONTEXT D-04 revised).

Phase 4 fixture FIX-01 will consume this as:
    async with McpTestClient(cfg.mcp_server.command, cfg.mcp_server.args,
                              cfg.mcp_server.timeout_seconds) as client: ...
"""
from __future__ import annotations

import asyncio
import io
import logging
import shutil
import tempfile
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import CallToolResult, Tool

from mcp_test_framework._isolation import _build_isolated_env

_log = logging.getLogger("mcp_test_framework.mcp_client.stderr")


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


# NOTE: _LoggerWriter is not currently wired into stdio_client (see 02.1
# RESEARCH Finding #2: passing a TextIOBase as errlog crashes on Windows
# because subprocess.Popen calls .fileno() on the stderr arg). The class
# is retained as the seed for a future Option-A re-wiring (a real os.pipe
# whose write end has a fileno, plus an asyncio reader task that forwards
# bytes to this writer). Until then it is exercised only by unit tests.
class _LoggerWriter(io.TextIOBase):
    """File-like adapter routing each written line to a stdlib logger.

    The SDK's stdio_client(server, errlog=...) accepts any TextIO and passes
    it directly to anyio.open_process(stderr=...). The OS writes subprocess
    stderr bytes to write() on Windows and POSIX alike. The SDK does NOT
    close errlog -- caller owns the lifecycle (which is fine for a
    process-lifetime logger).
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


class McpTestClient:
    """Async stdio MCP client over the official mcp SDK. See module docstring."""

    def __init__(self, command: str, args: list[str], timeout_seconds: int) -> None:
        self._command = command
        self._args = list(args)  # defensive copy
        self._timeout_seconds = timeout_seconds
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    @classmethod
    def _wrap(cls, session: ClientSession, timeout_seconds: int) -> "McpTestClient":
        """Build an instance pre-bound to a live ClientSession (Phase 4.1 owner-task pattern).

        Skips __aenter__ / AsyncExitStack ownership -- caller (the mcp_client
        fixture's owner task) owns stdio_client + ClientSession lifecycle.
        Used ONLY by the session-scoped fixture; smoke tests continue to use
        `async with McpTestClient(...)`. Mixing modes is undefined.

        The `_command`/`_args` attributes are set to placeholder values because
        they are only consulted inside __aenter__'s shutil.which() pre-flight,
        which this construction path bypasses. `_stack=None` signals "not
        owned by this instance" to __aexit__ (which is a no-op when _stack is
        None -- see existing __aexit__ guard).
        """
        instance = cls.__new__(cls)
        instance._command = "<wrapped>"
        instance._args = []
        instance._timeout_seconds = timeout_seconds
        instance._stack = None
        instance._session = session
        return instance

    async def __aenter__(self) -> "McpTestClient":
        # Pitfall 14: friendlier early error than the SDK's [WinError 2].
        # The SDK's get_windows_executable_command does its own which() walk;
        # this is belt-and-suspenders for the missing-binary diagnostic.
        if shutil.which(self._command) is None:
            raise FileNotFoundError(
                f"MCP server command not on PATH: {self._command!r}"
            )
        stack = AsyncExitStack()
        try:
            # Per-instance short-lived tempdir for the CLI/preflight spawn path
            # (Phase 06 D-16; D-17 -- enables unconditional README isolation
            # claim in Phase 10 DOC-05). Distinct prefix from the session
            # fixture to differentiate orphans in `dir %TEMP%`. Registered
            # with the stack BEFORE stdio_client so reverse-order unwind
            # tears down the subprocess first, then deletes the tempdir --
            # correct on Windows (closed file handles before rmdir) and POSIX.
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
            read, write = await stack.enter_async_context(
                stdio_client(params)
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
        # Reverse-order unwind in the SAME task that did __aenter__ -- the
        # documented Pitfall-1 mitigation. Trust the SDK's
        # _terminate_process_tree (SIGTERM -> SIGKILL on a 2.0s timer; Job
        # Object on Windows). NO 5s force-kill belt -- stdio_client does
        # not expose Process (RESEARCH Q1 decision: Option A).
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
