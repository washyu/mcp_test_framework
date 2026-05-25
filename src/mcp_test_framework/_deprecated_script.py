"""mcp-test-framework console-script removal stub -- v1.5.

The `[project.scripts] mcp-test-framework = "..._deprecated_script:main"`
entry stays wired in pyproject.toml so operators invoking the legacy
script see this pointer message rather than a shell-level
"command not found". The entry-point and this file are scheduled for
removal at a future EOL pass.
"""
from __future__ import annotations  # noqa: sdet-rename-shim

import sys


def main() -> None:  # noqa: sdet-rename-shim
    """Console-script entry point -- hard-rejects and points at mcp-contracts."""
    msg = (
        "[mcp-contracts] mcp-test-framework was removed in v1.5\n"
        "\n"
        "the `mcp-test-framework` console-script was renamed to "
        "`mcp-contracts` in v1.4 and removed in v1.5.\n"
        "every subcommand and every flag is unchanged -- only the script "
        "name moved.\n"
        "\n"
        "next: invoke `mcp-contracts` instead of `mcp-test-framework` "
        "(same args).\n"
    )
    print(msg, file=sys.stderr)
    sys.exit(2)
