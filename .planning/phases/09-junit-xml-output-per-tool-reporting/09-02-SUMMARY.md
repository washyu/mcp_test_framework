---
phase: 09
plan: 02
subsystem: reporting
tags: [pytest-plugin, terminal-output, output-03, per-tool-summary]
requires:
  - phase-07-parametrize-ids  # nodeids carry [<tool>] suffix the plugin parses
  - phase-08-skip-reasons     # operator-authored, non-empty pytest.skip(reason=...)
provides:
  - per-tool-summary-renderer  # terminal section after pytest's built-in summary
  - reporter-plugin-seam       # mcp_test_framework._reporter (sibling of fixtures)
affects:
  - tests/conftest.py          # pytest_plugins list extended
tech-stack:
  added: []
  patterns:
    - underscore-private-module-under-src   # mirrors _isolation.py
    - module-level-state-dict-over-stashkey # mirrors Phase 07 _DISCOVERED_TOOL_NAMES
    - pytest-plugin-via-pytest_plugins-list # mirrors Phase 04 fixtures registration
key-files:
  created:
    - src/mcp_test_framework/_reporter.py
  modified:
    - tests/conftest.py
decisions:
  - encodes D-02 D-02a D-02b D-02c (plugin placement & emit channel)
  - encodes D-03 D-03a D-03b (verdict aggregation rules)
  - encodes D-04 D-04a D-04b (always-on, post-summary, -q-suppressed)
  - encodes D-05 D-05a (skip-reason de-dup, cap-at-3, verbatim)
  - encodes CD-03 (FAIL -> SKIP -> PASS, alphabetical within group)
  - em-dash separator (U+2014) on SKIP-with-reason rows per ROADMAP SC-3
metrics:
  duration_minutes: 12
  task_count: 2
  files_changed: 2
  completed_date: "2026-05-07"
requirements:
  - OUTPUT-03  # mechanism in place; Plan 09-03 owns the formal test suite
---

# Phase 09 Plan 02: Per-tool summary plugin Summary

Per-tool terminal summary (OUTPUT-03) ships as a sibling pytest plugin
(`mcp_test_framework._reporter`), aggregating `pytest_runtest_logreport`
outcomes and rendering a grouped FAIL→SKIP→PASS section in
`pytest_terminal_summary` -- always-on, suppressed under `-q`, em-dash
separated SKIP reasons.

## What Shipped

### `src/mcp_test_framework/_reporter.py` (NEW, 202 lines)

Pytest plugin module with:

- **`_PER_TOOL: dict[str, dict]`** -- module-level aggregation buffer keyed
  by tool name (parametrize-id suffix).
- **`_SKIP_REASON_CAP: int = 3`** -- de-dup cap before `; ... (N more)`
  rollup per D-05.
- **`_extract_tool_name(nodeid)`** -- parses `[<tool>]` suffix from
  `report.nodeid`; returns `None` for tests without the suffix (D-02a:
  unit tests excluded from summary).
- **`_extract_skip_reason(longrepr)`** -- pulls the human-readable reason
  out of pytest's `(file, lineno, "Skipped: <reason>")` 3-tuple, stripping
  the `"Skipped: "` prefix per D-05a verbatim contract.
- **`pytest_runtest_logreport(report)`** -- accumulates outcomes per D-03:
  - `report.failed` (covers `failed` AND `error` outcomes per D-03a) → FAIL sticky.
  - `outcome == "passed"` → PASS unless already FAIL.
  - `outcome == "skipped"` → record reason; verdict→SKIP only if no PASS/FAIL set.
- **`_format_skip_reasons(reasons)`** -- de-duplicated, first-seen order,
  semicolon-space joined, capped at `_SKIP_REASON_CAP`.
- **`pytest_terminal_summary(terminalreporter, exitstatus, config)`** --
  early-returns under `-q` (D-04b) or empty buffer; otherwise renders
  three groups (FAIL/SKIP/PASS, alphabetical within) per CD-03 using
  `terminalreporter.write_sep` / `terminalreporter.write_line` ONLY (D-02c).

Em-dash separator (U+2014, `—`) on SKIP-with-reason rows matches ROADMAP
Phase 09 SC-3 verbatim wording. ASCII-hyphen form `' SKIP - '` is provably
absent from the source.

### `tests/conftest.py` (MODIFIED)

Single-line `pytest_plugins` extension and a one-sentence docstring
amendment citing OUTPUT-03:

```python
pytest_plugins = ["mcp_test_framework.fixtures", "mcp_test_framework._reporter"]
```

Order is intentional: `fixtures` first (it owns the autouse `_preflight`
session fixture); `_reporter` appended as a strict reader (no fixtures of
its own, only hooks).

## Decisions Encoded

| Decision | Where in source |
|----------|-----------------|
| D-02 (plugin under `src/`, sibling of `fixtures`) | `tests/conftest.py:15` `pytest_plugins` list |
| D-02a (no `[<tool>]` suffix → excluded) | `_extract_tool_name` early-return None; `pytest_runtest_logreport` early-return on None |
| D-02b (underscore-private module under `src/`) | filename `_reporter.py` |
| D-02c (terminalreporter only) | `pytest_terminal_summary` uses `write_sep`/`write_line` only; zero `print` / `sys.stdout` in source |
| D-03 rule 1 (any FAIL/error → FAIL sticky) | `if report.failed: bucket["verdict"] = "FAIL"; return` |
| D-03 rule 2 (any PASS → PASS unless FAIL) | `if bucket["verdict"] != "FAIL": bucket["verdict"] = "PASS"` |
| D-03 rule 3 (else SKIP) | `if bucket["verdict"] is None: bucket["verdict"] = "SKIP"` |
| D-03a (error collapses to FAIL) | `report.failed` is True for both `failed` AND `error` outcomes |
| D-03b (no reason text on PASS/FAIL rows) | renderer only emits `— <reasons>` inside the SKIP block |
| D-04 (always-on) | no flag, no toggle in CLI; renderer fires unconditionally if `_PER_TOOL` populated |
| D-04a (after pytest's built-in summary) | `pytest_terminal_summary` natural ordering |
| D-04b (suppressed under `-q`) | `if terminalreporter.config.option.verbose < 0: return` |
| D-05 (de-dup, first-seen order, cap=3, `; ` joiner) | `_format_skip_reasons` |
| D-05a (verbatim, no transform) | reasons stored as-is; `_extract_skip_reason` only strips the `"Skipped: "` pytest prefix |
| CD-03 (FAIL → SKIP → PASS, alphabetical) | three `sorted(...)` lists rendered in fixed order with header line |
| ROADMAP SC-3 em-dash | `f"  {tool.ljust(name_width)}  SKIP — {reasons_text}"` literal U+2014 |

## Verification

| # | Check | Result |
|---|-------|--------|
| 1 | `_reporter.py` exists | ✓ |
| 2 | `wc -l _reporter.py` ≥ 80 | 202 lines ✓ |
| 3 | 5 named functions present | `_extract_tool_name`, `_extract_skip_reason`, `pytest_runtest_logreport`, `_format_skip_reasons`, `pytest_terminal_summary` ✓ |
| 4 | `_PER_TOOL: dict` module-level | ✓ |
| 5 | No module-top `import pytest` / `from pytest` | ✓ |
| 6 | No `print(` / `sys.stdout.write` in code (only in docstrings) | ✓ |
| 7 | No `try:` / `except` in source | ✓ |
| 8 | `mcp_test_framework._reporter` in `pytest_plugins` | ✓ |
| 9 | `OUTPUT-03` cited in `tests/conftest.py` docstring | ✓ |
| 10 | Helper smoke (`_extract_tool_name`, `_format_skip_reasons` cap rule) | `ok` ✓ |
| 11 | `uv run ruff check src/mcp_test_framework/_reporter.py tests/conftest.py` | "All checks passed!" ✓ |
| 12 | `uv run pytest tests/unit/ -q` | `56 passed in 0.32s`; no `per-tool summary` section emitted (D-02a empty-set early-return) ✓ |
| 13 | Em-dash present, ASCII hyphen-form absent | ✓ |

## Real-run snippet

The worktree lacks a `config.yaml`/`MCPTF_CONFIG_FILE` (parent-repo state
not copied into worktrees per project memory), so a live
`mcp-test-framework run -m live_homelab` is not exercisable here. Instead,
an in-process simulation of the plugin hooks against synthetic reports
(zoo FAIL, beta FAIL, apple SKIP w/reason, mango PASS, plus an excluded
unit-test report) yielded:

```
===== per-tool summary =====
(grouping: failures (alphabetical) -> skipped (alphabetical) -> passing (alphabetical))
failures:
  beta   FAIL
  zoo    FAIL
skipped:
  apple  SKIP — requires homelab
passing:
  mango  PASS
========================================
```

Confirms:
- FAIL group rendered before SKIP rendered before PASS (CD-03).
- Within FAIL, `beta` precedes `zoo` (alphabetical).
- Unit-test nodeid `tests/unit/test_x.py::test_y` did NOT add a row (D-02a).
- SKIP row uses em-dash ` — ` separator (U+2014) before reason text.
- `name_width` padding aligns the verdict column.

The full live-run snippet (against `homelab-mcp` + Ollama judge, exercising
Phase 08 retained `suggest_deployments` failure and the per-tool 8-PASS /
2-SKIP `list_keyring_credentials` mix) is the responsibility of Plan 09-03's
fixture-driven test scenarios + the orchestrator's wave-2 verifier pass.

## Deviations from Plan

None - plan executed exactly as written.

The plan's "line 12" reference for `pytest_plugins` resolved to line 15
after the docstring grew by the prescribed 3-line Phase 9 amendment; the
content of the line matches the plan verbatim. Not a deviation -- the
plan's `behavior` test is `c.pytest_plugins == [...]`, content not
position.

The plan's `<verify>` block referenced `uv run --extra dev pytest ...`;
the project actually uses PEP 735 `[dependency-groups].dev` (per
`pyproject.toml` lines 28-39), so the equivalent invocation is
`uv run --group dev pytest ...`. Documented for the next executor.

## Self-Check: PASSED

- src/mcp_test_framework/_reporter.py: FOUND
- tests/conftest.py modified: FOUND (`mcp_test_framework._reporter` and `OUTPUT-03` both present)
- Commit 7ed681e (Task 1): FOUND
- Commit e56dedd (Task 2): FOUND
