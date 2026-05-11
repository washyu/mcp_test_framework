"""Phase 14 Plan 06 (gap-closure): Unicode encoding hygiene regression tests.

Closes GAP 1 (blocker) from 14-HUMAN-UAT.md. Two-sided defense:

- Write-side: ``cli.run`` must reconfigure ``sys.stdout`` to utf-8 with
  ``errors='replace'`` BEFORE any rendering or any ``_load_config`` error
  path. Windows PowerShell's default cp1252 console cannot encode the
  renderer's U+2717 (``✗``) / U+2714 (``✓``) / U+2013 (``–``) / U+2014
  (``—``) glyphs; without the reconfigure ``_render_per_tool_rows`` crashes
  mid-render.

- Read-side: ``_runner.run_pytest_subprocess`` reads child pytest stdout
  as utf-8. Without ``PYTHONIOENCODING=utf-8`` in the child env the child
  writes cp1252 bytes on Windows; without ``errors='replace'`` on the parent
  decoder a stray non-utf-8 byte (e.g. ``0x97`` = cp1252 em-dash) raises
  ``UnicodeDecodeError`` mid-capture.

Test grid (4 tests):

  A(a) renderer-on-strict-cp1252-raises    -- baseline pin: without fix this
                                              raises UnicodeEncodeError.
  A(b) renderer-on-replace-cp1252-survives -- proves cli.run's reconfigure
                                              choice (errors='replace') is
                                              sufficient on hostile streams.
  B    runner-source-pins-encoding         -- pins both kwargs literally in
                                              _runner.run_pytest_subprocess.
  C    cli-run-source-pins-reconfigure     -- pins sys.stdout.reconfigure
                                              call in cli.run.

Grep-style pins (Tests B + C) intentionally read source via
``inspect.getsource`` rather than spawning a child subprocess with a hostile
console -- portable across CI runners and fast enough for unit tests.
"""
from __future__ import annotations

import inspect
import io

import pytest

from mcp_test_framework import _runner
from mcp_test_framework import cli as _cli
from mcp_test_framework._runner import (
    ParsedRun,
    ToolVerdict,
    _render_per_tool_rows,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parsed_with_fail_and_pass() -> ParsedRun:
    """Build a ParsedRun containing one FAIL row (emits U+2717 ``✗``) and one
    PASS row (emits U+2714 ``✓``).

    The em-dash separator (U+2014 ``—``) appears whenever ``failure_message``
    is non-empty, so we also include a failure message to exercise that
    glyph path.
    """
    run = ParsedRun(total_time=1.0, total_cases=2, total_failures=1)
    run.per_tool["alpha"] = ToolVerdict(
        name="alpha",
        verdict="FAIL",
        failure_message="boom",
        case_count=1,
        duration=0.5,
    )
    run.per_tool["beta"] = ToolVerdict(
        name="beta",
        verdict="PASS",
        case_count=1,
        duration=0.5,
    )
    return run


def _cp1252_stream(*, errors: str) -> io.TextIOWrapper:
    """Return a TextIOWrapper backed by an in-memory BytesIO and configured
    with cp1252 encoding + the requested error policy. Mirrors the Windows
    PowerShell cp1252 console without spawning a child.
    """
    return io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors=errors)


# ---------------------------------------------------------------------------
# Test A(a) -- baseline pin: strict cp1252 stream raises.
# This test PASSES BOTH before and after the fix. It exists to make the
# contract explicit: the renderer itself does not silently degrade -- it
# relies on the caller (cli.run) to provide a hospitable stream.
# ---------------------------------------------------------------------------


def test_render_per_tool_rows_raises_on_strict_cp1252_stream() -> None:
    parsed = _parsed_with_fail_and_pass()
    stream = _cp1252_stream(errors="strict")
    with pytest.raises(UnicodeEncodeError):
        _render_per_tool_rows(parsed, {}, file=stream)


# ---------------------------------------------------------------------------
# Test A(b) -- proves cli.run's chosen reconfigure policy (errors='replace')
# is sufficient: the renderer emits, glyphs degrade to '?' on cp1252, tool
# names still appear. This test FAILS before Task 3 lands ONLY in the sense
# that without cli.run's reconfigure, real-world stdout would not be wrapped
# with errors='replace' and operators would see a crash. The unit test itself
# constructs the replace-cp1252 stream directly so it goes GREEN immediately;
# its purpose is to PIN the behavior cli.run's fix relies on.
# ---------------------------------------------------------------------------


def test_render_per_tool_rows_survives_replace_cp1252_stream() -> None:
    parsed = _parsed_with_fail_and_pass()
    stream = _cp1252_stream(errors="replace")
    # Must not raise.
    _render_per_tool_rows(parsed, {}, file=stream)
    stream.flush()
    raw_bytes: bytes = stream.buffer.getvalue()  # type: ignore[attr-defined]
    decoded = raw_bytes.decode("cp1252", errors="replace")
    # Tool names survive; glyphs may be replaced with '?'.
    assert "alpha" in decoded, "FAIL row's tool name missing from output"
    assert "beta" in decoded, "PASS row's tool name missing from output"


# ---------------------------------------------------------------------------
# Test B -- read-side: pin both encoding-hygiene kwargs in
# _runner.run_pytest_subprocess source. Grep-style pin via inspect.getsource
# so the test is portable across CI runners (no child subprocess with a
# hostile console).
# ---------------------------------------------------------------------------


def test_run_pytest_subprocess_source_pins_encoding_hygiene() -> None:
    src = inspect.getsource(_runner.run_pytest_subprocess)
    assert "PYTHONIOENCODING" in src, (
        "_runner.run_pytest_subprocess must set PYTHONIOENCODING=utf-8 in the "
        "child env so the child pytest writes utf-8 bytes (closes UAT GAP 1 "
        "read-side: cp1252 byte 0x97 in child stdout)."
    )
    assert 'errors="replace"' in src or "errors='replace'" in src, (
        "_runner.run_pytest_subprocess must pass errors='replace' to the "
        "parent decode so a stray non-utf-8 byte never raises "
        "UnicodeDecodeError mid-capture."
    )


# ---------------------------------------------------------------------------
# Test C -- write-side: pin sys.stdout.reconfigure call in cli.run source.
# ---------------------------------------------------------------------------


def test_cli_run_source_pins_stdout_reconfigure() -> None:
    src = inspect.getsource(_cli.run)
    assert "sys.stdout.reconfigure" in src, (
        "cli.run must reconfigure sys.stdout (closes UAT GAP 1 write-side: "
        "cp1252 console cannot encode renderer's U+2717/U+2714/U+2013/U+2014)."
    )
    # Independent kwarg pins -- robust to formatter reflow across lines.
    assert 'encoding="utf-8"' in src or "encoding='utf-8'" in src, (
        "cli.run's reconfigure must specify encoding='utf-8'."
    )
    assert 'errors="replace"' in src or "errors='replace'" in src, (
        "cli.run's reconfigure must specify errors='replace' for graceful "
        "degradation on streams that cannot encode the glyphs."
    )
    # Guarded with hasattr() so capsys-style wrappers (no reconfigure method)
    # do not crash on the missing attribute.
    assert "hasattr(sys.stdout" in src and "reconfigure" in src, (
        "cli.run's reconfigure call must be hasattr-guarded so test "
        "environments that wrap sys.stdout without reconfigure() don't crash."
    )
