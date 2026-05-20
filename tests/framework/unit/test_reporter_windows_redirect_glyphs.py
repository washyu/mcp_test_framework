"""Regression test for the library-mode reporter's Windows-redirect glyph guard.

Bug repro: when an operator runs library-mode pytest with stdout redirected
to a file via `cmd /c "pytest ... > out.txt"` on Windows, sys.stdout defaults
to cp1252 which cannot encode the renderer's U+2717 (✗) / U+2714 (✓) /
U+2013 (–) / U+2014 (—) glyphs. The CLI wrapper has a
`sys.stdout.reconfigure(encoding="utf-8", errors="replace")` call early in
`cli.py:run` to handle this. The library-mode reporter previously did NOT —
under `cmd /c >` redirect it crashed mid-render with
`UnicodeEncodeError: 'charmap' codec can't encode character '✗'`.

Surfaced 2026-05-19 during Phase 30 UAT-4 capture. Fix: mirror the CLI's
reconfigure inside the reporter plugin's `pytest_configure` so the same
guard fires under both CLI and library mode.

This test does NOT drive a Windows-specific subprocess. Instead it stubs
sys.stdout with a sentinel object exposing a `reconfigure` method, then
invokes the plugin's `pytest_configure` and asserts the reconfigure was
called with the expected encoding/errors kwargs.
"""
from __future__ import annotations

import sys
import types

import mcp_test_framework._reporter as reporter


class _ReconfigureSpy:
    """Stand-in for sys.stdout that records reconfigure() invocations."""

    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []
        # isatty -> True so the auto-mode branch doesn't early-return before
        # the reconfigure path is reached.
        self.isatty = lambda: True

    def reconfigure(self, *, encoding: str, errors: str) -> None:
        self.calls.append({"encoding": encoding, "errors": errors})


def _fake_config(domain_ui_choice: str) -> types.SimpleNamespace:
    """Minimal pytest.Config stand-in: only the bits pytest_configure reads."""
    return types.SimpleNamespace(
        getoption=lambda name, default=None: domain_ui_choice
        if name == "--mcp-domain-ui"
        else default,
    )


def test_pytest_configure_reconfigures_stdout_to_utf8_under_force(
    monkeypatch,
) -> None:
    """Under `--mcp-domain-ui=force` the plugin must call
    sys.stdout.reconfigure(encoding='utf-8', errors='replace') so the
    renderer's ✗/✓ glyphs survive a Windows cmd /c file redirect."""
    spy = _ReconfigureSpy()
    monkeypatch.setattr(reporter.sys, "stdout", spy)
    # _ORIGINAL_STDOUT is captured at module import; for the auto-tty branch
    # to not short-circuit, point it at an isatty=True fake too. force mode
    # bypasses the isatty check entirely, so this is belt-and-braces.
    monkeypatch.setattr(reporter, "_ORIGINAL_STDOUT", spy)
    monkeypatch.setattr(reporter, "_STATE", None)

    reporter.pytest_configure(_fake_config("force"))  # type: ignore[arg-type]

    assert spy.calls == [{"encoding": "utf-8", "errors": "replace"}], (
        f"pytest_configure must reconfigure stdout to utf-8/replace before "
        f"the reporter renders -- got {spy.calls!r}"
    )


def test_pytest_configure_skips_reconfigure_under_off(monkeypatch) -> None:
    """`--mcp-domain-ui=off` must early-return BEFORE touching stdout. The
    reconfigure is only safe to run when the reporter is actually going to
    render -- operators who opted out via --mcp-domain-ui=off (e.g. running
    on a non-UTF8-aware tty intentionally) must not see their stdout state
    silently changed."""
    spy = _ReconfigureSpy()
    monkeypatch.setattr(reporter.sys, "stdout", spy)
    monkeypatch.setattr(reporter, "_ORIGINAL_STDOUT", spy)
    monkeypatch.setattr(reporter, "_STATE", None)

    reporter.pytest_configure(_fake_config("off"))  # type: ignore[arg-type]

    assert spy.calls == [], (
        f"--mcp-domain-ui=off must not reconfigure stdout -- got {spy.calls!r}"
    )


def test_pytest_configure_tolerates_streams_without_reconfigure(
    monkeypatch,
) -> None:
    """pytest's capsys wrapper replaces sys.stdout with an object that does
    NOT implement reconfigure(). The hasattr() guard must skip cleanly so
    the reporter still initializes."""
    class _NoReconfigureStream:
        isatty = staticmethod(lambda: True)

    monkeypatch.setattr(reporter.sys, "stdout", _NoReconfigureStream())
    monkeypatch.setattr(reporter, "_ORIGINAL_STDOUT", _NoReconfigureStream())
    monkeypatch.setattr(reporter, "_STATE", None)

    # Must NOT raise AttributeError on missing reconfigure().
    reporter.pytest_configure(_fake_config("force"))  # type: ignore[arg-type]

    assert reporter._STATE is not None, (
        "pytest_configure must still initialize _STATE when sys.stdout "
        "lacks reconfigure() -- the guard short-circuits the reconfigure "
        "call but the rest of the init must proceed."
    )
