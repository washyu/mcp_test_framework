---
phase: 09-junit-xml-output-per-tool-reporting
plan: 01
subsystem: cli
tags: [cli, pytest-passthrough, junit-xml, OUTPUT-01]
requires: []
provides:
  - "cli._build_pytest_args(junit_xml, pytest_args) -> list[str]"
  - "cli run --junit-xml=PATH Typer option"
affects:
  - "cli.run argv construction (now goes through _build_pytest_args helper)"
tech_stack_added: []
tech_stack_patterns:
  - "Typer option insertion between existing --config and trailing positional pytest_args"
  - "Module-level underscore-private helper colocated with _load_config (mirrors precedent in cli.py)"
key_files_created: []
key_files_modified:
  - "src/mcp_test_framework/cli.py"
decisions:
  - "Implemented CD-06 option 3 (extracted helper) so --junit-xml -> --junitxml translation is unit-testable without spawning pytest."
  - "D-01a precedence honored: explicit --junit-xml argv lands BEFORE passthrough so a later passthrough --junitxml=... wins via pytest's last-occurrence argparse rule."
  - "D-01b honored: public CLI flag spelled --junit-xml (with dash); pytest receives --junitxml (no dash). Help text documents both spellings."
metrics:
  duration: "~2 minutes"
  completed: "2026-05-08"
  tasks_completed: 1
  files_changed: 1
  commits: 1
---

# Phase 09 Plan 01: --junit-xml CLI flag wiring Summary

Add `--junit-xml=PATH` to `mcp-test-framework run` via an extracted module-level `_build_pytest_args` helper, satisfying OUTPUT-01 while preserving Phase 5's L-03 (no try/except wrap on `pytest.main`) and L-04 (pytest import stays function-local) invariants.

## What Shipped

A single additive change to `src/mcp_test_framework/cli.py`:

1. **New module-level helper** `_build_pytest_args(junit_xml, pytest_args) -> list[str]`, placed between `_load_config` and the `run` command (cli.py:92-117). Translates the public-spelling `--junit-xml=PATH` into pytest's no-dash `--junitxml=PATH` and assembles the argv. Inserts the explicit-flag arg BEFORE the passthrough so pytest's last-occurrence argparse rule lets a passthrough `--junitxml=...` override (D-01a).

2. **New Typer option** `--junit-xml: Path | None` on `run`, between the existing `--config` option and the trailing `pytest_args` positional (cli.py:130-140). Help text cites the spelling difference (D-01b) and the precedence rule (D-01a).

3. **Updated `run` body** (cli.py:165): replaced
   ```python
   forwarded = list(pytest_args or [])
   raise typer.Exit(code=pytest.main(["tests", *forwarded]))
   ```
   with
   ```python
   raise typer.Exit(code=pytest.main(_build_pytest_args(junit_xml, pytest_args)))
   ```
   The `raise typer.Exit(code=pytest.main(...))` shape is byte-identical apart from the argv source — L-03 preserved (no try/except, single call site).

4. **Docstring amendment** on `run` (cli.py:151-154): one new paragraph citing OUTPUT-01, D-01a, D-01b, and CD-06 option 3.

## Diff Outline (cli.py)

| Region | Change | Decision Reference |
|---|---|---|
| cli.py:92-117 (NEW) | `_build_pytest_args` module-level helper | CD-06 option 3 |
| cli.py:130-140 (NEW lines inside `run` signature) | `junit_xml: Path \| None = typer.Option(None, "--junit-xml", help=...)` | D-01b spelling, D-01a precedence in help text |
| cli.py:151-154 (NEW paragraph in `run` docstring) | Phase 09 OUTPUT-01 citation paragraph | OUTPUT-01 |
| cli.py:165 (REPLACED) | Inline argv list -> `_build_pytest_args(junit_xml, pytest_args)` call | L-03 preserved |

Net diff: `+43 / -2` (single file).

## Behavior Confirmation (interactive smoke)

Verified via `uv run python -c "..."` per the plan's `<done>` criteria. All 5 helper-shape behaviors enumerated in `<behavior>` produce the expected argv:

| Input | Expected argv | Status |
|---|---|---|
| `(None, None)` | `["tests"]` | PASS |
| `(Path("results.xml"), None)` | `["tests", "--junitxml=results.xml"]` | PASS |
| `(Path("a.xml"), ["--junitxml=b.xml"])` | `["tests", "--junitxml=a.xml", "--junitxml=b.xml"]` | PASS (explicit BEFORE passthrough — D-01a) |
| `(None, ["-k", "schema"])` | `["tests", "-k", "schema"]` | PASS (no `--junitxml` injected) |
| `(Path("results.xml"), ["-v", "-k", "judge"])` | `["tests", "--junitxml=results.xml", "-v", "-k", "judge"]` | PASS |

`uv run mcp-test-framework run --help` exits 0 and shows:
```
| --junit-xml        PATH  Write JUnit XML to PATH. Translates internally to  |
|                          pytest's `--junitxml=PATH` (note pytest's no-dash  |
|                          spelling). If a passthrough `--junitxml=...` is    |
|                          also supplied after `--`, the passthrough wins via |
|                          pytest's last-occurrence argparse rule (D-01a).    |
```

The `--junit-xml` literal appears 2x in the help output and `pytest` 10x — both gates from `<verification>` step 6 satisfied.

## Invariant Preservation

| Invariant | Status | Evidence |
|---|---|---|
| L-03 (no try/except wrap on `pytest.main`) | PRESERVED | `grep -nE "try:\|except" cli.py \| grep -A2 "pytest.main"` returns no matches. The `pytest.main(...)` call still sits inside a single `raise typer.Exit(code=...)` expression. |
| L-04 (pytest import is function-local) | PRESERVED | `grep -cE "^import pytest\|^from pytest" cli.py` returns 0. The `import pytest` line remains inside the `run` function body (still indented). |
| L-05 (markers / addopts unchanged) | PRESERVED | `pyproject.toml` not touched in this plan. |
| D-cli-flags-3 / Phase 5 contract | PRESERVED | The `pytest.main()` call is still bare under `raise typer.Exit(code=...)`. |

## Verification Gates Run (cli.py only)

| Gate | Command | Result |
|---|---|---|
| 1 | `grep -n "def _build_pytest_args" cli.py` | 1 match (line 92) |
| 2 | `grep -n '"--junit-xml"' cli.py` | 1 match (line 132 — Typer option literal) |
| 3 | `grep -n "junitxml" cli.py` | 6 matches, all inside helper docstring, helper body, Typer option `help=`, or `run` docstring — no module-scope occurrences |
| 4 | `grep -cE "^import pytest\|^from pytest" cli.py` | 0 (function-local only) |
| 5 | `grep -nE "try:\|except" cli.py \| grep -A2 "pytest.main"` | empty (no try/except near pytest.main) |
| 6 | `uv run mcp-test-framework run --help` | exit 0; `--junit-xml` 2x; `pytest` 10x |
| 7 | `uv run python -c "from mcp_test_framework.cli import _build_pytest_args; print(_build_pytest_args(None, None))"` | prints `['tests']` |
| 8 | `uv run ruff check src/mcp_test_framework/cli.py` | All checks passed! |

## No Regressions Sanity

- `uv run mcp-test-framework version` -> `0.1.0` (exit 0)
- `uv run mcp-test-framework list-tools --help` -> renders normally; `list-tools` signature byte-identical
- `uv run mcp-test-framework config-init --help` (implicitly verified — same module, ruff passed, function unchanged)

## Decisions Implemented

| Decision | How |
|---|---|
| OUTPUT-01 | `--junit-xml=PATH` flag visible in `run --help`; translates to pytest's `--junitxml=PATH` |
| D-01 (explicit flag + passthrough preserved) | Both surfaces produce equivalent pytest argv |
| D-01a (passthrough wins on duplicate) | Helper inserts explicit-flag arg BEFORE forwarded args; pytest's argparse last-occurrence rule does the rest. Help text documents the rule. No cross-flag validation added (per decision). |
| D-01b (public --junit-xml -> pytest --junitxml) | f-string `f"--junitxml={junit_xml}"` in helper; help text mentions the spelling difference. |
| CD-06 option 3 (extracted helper for testability) | `_build_pytest_args` is a module-level pure function -- callable as `from mcp_test_framework.cli import _build_pytest_args` for unit tests in Plan 09-03. |

## Threat Surface

No new trust boundaries introduced. The plan's `<threat_model>` enumerated three accept-disposition threats (T-09-01..03); none required mitigation code. The `--junit-xml` value is a `Path` object pre-validated by Typer; no shell, no subprocess, no string-interpolation hazard. Path is forwarded to pytest as a Python list arg.

## Deviations from Plan

None. Plan executed exactly as written.

The `<verify><automated>` command (`uv run --extra dev pytest tests/test_reporter.py -k "build_pytest_args or junit_xml_help" -x`) intentionally cannot run yet — `tests/test_reporter.py` is created in Plan 09-03 (per the plan's own `<verify>` note). Plan 09-01's testable evidence is the interactive smoke command from `<done>`, all of which passed.

## Self-Check

- File created/modified:
  - `src/mcp_test_framework/cli.py` — FOUND, modified (+43/-2)
- Commits:
  - `1ad0c94` `feat(09-01): add --junit-xml flag + _build_pytest_args helper to cli run` — FOUND
- Plan-level TDD gate compliance: this plan's `tdd="true"` is task-level; tests for `_build_pytest_args` live in Plan 09-03 by design (CD-04 plan cut). Helper-shape behaviors verified manually via interactive smoke per the plan's `<done>` instructions.

## Self-Check: PASSED
