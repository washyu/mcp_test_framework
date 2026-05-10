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

# Phase 13 D-12 / SAFE-01: two distinct skip-reason strings for opt-in
# tool selection. Module-level constants so they cannot drift silently;
# tests/unit/test_reporter.py pins both verbatim.
_REASON_NOT_SELECTED = "not selected in config"        # state (a): unlisted
_REASON_EXPLICIT_DEFAULT = "explicit skip in config"   # state (c): default

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


def _compose_unparametrized_skips(config) -> dict[str, str]:
    """Phase 13 D-12/D-13: return {tool_name: reason} for every discovered
    tool that did NOT parametrize -- i.e., tools that dropped out of
    collection via tests/conftest.py:_resolve_tool_names' allowlist filter.

    State (c) wins over state (a) when a tool is listed-with-skip:true:
    we emit the operator's `skip_reason` if non-empty, else the default
    `_REASON_EXPLICIT_DEFAULT`. State (a) (unlisted): `_REASON_NOT_SELECTED`.

    Returns {} when discovery never ran (e.g., a pure-unit-test pytest
    session that never hit pytest_generate_tests for `target_tool`).

    Read from this module's own state, not from tests/conftest.py. tests/
    conftest.py is the WRITER of _DISCOVERED_TOOL_NAMES on this module;
    _reporter is the READER. Pre-empts Phase 15's `tests/contract/` split.
    """
    discovered = _DISCOVERED_TOOL_NAMES
    if not discovered:
        return {}

    tools_cfg = getattr(config, "tools", {}) or {}
    result: dict[str, str] = {}
    for name in discovered:
        if name in _PER_TOOL:
            continue  # parametrized -- the standard path handles it.
        cfg_entry = tools_cfg.get(name)
        if cfg_entry is not None and getattr(cfg_entry, "skip", False):
            # state (c)
            reason = (getattr(cfg_entry, "skip_reason", "") or "").strip()
            result[name] = reason or _REASON_EXPLICIT_DEFAULT
        else:
            # state (a)
            result[name] = _REASON_NOT_SELECTED
    return result


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    """Emit the per-tool summary section.

    D-04a: This hook fires AFTER pytest's built-in FAILURES / ERRORS /
    summary-line -- natural pytest_terminal_summary ordering.
    D-04b: Suppress under ``-q`` (``config.option.verbose < 0``).
    D-02c: Emit via terminalreporter ONLY -- no print, no sys.stdout.write.
    CD-03: Group rows FAIL -> SKIP -> PASS, alphabetical within each.

    Phase 13 D-12/D-13 addition: state-a/state-c SKIP rows are composed
    from `Config.tools` + the discovered-tools cache via
    `_compose_unparametrized_skips`. These rows render alongside the
    `_PER_TOOL`-derived SKIP rows so the operator sees one summary line
    per discovered tool, with the SAFE-01 reason strings distinguishing
    "not selected in config" (state a) from "explicit skip in config"
    (state c default) or the operator's curated skip_reason.
    """
    if terminalreporter.config.option.verbose < 0:
        return  # D-04b

    # Phase 13 D-12/D-13: even with _PER_TOOL empty, we may have state-a/c
    # skips to render (the operator's `tools: {}` run, or every tool
    # listed with skip:true). Load the framework Config to compose them.
    try:
        from mcp_test_framework.config import Config as _FwConfig
        _fw_cfg = _FwConfig()
    except Exception:  # noqa: BLE001 -- under unit-only runs Config() may
        # fail (SAFE-03 fail-loud, no config in cwd). The terminal-summary
        # path is best-effort; absence of Config means we cannot compose
        # state-a/c rows.
        _fw_cfg = None
    unparam_skips: dict[str, str] = (
        _compose_unparametrized_skips(_fw_cfg) if _fw_cfg is not None else {}
    )
    if not _PER_TOOL and not unparam_skips:
        return  # Nothing to summarize.

    # Phase 13: column width accounts for state-a/c additions.
    all_names = list(_PER_TOOL.keys()) + list(unparam_skips.keys())
    name_width = max((len(n) for n in all_names), default=0)

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

    # Phase 13: union the _PER_TOOL SKIP set with the state-a/c set so
    # operators see one row per discovered-but-unrun tool.
    all_skips = sorted(set(skips) | set(unparam_skips.keys()))
    if all_skips:
        terminalreporter.write_line("skipped:")
        for tool in all_skips:
            if tool in _PER_TOOL and _PER_TOOL[tool]["verdict"] == "SKIP":
                reasons_text = _format_skip_reasons(_PER_TOOL[tool]["reasons"])
            else:
                reasons_text = unparam_skips[tool]
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
