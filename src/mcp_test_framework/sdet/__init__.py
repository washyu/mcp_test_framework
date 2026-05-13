"""mcp_test_framework.sdet -- SDET test surface (Phase 17 + 18).

Phase 17 (CODEGEN-01..06) ships:
  - ToolResponse: uniform .raw / .data / .text / .is_error base class
    that every generated <Tool>Response inherits from (CODEGEN-04, D-07).

Phase 18 (SDET-01..04, UI-02) adds:
  - mcp_session: session-scoped pytest-asyncio fixture wrapping McpTestClient
    and activating the per-server generated registry (D-01/D-02/D-03).
  - tool(name): typed call wrapper factory; `tool("create_vm").call(params)`
    performs the wire call and returns a typed CreateVmResponse on success
    (CODEGEN-05 contract; .call() body wired in Phase 18).
  - ToolCallError: plain Exception subclass with .tool / .code / .message /
    .raw fields; raised by tool().call() when result.isError is True
    (UI-02; surfaced into the em-dash FAIL row + --debug appendix).

Phase 20 (PREFLIGHT-01..02) will add `requires_homelab`. Do not add it here
until Phase 20 lands -- keep this barrel narrow.
"""
from __future__ import annotations

from mcp_test_framework.sdet.errors import ToolCallError
from mcp_test_framework.sdet.response import ToolResponse
from mcp_test_framework.sdet.session import mcp_session
from mcp_test_framework.sdet._tool_factory import tool

__all__ = ["ToolCallError", "ToolResponse", "mcp_session", "tool"]
