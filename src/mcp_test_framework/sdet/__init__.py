"""Back-compat shim — re-exports the public surface from mcp_test_framework.test_code.

This module is the v1.4 deprecation-window placeholder for the old import
surface. Importing it fires a DeprecationWarning exactly once per process
(Python's default warning filter); the shim is removed in v1.5.
"""  # noqa: sdet-rename-shim
from __future__ import annotations

import warnings

warnings.warn(  # noqa: sdet-rename-shim
    "mcp_test_framework.sdet is deprecated since v1.4 and will be removed in v1.5 — "  # noqa: sdet-rename-shim
    "use mcp_test_framework.test_code instead.",
    DeprecationWarning,
    stacklevel=2,
)  # noqa: sdet-rename-shim

from mcp_test_framework.test_code import (  # noqa: sdet-rename-shim, E402
    ToolCallError,
    ToolResponse,
    mcp_session,
    tool,
)

__all__ = ["ToolCallError", "ToolResponse", "mcp_session", "tool"]  # noqa: sdet-rename-shim
