---
status: complete
phase: 05-cli-readme-acceptance
source: [05-01-SUMMARY.md, 05-02-SUMMARY.md, 05-03-SUMMARY.md, 05-04-SUMMARY.md, 05-05-SUMMARY.md]
started: 2026-05-07T00:47:29Z
updated: 2026-05-07T01:02:00Z
---

## Current Test

[testing complete]

## Tests

### 1. version command exits 0 and prints 0.1.0
expected: `uv run mcp-test-framework version` prints `0.1.0` and exits 0 (SC#3 regression check after the 5 code-review fixes).
result: pass

### 2. Top-level --help lists all three commands
expected: `uv run mcp-test-framework --help` exits 0 and lists `list-tools`, `run`, and `version` under Commands.
result: pass

### 3. run --config <missing>.yaml exits 2 with clean diagnostic (WR-02 fix)
expected: |
  `uv run mcp-test-framework run --config nonexistent.yaml` exits 2 and prints exactly one line to stderr:
  `error: --config path not found: nonexistent.yaml`.
  After the command exits, run `echo $env:MCPTF_CONFIG_FILE` in the same PowerShell session — it must be empty
  (the WR-02 fix pops the env var when Config() raises, so a stale path can't leak into a later invocation).
result: pass

### 4. list-tools --help shows --config and --json flags
expected: `uv run mcp-test-framework list-tools --help` exits 0 and the help block contains both `--config PATH` and `--json` options.
result: pass

### 5. list-tools (text mode) prints sorted tool list against live homelab-mcp
expected: |
  `uv run mcp-test-framework list-tools` connects to homelab-mcp via uvx, prints the alphabetically-sorted tool list
  with 2-space indented descriptions wrapped to terminal width, and exits 0. After exit, `Get-Process homelab-mcp`
  returns nothing (clean teardown — SC#4 natural-exit case).
result: pass

### 6. list-tools --json emits well-formed JSON with all four keys (WR-03 / WR-04 fix)
expected: |
  `uv run mcp-test-framework list-tools --json` exits 0 and prints a JSON array. Pipe through ConvertFrom-Json:
  `uv run mcp-test-framework list-tools --json | ConvertFrom-Json | Select-Object -First 1 | Format-List`
  The first record exposes `name`, `description`, `inputSchema`, AND `outputSchema` (WR-03 verified — direct attribute
  access for both schemas). No tool emits a stringified non-JSON value (WR-04 verified — `default=str` is gone, so
  any non-serializable schema content would have crashed instead of silently coercing).
result: pass

### 7. Full pytest sweep via run exits 0 (SC#1 / SC#6 + WR-01 regression)
expected: |
  `uv run mcp-test-framework run` (no `--`, no extra args) connects to live homelab-mcp + Ollama and produces standard
  pytest output ending with a green summary line (e.g., `67 passed, 5 deselected, 1 warning in ~22s`), exit code 0.
  This validates: (a) WR-01's `list[str] | None` typing of `pytest_args` doesn't break the no-extras invocation,
  (b) `MCPTF_CONFIG_FILE` env var (when --config is passed) still propagates into pytest's plugin chain after WR-02's
  fix, and (c) the green walkthrough is reproducible after the cli.py changes.
result: pass
observed: "67 passed, 5 deselected, 1 warning in 32.45s — exit 0. Warning is the benign anyio assert-rewrite warning carried over from prior runs."

### 8. SIGINT during list-tools exits 130 with no message (WR-05 fix)
expected: |
  Run `uv run mcp-test-framework list-tools` and press Ctrl+C while it is still running. Exit code is exactly 130
  and stderr/stdout do not print any traceback or "aborted" message. After exit, `Get-Process homelab-mcp` returns
  nothing.
result: pass
note: |
  WR-05 added an explicit `try/except KeyboardInterrupt -> typer.Exit(code=130)` handler in cli.py. The 05-05
  walkthrough's PARTIAL PASS verdict on OPS-03 (interrupt-window-narrowness on warm uvx cache) is now upgraded
  by direct UAT observation here.

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
