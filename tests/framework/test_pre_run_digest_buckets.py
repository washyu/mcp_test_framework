"""Phase 33 BUCKET-04 / SC#3: pre-run digest per-bucket skip count line tests.

Pins:
- When NO tool has non-empty skip_buckets, digest is byte-identical to v1.5 baseline (no new line).
- When >= 1 tool has non-empty skip_buckets, ONE new line emits between Skipping: and Judges:.
  Format: `Bucket skips: {N}  (use --explain to list)` where N is total (tool, bucket) pair count.
- When explain=True, the `(use --explain to list)` hint is omitted on the new line.
- _count_bucket_skips helper returns total (tool, bucket) pair count correctly.
"""
from __future__ import annotations

import io

import pytest

from mcp_test_framework._runner import (
    RenderContext,
    _count_bucket_skips,
    _render_pre_run_digest,
)
from mcp_test_framework.models import ToolConfig


def _ctx(
    discovered=None,
    tools_config=None,
    judges=None,
    server_cmd="uvx homelab-mcp",
):
    return RenderContext(
        server_cmd=server_cmd,
        discovered_tools=(
            discovered if discovered is not None else ["tool_a"]
        ),
        tools_config=tools_config if tools_config is not None else {},
        judges=judges if judges is not None else ["clarity"],
        total_planned_cases=0,
    )


# ---------------------------------------------------------------------------
# Test 1: No skip_buckets -> byte-identical baseline (no "Bucket skips:" line)
# ---------------------------------------------------------------------------


def test_digest_with_no_skip_buckets_is_byte_identical_to_baseline() -> None:
    """When all tools have empty skip_buckets, digest must not contain 'Bucket skips:'."""
    ctx = _ctx(
        discovered=["tool_a", "tool_b"],
        tools_config={
            "tool_a": ToolConfig(),
            "tool_b": ToolConfig(),
        },
    )
    buf = io.StringIO()
    _render_pre_run_digest(ctx, file=buf)
    out = buf.getvalue()

    assert "Bucket skips:" not in out, (
        f"unexpected 'Bucket skips:' in digest output when no skip_buckets set: {out!r}"
    )


# ---------------------------------------------------------------------------
# Test 2: Any tool with skip_buckets -> Bucket skips: line with count + hint
# ---------------------------------------------------------------------------


def test_digest_emits_bucket_skips_line_when_any_tool_has_skip_buckets() -> None:
    """One tool has skip_buckets=["output"], another has [], another has ["schema","judge"].

    Total (tool, bucket) pairs = 1 + 0 + 2 = 3. Expect one line starting with
    'Bucket skips:' containing '3' and '(use --explain to list)'.
    """
    ctx = _ctx(
        discovered=["tool_a", "tool_b", "tool_c"],
        tools_config={
            "tool_a": ToolConfig(skip_buckets=["output"]),
            "tool_b": ToolConfig(),
            "tool_c": ToolConfig(skip_buckets=["schema", "judge"]),
        },
    )
    buf = io.StringIO()
    _render_pre_run_digest(ctx, file=buf)
    out = buf.getvalue()

    # Exactly one Bucket skips: line
    bucket_lines = [line for line in out.splitlines() if line.startswith("Bucket skips:")]
    assert len(bucket_lines) == 1, (
        f"expected exactly 1 'Bucket skips:' line, got {len(bucket_lines)}: {out!r}"
    )

    bucket_line = bucket_lines[0]

    # Contains count 3
    assert "3" in bucket_line, (
        f"expected count 3 in bucket skips line: {bucket_line!r}"
    )

    # Contains the --explain hint
    assert "(use --explain to list)" in bucket_line, (
        f"expected hint in bucket skips line: {bucket_line!r}"
    )


# ---------------------------------------------------------------------------
# Test 3: explain=True -> Bucket skips: line present but hint omitted
# ---------------------------------------------------------------------------


def test_digest_bucket_skips_with_explain_omits_hint() -> None:
    """With explain=True, the Bucket skips: line is present but without the hint."""
    ctx = _ctx(
        discovered=["tool_a", "tool_b", "tool_c"],
        tools_config={
            "tool_a": ToolConfig(skip_buckets=["output"]),
            "tool_b": ToolConfig(),
            "tool_c": ToolConfig(skip_buckets=["schema", "judge"]),
        },
    )
    buf = io.StringIO()
    _render_pre_run_digest(ctx, explain=True, file=buf)
    out = buf.getvalue()

    # Bucket skips: line is present
    bucket_lines = [line for line in out.splitlines() if line.startswith("Bucket skips:")]
    assert len(bucket_lines) == 1, (
        f"expected exactly 1 'Bucket skips:' line with explain=True: {out!r}"
    )

    bucket_line = bucket_lines[0]

    # Hint must NOT be present
    assert "(use --explain to list)" not in bucket_line, (
        f"hint must be omitted when explain=True: {bucket_line!r}"
    )

    # Count must still be present
    assert "3" in bucket_line, (
        f"expected count 3 in bucket skips line with explain=True: {bucket_line!r}"
    )


# ---------------------------------------------------------------------------
# Test 4: Direct unit test on _count_bucket_skips
# ---------------------------------------------------------------------------


def test_count_bucket_skips_helper() -> None:
    """_count_bucket_skips returns total (tool, bucket) pair count across all tools."""
    tools_config = {
        "tool_a": ToolConfig(skip_buckets=["output"]),         # 1
        "tool_b": ToolConfig(),                                  # 0
        "tool_c": ToolConfig(skip_buckets=["schema", "judge"]), # 2
    }
    result = _count_bucket_skips(tools_config)
    assert result == 3, f"expected 3, got {result}"

    # Edge: all empty
    assert _count_bucket_skips({}) == 0
    assert _count_bucket_skips({"t": ToolConfig()}) == 0
