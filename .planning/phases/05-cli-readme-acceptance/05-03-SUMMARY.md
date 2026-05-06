---
phase: 05-cli-readme-acceptance
plan: 03
subsystem: cli
tags: [cli, typer, mcp, list-tools, asyncio-runner]

# Dependency graph
requires:
  - phase: 05-cli-readme-acceptance
    plan: 01
    provides: Typer `app`, `_load_config(path)` helper, `@app.callback()` multi-command lock, `version` command at src/mcp_test_framework/cli.py
  - phase: 05-cli-readme-acceptance
    plan: 02
    provides: `run` Typer command attached to the same `app` (CLI-01); proves the multi-command surface scales
  - phase: 04.1-mcp-client-teardown-fix
    provides: Phase 04.1 same-task lifecycle pattern (asyncio.Runner + AsyncExitStack-owned McpTestClient -- the Pitfall 1 mitigation reused at the CLI surface)
  - phase: 02-mcp-client-wrapper
    provides: McpTestClient(__aenter__/__aexit__/list_tools) at src/mcp_test_framework/mcp_client.py
provides:
  - "`list-tools` Typer command at src/mcp_test_framework/cli.py with --config + --json options (CLI-02)"
  - "`_list_tools_async(cfg)` helper -- single-task lifecycle driver via AsyncExitStack-owned McpTestClient"
  - "`_format_tools_text(tools)` -- stdlib textwrap.fill + shutil.get_terminal_size; D-list-1, D-list-3"
  - "`_format_tools_json(tools)` -- sorted full MCP tool records (name + description + inputSchema + outputSchema) with trailing newline; D-list-2, D-list-4"
  - "OPS-03 for the `list-tools` path (Pitfall 1 mitigation reused; verified end-to-end in Plan 05 UAT, D-teardown-2)"
  - "SEED-001 / GEN-01 seam -- `--json` output already emits the full Tool record shape an LLM-test-generator would consume, no re-fetch required"
affects: [05-04-readme-extending, 05-05-acceptance]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "asyncio.Runner + AsyncExitStack-owned McpTestClient for CLI bodies (D-teardown-1; reuses Phase 04.1 same-task lifecycle, NOT the cross-task owner-task pattern from fixtures.py)"
    - "Stdlib-only terminal text formatting (shutil.get_terminal_size + textwrap.fill); no rich dep"
    - "Defensive non-serializable fallback in JSON emit (`json.dumps(..., default=str)`) so a pathological tool schema never crashes list-tools"
    - "`getattr(t, 'outputSchema', None)` -- tolerates older Tool versions without an outputSchema attribute"

key-files:
  created:
    - ".planning/phases/05-cli-readme-acceptance/05-03-FORMATTER-SMOKE.txt - 4-check smoke capture (sort, indent, empty list, None description)"
  modified:
    - "src/mcp_test_framework/cli.py - inserted `list_tools` command between `run` and `version`; appended `_list_tools_async`, `_format_tools_text`, `_format_tools_json` helpers; expanded imports (asyncio, json, shutil, textwrap, AsyncExitStack, mcp.types.Tool, McpTestClient) -- 107 inserted lines"

key-decisions:
  - "asyncio.Runner over asyncio.run() (D-teardown-1) -- Runner gives explicit single-task event-loop ownership so KeyboardInterrupt unwind happens on the same task that did __aenter__; this is the Phase 04.1 lesson reused at the CLI surface"
  - "AsyncExitStack inside _list_tools_async even though there is currently only one resource -- future-proofing + explicit ownership signal that mirrors Phase 04.1"
  - "Stdlib textwrap + shutil ONLY for text formatting -- no rich dependency added; Discretion bullet from CONTEXT.md"
  - "`--json` emits the FULL MCP tool record (name + description + inputSchema + outputSchema), sorted alphabetically -- D-list-2/D-list-4; deliberately the shape SEED-001 / GEN-01 will consume"
  - "Silent exit 130 on Ctrl+C (D-teardown-3) -- no try/except KeyboardInterrupt, no 'Interrupted' message; subprocess teardown is the only hard requirement"

requirements-completed: [CLI-02, OPS-03]

# Metrics
duration: 3 min
completed: 2026-05-06
---

# Phase 5 Plan 03: `list-tools` Command Summary

**Adds the `list-tools` Typer command to `src/mcp_test_framework/cli.py` -- one command body + three helpers (107 lines) that wire `uv run mcp-test-framework list-tools [--config PATH] [--json]` to a single-task asyncio.Runner + AsyncExitStack-owned McpTestClient lifecycle. Reuses Phase 04.1's hardened same-task pattern for OPS-03 on the list-tools path. CLI-02 + OPS-03 (list-tools path) complete; SEED-001 / GEN-01 input shape seeded by `--json`.**

## Performance

- **Duration:** ~3 minutes
- **Started:** 2026-05-06T23:08:21Z
- **Completed:** 2026-05-06T23:10:44Z
- **Tasks:** 2
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- `list-tools` Typer command appended to `cli.py` between `run` and `version`; `_list_tools_async`, `_format_tools_text`, `_format_tools_json` helpers appended after `version`
- `uv run mcp-test-framework list-tools --help` exits 0 and lists both `--config PATH` and `--json`
- `uv run mcp-test-framework --help` lists three commands: `list-tools`, `run`, `version`
- `uv run mcp-test-framework list-tools --config /nonexistent.yaml` exits 2 with one-line stderr diagnostic (`error: --config path not found: ...`) -- routed through Plan 01's `_load_config`
- Module imports cleanly: `from mcp_test_framework.cli import app, run, version, list_tools, _load_config, _list_tools_async, _format_tools_text, _format_tools_json` -> exit 0
- Four formatter smoke checks PASS (synthetic Tool records): alphabetical sort, 2-space indent, empty-list (`(no tools registered on the server)`), None-description (`(no description)`)
- JSON emit is sorted by name, contains all four keys per record (name, description, inputSchema, outputSchema), and ends with a trailing newline
- CLI-02 (connect to MCP server, list tools, no pytest, no Ollama) requirement complete
- OPS-03 for the `list-tools` path is wired: asyncio.Runner + AsyncExitStack-owned McpTestClient -> KeyboardInterrupt unwinds the same task that did `__aenter__` -> `stdio_client._terminate_process_tree` kills the subprocess. Live Ctrl+C UAT is Plan 05's responsibility (D-teardown-2)

## Task Commits

Each task was committed atomically on the main working tree (sequential executor):

1. **Task 1: Add list-tools command + helpers to cli.py** - `b04cf42` (feat)
2. **Task 2: Smoke-verify formatter helpers with synthetic Tool records** - `2a2c794` (docs)

## Files Created/Modified

- `src/mcp_test_framework/cli.py` (MODIFIED) - inserted the `list_tools` Typer command between `_load_config`+`run` and `version`; appended three module-scope helpers (`_list_tools_async`, `_format_tools_text`, `_format_tools_json`) after `version`. Expanded the import block with stdlib (asyncio, json, shutil, textwrap, AsyncExitStack), `mcp.types.Tool`, and `mcp_test_framework.mcp_client.McpTestClient`. The `list_tools` body is three substantive lines (`cfg = _load_config(config)`, `with asyncio.Runner() as runner: tools = runner.run(_list_tools_async(cfg))`, then either `_format_tools_json` or `_format_tools_text`); the rest is the Plan-spec docstring covering D-list-1..4 + D-teardown-1..3 + the Phase 04.1 reuse rationale. 107 inserted lines, no existing code touched.
- `.planning/phases/05-cli-readme-acceptance/05-03-FORMATTER-SMOKE.txt` (NEW) - 4-check smoke capture: text-format sort + indent, JSON-format sort + full record + trailing newline, empty-list edge case, None-description tolerance. All four PASS on first attempt.

## Decisions Made

- **asyncio.Runner over asyncio.run().** D-teardown-1 / Phase 04.1 reuse. `asyncio.Runner()` gives explicit single-task event-loop ownership for the entire `_list_tools_async` coroutine -- the McpTestClient `__aenter__` and `__aexit__` are guaranteed to run on the same task, which is the documented Pitfall 1 mitigation. `asyncio.run()` would also keep them on a single task today, but Runner is the future-proof primitive (re-entry safety, explicit teardown order) and visibly mirrors the Phase 04.1 lesson for any future reader.
- **AsyncExitStack despite a single resource.** The plan calls this out explicitly (`<action>` step 3 docstring): the AsyncExitStack form is technically redundant with `async with McpTestClient(...)` for a single resource, BUT it (1) future-proofs against a second resource (e.g., a logger handle), (2) mirrors the Phase 04.1 ownership lesson at the CLI surface, and (3) keeps `__aexit__` semantics identical regardless of how many resources land later. Net cost is two lines of indentation; net benefit is documentation discipline.
- **Stdlib-only text formatting.** No `rich` dependency added. CONTEXT.md Discretion bullet locks `shutil.get_terminal_size((80, 20))` + `textwrap.fill(width=max(20, width-2), initial_indent='  ', subsequent_indent='  ')`. The terminal-size fallback to 80 cols means redirected stdout still gets sane wrapping, and the `max(20, width-2)` floor prevents pathological 1-col output if a hostile environment reports a tiny TTY.
- **`--json` emits the full MCP tool record.** D-list-2 / D-list-4: `[{name, description, inputSchema, outputSchema}, ...]` sorted alphabetically by name, with a trailing newline so the output composes with shell pipelines. `default=str` is a defensive fallback for non-serializable annotation values; `getattr(t, "outputSchema", None)` tolerates older Tool versions. The shape is deliberately the input an LLM-test-generator (SEED-001 / GEN-01) would consume -- no re-fetch needed.
- **Silent exit 130 on Ctrl+C.** D-teardown-3 / CONTEXT.md "no partial-output message on Ctrl+C". No `try/except KeyboardInterrupt` anywhere in the body; KeyboardInterrupt propagates out of the runner, out of the Typer command, out of the Python interpreter -> default exit code 130. Subprocess teardown is the only hard requirement; absence of a message is a feature, not an oversight.

## Deviations from Plan

None - plan executed exactly as written. No bugs found, no missing critical functionality, no blocking issues, no architectural changes needed.

The plan's `<interfaces>` and `<action>` blocks already contained the canonical recipe (lines 71-114 / 138-259 of `05-03-PLAN.md`); the implementation is a verbatim transcription. The earlier checker-feedback fix to this plan (commit `c3aa52f`, mentioned in the Phase 5 ROADMAP context) had already addressed the false-positive grep on prose `owner-task` and the dev-dep `import pytest` issue from Plan 02 -- neither concern manifested here.

## Authentication Gates

None - the `list-tools` command's CLI plumbing is purely local (file existence check + module construction). Live MCP execution (which would actually launch `homelab-mcp`) is reserved for Plan 05 UAT; no homelab-mcp subprocess was spawned during this plan's execution.

## Issues Encountered

None. All Task 1 grep acceptance criteria, all Task 2 smoke checks, and all final-verification commands passed on first attempt:

| Verification check                                                | Expected            | Actual              | Result |
|-------------------------------------------------------------------|---------------------|---------------------|--------|
| `grep -c '^import asyncio'` on cli.py                             | 1                   | 1                   | PASS   |
| `grep -c '^import json'` / `^import shutil` / `^import textwrap`  | 1 each              | 1 each              | PASS   |
| `grep -c 'from contextlib import AsyncExitStack'`                 | 1                   | 1                   | PASS   |
| `grep -c 'from mcp.types import Tool'`                            | 1                   | 1                   | PASS   |
| `grep -c 'from mcp_test_framework.mcp_client import McpTestClient'` | 1                 | 1                   | PASS   |
| `grep -c '@app.command("list-tools")'`                            | 1                   | 1                   | PASS   |
| `grep -c 'def list_tools('`                                       | 1                   | 1                   | PASS   |
| `grep -cE 'asyncio\.Future\|asyncio\.Event\|owner_task'`          | 0                   | 0                   | PASS   |
| `grep -c 'asyncio.run('`                                          | 0 (Runner only)     | 0                   | PASS   |
| `grep -c 'import rich'`                                           | 0                   | 0                   | PASS   |
| `grep -cE 'except KeyboardInterrupt'`                             | 0                   | 0                   | PASS   |
| `grep -c '"-m"'` (D-markers-3 contract)                           | 0                   | 0                   | PASS   |
| `list-tools --help` exits 0 + lists `--config` and `--json`       | yes                 | yes                 | PASS   |
| `--help` lists `list-tools`, `run`, `version`                     | three commands      | three commands      | PASS   |
| `list-tools --config /nonexistent.yaml` exits 2                   | exit 2              | exit 2              | PASS   |
| Module import smoke                                               | imports ok          | imports ok          | PASS   |
| Smoke check 1: text sorted + indented                             | sorted, '  A...'    | sorted, '  A...'    | PASS   |
| Smoke check 2: JSON sorted + 4 keys + trailing newline            | as-spec'd           | as-spec'd           | PASS   |
| Smoke check 3: empty list                                         | exact strings       | exact strings       | PASS   |
| Smoke check 4: None description -> '(no description)'             | substring present   | substring present   | PASS   |

## User Setup Required

None - no external service configuration required. Plan 05 UAT will require live homelab-mcp + Ollama for the `run` path's green-suite check and a manual Ctrl+C exercise for `list-tools` (D-teardown-2).

## Next Phase Readiness

- **Plan 05-04 (README + EXTENDING)** can now document `mcp-test-framework list-tools [--json]` as a working invocation. The smoke capture in `05-03-FORMATTER-SMOKE.txt` is evidence the formatters behave correctly; the `--help` output is the live source for the README's commands section.
- **Plan 05-05 (acceptance UAT)** has its CLI-02 verification target ready: against live homelab-mcp, `uv run mcp-test-framework list-tools` should print all server tools alphabetically with their full descriptions. The Ctrl+C UAT (Get-Process homelab-mcp returns no matches after SIGINT mid-call) is the OPS-03 / D-teardown-2 manual check.
- The CLI's three-command surface is now complete and stable. No further `cli.py` edits are anticipated for this phase; remaining plans are documentation (05-04) and acceptance (05-05).

## Self-Check: PASSED

- File `src/mcp_test_framework/cli.py` modified (def list_tools + 3 helpers inserted) -> FOUND
- File `.planning/phases/05-cli-readme-acceptance/05-03-FORMATTER-SMOKE.txt` created -> FOUND
- Commit `b04cf42` (Task 1: list-tools command + helpers) -> FOUND in `git log --oneline`
- Commit `2a2c794` (Task 2: formatter smoke capture) -> FOUND in `git log --oneline`
- `uv run mcp-test-framework list-tools --help` exits 0, lists `--config` and `--json` -> verified
- `uv run mcp-test-framework --help` lists `list-tools`, `run`, `version` -> verified
- `uv run mcp-test-framework list-tools --config /nonexistent.yaml` exits 2 with `error: --config path not found:` stderr -> verified
- `uv run python -c "from mcp_test_framework.cli import app, run, version, list_tools, _load_config, _list_tools_async, _format_tools_text, _format_tools_json; print('imports ok')"` -> imports ok
- All Task 1 grep acceptance criteria pass (counts match)
- All four Task 2 smoke checks PASS

---
*Phase: 05-cli-readme-acceptance*
*Completed: 2026-05-06*
