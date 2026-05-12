"""Phase 16 D-01/D-03/D-12: pre-run digest renderer regression tests.

Pins:
- CASES_PER_CONTRACT_TOOL constant (must not silently drift)
- AST-counted parametrize count in tests/contract/test_mcp_tool_contract.py
  must equal the constant (drift guard: either side changing breaks this)
- Digest height <= 10 lines at all N (D-12 invariant)
- Banner / label / Test plan line shape (locked by Phase 14 D-07 + D-03)
"""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from mcp_test_framework._runner import (
    CASES_PER_CONTRACT_TOOL,
    RenderContext,
    _compose_pre_run_skip_reasons,
    _render_pre_run_digest,
)

# tests/framework/unit/<here> -> tests/framework/fixtures
# (precedent: test_runner_parser.py:31)
_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
# tests/framework/unit/<here> -> repo_root/tests/contract/test_mcp_tool_contract.py
_CONTRACT_FILE = (
    Path(__file__).resolve().parents[3]
    / "tests"
    / "contract"
    / "test_mcp_tool_contract.py"
)


def _ctx(
    discovered=None,
    tools_config=None,
    judges=None,
    server_cmd="uvx homelab-mcp",
):
    return RenderContext(
        server_cmd=server_cmd,
        discovered_tools=(
            discovered if discovered is not None else ["alpha", "beta", "gamma"]
        ),
        tools_config=tools_config if tools_config is not None else {},
        judges=judges if judges is not None else ["clarity"],
        total_planned_cases=0,
    )


# ---------------------------------------------------------------------------
# Locked-constant regression (D-03)
# ---------------------------------------------------------------------------


def test_cases_per_contract_tool_constant_locked() -> None:
    """D-03: pre-run test-plan count = running x CASES_PER_CONTRACT_TOOL.
    Sources: 5 schema validators + 4 judge dimensions + 1 output conformance = 10."""
    assert CASES_PER_CONTRACT_TOOL == 10


def test_cases_per_contract_tool_matches_actual_parametrize_count() -> None:
    """D-03: the constant must equal the number of test_* functions in
    tests/contract/test_mcp_tool_contract.py. If either side moves and the
    other doesn't, this test fails -- preventing silent drift between the
    digest's pre-run count and the actual contract surface.
    """
    assert _CONTRACT_FILE.exists(), f"expected contract test at {_CONTRACT_FILE}"
    source = _CONTRACT_FILE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    test_funcs = [
        n
        for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name.startswith("test_")
    ]
    assert len(test_funcs) == CASES_PER_CONTRACT_TOOL, (
        f"contract file has {len(test_funcs)} test_* funcs but "
        f"CASES_PER_CONTRACT_TOOL = {CASES_PER_CONTRACT_TOOL}. "
        f"Update one to match the other."
    )


# ---------------------------------------------------------------------------
# Digest shape (D-01)
# ---------------------------------------------------------------------------


def test_pre_run_digest_emits_banner_and_label_block(capsys) -> None:
    ctx = _ctx(
        discovered=["alpha", "beta", "gamma"],
        tools_config={"alpha": SimpleNamespace(skip=False)},
        judges=["clarity"],
    )
    _render_pre_run_digest(ctx)
    out = capsys.readouterr().out
    lines = out.split("\n")
    # Banner = 40 equals signs (Phase 14 D-07 locked).
    assert lines[0] == "=" * 40
    assert lines[1] == "MCP Test Framework"
    assert lines[2] == "=" * 40
    assert "MCP server:  uvx homelab-mcp" in out
    assert "Discovered:  3 tools" in out
    assert "Running:      1  (alpha)" in out, repr(out)
    assert "Skipping:     2  (use --explain to list)" in out, repr(out)
    assert "Judges:      clarity" in out
    assert "Test plan:   10 contract cases" in out, repr(out)


def test_pre_run_digest_test_plan_uses_constant(capsys) -> None:
    """D-03: Test plan = running_n x CASES_PER_CONTRACT_TOOL."""
    ctx = _ctx(
        discovered=["a", "b"],
        tools_config={
            "a": SimpleNamespace(skip=False),
            "b": SimpleNamespace(skip=False),
        },
    )
    _render_pre_run_digest(ctx)
    out = capsys.readouterr().out
    assert f"Test plan:   {2 * CASES_PER_CONTRACT_TOOL} contract cases" in out


def test_pre_run_digest_height_bounded_at_small_N(capsys) -> None:
    """D-12: digest height <= 10 content lines regardless of N."""
    ctx = _ctx(
        discovered=["alpha"],
        tools_config={"alpha": SimpleNamespace(skip=False)},
    )
    _render_pre_run_digest(ctx)
    out = capsys.readouterr().out
    # 8 label-bearing lines + 1 trailing blank => max 11 split chunks
    # (split("\n") on "a\nb\n" yields ["a","b",""] - trailing empty).
    assert len(out.split("\n")) <= 11, (
        f"got {len(out.split(chr(10)))} lines: {out!r}"
    )


def test_pre_run_digest_height_bounded_at_N_70(capsys) -> None:
    """D-12: digest height <= 10 lines even at homelab-mcp's full N=70 surface.
    The Skipping list is NEVER inline-expanded here -- `--explain` is the
    expansion surface, not the digest.
    """
    discovered = [f"tool_{i:02d}" for i in range(70)]
    tools_config = {
        "tool_00": SimpleNamespace(skip=False),
        "tool_01": SimpleNamespace(skip=False),
    }
    ctx = _ctx(discovered=discovered, tools_config=tools_config, judges=["clarity"])
    _render_pre_run_digest(ctx)
    out = capsys.readouterr().out
    assert len(out.split("\n")) <= 11, (
        f"N=70 digest too tall: {len(out.split(chr(10)))} lines"
    )
    # Sanity: the 68 skipped tool names must NOT appear inline.
    assert "tool_02" not in out, "Skipping list leaked into digest at N=70"
    # Test plan still computes correctly: 2 * 10 = 20.
    assert "Test plan:   20 contract cases" in out


def test_pre_run_digest_handles_empty_judges(capsys) -> None:
    ctx = _ctx(
        discovered=["a"],
        tools_config={"a": SimpleNamespace(skip=False)},
        judges=[],
    )
    _render_pre_run_digest(ctx)
    out = capsys.readouterr().out
    assert "Judges:      (none configured)" in out


# ---------------------------------------------------------------------------
# _compose_pre_run_skip_reasons (D-05 / D-14)
# ---------------------------------------------------------------------------


def test_compose_pre_run_skip_reasons_state_a_unlisted() -> None:
    """state (a): tool discovered but not in tools_config -> 'not selected in config'."""
    skipped = _compose_pre_run_skip_reasons(
        ["a", "b"], {"a": SimpleNamespace(skip=False)}
    )
    assert "b" in skipped
    assert skipped["b"] == "not selected in config"
    assert "a" not in skipped


def test_compose_pre_run_skip_reasons_empty_on_all_running() -> None:
    skipped = _compose_pre_run_skip_reasons(
        ["a"], {"a": SimpleNamespace(skip=False)}
    )
    assert skipped == {}


def test_compose_pre_run_skip_reasons_state_c_explicit_default() -> None:
    """state (c): tool in config with skip=True and no custom reason
    -> 'explicit skip in config' (locked Phase 13 D-12 string)."""
    skipped = _compose_pre_run_skip_reasons(
        ["a"], {"a": SimpleNamespace(skip=True, skip_reason=None)}
    )
    assert skipped.get("a") == "explicit skip in config"


def test_compose_pre_run_skip_reasons_state_c_custom_reason() -> None:
    """state (c) with operator-supplied skip_reason: custom text replaces the default."""
    skipped = _compose_pre_run_skip_reasons(
        ["a"], {"a": SimpleNamespace(skip=True, skip_reason="dangerous in CI")}
    )
    assert skipped.get("a") == "dangerous in CI"
