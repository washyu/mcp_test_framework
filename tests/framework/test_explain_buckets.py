"""Phase 33 BUCKET-04 / SC#3: --explain per-tool block bucket-level extension tests.

Pins:
- When no tool has skip_buckets, output is byte-identical to v1.5 baseline (no bucket= lines).
- State-b tools (running, skip=False) with skip_buckets render a "Bucket-skipped tools (M):"
  section below the existing "Skipping (N):" block.
- Each skipped bucket renders as exactly:
      bucket=<bucket>: skipped via tools.<tool>.skip_buckets
  (grep-able on the literal `bucket=`).
- Multiple skip_buckets on one tool render in operator order (preserved list order).
"""
from __future__ import annotations

import io

import pytest

from mcp_test_framework._runner import RenderContext, _render_skipped_tools_explain
from mcp_test_framework.models import ToolConfig


def _ctx(
    discovered=None,
    tools_config=None,
    server_cmd="uvx homelab-mcp",
):
    return RenderContext(
        server_cmd=server_cmd,
        discovered_tools=(
            discovered if discovered is not None else []
        ),
        tools_config=tools_config if tools_config is not None else {},
        judges=[],
        total_planned_cases=0,
    )


# ---------------------------------------------------------------------------
# Test 1: No skip_buckets -> byte-identical baseline (no bucket= lines)
# ---------------------------------------------------------------------------


def test_explain_with_no_skip_buckets_is_byte_identical_to_baseline() -> None:
    """When no tool has skip_buckets, output must not contain 'bucket=' or 'Bucket-skipped'.

    Tools with skip=True (state-c) render the existing Skipping block unchanged.
    """
    ctx = _ctx(
        discovered=["tool_a", "tool_b"],
        tools_config={
            "tool_a": ToolConfig(skip=True, skip_reason="deprecated"),
        },
    )
    buf = io.StringIO()
    _render_skipped_tools_explain(ctx, file=buf)
    out = buf.getvalue()

    # No bucket= lines (baseline invariant)
    assert "bucket=" not in out, f"unexpected bucket= in output: {out!r}"
    assert "Bucket-skipped" not in out, f"unexpected Bucket-skipped in output: {out!r}"

    # Existing Skipping block is present unchanged
    assert "Skipping (2):" in out, f"expected Skipping (2): in output: {out!r}"
    assert "tool_a" in out
    assert "tool_b" in out


# ---------------------------------------------------------------------------
# Test 2: State-b tool with skip_buckets renders bucket lines
# ---------------------------------------------------------------------------


def test_explain_state_b_tool_with_skip_buckets_renders_bucket_lines() -> None:
    """State-b (running, skip=False) tool with skip_buckets=["output"] emits bucket= lines.

    Expects:
      Bucket-skipped tools (1):
        tool_a:
          bucket=output: skipped via tools.tool_a.skip_buckets
    """
    ctx = _ctx(
        discovered=["tool_a"],
        tools_config={
            "tool_a": ToolConfig(skip_buckets=["output"]),
        },
    )
    buf = io.StringIO()
    _render_skipped_tools_explain(ctx, file=buf)
    out = buf.getvalue()

    # Bucket-skipped tools section header
    assert "Bucket-skipped tools (1):" in out, f"missing section header: {out!r}"

    # Tool header line
    assert "  tool_a:" in out, f"missing tool header line: {out!r}"

    # Exact bucket line
    assert "    bucket=output: skipped via tools.tool_a.skip_buckets" in out, (
        f"missing bucket line: {out!r}"
    )

    # Zero whole-tool skips (tool_a is running, not whole-tool-skipped)
    assert "Skipping (0):" in out, f"expected empty Skipping (0): in output: {out!r}"


# ---------------------------------------------------------------------------
# Test 3: Multiple buckets on one tool render in operator order
# ---------------------------------------------------------------------------


def test_explain_multiple_buckets_one_tool() -> None:
    """skip_buckets=["judge", "output"] renders two bucket= lines in operator order."""
    ctx = _ctx(
        discovered=["tool_a"],
        tools_config={
            "tool_a": ToolConfig(skip_buckets=["judge", "output"]),
        },
    )
    buf = io.StringIO()
    _render_skipped_tools_explain(ctx, file=buf)
    out = buf.getvalue()

    judge_line = "    bucket=judge: skipped via tools.tool_a.skip_buckets"
    output_line = "    bucket=output: skipped via tools.tool_a.skip_buckets"

    assert judge_line in out, f"missing judge bucket line: {out!r}"
    assert output_line in out, f"missing output bucket line: {out!r}"

    # Operator order preserved: judge appears before output
    assert out.index(judge_line) < out.index(output_line), (
        f"bucket order not preserved (judge must come before output): {out!r}"
    )


# ---------------------------------------------------------------------------
# Test 4: Grep anchor -- literal `bucket=` present
# ---------------------------------------------------------------------------


def test_explain_grep_anchor() -> None:
    """The literal substring `bucket=` must appear in the output for grep-ability.

    This is the CONTEXT.md D-3 locked grep anchor:
      bucket=<name>: skipped via tools.<name>.skip_buckets
    """
    ctx = _ctx(
        discovered=["tool_a"],
        tools_config={
            "tool_a": ToolConfig(skip_buckets=["output"]),
        },
    )
    buf = io.StringIO()
    _render_skipped_tools_explain(ctx, file=buf)
    out = buf.getvalue()

    assert "bucket=" in out, (
        f"grep anchor `bucket=` not found in explain output: {out!r}"
    )
