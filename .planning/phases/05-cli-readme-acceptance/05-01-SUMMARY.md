---
phase: 05-cli-readme-acceptance
plan: 01
subsystem: cli
tags: [cli, typer, scaffolding, importlib-metadata, console-script]

# Dependency graph
requires:
  - phase: 01-foundation-pure-data-core
    provides: Config() loader (pydantic-settings, MCPTF_CONFIG_FILE env-var seam at config.py:182)
  - phase: 01-foundation-pure-data-core
    provides: Package distribution metadata (pyproject.toml [project] name = "mvp-test-framework"; package = mcp_test_framework)
provides:
  - Typer `app` instance at module scope of src/mcp_test_framework/cli.py (no_args_is_help=True, add_completion=False)
  - `_load_config(path: Path | None) -> Config` shared helper for `run` (Plan 02) and `list-tools` (Plan 03)
  - `version` subcommand that prints package version via importlib.metadata (CLI-03)
  - Console-script entry point `mcp-test-framework` resolving to `mcp_test_framework.cli:app`
  - No-op `@app.callback()` that locks the app into Typer multi-command mode for Plans 02/03 to extend without churn
affects: [05-02-list-tools, 05-03-run, 05-04-readme-extending, 05-05-acceptance]

# Tech tracking
tech-stack:
  added:
    - "typer 0.25.1 (transitive via mcp[cli] extra)"
    - "rich 15.0.0 (transitive via typer)"
    - "shellingham 1.5.4, markdown-it-py 4.1.0, mdurl 0.1.2, annotated-doc 0.0.4 (transitive via typer/rich)"
  patterns:
    - "CLI scaffolding-first plan (split scaffold from command bodies so parallel waves don't collide)"
    - "No-op @app.callback() to force Typer multi-command mode when only one @app.command() is registered"
    - "importlib.metadata.version with PackageNotFoundError fallback to package __version__ constant"
    - "_load_config helper as the only Config()-instantiation seam from CLI; sets MCPTF_CONFIG_FILE env var when --config flag provided"

key-files:
  created:
    - "src/mcp_test_framework/cli.py - Typer CLI surface with app, _load_config helper, version command"
  modified:
    - "pyproject.toml - mcp>=1.27 -> mcp[cli]>=1.27 (deps); uncommented [project.scripts] mcp-test-framework = mcp_test_framework.cli:app"
    - "uv.lock - regenerated to lock typer + transitive deps"

key-decisions:
  - "Switched mcp>=1.27 to mcp[cli]>=1.27 (single source of truth for the CLI framework version; preserves the 'no direct typer dep' acceptance criterion)"
  - "Added no-op @app.callback() to force multi-command mode -- without it, Typer collapses a single-command app into single-callback mode and rejects the subcommand name as a positional arg"
  - "metadata.version('mvp-test-framework') uses the distribution name (M-V-P), distinct from the package name 'mcp_test_framework' (M-C-P) and the script name 'mcp-test-framework' (M-C-P) -- documented inline in cli.py"

patterns-established:
  - "Pattern: CLI controller with Typer app + module-scope helpers (_load_config) + @app.command()-registered subcommands. Module footer `if __name__ == '__main__': app()` for direct invocation via `python -m mcp_test_framework.cli`."
  - "Pattern: console-script entry point format `<distribution-name>-friendly = '<package_name>.module:app'` where the LHS uses hyphens and the RHS uses the importable underscore-package name."

requirements-completed: [CLI-03]

# Metrics
duration: 3 min
completed: 2026-05-06
---

# Phase 5 Plan 01: CLI Scaffold + version Command Summary

**Typer CLI scaffold with `version` subcommand, console-script entry point, and shared `_load_config` helper -- the foundation Plans 02 and 03 attach `run` and `list-tools` to without conflicts.**

## Performance

- **Duration:** ~3 minutes
- **Started:** 2026-05-06T22:56:40Z
- **Completed:** 2026-05-06T22:59:31Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- `src/mcp_test_framework/cli.py` exists with Typer `app`, `_load_config(path)` helper, and `version` subcommand
- Console-script `mcp-test-framework` resolves through `[project.scripts]` -- `uv run mcp-test-framework version` prints `0.1.0`
- `--help` lists `version` as an available subcommand; no-args invocation prints help and exits 2 (Typer `no_args_is_help=True`)
- `_load_config(Path('nonexistent.yaml'))` emits `error: --config path not found: nonexistent.yaml` to stderr and raises `typer.Exit(code=2)` (matches Phase 4 D-markers-2 / `_preflight` discipline)
- CLI-03 (`version` command) requirement complete

## Task Commits

Each task was committed atomically:

1. **Task 1: Create cli.py scaffold with version command + _load_config helper** - `27a5c17` (feat)
2. **Task 2: Uncomment [project.scripts] entry in pyproject.toml and refresh uv.lock** - `1efd58d` (feat)

## Files Created/Modified

- `src/mcp_test_framework/cli.py` (NEW) - Typer CLI surface (`run` placeholder reserved for Plan 02, `list-tools` for Plan 03, `version` shipped here). Module docstring indexes the spec section, decisions (D-cli-flags-1..3, D-list-1..4, D-teardown-1..3, CLI-03), and the Pitfall-1 mitigation reused via Plan 03's asyncio.Runner pattern.
- `pyproject.toml` - dependency `mcp>=1.27` upgraded to `mcp[cli]>=1.27` so Typer is pulled transitively; `[project.scripts]` block uncommented with provenance comment; commented-out shim removed.
- `uv.lock` - regenerated by `uv sync` to lock typer 0.25.1 + 5 transitive deps (rich 15.0.0, shellingham 1.5.4, markdown-it-py 4.1.0, mdurl 0.1.2, annotated-doc 0.0.4).

## Decisions Made

- **mcp[cli] extra over direct typer dep.** The plan's acceptance criterion forbids `"typer"` appearing directly in `pyproject.toml`. To make the dep resolvable while honoring that constraint, the existing `mcp>=1.27` line was upgraded to `mcp[cli]>=1.27` (the `[cli]` extra of the `mcp` SDK pulls Typer 0.25.1 + python-dotenv). Single source of truth for the CLI framework version stays with the `mcp` SDK.
- **No-op `@app.callback()` to force multi-command mode.** With exactly one `@app.command()` registered, Typer 0.25 collapses the app into a single-callback surface (the command's name becomes implicit). Calling `mcp-test-framework version` would then be parsed as an unexpected positional arg. An empty `_main()` callback decorated with `@app.callback()` keeps Typer in subcommand mode so `version` resolves correctly today and so Plans 02/03 can attach `run` and `list-tools` without churning the help shape.
- **importlib.metadata distribution-name lookup.** `metadata.version("mvp-test-framework")` uses the distribution name (`name = "mvp-test-framework"` in `[project]`), distinct from both the importable package (`mcp_test_framework`) and the console-script (`mcp-test-framework`). The discrepancy is documented inline in cli.py's module docstring and at the call site so future readers don't "fix" it back to one of the other two spellings.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Typer was not actually transitive via mcp's default install**

- **Found during:** Task 1 (verification step `uv run python -c "from mcp_test_framework.cli import app, ..."`)
- **Issue:** The plan asserts "Typer is already transitive via `mcp[cli]`" and the acceptance criterion `grep -c '"typer"' pyproject.toml` must return 0. But the existing `dependencies` line was `"mcp>=1.27"` (without the `[cli]` extra), so `uv sync` had not pulled typer. Result: `ModuleNotFoundError: No module named 'typer'` at import time.
- **Fix:** Changed `"mcp>=1.27"` -> `"mcp[cli]>=1.27"` in `[project.dependencies]` so the `[cli]` extra is requested, which pulls `typer>=0.16.0` per the mcp 1.27 metadata. `uv sync` then installed typer 0.25.1 + 5 transitive deps. The acceptance criterion `grep -c '"typer"'` still returns 0 because no direct typer dep was added.
- **Files modified:** `pyproject.toml`, `uv.lock`
- **Verification:** `uv pip list | grep typer` -> `typer 0.25.1`. `uv run python -c "from mcp_test_framework.cli import app, _load_config, version"` -> imports OK.
- **Committed in:** `27a5c17` (Task 1 commit)

**2. [Rule 3 - Blocking] Single-command Typer app collapsed into single-callback mode**

- **Found during:** Task 2 (verification step `uv run mcp-test-framework version`)
- **Issue:** With only one `@app.command()` registered (`version`), Typer 0.25 treated the app as a single-command surface: `--help` rendered the `version` command's help directly, and `mcp-test-framework version` was parsed as `mcp-test-framework <unexpected positional 'version'>` -> exit 2 with `Got unexpected extra argument (version)`. The plan's success criterion `uv run mcp-test-framework version` exits 0 and prints version was therefore unreachable.
- **Fix:** Added a no-op `@app.callback()` decorator on a `_main()` function in cli.py. Typer treats the presence of an `app.callback()` as a signal to operate in multi-command mode regardless of how many `@app.command()`s are registered. The behavior matches the eventual Plans 02/03 shape (where `run` and `list-tools` will require multi-command mode anyway), so the callback is permanent rather than a temporary scaffold.
- **Files modified:** `src/mcp_test_framework/cli.py`
- **Verification:** `uv run mcp-test-framework version` -> `0.1.0` (exit 0). `uv run mcp-test-framework --help` lists `version` under `Commands`. `uv run mcp-test-framework` (no args) prints help and exits 2.
- **Committed in:** `1efd58d` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 blocking)
**Impact on plan:** Both auto-fixes were necessary to reach the plan's stated success criteria. The first preserved an explicit acceptance criterion (`grep -c '"typer"' pyproject.toml` returns 0) by routing through the `mcp[cli]` extra rather than declaring typer directly. The second fixed a Typer behavioral quirk that the plan did not anticipate; the chosen mitigation (`@app.callback()`) is also the recommended shape for Plans 02/03 once they land, so no rework is needed downstream. No scope creep -- the plan's deliverable surface is unchanged.

## Issues Encountered

None beyond the two deviations documented above. Both were caught at verification, fixed inline, and re-verified before commit.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 05-02 (`list-tools`) can append `@app.command()` for `list_tools` to `cli.py` without scaffolding work; `_load_config(path)` is the documented entry point and the multi-command mode is locked by `@app.callback()`.
- Plan 05-03 (`run`) can append `@app.command()` for `run` similarly. Pytest delegation pattern (`pytest.main(["tests", *forwarded])`) is independent of this plan's surface.
- Plans 02 and 03 are now safely parallelizable per Phase 5's wave plan -- the file shape and import surface are stable.

## Self-Check: PASSED

- File `src/mcp_test_framework/cli.py` exists -> FOUND
- File `pyproject.toml` modified ([project.scripts] uncommented + mcp[cli]) -> FOUND
- Commit `27a5c17` (Task 1: cli.py scaffold) -> FOUND in `git log --oneline`
- Commit `1efd58d` (Task 2: [project.scripts] + multi-command callback) -> FOUND in `git log --oneline`
- `uv run mcp-test-framework version` exits 0 and prints `0.1.0` -> verified
- `uv run mcp-test-framework --help` lists `version` -> verified
- `uv run mcp-test-framework` (no args) exits 2 with help -> verified
- `_load_config(Path('nonexistent.yaml'))` raises `typer.Exit(code=2)` -> verified
- Acceptance criterion `grep -c '"typer"' pyproject.toml` returns 0 -> verified

---
*Phase: 05-cli-readme-acceptance*
*Completed: 2026-05-06*
