"""Phase 18 D-06 unit tests: scenario-aware pre-run digest renderer.

Pins:
- `_render_scenario_pre_run_digest` exists and emits the SDET-flavored header
  (banner "MCP Test Framework (SDET)", running list alphabetized, Skipping
  count + --explain hint or per-scenario expansion, judges-text sentinel
  "(none — SDET scope)" with em-dash U+2014, optional framework breadcrumb,
  digest height <= 10 lines).
- `_collect_test_code_scenarios` enumerates `tests/sdet/test_*.py` stems sorted
  alphabetically; returns empty when the directory is absent.
- The non-SDET `_render_pre_run_digest` byte-shape is preserved (regression
  guard covered by test_runner_pre_run_digest.py; this file does NOT touch
  the tool digest).
- cli.py dispatches the SDET digest under `--sdet` with a fresh sdet-only
  RenderContext (server_cmd only).
"""
from __future__ import annotations

import io
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from mcp_test_framework._runner import (
    RenderContext,
    _collect_test_code_scenarios,
    _render_pre_run_digest,
    _render_scenario_pre_run_digest,
)


def _ctx(server_cmd: str = "uvx homelab-mcp") -> RenderContext:
    return RenderContext(server_cmd=server_cmd)


# ---------------------------------------------------------------------------
# _render_scenario_pre_run_digest shape (D-06)
# ---------------------------------------------------------------------------


def test_scenario_digest_banner_says_sdet(capsys) -> None:
    """D-06: banner identifies the scope as test-code (distinguishable from
    the contract-scope digest's 'MCP Test Framework' banner)."""
    _render_scenario_pre_run_digest(_ctx(), [], {})
    out = capsys.readouterr().out
    lines = out.split("\n")
    assert lines[0] == "=" * 40
    assert lines[1] == "MCP Test Framework (test-code)"
    assert lines[2] == "=" * 40


def test_scenario_digest_running_list_alphabetized(capsys) -> None:
    """D-06: scenario list emitted in alphabetical order regardless of input
    order so output is stable."""
    _render_scenario_pre_run_digest(
        _ctx(), ["proxmox_vm_lifecycle", "basic_call"], {}
    )
    out = capsys.readouterr().out
    assert "Running:      2  (basic_call, proxmox_vm_lifecycle)" in out, repr(out)


def test_scenario_digest_skipping_hint_without_explain(capsys) -> None:
    """D-06: explain=False shows the (use --explain to list) hint, NOT the
    per-scenario expansion."""
    _render_scenario_pre_run_digest(
        _ctx(),
        ["a_scenario"],
        {"flaky_thing": "skip-reason text"},
        explain=False,
    )
    out = capsys.readouterr().out
    assert "Skipping:     1  (use --explain to list)" in out
    assert "flaky_thing" not in out


def test_scenario_digest_explain_expands_per_scenario(capsys) -> None:
    """D-06: explain=True emits one line per skipped scenario, em-dash
    U+2014 separator, two-space hang."""
    _render_scenario_pre_run_digest(
        _ctx(),
        ["a_scenario"],
        {"flaky_thing": "skip-reason text"},
        explain=True,
    )
    out = capsys.readouterr().out
    # Em-dash U+2014 separator with two-space hang under "Skipping:".
    assert "  flaky_thing  — skip-reason text" in out, repr(out)
    # When explain=True, the inline hint is NOT emitted.
    assert "(use --explain to list)" not in out


def test_scenario_digest_with_framework_breadcrumb(capsys) -> None:
    _render_scenario_pre_run_digest(
        _ctx(), ["s"], {}, with_framework=True
    )
    out = capsys.readouterr().out
    assert "+ framework self-tests" in out


def test_scenario_digest_judges_sentinel_uses_em_dash(capsys) -> None:
    """D-06: test-code scope reports judges as '(none — test-code scope)' with
    em-dash U+2014, signaling that test-code runs don't grade with Ollama."""
    _render_scenario_pre_run_digest(_ctx(), ["s"], {})
    out = capsys.readouterr().out
    assert "Judges:      (none — test-code scope)" in out, repr(out)


def test_scenario_digest_height_bounded(capsys) -> None:
    """D-06: scenario digest height <= 10 content lines (matches the lock
    in _render_pre_run_digest)."""
    scenarios = [f"s_{i:02d}" for i in range(70)]
    _render_scenario_pre_run_digest(_ctx(), scenarios, {})
    out = capsys.readouterr().out
    # 8 label lines + 1 trailing blank => max 11 split chunks.
    assert len(out.split("\n")) <= 11, (
        f"got {len(out.split(chr(10)))} lines: {out!r}"
    )


def test_scenario_digest_discovered_total(capsys) -> None:
    """D-06: Discovered line = running + skipping count."""
    _render_scenario_pre_run_digest(
        _ctx(), ["a", "b"], {"c": "reason1", "d": "reason2"}
    )
    out = capsys.readouterr().out
    assert "Discovered:  4 scenarios" in out


def test_scenario_digest_empty_scenarios_running_text(capsys) -> None:
    _render_scenario_pre_run_digest(_ctx(), [], {})
    out = capsys.readouterr().out
    assert "Running:      0  ((none))" in out, repr(out)


def test_scenario_digest_accepts_file_kwarg() -> None:
    """capsys-parity: file=stream redirects output."""
    buf = io.StringIO()
    _render_scenario_pre_run_digest(_ctx(), ["s"], {}, file=buf)
    assert "MCP Test Framework (test-code)" in buf.getvalue()


# ---------------------------------------------------------------------------
# _collect_test_code_scenarios
# ---------------------------------------------------------------------------


def test_collect_test_code_scenarios_empty_when_directory_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing tests/test_code/ -> ([], {})."""
    monkeypatch.chdir(tmp_path)
    stems, skipped = _collect_test_code_scenarios(_ctx())
    assert stems == []
    assert skipped == {}


def test_collect_test_code_scenarios_returns_stems_alphabetized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """tests/test_code/test_X.py -> X (sorted)."""
    tc_dir = tmp_path / "tests" / "test_code"
    tc_dir.mkdir(parents=True)
    (tc_dir / "test_zoo.py").write_text("# scenario z\n", encoding="utf-8")
    (tc_dir / "test_alpha.py").write_text("# scenario a\n", encoding="utf-8")
    (tc_dir / "test_proxmox_vm_lifecycle.py").write_text("# p\n", encoding="utf-8")
    # Non-test_*.py files must be ignored.
    (tc_dir / "conftest.py").write_text("# noscan\n", encoding="utf-8")
    (tc_dir / "helpers.py").write_text("# noscan\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    stems, skipped = _collect_test_code_scenarios(_ctx())
    assert stems == ["alpha", "proxmox_vm_lifecycle", "zoo"]
    assert skipped == {}  # discovery only; skip detection is a future extension.


# ---------------------------------------------------------------------------
# Regression: non-SDET _render_pre_run_digest is unchanged
# ---------------------------------------------------------------------------


def test_non_sdet_digest_banner_unchanged(capsys) -> None:
    """Plan 18-06 regression guard: the existing tool digest does NOT gain a
    '(SDET)' suffix or any other shape change."""
    ctx = RenderContext(
        server_cmd="uvx homelab-mcp",
        discovered_tools=["alpha"],
        tools_config={"alpha": SimpleNamespace(skip=False)},
        judges=["clarity"],
    )
    _render_pre_run_digest(ctx)
    out = capsys.readouterr().out
    assert "MCP Test Framework\n" in out
    assert "MCP Test Framework (test-code)" not in out
