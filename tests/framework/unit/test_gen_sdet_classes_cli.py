"""CLI tests for `mcp-test-framework gen-sdet-classes` (CODEGEN-01).

Pins:
  - --help works and lists --config
  - SAFE-03 fail-loud when no config is discoverable (Phase 13 D-03)
  - --config <path-not-found> fails with exit 2
  - MCP-server-not-on-PATH operator-tone error path
  - End-to-end emission against a stub MCP server (subprocess) writes the
    expected directory tree

Live-homelab smoke (only when @pytest.mark.live_homelab is opted in) confirms
real-world behavior against the actual homelab-mcp.
"""
from __future__ import annotations

import shutil
import textwrap
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from mcp_test_framework.cli import app


def _invoke(*args: str, env: dict | None = None):
    """CliRunner construction site -- isolated for forward-compat with Typer
    kwarg changes. Pattern lifted from tests/framework/test_config_init_cli.py:22-25.
    """
    return CliRunner().invoke(app, list(args), env=env or {})


def _write_config(
    tmp_path: Path,
    *,
    command: str,
    args: list[str] | None = None,
    generated_root: Path | None = None,
) -> Path:
    """Build a config.yaml under tmp_path including the Phase 21.1 RELOC-01
    required ``test_code.generated_root`` field. Defaults to ``<tmp_path>/_generated``.
    """
    if generated_root is None:
        generated_root = tmp_path / "_generated"
    cfg_path = tmp_path / "config.yaml"
    payload = {
        "version": 2,
        "mcp_server": {
            "command": command,
            "args": args or [],
            "timeout_seconds": 30,
        },
        # Phase 21.1 RELOC-01: required field. Tests point it at tmp_path so
        # no test writes generated .py files into the installed framework dir.
        "test_code": {"generated_root": str(generated_root)},
    }
    cfg_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return cfg_path


def test_help_lists_flags() -> None:
    """The canonical command exposes --config; --output-dir and --force are
    deliberately absent per D-08. (The legacy `gen-sdet-classes` alias was
    removed in v1.5; its `--config` is now hidden so it no longer appears
    in --help.)"""
    result = _invoke("gen-test-classes", "--help")
    assert result.exit_code == 0, result.output
    assert "gen-test-classes" in result.output
    assert "--config" in result.output
    # No --output-dir or --force per D-08
    assert "--output-dir" not in result.output
    assert "--force" not in result.output


def test_no_config_safe03_fails_loud(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SAFE-03: no --config, no MCPTF_CONFIG_FILE, no ./config.yaml -> exit 2."""
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
    monkeypatch.chdir(tmp_path)  # ensure no ./config.yaml is discoverable
    result = _invoke("gen-test-classes")
    assert result.exit_code == 2, result.output


def test_config_path_not_found_fails_loud(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
    monkeypatch.chdir(tmp_path)
    fake = tmp_path / "does-not-exist.yaml"
    result = _invoke("gen-test-classes", "--config", str(fake))
    assert result.exit_code == 2, result.output


def test_mcp_command_not_on_path_operator_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FileNotFoundError branch: operator-tone error + exit 2."""
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
    cfg = _write_config(tmp_path, command="this-command-does-not-exist-anywhere-12345")
    result = _invoke("gen-test-classes", "--config", str(cfg))
    assert result.exit_code == 2, result.output
    # Operator-tone error mentioning the missing command
    assert "this-command-does-not-exist-anywhere-12345" in result.output
    assert "not found" in result.output.lower() or "not on PATH" in result.output


# --- Stub-server end-to-end ----------------------------------------------

_STUB_SERVER_SOURCE = textwrap.dedent('''\
    """Minimal MCP server for gen-sdet-classes E2E testing.

    Implements just enough of the MCP protocol to:
      - respond to `initialize` with a fixed serverInfo
      - respond to `list_tools` with a fixed 2-tool set
    Built on the official mcp Python SDK.
    """
    from mcp.server.fastmcp import FastMCP

    app = FastMCP("stub-server-for-codegen-test")


    @app.tool()
    def create_thing(name: str, quantity: int = 1) -> dict:
        """Create a thing."""
        return {"id": f"thing-{name}", "qty": quantity}


    @app.tool()
    def delete_thing(thing_id: str) -> dict:
        """Delete a thing."""
        return {"deleted": thing_id}


    if __name__ == "__main__":
        app.run()
    ''')


@pytest.mark.skipif(
    shutil.which("python") is None and shutil.which("python3") is None,
    reason="no python on PATH for stub-server spawn",
)
def test_e2e_emits_generated_dir_for_stub_server(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Drive the full pipeline against a stub MCP server. Asserts that
    ``<cfg.sdet.generated_root>/<slug>/`` contains per-tool files + __init__.py.

    Phase 21.1 RELOC-03 reworked: writes into tmp_path, not the installed
    framework package -- gen-test-classes resolves out_root from cfg now.

    Phase 25 RENAME-02: invoke under the new command name `gen-test-classes`;
    the legacy `gen-sdet-classes` is still callable as a deprecation shim
    but the canonical surface this test pins is the new name. The
    AUTOGENERATED header marker emitted by _codegen.py still references
    `gen-sdet-classes` -- that string lives in _codegen.py and is
    owned by the plan 06 terminology sweep, not plan 02.
    """
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
    stub_path = tmp_path / "stub_server.py"
    stub_path.write_text(_STUB_SERVER_SOURCE, encoding="utf-8")

    import sys
    generated_root = tmp_path / "_generated"
    cfg = _write_config(
        tmp_path,
        command=sys.executable,
        args=[str(stub_path)],
        generated_root=generated_root,
    )

    target_slug_dir = generated_root / "stub_server_for_codegen_test"

    result = _invoke("gen-test-classes", "--config", str(cfg))
    assert result.exit_code == 0, f"stdout: {result.output}\nexc: {result.exception}"

    # Layout assertions
    assert target_slug_dir.is_dir(), result.output
    assert (target_slug_dir / "create_thing.py").is_file()
    assert (target_slug_dir / "delete_thing.py").is_file()
    assert (target_slug_dir / "__init__.py").is_file()

    # Header marker -- now emitted by _codegen.py as `gen-test-classes`;
    # plan 06 (terminology sweep) owns repointing the embedded marker.
    create_text = (target_slug_dir / "create_thing.py").read_text(encoding="utf-8")
    assert "# AUTOGENERATED by mcp-test-framework gen-test-classes -- DO NOT HAND-EDIT." in create_text
    assert "class CreateThingParams(BaseModel):" in create_text
    assert "class CreateThingResponse(ToolResponse):" in create_text

    # __init__.py registry
    init_text = (target_slug_dir / "__init__.py").read_text(encoding="utf-8")
    assert "_REGISTRY:" in init_text
    assert '"create_thing": (CreateThingParams, CreateThingResponse),' in init_text

    # Digest header on stdout -- under the new command name.
    assert "gen-test-classes: wrote test-code classes for" in result.output
    assert "tools:     2 generated" in result.output
    # The target echo should reference the resolved tmp_path location.
    assert str(target_slug_dir) in result.output or str(generated_root) in result.output


@pytest.mark.live_homelab
def test_live_homelab_emit_smoke(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Against live homelab-mcp (gated by marker), confirms gen-test-classes
    populates ``<cfg.test_code.generated_root>/<homelab-mcp-slug>/``.

    Phase 21.1 RELOC-03 reworked: writes into tmp_path, not the installed
    framework package."""
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
    generated_root = tmp_path / "_generated"
    cfg = _write_config(
        tmp_path,
        command="uvx",
        args=["--from", "git+https://github.com/washyu/homelab-mcp", "homelab-mcp"],
        generated_root=generated_root,
    )

    target_slug_dir = generated_root / "homelab_mcp"

    result = _invoke("gen-test-classes", "--config", str(cfg))
    assert result.exit_code == 0, result.output
    assert target_slug_dir.is_dir()
    assert (target_slug_dir / "__init__.py").is_file()
    # At least one tool was generated; the digest names a non-zero count.
    assert "tools:     0 generated" not in result.output


def test_write_config_helper_includes_test_code_generated_root(tmp_path: Path) -> None:
    """Phase 21.1 RELOC-03 regression guard: future test authors must keep
    the ``test_code.generated_root`` field populated in ``_write_config`` payloads.
    """
    cfg_path = _write_config(tmp_path, command="some-command")
    payload = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    assert "test_code" in payload
    assert "generated_root" in payload["test_code"]
    assert payload["test_code"]["generated_root"]  # non-empty
