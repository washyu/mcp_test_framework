"""Runtime sys.modules guard for the homelab-mcp black-box rule.

Relocated from tests/conftest.py per Phase 27 so the guard ships inside
the installed wheel and fires for library-mode operators -- not just for
the framework's own test suite. Invoked from the plugin's
pytest_configure after Config is loaded.

The guard is GENERIC despite mentioning `homelab_mcp` by name: that
string is the framework's MVP target SUT, and the black-box principle
is what's being enforced (framework-primitives / SDET-safety principle).
Generalizing to a config-driven allowlist is deferred to a later milestone.
"""
from __future__ import annotations

import sys


def check_black_box() -> None:
    """Raise RuntimeError if any homelab_mcp.* module is in sys.modules.

    Called from `_plugin.py:pytest_configure` after Config is loaded.
    The error message is preserved verbatim from the relocated
    `tests/conftest.py:pytest_configure` body to keep operator-facing
    diagnostics stable across the relocation.
    """
    leaked = [
        name
        for name in sys.modules
        if name == "homelab_mcp" or name.startswith("homelab_mcp.")
    ]
    if leaked:
        raise RuntimeError(
            f"Black-box rule violated: homelab_mcp modules in sys.modules "
            f"at test start: {leaked}. The framework must drive homelab-mcp "
            f"via stdio_client only -- never import."
        )
