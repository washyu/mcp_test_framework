"""mcp-test-framework console-script deprecation shim.

The console-script `mcp-test-framework` is retained for v1.4 as a back-compat
entry point (Phase 26 D-06). It emits a single DeprecationWarning on first
process call and then dispatches to the same Typer `app` the new
`mcp-contracts` script targets.

Removed in v1.5 (D-18) alongside every other Phase 25 / Phase 26
deprecation shim.

Deprecation copy is hardcoded per Phase 25 D-05 (no central constant); the
literal string is greppable for the v1.5 cleanup sweep.
"""
from __future__ import annotations

import warnings


def main() -> None:
    """Console-script entry point — warn once then delegate to cli:app."""
    warnings.warn(
        "mcp-test-framework command is deprecated since v1.4 and will be removed in v1.5 — "
        "use mcp-contracts instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Import here (not at module top) so a `--help` short-circuit on the
    # primary `mcp-contracts` script doesn't pay this import cost. The
    # console-script trampoline created by pip/uv invokes `main()` directly,
    # so this lazy import only fires when the legacy script is actually run.
    from mcp_test_framework.cli import app

    app()
