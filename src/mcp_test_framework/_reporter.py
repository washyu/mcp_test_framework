"""Per-tool summary reporter (OUTPUT-03).

Phase 09 implementation of OUTPUT-03 -- a pytest plugin that subscribes to
``pytest_runtest_logreport`` to accumulate per-tool outcomes during the run,
then emits a grouped per-tool summary section in ``pytest_terminal_summary``
AFTER pytest's built-in FAILURES / ERRORS / summary-line sections (D-04a).

Design constraints (per .planning/phases/09-junit-xml-output-per-tool-reporting/09-CONTEXT.md):
- D-02:  Plugin lives under ``src/`` (not ``tests/``); registered via
         ``pytest_plugins`` chain in ``tests/conftest.py``; sibling to
         ``mcp_test_framework.fixtures``.
- D-02a: Tool-name extraction parses the ``[<tool_name>]`` parametrize-id
         suffix from ``report.nodeid`` (Phase 07 ``ids=names`` convention at
         tests/conftest.py:124-136). Reports without the suffix (unit tests)
         are excluded from the summary entirely.
- D-02c: Output goes through ``terminalreporter.write_sep`` /
         ``terminalreporter.write_line`` -- never raw ``print`` /
         ``sys.stdout.write``. Keeps formatting consistent with pytest's
         section dividers and respects ``-q``.
- D-03:  Any-fail-wins. Algorithm per tool:
            1) any failed/error -> FAIL
            2) else any passed  -> PASS
            3) else             -> SKIP
- D-03a: ``error`` outcome (collection / fixture-setup) collapses into FAIL.
         (XML preserves <error> vs <failure> natively per CD-01.)
- D-03b: PASS / FAIL rows have NO reason text. Reason text is only on SKIP rows.
- D-04:  Always-on under ``mcp-test-framework run``. No flag, no toggle.
- D-04b: Suppressed under ``-q`` (verbose < 0).
- D-05:  SKIP reasons collected from ``report.longrepr``, de-duplicated
         preserving first-seen order, joined with ``; ``, capped at 3
         distinct (append ``; ... (N more)`` if more).
- D-05a: Reasons rendered VERBATIM -- no truncation, no escaping.
- CD-03: Row ordering: FAIL (alphabetical) -> SKIP (alphabetical) -> PASS
         (alphabetical), with a header line above the table.
- L-01:  ``[<tool_name>]`` IDs already emit through pytest's JUnit reporter;
         this plugin reads them OUT for terminal aggregation only.
- L-02:  ``pytest.skip(reason=...)`` flows through ``report.longrepr`` --
         the reporter reads it for terminal text; XML emission is automatic.
- L-06:  Phase 08 D-09 contract: skip reasons reach the active reporter.
         This plugin IS that reporter for the terminal channel.

The SKIP-with-reason row separator is an em-dash (U+2014, ``—``) -- the
literal character ``—`` -- matching ROADMAP Phase 09 SC-3 verbatim
wording (``<tool_name>: PASS|FAIL|SKIP — <reason>``). NOT an ASCII hyphen.
"""
from __future__ import annotations

# Module-level per-tool aggregation buffer. Keyed by extracted tool name
# (the parametrize-suffix from report.nodeid). Plain module global with
# type annotation -- same style as tests/conftest.py:65 _DISCOVERED_TOOL_NAMES.
# CD-01 in Phase 07 chose dict over pytest.StashKey for simplicity; same
# logic applies here per D-02 "live state -- no JUnit XML re-parse, no extra
# parser dep". Reset semantics: pytest re-imports the plugin once per
# session, so module-load is the reset boundary.
_PER_TOOL: dict[str, dict] = {}

_SKIP_REASON_CAP: int = 3

# Phase 13 revision iteration 1: the discovered-tools cache lives HERE
# (production code), not in tests/conftest.py. tests/conftest.py WRITES
# this attribute during pytest_generate_tests; _compose_unparametrized_skips
# READS it at pytest_terminal_summary time. Single-direction dependency:
# production exports state, tests read. Pre-empts Phase 15's `tests/contract/`
# vs `tests/framework/` split.
_DISCOVERED_TOOL_NAMES: "list[str] | None" = None


def _extract_tool_name(nodeid: str) -> str | None:
    """Return tool name from ``<file>::<test>[<tool>]`` nodeid, or None.

    Phase 07 parametrize ID convention (tests/conftest.py:124-136 emits
    ``ids=names`` so the bracketed suffix IS the tool name verbatim).
    Tests without the ``[...]`` suffix (unit tests under tests/unit/)
    return None -- D-02a excludes them from the per-tool summary.
    """
    if "[" not in nodeid or not nodeid.endswith("]"):
        return None
    return nodeid[nodeid.rindex("[") + 1 : -1]


def _extract_skip_reason(longrepr) -> str | None:
    """Pull the human-readable reason string out of ``report.longrepr``.

    For tests skipped via ``pytest.skip(reason=...)``, ``longrepr`` is the
    3-tuple ``(filepath, lineno, "Skipped: <reason>")`` (pytest prefixes
    "Skipped: " automatically). Strip the prefix so the rendered row
    matches D-05a verbatim-no-transform on the operator-supplied portion.
    Other longrepr shapes (string, ExceptionInfo) are tolerated by the
    isinstance-tuple guard; on shape mismatch we return None and the row
    falls back to "<tool>: SKIP" with no reason text.
    """
    if isinstance(longrepr, tuple) and len(longrepr) >= 3:
        reason = longrepr[2]
        if isinstance(reason, str):
            # pytest prefixes "Skipped: " on the longrepr text; the
            # operator-authored string is everything after that prefix.
            prefix = "Skipped: "
            return reason[len(prefix):] if reason.startswith(prefix) else reason
    return None


def pytest_runtest_logreport(report) -> None:
    """Accumulate per-tool outcomes. Fires 3x per test (setup/call/teardown).

    Aggregation rule (D-03):
      - report.failed  (covers outcome="failed" AND setup/teardown errors)
        -> mark verdict FAIL (sticky -- later passes do not downgrade).
      - report.outcome == "passed" on the call phase
        -> mark verdict PASS unless already FAIL.
      - report.outcome == "skipped"
        -> record reason; verdict only becomes SKIP if no PASS/FAIL ever set.

    D-03a: ``report.failed`` is True for both ``failed`` outcomes (assertion
    failures) AND ``error`` outcomes (collection / fixture-setup errors).
    Both collapse into FAIL in the terminal summary; XML preserves both
    distinctly via pytest's defaults (CD-01).
    """
    tool = _extract_tool_name(report.nodeid)
    if tool is None:
        return  # D-02a: tests without [<tool>] suffix excluded.

    bucket = _PER_TOOL.setdefault(tool, {"verdict": None, "reasons": []})

    # D-03 rule 1: any failed/error -> FAIL (sticky).
    if report.failed:
        bucket["verdict"] = "FAIL"
        return

    if report.outcome == "passed":
        # D-03 rule 2: PASS only sets if not already FAIL.
        if bucket["verdict"] != "FAIL":
            bucket["verdict"] = "PASS"
        return

    if report.outcome == "skipped":
        reason = _extract_skip_reason(report.longrepr)
        if reason is not None and reason not in bucket["reasons"]:
            bucket["reasons"].append(reason)
        # D-03 rule 3: SKIP only sticks if nothing else ever set verdict.
        if bucket["verdict"] is None:
            bucket["verdict"] = "SKIP"
        return


def _format_skip_reasons(reasons: list[str]) -> str:
    """Render the skip-reason text per D-05.

    Rules:
      - empty list -> empty string (caller decides whether to render the row
        without a ``— <reason>`` suffix).
      - 1-N reasons (N <= cap) -> ``r1; r2; r3``.
      - more than cap -> first ``cap`` reasons + ``; ... (M more)`` where M
        is the number trimmed.
    Reasons are rendered VERBATIM -- D-05a (no quoting/normalization).
    """
    if not reasons:
        return ""
    if len(reasons) <= _SKIP_REASON_CAP:
        return "; ".join(reasons)
    head = "; ".join(reasons[:_SKIP_REASON_CAP])
    return f"{head}; ... ({len(reasons) - _SKIP_REASON_CAP} more)"


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    """Emit the per-tool summary section.

    D-04a: This hook fires AFTER pytest's built-in FAILURES / ERRORS /
    summary-line -- natural pytest_terminal_summary ordering.
    D-04b: Suppress under ``-q`` (``config.option.verbose < 0``).
    D-02c: Emit via terminalreporter ONLY -- no print, no sys.stdout.write.
    CD-03: Group rows FAIL -> SKIP -> PASS, alphabetical within each.
    """
    if terminalreporter.config.option.verbose < 0:
        return  # D-04b
    if not _PER_TOOL:
        return  # No tool-affined tests collected; nothing to summarize.

    # Compute column width for tool-name padding so PASS/FAIL/SKIP align.
    name_width = max(len(name) for name in _PER_TOOL)

    fails = sorted(t for t, v in _PER_TOOL.items() if v["verdict"] == "FAIL")
    skips = sorted(t for t, v in _PER_TOOL.items() if v["verdict"] == "SKIP")
    passes = sorted(t for t, v in _PER_TOOL.items() if v["verdict"] == "PASS")

    terminalreporter.write_sep("=", "per-tool summary")
    terminalreporter.write_line(
        "(grouping: failures (alphabetical) -> skipped (alphabetical) -> passing (alphabetical))"
    )

    if fails:
        terminalreporter.write_line("failures:")
        for tool in fails:
            terminalreporter.write_line(f"  {tool.ljust(name_width)}  FAIL")
    if skips:
        terminalreporter.write_line("skipped:")
        for tool in skips:
            reasons_text = _format_skip_reasons(_PER_TOOL[tool]["reasons"])
            if reasons_text:
                # Em-dash (U+2014) per ROADMAP Phase 09 SC-3 verbatim wording.
                terminalreporter.write_line(
                    f"  {tool.ljust(name_width)}  SKIP — {reasons_text}"
                )
            else:
                terminalreporter.write_line(f"  {tool.ljust(name_width)}  SKIP")
    if passes:
        terminalreporter.write_line("passing:")
        for tool in passes:
            terminalreporter.write_line(f"  {tool.ljust(name_width)}  PASS")

    terminalreporter.write_sep("=")
