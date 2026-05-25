"""mcp_test_framework.sdet removal stub -- raises on import.

The `sdet` package was renamed to `test_code` in v1.4. The re-export
shim survives as this stub for v1.5 so that operators still importing
the old name see a pointer at the new location rather than Python's
stock "No module named" message. The stub directory is removed
outright in a future EOL pass.
"""
from __future__ import annotations  # noqa: sdet-rename-shim

raise ModuleNotFoundError(  # noqa: sdet-rename-shim
    "mcp_test_framework.sdet was removed in v1.5\n"
    "\n"
    "the `mcp_test_framework.sdet` import surface was renamed to "
    "`mcp_test_framework.test_code` in v1.4 and removed in v1.5.\n"
    "every public symbol (ToolCallError, ToolResponse, mcp_session, tool) "
    "is re-exported unchanged from the new location.\n"
    "\n"
    "next: replace `from mcp_test_framework.sdet import X` with "
    "`from mcp_test_framework.test_code import X` in your tests."
)
