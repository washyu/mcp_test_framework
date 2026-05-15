"""Live integration smoke test against the real homelab-mcp binary.

Permanent live-marker pytest -- D-01 in CONTEXT.md (NOT a throwaway script).
Skipped by default via pyproject.toml `addopts = "-m 'not live_homelab'"`.
Opt in with `uv run pytest -m live_homelab`.

Falsifies BOTH Phase 2 success criteria (D-04):
  SC#1 -- raw stdio_client + ClientSession lists target tool with non-empty
          schema (proves the framework can drive the SDK without any
          homelab_mcp import or wrapper helper).
  SC#2 -- McpTestClient.call_tool returns isError=False with non-empty
          content or structuredContent (proves Plan 02's wrapper handles
          the full lifecycle end-to-end).

Pre-req: `homelab-mcp` binary must be on PATH. If missing, the wrapper test
fails fast inside the test body via FileNotFoundError raised by
McpTestClient.__aenter__'s shutil.which() pre-flight (D-02). The raw
test fails inside `stdio_client()` for the same reason -- both failures
surface inside the test body, NOT at collection time.
"""
from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from mcp_test_framework.config import Config
from mcp_test_framework.mcp_client import McpTestClient
from mcp_test_framework.models import SdetConfig

pytestmark = [
    pytest.mark.live_homelab,
    pytest.mark.asyncio(loop_scope="session"),
]

# Phase 23 D-01 (Cluster A) Pattern S1: Config.sdet is REQUIRED post Phase
# 21.1 RELOC-01. Both SC#1 and SC#2 here construct Config() bare; module-
# level stub avoids repeating the SdetConfig literal at each site.
_SDET_STUB = SdetConfig(generated_root="tests/sdet/_generated")


async def test_raw_stdio_lists_target_tool() -> None:
    """SC#1: raw stdio_client + ClientSession lists target tool with non-empty schema."""
    cfg = Config(sdet=_SDET_STUB)
    params = StdioServerParameters(
        command=cfg.mcp_server.command,
        args=cfg.mcp_server.args,
    )
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
    """SC#2: McpTestClient.call_tool returns isError=False with content or structuredContent."""
    cfg = Config(sdet=_SDET_STUB)
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
