"""Contract pins for ``McpTestClient`` host_isolation parameter wiring.

Three load-bearing invariants from Phase 34 CONTEXT.md:

1. ``McpTestClient.__init__`` accepts a keyword-only ``host_isolation``
   parameter with default ``'strict'`` -- preserves all v1.0-v1.4 callers
   without modification.
2. The constructor stores the mode as ``self._host_isolation`` so
   ``__aenter__`` can branch on it (no Config object stored -- caller
   passes plain data per the framework-primitive contract).
3. ``mcp_client.py`` does NOT import config.py (framework primitive
   takes plain data, never a Config blob).
"""
from __future__ import annotations

import inspect
from pathlib import Path

from mcp_test_framework.mcp_client import McpTestClient


def test_mcp_test_client_init_accepts_host_isolation_kw_only() -> None:
    """``__init__`` accepts ``host_isolation`` as a keyword-only parameter."""
    sig = inspect.signature(McpTestClient.__init__)
    assert "host_isolation" in sig.parameters, (
        "McpTestClient.__init__ must accept a host_isolation parameter. "
        f"Current signature: {sig!r}"
    )
    param = sig.parameters["host_isolation"]
    assert param.kind is inspect.Parameter.KEYWORD_ONLY, (
        "host_isolation must be KEYWORD_ONLY (declared after a `*,` marker) "
        "so it doesn't accidentally land as a positional 4th arg. "
        f"Current kind: {param.kind!r}"
    )
    assert param.default == "strict", (
        "host_isolation default must be 'strict' to preserve existing callers. "
        f"Current default: {param.default!r}"
    )


def test_mcp_test_client_default_host_isolation_is_strict() -> None:
    """Existing callers (no host_isolation arg) get strict mode."""
    client = McpTestClient("true", [], 5)
    assert client._host_isolation == "strict", (
        "Default-constructed McpTestClient must store 'strict' as the mode."
    )


def test_mcp_test_client_passthrough_stored() -> None:
    """Explicit passthrough is stored on the instance for __aenter__ to branch on."""
    client = McpTestClient("true", [], 5, host_isolation="passthrough")
    assert client._host_isolation == "passthrough", (
        "host_isolation='passthrough' must be stored verbatim on the instance."
    )


def test_mcp_client_module_does_not_import_config() -> None:
    """Framework-primitive invariant: mcp_client.py must take plain data,
    never import the Config model. The constructor accepts a Literal[str].
    """
    src = Path(__file__).resolve().parents[3] / "src" / "mcp_test_framework" / "mcp_client.py"
    text = src.read_text(encoding="utf-8")
    assert "from mcp_test_framework.config" not in text, (
        "mcp_client.py must not import from mcp_test_framework.config -- "
        "framework primitives take plain data, not Config blobs."
    )
    assert "from .config" not in text, (
        "mcp_client.py must not import from .config -- "
        "framework primitives take plain data, not Config blobs."
    )


def test_mcp_client_routes_through_dispatcher() -> None:
    """The ``__aenter__`` spawn site calls ``_build_subprocess_env`` with
    the stored mode -- NOT the legacy ``_build_isolated_env`` direct call.
    """
    src = Path(__file__).resolve().parents[3] / "src" / "mcp_test_framework" / "mcp_client.py"
    text = src.read_text(encoding="utf-8")
    assert "_build_subprocess_env(self._host_isolation" in text, (
        "__aenter__ must route through "
        "_build_subprocess_env(self._host_isolation, isolated_home)."
    )
    assert "_build_isolated_env(" not in text, (
        "mcp_client.py must not call _build_isolated_env directly anymore; "
        "the dispatcher in _isolation.py is the only entry point."
    )
