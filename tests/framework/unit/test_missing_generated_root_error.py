"""Regression test for the missing-`test_code.generated_root` operator error.

Locks two literal-string requirements in the operator-facing error rendered
when a config has a `test_code:` block but no `generated_root` field:

    1. The full field path `test_code.generated_root` appears verbatim.
    2. The next-step copy points at `mcp-contracts config-init` (the
       canonical v1.4 CLI name), NOT the legacy `mcp-test-framework
       config-init` (which only survives as a working compatibility shim
       through the v1.4 deprecation window and is removed in v1.5).

The operator-tone error is the first contact point with the fail-loud
missing-field path; the legacy CLI name must not appear in any
operator-facing next-step copy along this branch.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from mcp_test_framework.cli import app


def _write_no_generated_root_config(tmp_path: Path) -> Path:
    cfg_path = tmp_path / "config.yaml"
    payload = {
        "version": 2,
        "mcp_server": {"command": "irrelevant", "args": []},
        "test_code": {},  # NO generated_root field
        "tools": {},
    }
    cfg_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return cfg_path


def test_missing_generated_root_error_names_field_and_config_init(
    tmp_path: Path,
) -> None:
    """The missing-`test_code.generated_root` error must name the field path
    AND point at `mcp-contracts config-init` for scaffold generation."""
    cfg_path = _write_no_generated_root_config(tmp_path)
    runner = CliRunner()
    # `run` is the most common operator entry into this error path.
    result = runner.invoke(app, ["run", "--config", str(cfg_path)])

    # The CliRunner version available here may collapse stderr into stdout
    # depending on Click version; combine both to stay version-tolerant.
    stderr = result.stderr if result.stderr is not None else ""
    combined = result.stdout + stderr

    assert result.exit_code == 2, (
        f"expected exit 2 for missing required field; got "
        f"{result.exit_code}.\noutput:\n{combined}"
    )
    # Literal-string requirements:
    assert "test_code.generated_root" in combined, (
        "operator error must name the missing field by full path; got:\n"
        + combined
    )
    assert "mcp-contracts config-init" in combined, (
        "operator next-step must point at `mcp-contracts config-init`; "
        "got:\n" + combined
    )
    # Negative assertion: legacy CLI name must not appear in next-step copy.
    assert "mcp-test-framework config-init" not in combined, (
        "operator next-step must use canonical `mcp-contracts`, not the "
        "legacy v1.4-deprecated `mcp-test-framework` command name; got:\n"
        + combined
    )
