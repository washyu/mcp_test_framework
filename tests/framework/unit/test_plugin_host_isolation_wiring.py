"""Contract pin for ``_plugin.py`` library-mode host_isolation wiring.

Every ``McpTestClient(...)`` constructor call in ``_plugin.py`` must pass
``host_isolation=cfg.host_isolation`` so library-mode tool discovery
honors the operator's mode choice.

Pinned via static-source check (no live MCP needed): the file must
balance ``McpTestClient(`` call sites against ``host_isolation=cfg.host_isolation``
occurrences (or document the omission with a 1-line comment when ``cfg``
is not in scope, per the plan's allowance).
"""
from __future__ import annotations

import re
from pathlib import Path

_PLUGIN_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "mcp_test_framework"
    / "_plugin.py"
)


def test_plugin_passes_host_isolation_to_mcp_client() -> None:
    """Every McpTestClient(...) call in _plugin.py must thread cfg.host_isolation
    through, otherwise library-mode tool discovery silently runs strict
    while the operator's config asks for passthrough.
    """
    text = _PLUGIN_PATH.read_text(encoding="utf-8")
    constructor_calls = len(re.findall(r"McpTestClient\(", text))
    wiring_lines = len(re.findall(r"host_isolation=cfg\.host_isolation", text))

    # Allow a documented "no cfg in scope" exemption (the plan permits it).
    exemption_comments = len(
        re.findall(
            r"#\s*host_isolation defaults to 'strict'.*no Config in scope",
            text,
        )
    )

    assert constructor_calls == wiring_lines + exemption_comments, (
        f"_plugin.py has {constructor_calls} McpTestClient(...) call sites "
        f"but only {wiring_lines} pass host_isolation=cfg.host_isolation "
        f"(and {exemption_comments} documented no-cfg-in-scope exemptions). "
        "Every call site must either thread the mode or carry a 1-line "
        "comment explaining why the default suffices."
    )
    assert wiring_lines >= 1, (
        "At least one McpTestClient(...) call in _plugin.py should pass "
        "host_isolation=cfg.host_isolation (the _discover_tools_live path "
        "has cfg in scope by construction)."
    )
