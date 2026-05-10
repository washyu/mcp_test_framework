---
phase: 12-doc-persona-foundation
plan: 05
subsystem: cli/list-tools
tags: [cli, list-tools, persona, ergonomics, persona-02]
requirements: [PERSONA-02]
dependency-graph:
  requires:
    - 12-04 (cli.py absorbs _emit_operator_error + FileNotFoundError handler before this plan rewrites _format_tools_text)
  provides:
    - list-tools default render at signature granularity (D-05)
    - list-tools --full verbosity flag (D-06)
    - list-tools --name PATTERN substring filter (D-08)
    - _format_param_signature(tool) helper for downstream reuse
  affects:
    - tests/test_readme_snippets.py (snippet text may need update if README ships a list-tools sample; Plan 06 will reconcile)
tech-stack:
  added: []
  patterns:
    - "JSON Schema -> Python type-label mapping (string->str, integer->int, etc.); unknown types fall back to 'Any'"
    - "Defaults rendered via repr() for injection containment (T-12-14 mitigation)"
    - "Two orthogonal flags: --full (verbosity) vs --json (format) per D-07"
    - "Filter-before-serialize for --json --name composition"
key-files:
  created:
    - tests/unit/test_list_tools_format.py
  modified:
    - src/mcp_test_framework/cli.py
decisions:
  - "D-07 orthogonality enforced at the CLI level by passing --full into the human-readable formatter only; --json branch ignores it (output byte-identical to --json alone, asserted by test_json_full_orthogonal)."
  - "Required params preserve their order from inputSchema.required (often domain-meaningful); optional kwargs are sorted alphabetically for determinism."
  - "Empty-after-filter message names the unfiltered server total so the operator knows the filter (not the server) was the cause (Pitfall 3 mitigation)."
metrics:
  duration: ~10min
  completed: 2026-05-09
  commits: 2
  tasks_completed: 1
  files_changed: 2
  tests_added: 18
---

# Phase 12 Plan 05: list-tools UX at N=70 Summary

**One-liner:** Reshaped `list-tools` for the 70-tool persona surface — signature-first default render, `--full` verbosity flag, and case-insensitive `--name` substring filter, with `--json` orthogonality preserved by test.

## Tasks Completed

| Task | Name                                                                                          | Commit  | Files                                                              |
| ---- | --------------------------------------------------------------------------------------------- | ------- | ------------------------------------------------------------------ |
| 1a   | RED: failing tests for `_format_param_signature` + `_format_tools_text` + CLI orthogonality | ab9b8e1 | tests/unit/test_list_tools_format.py                               |
| 1b   | GREEN: add helper + rewrite formatter + add `--full` / `--name` Typer options                 | 4a53428 | src/mcp_test_framework/cli.py, tests/unit/test_list_tools_format.py |

## What Shipped

- `_format_param_signature(tool: Tool) -> str` — derives `"()"`, `"(host: str)"`, `"(*, timeout: int = 30)"`, or `"(host: str, *, timeout: int = 30)"` from `tool.inputSchema`. JSON Schema scalar types mapped to short Python labels; unknown types fall back to `"Any"`. Defaults rendered via `repr()` so strings stay quoted and newlines/quotes are escaped (T-12-14 mitigation against malicious-server signature injection).
- `_format_tools_text(tools, *, full=False, name_filter=None)` — signature-first per-tool blocks. Default uses `textwrap.shorten` for the description (1-line truncated, `...` placeholder); `--full` uses `textwrap.fill` for wrapped description plus a `parameters:` block listing per-param descriptions from `inputSchema`. Empty-after-filter returns a distinct message naming the filter and the unfiltered server total.
- `list-tools` Typer command — adds `--full` (bool) and `--name PATTERN` (str) options. Under `--json`, `--full` is silently a no-op (D-07 orthogonality enforced by `test_json_full_orthogonal`); `--name` filter still applies pre-serialization so JSON consumers can narrow output too.
- `_format_tools_json` body **untouched** (only the call-site argument changed from `tools` to `filtered`) — preserves the v1.1 D-list-2 / D-07 byte-shape contract.

## Verification

- `uv run pytest tests/unit/test_list_tools_format.py -x` — **18/18 passed**.
- `uv run pytest tests/unit/` — **126/126 passed** (no regressions across the unit suite).
- `git diff src/mcp_test_framework/cli.py` inside `_format_tools_json` body — **no `+`/`-` lines** (D-07 contract held).
- Acceptance criteria grep checks: `"--full"` x1, `"--name"` x1, `_format_param_signature` x2 — all met.
- `tests/test_readme_snippets.py` aborts on collection in this worktree because `homelab-mcp` is not on PATH — **pre-existing environmental issue, not a regression** (the worktree env does not ship the live SUT). The snippet test will run in CI/operator environments where `homelab-mcp` is installed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocker] CliRunner removed `mix_stderr` kwarg in current Click**
- **Found during:** Task 1, GREEN run
- **Issue:** `runner = CliRunner(mix_stderr=False)` raised `TypeError: CliRunner.__init__() got an unexpected keyword argument 'mix_stderr'`. The plan's literal test code reflects an older Click API; the current installed Click no longer accepts that kwarg.
- **Fix:** Switched to default `CliRunner()` (which already exposes combined output via `result.output`). Updated assertion failure messages from `res.stderr` to `res.output`. The byte-identical `stdout` comparison is preserved — only the *failure-case* diagnostic surface changed.
- **Files modified:** tests/unit/test_list_tools_format.py
- **Commit:** 4a53428 (folded into GREEN since the test was uncommitted at this point)

## Threat Model Status

The plan's `<threat_model>` register (T-12-13, T-12-14, T-12-15) was honored:

- **T-12-14 (Tampering, mitigate)** — Defaults are rendered via `{prop['default']!r}` in `_format_param_signature`. `repr()` quotes strings and escapes newlines/quotes, so a malicious server emitting `default: "\nfake_param: 'evil'"` produces `'\nfake_param: \'evil\''` (visibly escaped, single line) rather than a fake parameter line. Verified by `test_param_signature_default_value_repr` which asserts `= 'hello'` (with quotes).
- **T-12-13, T-12-15 (Information Disclosure / DoS, accept)** — No mitigation required per plan; surface is no different from v1.1's wrapped-description default.

No new threat surface introduced. No `## Threat Flags` needed.

## Known Stubs

None. The plan delivered a complete user-facing capability with no placeholder data paths.

## Self-Check: PASSED

- [x] `tests/unit/test_list_tools_format.py` exists (FOUND)
- [x] `src/mcp_test_framework/cli.py` modified (FOUND)
- [x] Commit ab9b8e1 (RED) exists in `git log` (FOUND)
- [x] Commit 4a53428 (GREEN) exists in `git log` (FOUND)
- [x] All 18 new tests pass; full unit suite (126) green
- [x] Acceptance criteria grep checks satisfied (`"--full"` x1, `"--name"` x1, `_format_param_signature` x2)
- [x] `_format_tools_json` body unchanged (only call site argument changed `tools` -> `filtered`)
- [x] TDD gate sequence: `test(12-05)` -> `feat(12-05)` present in git log (RED -> GREEN compliant)

## TDD Gate Compliance

- RED gate: commit `ab9b8e1` (`test(12-05): add failing tests ...`)
- GREEN gate: commit `4a53428` (`feat(12-05): add --full / --name flags ...`)
- REFACTOR gate: skipped (no refactor needed; implementation arrived clean from research's Code Example 5)
