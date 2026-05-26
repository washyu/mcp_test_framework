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


# ---------------------------------------------------------------------------
# WR-02 regression: _count_bucket_skips honors discovered filter
# ---------------------------------------------------------------------------


def test_count_bucket_skips_filters_by_discovered() -> None:
    """WR-02: configured-but-undiscovered tools must not inflate the count.

    Consistent with the rest of the digest (such tools are absent from
    both Running and Skipping). When ``discovered`` is supplied, only
    tools present in ``discovered`` contribute to the total. When omitted
    (legacy callers), every entry in ``tools_config`` is counted.
    """
    tools_config = {
        "tool_a": ToolConfig(skip_buckets=["output"]),          # 1
        "ghost_tool": ToolConfig(skip_buckets=["schema"]),       # 1, but undiscovered
        "tool_c": ToolConfig(skip_buckets=["schema", "judge"]), # 2
    }
    # Legacy behavior preserved when discovered is None
    assert _count_bucket_skips(tools_config) == 4

    # With discovered list, ghost_tool's 1 bucket is excluded
    assert _count_bucket_skips(tools_config, ["tool_a", "tool_c"]) == 3

    # Empty discovered set excludes everything
    assert _count_bucket_skips(tools_config, []) == 0


def test_digest_bucket_skips_excludes_undiscovered_tools() -> None:
    """WR-02 integration: digest Bucket skips: count excludes configured-but-undiscovered tools."""
    ctx = _ctx(
        discovered=["tool_a"],
        tools_config={
            "tool_a": ToolConfig(skip_buckets=["output"]),
            # Configured but NOT in discovered list -- must be ignored
            "ghost_tool": ToolConfig(skip_buckets=["schema", "judge"]),
        },
    )
    buf = io.StringIO()
    _render_pre_run_digest(ctx, file=buf)
    out = buf.getvalue()

    bucket_lines = [line for line in out.splitlines() if line.startswith("Bucket skips:")]
    assert len(bucket_lines) == 1, f"expected 1 Bucket skips: line: {out!r}"
    # Only tool_a's 1 bucket should count -- not ghost_tool's 2
    assert "1" in bucket_lines[0] and "3" not in bucket_lines[0], (
        f"undiscovered tool inflated the count: {bucket_lines[0]!r}"
    )


# ---------------------------------------------------------------------------
# Test 5 (regression, phase 33-06): Test plan: count deducts skip_buckets
# CR-01 BLOCKER guard: pins digest internal consistency between the
# Bucket skips: line and the Test plan: line. The expected value is
# computed dynamically from TEST_FUNCTION_BUCKETS so a future re-balance
# of bucket contents in contracts/_buckets.py does not silently break
# this regression test.
# ---------------------------------------------------------------------------


def test_digest_test_plan_count_deducts_skip_buckets() -> None:
    """`Test plan: N contract cases` reflects per-tool skip_buckets deductions.

    Pins CR-01 (33-VERIFICATION.md). Without the bucket-aware loop in
    _render_pre_run_digest, this line overstates planned cases by
    len(skip_buckets) * bucket_size per tool — internally contradicting
    the Bucket skips: line emitted directly above it.
    """
    from mcp_test_framework.contracts._buckets import TEST_FUNCTION_BUCKETS

    bucket_size = {b: len(fns) for b, fns in TEST_FUNCTION_BUCKETS.items()}
    full_tool = sum(bucket_size.values())  # == 10 by invariant

    def _plan_count(out: str) -> int:
        plan_lines = [
            line for line in out.splitlines() if line.startswith("Test plan:")
        ]
        assert len(plan_lines) == 1, (
            f"expected exactly 1 'Test plan:' line, got {len(plan_lines)}: {out!r}"
        )
        # Format: "Test plan:   {N} contract cases"
        parts = plan_lines[0].split()
        # parts == ["Test", "plan:", "{N}", "contract", "cases"]
        return int(parts[2])

    # --- Scenario A: baseline (no skip_buckets anywhere) -------------------
    ctx_a = _ctx(
        discovered=["tool_a", "tool_b"],
        tools_config={"tool_a": ToolConfig(), "tool_b": ToolConfig()},
    )
    buf_a = io.StringIO()
    _render_pre_run_digest(ctx_a, file=buf_a)
    expected_a = 2 * full_tool  # 20
    assert _plan_count(buf_a.getvalue()) == expected_a, (
        f"baseline mismatch: expected {expected_a}, output: {buf_a.getvalue()!r}"
    )

    # --- Scenario B: one tool, one bucket skipped --------------------------
    ctx_b = _ctx(
        discovered=["create_proxmox_vm"],
        tools_config={"create_proxmox_vm": ToolConfig(skip_buckets=["output"])},
    )
    buf_b = io.StringIO()
    _render_pre_run_digest(ctx_b, file=buf_b)
    expected_b = full_tool - bucket_size["output"]  # 10 - 3 = 7
    assert _plan_count(buf_b.getvalue()) == expected_b, (
        f"single-bucket skip mismatch: expected {expected_b}, output: {buf_b.getvalue()!r}"
    )

    # --- Scenario C: one tool, all three buckets skipped -------------------
    ctx_c = _ctx(
        discovered=["tool_a"],
        tools_config={
            "tool_a": ToolConfig(skip_buckets=["schema", "judge", "output"]),
        },
    )
    buf_c = io.StringIO()
    _render_pre_run_digest(ctx_c, file=buf_c)
    expected_c = 0
    assert _plan_count(buf_c.getvalue()) == expected_c, (
        f"all-buckets skip mismatch: expected {expected_c}, output: {buf_c.getvalue()!r}"
    )

    # --- Scenario D: two tools, different buckets skipped ------------------
    ctx_d = _ctx(
        discovered=["tool_a", "tool_b"],
        tools_config={
            "tool_a": ToolConfig(skip_buckets=["judge"]),
            "tool_b": ToolConfig(skip_buckets=["output"]),
        },
    )
    buf_d = io.StringIO()
    _render_pre_run_digest(ctx_d, file=buf_d)
    expected_d = (full_tool - bucket_size["judge"]) + (
        full_tool - bucket_size["output"]
    )  # 7 + 7 = 14
    assert _plan_count(buf_d.getvalue()) == expected_d, (
        f"multi-tool mixed-bucket mismatch: expected {expected_d}, output: {buf_d.getvalue()!r}"
    )
