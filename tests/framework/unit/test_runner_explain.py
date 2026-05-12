"""Phase 16 D-05/D-06/D-08/D-09: --explain Typer flag end-to-end tests.

Pins:
- --explain is registered in `run --help` (inverse of Phase 14 D-14)
- --explain expands the Skipping bucket to one line per tool, sorted, em-dash
- --explain composes correctly with -q (quiet wins), --raw (raw bypasses),
  --with-framework (framework suffix coexists)
- --explain is NEVER forwarded to pytest (wrapper-owned per D-07)
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest


_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _invoke(*args: str):
    from typer.testing import CliRunner
    from mcp_test_framework.cli import app
    return CliRunner().invoke(app, list(args))


def _stub_subprocess_writing_xml(fixture_name: str, returncode: int = 0):
    fixture_content = (_FIXTURES / fixture_name).read_text(encoding="utf-8")

    def _fake(argv, **kwargs):
        junit_args = [
            a for a in argv if isinstance(a, str) and a.startswith("--junitxml=")
        ]
        if junit_args:
            path = Path(junit_args[-1].split("=", 1)[1])
            path.write_text(fixture_content, encoding="utf-8")
        # D-07 guard: --explain must never reach pytest's argv.
        assert "--explain" not in argv, "--explain leaked to pytest argv"
        return SimpleNamespace(
            returncode=returncode, stdout="...", stderr="", args=argv
        )

    return _fake


def _make_valid_config(tmp_path: Path, tools: dict | None = None) -> Path:
    """Minimal config.yaml. `tools` dict controls which tools are in
    tools_config (state-b) vs absent (state-a)."""
    cfg = tmp_path / "config.yaml"
    if not tools:
        tools_yaml = "tools: {}\n"
    else:
        tools_yaml = "tools:\n"
        for name, spec in tools.items():
            tools_yaml += f"  {name}:\n"
            wrote_child = False
            if spec.get("skip"):
                tools_yaml += "    skip: true\n"
                wrote_child = True
                if "skip_reason" in spec:
                    tools_yaml += f"    skip_reason: \"{spec['skip_reason']}\"\n"
            judges = spec.get("judges", [])
            if judges:
                tools_yaml += f"    judges: {judges}\n"
                wrote_child = True
            if not wrote_child:
                tools_yaml += "    {}\n"
    cfg.write_text(
        "version: 2\n"
        "ollama:\n  base_url: http://127.0.0.1:11434\n  model: q\n"
        "mcp_server:\n  command: uvx\n  args: [homelab-mcp]\n"
        + tools_yaml,
        encoding="utf-8",
    )
    return cfg


# ---------------------------------------------------------------------------
# Help registration (inverts Phase 14's negative test)
# ---------------------------------------------------------------------------


def test_run_help_lists_explain_flag() -> None:
    """Phase 16 D-07: --explain is owned by the Typer wrapper, registered here.
    Inverts Phase 14 D-14's negative test (which is updated separately)."""
    result = _invoke("run", "--help")
    assert result.exit_code == 0, result.output
    assert "--explain" in result.output


def test_run_help_explain_mentions_raw_and_quiet_interactions() -> None:
    """D-08: --explain help text must document composition with --raw and -q."""
    result = _invoke("run", "--help")
    assert result.exit_code == 0
    out = result.output.lower()
    assert "--explain" in out
    assert "--raw" in out, "--explain help should mention --raw composition"
    assert "-q" in out or "--quiet" in out, "--explain help should mention quiet"


# ---------------------------------------------------------------------------
# Skipping block shape (D-05 / D-06)
# ---------------------------------------------------------------------------


def test_run_explain_lists_skipped_tools_alphabetically(monkeypatch, tmp_path) -> None:
    cfg = _make_valid_config(tmp_path, tools={"alpha": {"judges": ["clarity"]}})
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_writing_xml("junit-all-pass.xml"),
    )
    # Discovered: alpha (running), gamma + beta (skipping state-a, sorted in explain).
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha", "gamma", "beta"],
    )
    result = _invoke("run", "--explain", "--config", str(cfg))
    assert result.exit_code == 0, result.output
    out = result.output
    assert "MCP Test Framework" in out  # digest still emits
    assert "Skipping (2):" in out
    # em-dash present, sort order beta < gamma.
    assert "—" in out, repr(out)
    beta_idx = out.index("beta")
    gamma_idx = out.index("gamma")
    assert beta_idx < gamma_idx, "explain sort order broken"
    # state-a reason verbatim.
    assert "not selected in config" in out


def test_run_explain_renders_after_digest_before_pytest(monkeypatch, tmp_path) -> None:
    """D-06: digest -> Skipping block -> pytest output order."""
    cfg = _make_valid_config(tmp_path, tools={"alpha": {}})
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_writing_xml("junit-all-pass.xml"),
    )
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha", "beta"],
    )
    result = _invoke("run", "--explain", "--config", str(cfg))
    out = result.output
    digest_idx = out.index("MCP Test Framework")
    explain_idx = out.index("Skipping (1):")
    result_idx = out.index("Result:")
    assert digest_idx < explain_idx < result_idx, (
        f"order: digest={digest_idx} explain={explain_idx} result={result_idx}\n{out}"
    )


# ---------------------------------------------------------------------------
# Composition (D-08 / D-09)
# ---------------------------------------------------------------------------


def test_run_quiet_with_explain_is_noop(monkeypatch, tmp_path) -> None:
    """D-09 / UX-05: -q suppresses BOTH digest AND --explain expansion."""
    cfg = _make_valid_config(tmp_path, tools={"alpha": {}})
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_writing_xml("junit-all-pass.xml"),
    )
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha", "beta"],
    )
    result = _invoke("run", "-q", "--explain", "--config", str(cfg))
    assert result.exit_code == 0, result.output
    assert "MCP Test Framework" not in result.output  # no digest
    assert "Skipping (" not in result.output  # no explain block
    assert "Result:" in result.output  # summary line only


def test_run_raw_with_explain_is_bypassed(monkeypatch, tmp_path) -> None:
    """D-08: --raw bypasses domain UI entirely; --explain has no effect."""
    cfg = _make_valid_config(tmp_path, tools={"alpha": {}})

    def _fake_subprocess(argv, **kwargs):
        # Under --raw, no tempfile is written by the wrapper; just return rc=0.
        # --explain must NOT appear in argv (wrapper-owned).
        assert "--explain" not in argv
        return SimpleNamespace(returncode=0, stdout="", stderr="", args=argv)

    monkeypatch.setattr("mcp_test_framework._runner.subprocess.run", _fake_subprocess)
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha", "beta"],
    )
    result = _invoke("run", "--raw", "--explain", "--config", str(cfg))
    # --raw exits via Typer.Exit with the mapped pytest exit code (0 here).
    assert result.exit_code == 0, result.output
    assert "MCP Test Framework" not in result.output
    assert "Skipping (" not in result.output


def test_run_explain_with_with_framework_emits_suffix(monkeypatch, tmp_path) -> None:
    """D-03 / D-08: --explain --with-framework: digest gets the suffix,
    Skipping block lists tool-side skips only."""
    cfg = _make_valid_config(tmp_path, tools={"alpha": {}})
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_writing_xml("junit-all-pass.xml"),
    )
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha", "beta"],
    )
    result = _invoke("run", "--explain", "--with-framework", "--config", str(cfg))
    assert result.exit_code == 0, result.output
    assert "+ framework self-tests" in result.output
    assert "Skipping (1):" in result.output


def test_run_default_emits_digest_without_explain_block(monkeypatch, tmp_path) -> None:
    """D-01: default mode emits digest but NOT the Skipping (N): block."""
    cfg = _make_valid_config(tmp_path, tools={"alpha": {}})
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_writing_xml("junit-all-pass.xml"),
    )
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha", "beta"],
    )
    result = _invoke("run", "--config", str(cfg))
    assert result.exit_code == 0, result.output
    assert "MCP Test Framework" in result.output  # digest emits
    assert "(use --explain to list)" in result.output  # hint stays
    assert "Skipping (1):" not in result.output  # no inline expansion


def test_run_default_post_run_has_no_second_banner(monkeypatch, tmp_path) -> None:
    """D-01: post-run output (per-tool rows + summary) MUST NOT include
    a second `MCP Test Framework` banner. Banner appears exactly once."""
    cfg = _make_valid_config(tmp_path, tools={"alpha": {}})
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_writing_xml("junit-all-pass.xml"),
    )
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha"],
    )
    result = _invoke("run", "--config", str(cfg))
    assert result.exit_code == 0, result.output
    assert result.output.count("MCP Test Framework") == 1, (
        f"banner repeated: {result.output!r}"
    )


# REVISION (checker WARNING 4): the digest's "(use --explain to list)" hint
# must be omitted when --explain is set (the list is right there inline; the
# hint would lie). Pinned here at the CLI end-to-end layer.


def test_run_default_includes_explain_hint(monkeypatch, tmp_path) -> None:
    """WARNING 4: default mode (no --explain) shows the hint string."""
    cfg = _make_valid_config(tmp_path, tools={"alpha": {}})
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_writing_xml("junit-all-pass.xml"),
    )
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha", "beta"],
    )
    result = _invoke("run", "--config", str(cfg))
    assert result.exit_code == 0, result.output
    assert "(use --explain to list)" in result.output


def test_run_explain_suppresses_hint(monkeypatch, tmp_path) -> None:
    """WARNING 4: --explain mode omits the hint (the list is inline below)."""
    cfg = _make_valid_config(tmp_path, tools={"alpha": {}})
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_writing_xml("junit-all-pass.xml"),
    )
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha", "beta"],
    )
    result = _invoke("run", "--explain", "--config", str(cfg))
    assert result.exit_code == 0, result.output
    assert "(use --explain to list)" not in result.output, (
        f"hint should be suppressed under --explain: {result.output!r}"
    )
    # Sanity: the Skipping (N): block header still emits.
    assert "Skipping (1):" in result.output
