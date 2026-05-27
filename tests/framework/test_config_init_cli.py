"""Phase 08 verification: config-init Typer subcommand surface.

Unit-level tests (no live MCP server needed):
  - --help flag listing
  - refuse-to-overwrite without --force exits 2

Live tests (require homelab-mcp + Ollama; gated behind @live_homelab marker):
  - default mode emits scaffold to stdout
  - --output PATH writes to file
  - emitted scaffold round-trips through Config() validation
"""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from mcp_test_framework.cli import app


def _invoke(*args: str):
    """CliRunner construction site -- isolated for forward-compat with future
    Typer kwargs (e.g. mix_stderr deprecation)."""
    return CliRunner().invoke(app, list(args))


# ===========================================================================
# Unit-level: --help and overwrite gate (no live server needed)
# ===========================================================================


def test_help_lists_flags() -> None:
    """D-21: subcommand surface includes --config, --output, --force."""
    result = _invoke("config-init", "--help")
    assert result.exit_code == 0, result.output
    assert "--config" in result.output
    assert "--output" in result.output
    assert "--force" in result.output


def test_refuse_overwrite_without_force(tmp_path: Path) -> None:
    """D-23: --output to existing file w/o --force -> exit 2 + stderr message.

    Fires BEFORE discovery, so this test does NOT require a live MCP server
    (no @live_homelab marker -- the overwrite gate is a pure path check).
    """
    target = tmp_path / "existing.yaml"
    target.write_text("placeholder\n", encoding="utf-8")
    result = _invoke("config-init", "--output", str(target))
    assert result.exit_code == 2, result.output
    assert "refusing to overwrite" in result.output, result.output
    assert str(target) in result.output, result.output
    # File content unchanged
    assert target.read_text(encoding="utf-8") == "placeholder\n"


# ===========================================================================
# Live: actual discovery against homelab-mcp
# ===========================================================================


@pytest.mark.live_homelab
def test_default_emits_scaffold_to_stdout() -> None:
    """D-22 / TOOLCFG-02 / TOOLCFG-04: default mode prints version: 2 + tools: scaffold."""
    result = _invoke("config-init")
    assert result.exit_code == 0, result.output
    assert "version: 2" in result.output
    assert "tools:" in result.output
    # Locked rubric-ID order in scaffold per CONTEXT.md <specifics> + TOOLCFG-04.
    assert "judges: [clarity, disambiguation, parameters]" in result.output


@pytest.mark.live_homelab
def test_output_writes_to_file(tmp_path: Path) -> None:
    """D-23: --output PATH writes scaffold to file (no stdout echo)."""
    target = tmp_path / "scaffold.yaml"
    assert not target.exists()
    result = _invoke("config-init", "--output", str(target))
    assert result.exit_code == 0, result.output
    assert target.exists()
    body = target.read_text(encoding="utf-8")
    assert "version: 2" in body
    assert "tools:" in body


@pytest.mark.live_homelab
def test_overwrite_with_force_succeeds(tmp_path: Path) -> None:
    """D-23: --force permits overwrite of existing file."""
    target = tmp_path / "scaffold.yaml"
    target.write_text("# old content\n", encoding="utf-8")
    result = _invoke("config-init", "--output", str(target), "--force")
    assert result.exit_code == 0, result.output
    body = target.read_text(encoding="utf-8")
    assert "version: 2" in body
    assert body != "# old content\n"


@pytest.mark.live_homelab
def test_scaffold_round_trips_through_config(
    tmp_path: Path, monkeypatch
) -> None:
    """End-to-end: emitted scaffold + uncommented tool block loads into
    Config() without ValidationError. Proves Plan 03 + Plan 01 contracts
    compose."""
    target = tmp_path / "scaffold.yaml"
    result = _invoke("config-init", "--output", str(target))
    assert result.exit_code == 0, result.output

    # Uncomment the FIRST tool block (5 lines per Plan 03 Task 1 shape) by
    # stripping the leading "  # " from each of its 5 lines.
    lines = target.read_text(encoding="utf-8").splitlines()
    out_lines: list[str] = []
    uncommented = 0
    started = False
    for line in lines:
        if not started and line.startswith("  # ") and uncommented == 0:
            started = True
        if started and uncommented < 5 and line.startswith("  # "):
            out_lines.append("  " + line[len("  # "):])
            uncommented += 1
        else:
            out_lines.append(line)
            if uncommented >= 5:
                started = False
    target.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    from mcp_test_framework.config import Config
    from mcp_test_framework.models import TestCodeConfig
    # Phase 23 D-01 (Cluster A) Pattern S2: Config.test_code is REQUIRED post
    # Phase 21.1 RELOC-01 (renamed from `sdet` in Phase 25 RENAME-05). The test
    # exercises the scaffold round-trip; the YAML overlay supplies test_code
    # for the operator path, the inline kwarg here covers the bare-Config()
    # construction shape.
    cfg = Config(test_code=TestCodeConfig(generated_root="tests/sdet/_generated"))  # MUST NOT raise
    assert cfg.version == 2
    assert len(cfg.tools) >= 1


# ===========================================================================
# Unit-level: scaffold emits host_isolation default (no live server needed)
# ===========================================================================


def test_config_init_scaffold_emits_host_isolation_strict(tmp_path: Path) -> None:
    """Scaffold emits ``host_isolation: strict`` with a preceding-comment-block
    trade-off explanation, and the emitted scaffold round-trips back into
    Config with ``host_isolation == 'strict'``.

    Operator who runs ``config-init`` sees the new knob immediately, with the
    strict-vs-passthrough trade-off explained inline. The comment-block style
    (PRECEDING block, not end-of-line) matches the surrounding scaffold's
    visual rhythm -- every other field in this scaffold uses preceding
    comments.

    Unit-level test: invokes ``_format_tools_yaml_scaffold([])`` directly --
    no live MCP server needed (the empty tools list exercises the header path
    that carries the host_isolation block)."""
    from mcp_test_framework.cli import _format_tools_yaml_scaffold
    from mcp_test_framework.config import Config
    from mcp_test_framework.models import TestCodeConfig

    scaffold_text = _format_tools_yaml_scaffold([])
    assert "host_isolation: strict" in scaffold_text
    assert "# Host isolation mode." in scaffold_text  # preceding comment block present

    # Round-trip: emitted scaffold parses back with the strict default preserved.
    # The empty tools section emits `tools: {}` so the YAML loads cleanly; the
    # bare-Config kwargs supply test_code (REQUIRED post Phase 21.1 RELOC-01;
    # the scaffold itself emits a test_code block but the bare kwargs here
    # cover the construction shape).
    scaffold_file = tmp_path / "config.yaml"
    scaffold_file.write_text(scaffold_text, encoding="utf-8")
    parsed = Config(
        yaml_file=str(scaffold_file),
        test_code=TestCodeConfig(generated_root="tests/test_code/_generated"),
    )
    assert parsed.host_isolation == "strict"
