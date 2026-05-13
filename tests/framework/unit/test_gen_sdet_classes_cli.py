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


def _write_config(tmp_path: Path, *, command: str, args: list[str] | None = None) -> Path:
    cfg_path = tmp_path / "config.yaml"
    payload = {
        "version": 2,
        "mcp_server": {
            "command": command,
            "args": args or [],
            "timeout_seconds": 30,
        },
    }
    cfg_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return cfg_path


def test_help_lists_flags() -> None:
    result = _invoke("gen-sdet-classes", "--help")
    assert result.exit_code == 0, result.output
    assert "gen-sdet-classes" in result.output
    assert "--config" in result.output
    # No --output-dir or --force per D-08
    assert "--output-dir" not in result.output
    assert "--force" not in result.output


def test_no_config_safe03_fails_loud(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SAFE-03: no --config, no MCPTF_CONFIG_FILE, no ./config.yaml -> exit 2."""
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
    monkeypatch.chdir(tmp_path)  # ensure no ./config.yaml is discoverable
    result = _invoke("gen-sdet-classes")
    assert result.exit_code == 2, result.output


def test_config_path_not_found_fails_loud(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
    monkeypatch.chdir(tmp_path)
    fake = tmp_path / "does-not-exist.yaml"
    result = _invoke("gen-sdet-classes", "--config", str(fake))
    assert result.exit_code == 2, result.output


def test_mcp_command_not_on_path_operator_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FileNotFoundError branch: operator-tone error + exit 2."""
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
    cfg = _write_config(tmp_path, command="this-command-does-not-exist-anywhere-12345")
    result = _invoke("gen-sdet-classes", "--config", str(cfg))
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
    """Drive the full pipeline against a stub MCP server. Asserts that the
    generated/<slug>/ directory contains per-tool files + __init__.py with
    the correct CODEGEN-06 header."""
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
    stub_path = tmp_path / "stub_server.py"
    stub_path.write_text(_STUB_SERVER_SOURCE, encoding="utf-8")

    import sys
    cfg = _write_config(
        tmp_path,
        command=sys.executable,
        args=[str(stub_path)],
    )

    # Cleanup whatever the test writes to keep the repo clean.
    import mcp_test_framework
    pkg_root = Path(mcp_test_framework.__file__).parent
    generated_root = pkg_root / "sdet" / "generated"
    target_slug_dir = generated_root / "stub_server_for_codegen_test"

    # NOTE: writes to package dir (not tmp_path) because gen-sdet-classes resolves
    # out_root relative to the installed package; monkeypatching out_root would test
    # a different code path. Pre-test rmtree + try/finally guard against orphaned artifacts.
    if target_slug_dir.exists():
        shutil.rmtree(target_slug_dir)

    try:
        result = _invoke("gen-sdet-classes", "--config", str(cfg))
        # The stub-server may not be reachable in all CI environments; if it
        # spawns successfully the test should pass cleanly. We assert exit 0
        # for the success path.
        assert result.exit_code == 0, f"stdout: {result.output}\nexc: {result.exception}"

        # Layout assertions
        assert target_slug_dir.is_dir(), result.output
        assert (target_slug_dir / "create_thing.py").is_file()
        assert (target_slug_dir / "delete_thing.py").is_file()
        assert (target_slug_dir / "__init__.py").is_file()

        # Header marker
        create_text = (target_slug_dir / "create_thing.py").read_text(encoding="utf-8")
        assert "# AUTOGENERATED by mcp-test-framework gen-sdet-classes -- DO NOT HAND-EDIT." in create_text
        assert "class CreateThingParams(BaseModel):" in create_text
        assert "class CreateThingResponse(ToolResponse):" in create_text

        # __init__.py registry
        init_text = (target_slug_dir / "__init__.py").read_text(encoding="utf-8")
        assert "_REGISTRY:" in init_text
        assert '"create_thing": (CreateThingParams, CreateThingResponse),' in init_text

        # Digest header on stdout
        assert "gen-sdet-classes: wrote SDET classes for" in result.output
        assert "tools:     2 generated" in result.output

    finally:
        if target_slug_dir.exists():
            shutil.rmtree(target_slug_dir)


@pytest.mark.live_homelab
def test_live_homelab_emit_smoke(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Against live homelab-mcp (gated by marker), confirms gen-sdet-classes
    populates src/mcp_test_framework/sdet/generated/<homelab-mcp-slug>/.

    Per existing live-marker convention (test_config_init_cli's live tests).
    """
    monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)
    cfg = _write_config(
        tmp_path,
        command="uvx",
        args=["--from", "git+https://github.com/washyu/homelab-mcp", "homelab-mcp"],
    )

    import mcp_test_framework
    pkg_root = Path(mcp_test_framework.__file__).parent
    generated_root = pkg_root / "sdet" / "generated"
    target_slug_dir = generated_root / "homelab_mcp"
    # NOTE: writes to package dir (not tmp_path) because gen-sdet-classes resolves
    # out_root relative to the installed package; monkeypatching out_root would test
    # a different code path. Pre-test rmtree + try/finally guard against orphaned artifacts.
    if target_slug_dir.exists():
        shutil.rmtree(target_slug_dir)

    try:
        result = _invoke("gen-sdet-classes", "--config", str(cfg))
        assert result.exit_code == 0, result.output
        assert target_slug_dir.is_dir()
        assert (target_slug_dir / "__init__.py").is_file()
        # At least one tool was generated; the digest names a non-zero count.
        assert "tools:     0 generated" not in result.output
    finally:
        if target_slug_dir.exists():
            shutil.rmtree(target_slug_dir)
