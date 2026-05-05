"""Unit tests for mcp_test_framework.mcp_client (mock-friendly slices only).

Live subprocess / timeout behavior is exercised by
tests/smoke/test_smoke_homelab_mcp.py (Plan 03). Mocking stdio_client to
assert "timeout fires" is high-cost / low-signal -- the smoke test against
the real binary is the load-bearing check (CONTEXT.md "Phase 2 unit tests
scope" Discretion item).

Coverage in this file:
  - ToolNotFoundError payload shape (tool_name, available, message, base class)
  - _LoggerWriter line-buffering and flush() behavior

All tests are synchronous -- no @pytest.mark.asyncio (Phase 1 LEARNINGS:
sync tests don't get the asyncio marker; doing so is the documented
anti-pattern).
"""
from __future__ import annotations

import logging

import pytest

from mcp_test_framework.mcp_client import ToolNotFoundError, _LoggerWriter


def test_tool_not_found_carries_name_and_available() -> None:
    """ToolNotFoundError exposes tool_name and available for FIX-03 diagnostic."""
    err = ToolNotFoundError("missing_tool", available=["a", "b"])
    assert err.tool_name == "missing_tool"
    assert err.available == ["a", "b"]


def test_tool_not_found_message_includes_name_and_candidates() -> None:
    """str(ToolNotFoundError) contains the missing name and the candidate list."""
    err = ToolNotFoundError("missing_tool", available=["a", "b"])
    msg = str(err)
    assert "missing_tool" in msg
    # repr of list is "['a', 'b']" -- accept either single or double quoting
    # in case repr changes across Python versions.
    assert "['a', 'b']" in msg or '["a", "b"]' in msg


def test_tool_not_found_is_lookup_error() -> None:
    """ToolNotFoundError subclasses LookupError so callers can catch it generically."""
    err = ToolNotFoundError("x", available=[])
    assert isinstance(err, LookupError)


def test_logger_writer_emits_complete_lines(caplog: pytest.LogCaptureFixture) -> None:
    """_LoggerWriter buffers partial writes and emits one record per newline."""
    logger = logging.getLogger("mcp_test_framework.mcp_client.stderr")
    writer = _LoggerWriter(logger)
    with caplog.at_level(logging.WARNING, logger=logger.name):
        writer.write("hello ")  # no newline yet -> nothing emitted
        assert not caplog.records
        writer.write("world\n")  # newline -> one record
    assert len(caplog.records) == 1
    assert caplog.records[0].message == "hello world"
    assert caplog.records[0].levelno == logging.WARNING


def test_logger_writer_flush_emits_buffered_partial(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """_LoggerWriter.flush() emits any unterminated buffered text."""
    logger = logging.getLogger("mcp_test_framework.mcp_client.stderr")
    writer = _LoggerWriter(logger)
    with caplog.at_level(logging.WARNING, logger=logger.name):
        writer.write("partial line without newline")
        assert not caplog.records
        writer.flush()
    assert len(caplog.records) == 1
    assert caplog.records[0].message == "partial line without newline"
