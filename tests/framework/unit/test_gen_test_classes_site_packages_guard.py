"""Unit + CLI tests for the CODEGEN-LIB-02 pre-handshake site-packages guard.

Covers the four required behaviors:
    1. Descendant-of-install-root abort with exit 2.
    2. Sibling-of-install-root passes (no-op).
    3. Error message names the offending field + paths.
    4. Guard fires BEFORE the MCP handshake (no subprocess spawn).
"""
from __future__ import annotations

from pathlib import Path

import pytest
import typer
import yaml
from typer.testing import CliRunner

import mcp_test_framework
from mcp_test_framework.cli import _guard_against_site_packages_target, app


def _framework_install_root() -> Path:
    return Path(mcp_test_framework.__file__).resolve().parent.parent


def test_guard_aborts_when_target_inside_framework_install_root() -> None:
    install_root = _framework_install_root()
    inside = install_root / "tests_generated"
    with pytest.raises(typer.Exit) as exc_info:
        _guard_against_site_packages_target(inside)
    assert exc_info.value.exit_code == 2


def test_guard_passes_when_target_outside_framework_install_root(tmp_path: Path) -> None:
    # tmp_path is guaranteed outside the install root.
    result = _guard_against_site_packages_target(tmp_path / "_generated")
    assert result is None


def test_guard_passes_when_target_is_sibling_of_install_root() -> None:
    install_root = _framework_install_root()
    sibling = install_root.parent / "_sibling_generated"
    result = _guard_against_site_packages_target(sibling)
    assert result is None


def test_guard_error_message_names_field_and_paths(
    capsys: pytest.CaptureFixture[str],
) -> None:
    install_root = _framework_install_root()
    inside = install_root / "leak_target"
    with pytest.raises(typer.Exit):
        _guard_against_site_packages_target(inside)
    captured = capsys.readouterr()
    combined = captured.err + captured.out
    assert "test_code.generated_root" in combined
    assert str(install_root) in combined
    assert str(inside.resolve()) in combined


def _write_config_with_generated_root(tmp_path: Path, generated_root: Path) -> Path:
    cfg_path = tmp_path / "config.yaml"
    payload = {
        "version": 2,
        "mcp_server": {
            # Sentinel that would otherwise raise FileNotFoundError if the
            # handshake were attempted. The guard MUST fire first.
            "command": "this-command-never-exists-and-must-not-be-spawned",
            "args": [],
        },
        "test_code": {
            "generated_root": str(generated_root),
        },
        "tools": {},
    }
    cfg_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return cfg_path


def test_gen_test_classes_cli_aborts_before_handshake_when_target_inside_install_root(
    tmp_path: Path,
) -> None:
    install_root = _framework_install_root()
    inside = install_root / "blocked_target"
    cfg_path = _write_config_with_generated_root(tmp_path, inside)
    runner = CliRunner()
    result = runner.invoke(app, ["gen-test-classes", "--config", str(cfg_path)])
    assert result.exit_code == 2
    combined = result.stdout + (result.stderr if hasattr(result, "stderr") else "")
    # Guard message present:
    assert "test_code.generated_root" in combined
    # MCP-server-not-on-PATH message absent (handshake never attempted):
    assert "MCP server command not found" not in combined
    assert "MCP server failed to start" not in combined
