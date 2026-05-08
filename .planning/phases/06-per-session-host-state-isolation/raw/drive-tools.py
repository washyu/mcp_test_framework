"""Minimal driver: spawn homelab-mcp via stdio, list tools, call the two
v1.1-surface tools, exit. Bypasses pytest preflight (Ollama unavailable in
this environment) per Plan 06-01 Task 2 fallback clause.

Black-box: imports only the framework's McpTestClient (which treats
homelab-mcp as a subprocess). Does NOT import homelab_mcp.
"""
from __future__ import annotations

import asyncio
import sys

from mcp_test_framework.mcp_client import McpTestClient


async def main() -> int:
    print("Driver: spawning homelab-mcp via stdio (uvx homelab-mcp)...")
    client = McpTestClient(
        command="uvx",
        args=["homelab-mcp"],
        timeout_seconds=60,
    )
    async with client:
        print("Driver: connected. Listing tools...")
        tools = await client.list_tools()
        names = sorted(t.name for t in tools)
        print(f"Driver: {len(names)} tools available")
        for name in names:
            print(f"  - {name}")

        targets = ("list_keyring_credentials", "list_registered_servers")
        for tool_name in targets:
            if tool_name not in names:
                print(f"Driver: SKIP {tool_name} (not exposed by server)")
                continue
            print(f"Driver: calling {tool_name}({{}})...")
            try:
                result = await client.call_tool(tool_name, {})
                err = bool(result.isError)
                print(f"  isError={err}")
                content = result.content or []
                print(f"  content blocks: {len(content)}")
                if content and hasattr(content[0], "text"):
                    snippet = (content[0].text or "")[:200].replace("\n", " ")
                    print(f"  text[0][:200]: {snippet}")
            except Exception as exc:  # noqa: BLE001
                print(f"  call_tool({tool_name}) raised: {exc!r}")

    print("Driver: clean exit (subprocess torn down).")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
