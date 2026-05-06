---
phase: 05-cli-readme-acceptance
plan: 02
subsystem: cli
tags: [cli, typer, pytest, run, ops-03]

# Dependency graph
requires:
  - phase: 05-cli-readme-acceptance
    plan: 01
    provides: Typer `app`, `_load_config(path)` helper, no-op `@app.callback()` multi-command lock, `version` command at src/mcp_test_framework/cli.py
  - phase: 04-fixtures-test-cases
    provides: pytest_plugins registration in tests/conftest.py + addopts contract `-m 'not live_homelab and not live_ollama'` in pyproject.toml (D-markers-3)
  - phase: 04.1-mcp-client-teardown-fix
    provides: AsyncExitStack-owned mcp_client fixture in src/mcp_test_framework/fixtures.py (covers OPS-03 for the run path via pytest's SIGINT handling)
provides:
  - "`run` Typer command at src/mcp_test_framework/cli.py with --config + pytest-args forwarding via `--`"
  - "CLI-01 (canonical CI/CD entry point: `uv run mcp-test-framework run` invokes pytest.main([\"tests\", *forwarded]))"
  - "OPS-03 for the `run` path (falls out free via pytest's SIGINT + Phase 04.1 fixture; verified end-to-end in Plan 05 UAT)"
affects: [05-03-list-tools, 05-04-readme-extending, 05-05-acceptance]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Function-local `import pytest` inside `run` -- pytest is dev-only ([dependency-groups] dev), NOT in [project.dependencies]; module-scope import would break version/list-tools for users installing the wheel without dev extras"
    - "Typer context_settings={allow_extra_args: True, ignore_unknown_options: True} + pytest_args: list[str] = typer.Argument(None, ...) -- collects everything after `--` for forwarding to pytest.main()"
    - "Config loaded at the CLI level BEFORE pytest.main() so config errors fail with a clean diagnostic before pytest's plugin chain produces opaque INTERNALERROR (D-discretion bullet 4)"
    - "NO try/except wrap around pytest.main() (D-cli-flags-3) -- pytest's own SIGINT handler unwinds finalizers; AsyncExitStack-owned mcp_client fixture terminates homelab-mcp.exe; OS exit code is whatever pytest returns"
    - "NO explicit -m flag passed to pytest.main() -- addopts contract from pyproject.toml (D-markers-3) stays in effect automatically"

key-files:
  created:
    - ".planning/phases/05-cli-readme-acceptance/05-02-RUN-SMOKE.txt - 4-check smoke capture (exit codes + stderr cleanliness) for the SUMMARY"
  modified:
    - "src/mcp_test_framework/cli.py - inserted `run` command between `_load_config` and `version` (42 lines added)"

key-decisions:
  - "function-local import pytest inside run() -- preserves wheel install for users without dev extras"
  - "context_settings allow_extra_args + ignore_unknown_options -- canonical Typer recipe for `argv after --` forwarding (the `--` separator itself is consumed by Click and does NOT appear in pytest_args)"
  - "_load_config(config) called BEFORE pytest.main() -- config errors fail at the CLI seam, not deep inside pytest's plugin chain (D-discretion bullet 4)"

patterns-established:
  - "Pattern: Typer subcommand for forwarding stdlib runner argv -- @app.command(context_settings={allow_extra_args: True, ignore_unknown_options: True}) + positional list[str] argument + raise typer.Exit(code=runner.main([fixed_args, *forwarded]))"
  - "Pattern: dev-only dependency in a CLI subcommand -- function-local import (deferred); module docstring documents WHY (so a future reader doesn't 'fix' it back to module-scope)"

requirements-completed: [CLI-01, OPS-03]

# Metrics
duration: 2 min
completed: 2026-05-06
---

# Phase 5 Plan 02: `run` Command Summary

**Adds the `run` Typer command at `src/mcp_test_framework/cli.py` -- three substantive lines (load config, collect args, delegate) that wire `uv run mcp-test-framework run` to `pytest.main(["tests", *forwarded])` with --config error handling and pytest-args forwarding via `--`. CLI-01 + OPS-03 (run path) complete.**

## Performance

- **Duration:** ~2 minutes
- **Started:** 2026-05-06T23:03:46Z
- **Completed:** 2026-05-06T23:05:28Z
- **Tasks:** 2
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- `run` Typer command appended to `cli.py` between `_load_config` and `version` -- 42 inserted lines, no existing code touched
- `uv run mcp-test-framework run --help` exits 0 and lists `--config PATH` plus the `[PYTEST_ARGS]...` positional
- `uv run mcp-test-framework run --config <nonexistent>.yaml` exits 2 with one-line stderr diagnostic (`error: --config path not found: ...`) -- routed through `_load_config` from Plan 01
- `uv run mcp-test-framework run -- --collect-only -q` exits 0; pytest collects 67/72 tests (5 deselected by `addopts -m 'not live_homelab and not live_ollama'` -- D-markers-3 contract honored automatically)
- `uv run mcp-test-framework run -- --invalid-pytest-flag-xyz` exits 4 (pytest's usage-error code propagates through `typer.Exit(code=...)`)
- stderr is CLEAN on the collect-only run (zero matches for `Traceback|ImportError|INTERNALERROR`) -- confirms function-local `import pytest` doesn't leak any startup-time failure
- `uv run mcp-test-framework --help` now lists both `run` and `version` as commands (Plan 03 will add `list-tools`)
- CLI-01 (canonical CI/CD entry point) requirement complete
- OPS-03 for the `run` path is free via pytest's SIGINT handler + Phase 04.1's AsyncExitStack-owned `mcp_client` fixture (Plan 05 UAT will manually verify end-to-end)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add `run` command to cli.py with --config + pytest-args forwarding** - `7c627bd` (feat)
2. **Task 2: Smoke-verify the `run` command delegates to pytest correctly** - `9dab436` (docs)

## Files Created/Modified

- `src/mcp_test_framework/cli.py` (MODIFIED) - inserted the `run` Typer command between `_load_config` and `version`. 42 inserted lines: `@app.command(context_settings={...})` decorator (allow_extra_args + ignore_unknown_options), `def run(config: Path | None, pytest_args: list[str])` signature, docstring covering D-cli-flags-1..3 + D-markers-3 + the function-local-import rationale, and the three-line body (`import pytest` (function-local), `_load_config(config)`, `raise typer.Exit(code=pytest.main(["tests", *forwarded]))`).
- `.planning/phases/05-cli-readme-acceptance/05-02-RUN-SMOKE.txt` (NEW) - 4-check smoke capture: EXIT_HELP=0, EXIT_BAD_CONFIG=2, EXIT_COLLECT=0 (with empty stderr), EXIT_INVALID=4 (pytest's usage-error code).

## Decisions Made

- **Function-local `import pytest` inside `run`.** pytest lives in `[dependency-groups] dev` -- it is NOT in `[project.dependencies]`. A user installing the wheel without dev extras (e.g., `pip install mvp-test-framework`) would hit `ImportError: No module named "pytest"` on `mcp-test-framework version` or any future `list-tools` command at module-import time. The deferred import inside `run`'s body keeps the dev-only dep out of the CLI's startup path. The module docstring explains the rationale so future readers don't "fix" it back to module-scope.
- **`context_settings={"allow_extra_args": True, "ignore_unknown_options": True}` + positional `list[str]` argument.** Canonical Typer recipe for the `argv after --` forwarding pattern. With `allow_extra_args=True`, Typer/Click collects positional args (including everything after `--`) into the `Argument` list. The `--` separator itself is consumed by Click and does NOT appear in `pytest_args`, so the body just unpacks `*pytest_args` into `pytest.main(["tests", ...])` with no separator-stripping needed.
- **Config loaded at the CLI level (BEFORE pytest.main()).** `_load_config(config)` runs first; if `--config` points at a missing file, `_load_config` (Plan 01) emits the diagnostic and raises `typer.Exit(code=2)` -- the user sees a clean one-line error before pytest's plugin chain produces an opaque `INTERNALERROR`. Pydantic `ValidationError` from a malformed YAML still propagates uncaught (D-discretion bullet 2: "Pydantic's own messages are good enough for MVP").

## Deviations from Plan

None - plan executed exactly as written. No bugs found, no missing critical functionality, no blocking issues, no architectural changes needed.

The plan's `<interfaces>` block already contained the canonical Typer recipe (lines 92-103); the `<action>` block already specified the exact code to insert (lines 138-178). The implementation is a verbatim transcription of that recipe with the docstring expanded inline as the plan instructed.

## Authentication Gates

None - the `run` command's CLI plumbing is purely local (file existence check + pytest delegation). No external services touched in this plan; live homelab-mcp / Ollama gates are reserved for Plan 05 UAT.

## Issues Encountered

None. All four smoke checks passed on the first attempt:

| Smoke check | Expected | Actual | Result |
|---|---|---|---|
| `run --help` lists `--config` | grep matches `--config` | matched on stdout line `\| --config        PATH  ...` | PASS |
| `run --config <missing>.yaml` exits 2 | EXIT=2 + one-line stderr | EXIT=2, stderr: `error: --config path not found: ...` | PASS |
| `run -- --collect-only -q` | EXIT=0, stderr clean | EXIT=0, stderr 0 bytes, 67/72 tests collected (5 deselected) | PASS |
| `run -- --invalid-flag` | non-zero EXIT | EXIT=4 (pytest's usage-error code) | PASS |

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Plan 05-03 (`list-tools`)** can append `@app.command()` for `list_tools` to the same `cli.py` file without conflict. The shared `_load_config` helper is in place; the import surface (typer, Path, Config) is already imported at module scope.
- **Plan 05-04 (README + EXTENDING)** can document `mcp-test-framework run --config foo.yaml -- -k pattern` as a working invocation -- the smoke captures in `05-02-RUN-SMOKE.txt` are evidence the example is live.
- **Plan 05-05 (acceptance UAT)** has its CLI-01 verification target ready: SC#6 ("standard pytest terminal output and exits 0") is achievable via `uv run mcp-test-framework run` with live homelab-mcp + Ollama. The smoke run already proved pytest collection and forwarding work; UAT just needs to flip the live markers via env vars.

## Self-Check: PASSED

- File `src/mcp_test_framework/cli.py` modified (def run inserted) -> FOUND
- File `.planning/phases/05-cli-readme-acceptance/05-02-RUN-SMOKE.txt` created -> FOUND
- Commit `7c627bd` (Task 1: add run command) -> FOUND in git log
- Commit `9dab436` (Task 2: smoke capture) -> FOUND in git log
- `uv run mcp-test-framework run --help` exits 0, lists `--config` and `pytest_args` -> verified
- `uv run mcp-test-framework run --config <nonexistent>` exits 2 with `error: --config path not found:` stderr -> verified
- `uv run mcp-test-framework run -- --collect-only -q` exits 0, stderr clean -> verified
- `uv run python -c "from mcp_test_framework.cli import app, run, version, _load_config; print('imports ok')"` -> imports ok
- Acceptance criterion `grep -c "^import pytest$" src/mcp_test_framework/cli.py` returns 0 (no module-scope import) -> verified
- Acceptance criterion `grep -c "    import pytest" src/mcp_test_framework/cli.py` returns 1 (function-local) -> verified
- Acceptance criterion `grep -c "^def run(" src/mcp_test_framework/cli.py` returns 1 -> verified
- Acceptance criterion `grep -c "allow_extra_args" src/mcp_test_framework/cli.py` returns 1 -> verified
- Acceptance criterion `grep -B 5 "pytest.main" cli.py | grep -c "try:"` returns 0 (D-cli-flags-3) -> verified
- Acceptance criterion `grep -c '"-m"' src/mcp_test_framework/cli.py` returns 0 (D-markers-3) -> verified

---
*Phase: 05-cli-readme-acceptance*
*Completed: 2026-05-06*
