"""mcp_test_framework.test_code -- public test-code authoring surface.

Exports:
  - ToolResponse: uniform .raw / .data / .text / .is_error base class that
    every generated <Tool>Response inherits from.
  - mcp_session: session-scoped pytest-asyncio fixture wrapping McpTestClient
    and activating the per-server generated registry.
  - tool(name): typed call wrapper factory; ``tool("create_vm").call(params)``
    performs the wire call and returns a typed CreateVmResponse on success.
  - ToolCallError: typed exception raised by ``tool().call()`` when
    ``result.isError`` is True; carries ``.tool / .code / .message / .raw``.

See docs/TEST-CODE-AUTHORING.md for the authoring walkthrough.
"""
from __future__ import annotations

from mcp_test_framework.test_code._tool_factory import tool
from mcp_test_framework.test_code.errors import ToolCallError
from mcp_test_framework.test_code.response import ToolResponse
from mcp_test_framework.test_code.session import mcp_session

__all__ = ["ToolCallError", "ToolResponse", "mcp_session", "tool"]
