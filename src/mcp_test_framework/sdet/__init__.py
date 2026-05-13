"""mcp_test_framework.sdet -- SDET test surface (Phase 17 onwards).

Phase 17 (CODEGEN-01..06) ships:
  - ToolResponse: uniform .raw / .data / .text / .is_error base class
    that every generated <Tool>Response inherits from (CODEGEN-04, D-07).

Phases 18-20 will extend this re-export with `mcp_session`, `tool`,
`requires_homelab`. Do not add those here -- they are out of scope per
CONTEXT.md "Out of scope (deliberate)".
"""
from __future__ import annotations

from mcp_test_framework.sdet.response import ToolResponse

__all__ = ["ToolResponse"]
