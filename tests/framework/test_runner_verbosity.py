"""Phase 14 Plan 04 unit tests: verbosity ladder (-q / default / --debug).

Pins Phase 14 D-12/D-13/D-14 + RUNNER-04 invariants:
  - -q is Typer-level (not forwarded to pytest)
  - --debug appends AFTER the domain UI (default unchanged)
  - --explain is NOT registered (Phase 16 owns it)
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from mcp_test_framework._runner import (
    ParsedRun,
    RenderContext,
    parse_junit_xml,
    render_debug_appendix,
    render_domain_ui,
    render_summary_only,
)
from mcp_test_framework.cli import app


_FIXTURES = Path(__file__).parent / "fixtures"


def _invoke(*args):
    return CliRunner().invoke(app, list(args))


def _ctx(discovered=None) -> RenderContext:
    return RenderContext(
        server_cmd="uvx homelab-mcp",
        discovered_tools=discovered or ["alpha", "beta", "gamma"],
        tools_config={},
        judges=["clarity"],
        total_planned_cases=0,
    )


# ---------------------------------------------------------------------------
# render_summary_only
# ---------------------------------------------------------------------------

def test_render_summary_only_prints_only_summary_line(capsys) -> None:
    parsed = parse_junit_xml(_FIXTURES / "junit-mixed.xml")
    render_summary_only(parsed, _ctx(discovered=["alpha", "gamma", "mango", "zoo"]))
    out = capsys.readouterr().out
    assert "Result:" in out
    # No header strings.
    assert "MCP Test Framework" not in out
    assert "MCP server:" not in out
    assert "Discovered:" not in out
    assert "Running:" not in out
    # No per-tool row sections.
    assert "failures:" not in out
    assert "skipped:" not in out
    assert "passing:" not in out


def test_render_summary_only_includes_state_a_in_skip_count(capsys) -> None:
    """State-(a) SKIPs count toward summary even in quiet mode."""
    parsed = parse_junit_xml(_FIXTURES / "junit-all-pass.xml")  # 3 PASS
    # Discovered includes 2 extra tools not in tools_config -> state-(a) SKIPs.
    ctx = _ctx(discovered=["alpha", "beta", "gamma", "extra1", "extra2"])
    render_summary_only(parsed, ctx)
    out = capsys.readouterr().out
    assert "3 PASS / 0 FAIL / 2 SKIP" in out


# ---------------------------------------------------------------------------
# render_debug_appendix
# ---------------------------------------------------------------------------

def test_render_debug_appendix_emits_separator_and_stdout(capsys) -> None:
    parsed = parse_junit_xml(_FIXTURES / "junit-all-pass.xml")
    render_debug_appendix(
        captured_stdout="pytest output line 1\npytest output line 2",
        captured_stderr="",
        parsed=parsed,
    )
    out = capsys.readouterr().out
    assert "--- raw pytest output ---" in out
    assert "pytest output line 1" in out
    assert "pytest output line 2" in out


def test_render_debug_appendix_includes_failure_body_when_present(capsys) -> None:
    parsed = parse_junit_xml(_FIXTURES / "junit-one-fail-with-reasoning.xml")
    render_debug_appendix(
        captured_stdout="",
        captured_stderr="",
        parsed=parsed,
    )
    out = capsys.readouterr().out
    assert "--- failure tracebacks ---" in out
    # The fixture's failure body contains 'AssertionError'.
    assert "AssertionError" in out


def test_render_debug_appendix_omits_failures_section_when_no_fails(capsys) -> None:
    parsed = parse_junit_xml(_FIXTURES / "junit-all-pass.xml")
    render_debug_appendix(
        captured_stdout="some output",
        captured_stderr="",
        parsed=parsed,
    )
    out = capsys.readouterr().out
    assert "--- raw pytest output ---" in out
    assert "--- failure tracebacks ---" not in out


def test_render_debug_appendix_emits_stderr_section_when_nonempty(capsys) -> None:
    parsed = parse_junit_xml(_FIXTURES / "junit-all-pass.xml")
    render_debug_appendix(
        captured_stdout="stdout content",
        captured_stderr="stderr content",
        parsed=parsed,
    )
    out = capsys.readouterr().out
    assert "--- captured stderr ---" in out
    assert "stderr content" in out


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------

def test_run_help_lists_quiet_and_debug() -> None:
    result = _invoke("run", "--help")
    assert result.exit_code == 0, result.output
    assert "--quiet" in result.output or "-q" in result.output
    assert "--debug" in result.output


def test_run_help_does_not_list_explain() -> None:
    """D-14: --explain is owned by Phase 16, not Phase 14."""
    result = _invoke("run", "--help")
    assert result.exit_code == 0, result.output
    # `--explain` flag MUST NOT appear in the help text. The literal
    # string "use --explain to list" IS allowed inside the header at
    # runtime (forward-reference hint) but is not in `--help`.
    assert "--explain " not in result.output
    assert "--explain\n" not in result.output


# ---------------------------------------------------------------------------
# CLI end-to-end with mocked subprocess (verbosity branching)
# ---------------------------------------------------------------------------

def _stub_subprocess_writing_xml(fixture_name: str, returncode: int = 0):
    """Build a fake subprocess.run that writes a pre-canned fixture XML to
    the last --junitxml=PATH arg before returning."""
    fixture_content = (_FIXTURES / fixture_name).read_text(encoding="utf-8")

    def _fake(argv, **kwargs):
        junit_args = [a for a in argv if isinstance(a, str) and a.startswith("--junitxml=")]
        if junit_args:
            path = Path(junit_args[-1].split("=", 1)[1])
            path.write_text(fixture_content, encoding="utf-8")
        return SimpleNamespace(
            returncode=returncode,
            stdout="=== test session starts ===\n....\n4 passed\n",
            stderr="",
            args=argv,
        )
    return _fake


def _make_valid_config(tmp_path: Path) -> Path:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "version: 2\nollama:\n  base_url: http://127.0.0.1:11434\n  model: q\n"
        "mcp_server:\n  command: uvx\n  args: [homelab-mcp]\ntools: {}\n",
        encoding="utf-8",
    )
    return cfg


def test_run_quiet_renders_summary_only(monkeypatch, tmp_path) -> None:
    """End-to-end: -q produces no header strings."""
    cfg = _make_valid_config(tmp_path)
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_writing_xml("junit-all-pass.xml"),
    )
    # Stub discovery so the test does not actually spawn an MCP server.
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha", "beta", "gamma"],
    )

    result = _invoke("run", "-q", "--config", str(cfg))
    assert result.exit_code == 0, result.output
    assert "Result:" in result.output
    assert "MCP Test Framework" not in result.output
    assert "Discovered:" not in result.output


def test_run_default_renders_full_domain_ui(monkeypatch, tmp_path) -> None:
    cfg = _make_valid_config(tmp_path)
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_writing_xml("junit-all-pass.xml"),
    )
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha", "beta", "gamma"],
    )

    result = _invoke("run", "--config", str(cfg))
    assert result.exit_code == 0, result.output
    # Phase 16 D-01: header moved pre-run. Plan 16-01 removed the call site
    # from render_domain_ui; Plan 16-02 will wire _render_pre_run_digest in
    # cli.py. Until 16-02 lands, default-mode CLI output omits the banner.
    assert "MCP Test Framework" not in result.output
    assert "Result:" in result.output
    # No pytest framing.
    assert "test session starts" not in result.output


def test_run_debug_appends_appendix_after_domain_ui(monkeypatch, tmp_path) -> None:
    cfg = _make_valid_config(tmp_path)
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_writing_xml("junit-all-pass.xml"),
    )
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha", "beta", "gamma"],
    )

    result = _invoke("run", "--debug", "--config", str(cfg))
    assert result.exit_code == 0, result.output
    # D-13 invariant + Phase 16 D-01: header moved pre-run (wired in Plan 16-02);
    # appendix still appears after the per-tool rows in the post-run output.
    assert "--- raw pytest output ---" in result.output
    # Order: per-tool rows ("passing:") BEFORE the appendix.
    passing_idx = result.output.index("Result:")
    appendix_idx = result.output.index("--- raw pytest output ---")
    assert passing_idx < appendix_idx


def test_run_quiet_plus_debug_renders_summary_then_appendix(
    monkeypatch, tmp_path,
) -> None:
    """-q + --debug = summary-only THEN debug appendix.
    D-13 invariant: --debug appends to whatever rung below produced."""
    cfg = _make_valid_config(tmp_path)
    monkeypatch.setattr(
        "mcp_test_framework._runner.subprocess.run",
        _stub_subprocess_writing_xml("junit-all-pass.xml"),
    )
    monkeypatch.setattr(
        "mcp_test_framework.cli._discover_tools_for_run",
        lambda c: ["alpha", "beta", "gamma"],
    )

    result = _invoke("run", "-q", "--debug", "--config", str(cfg))
    assert result.exit_code == 0, result.output
    # No header.
    assert "MCP Test Framework" not in result.output
    # Summary present.
    assert "Result:" in result.output
    # Appendix present.
    assert "--- raw pytest output ---" in result.output
    # Order: Result BEFORE appendix.
    summary_idx = result.output.index("Result:")
    appendix_idx = result.output.index("--- raw pytest output ---")
    assert summary_idx < appendix_idx


def test_run_raw_ignores_quiet_and_debug(monkeypatch, tmp_path) -> None:
    """--raw bypasses all renderers; -q and --debug do not apply.
    The output is pytest's raw stdout (which includes 'test session starts')."""
    cfg = _make_valid_config(tmp_path)

    def _fake_raw(argv, **kwargs):
        # Raw mode does NOT capture; we cannot inspect stdout here. The
        # invariant under test is just "subprocess invoked, no domain UI
        # rendered". We can't see "test session starts" via CliRunner
        # because CliRunner doesn't intercept os-level stdout for raw mode.
        # Pin the absence of domain UI strings instead.
        return SimpleNamespace(returncode=0, stdout="", stderr="", args=argv)
    monkeypatch.setattr("mcp_test_framework._runner.subprocess.run", _fake_raw)

    result = _invoke("run", "--raw", "-q", "--debug", "--config", str(cfg))
    assert result.exit_code == 0, result.output
    assert "MCP Test Framework" not in result.output  # no domain UI header
    assert "Result:" not in result.output  # no domain UI summary
    assert "--- raw pytest output ---" not in result.output  # no appendix
