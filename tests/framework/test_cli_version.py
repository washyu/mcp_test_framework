"""mcp-contracts version regression: CLI version command resolves the dist name.

Pins the cli.py version-command fix -- before the dist rename, the lookup
string was `metadata.version("mvp-test-framework")` which would raise
PackageNotFoundError post-rename, silently falling back to the hard-coded
`__version__` constant. This test belt-and-suspenders the wheel-shape
gate by also asserting the source-of-truth string in cli.py itself, so a
future refactor that moves the lookup string elsewhere still fails loudly.
"""
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

import mcp_test_framework.cli as cli_mod
from mcp_test_framework.cli import app


def _invoke(*args: str):
    return CliRunner().invoke(app, list(args))


def test_version_command_exits_zero_with_non_empty_output() -> None:
    """`version` command runs to completion. Output is either the
    installed-dist version or the `__version__` fallback -- both acceptable.
    The regression is that the command does not crash with the wrong
    distribution-name argument.
    """
    result = _invoke("version")
    assert result.exit_code == 0
    assert result.stdout.strip() != ""


def test_cli_source_references_new_dist_name() -> None:
    """The literal `metadata.version("mcp-contracts")` appears in cli.py;
    the legacy `metadata.version("mvp-test-framework")` does NOT.
    """
    src = Path(cli_mod.__file__).read_text(encoding="utf-8")
    assert 'metadata.version("mcp-contracts")' in src, (
        "cli.py is missing the post-rename dist-name lookup; "
        "expected `metadata.version(\"mcp-contracts\")`"
    )
    assert 'metadata.version("mvp-test-framework")' not in src, (
        "cli.py still contains the legacy `metadata.version(\"mvp-test-framework\")` "
        "lookup string -- regression"
    )
