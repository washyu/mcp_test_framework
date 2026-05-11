---
phase: 14-hybrid-runner-with-domain-ui
plan: 03
subsystem: cli
tags: [renderer, domain-ui, ansi, header, summary, em-dash, render-context]

# Dependency graph
requires:
  - phase: 14-01-subprocess-spine
    provides: "src/mcp_test_framework/_runner.py module + cli.py:run subprocess + tempfile JUnit; the `PLAN-03 REMOVES` seam at the renderer hook point"
  - phase: 14-02-junit-xml-parser
    provides: "parse_junit_xml(path) -> ParsedRun + ToolVerdict; the typed domain model the renderer consumes"
provides:
  - "render_domain_ui(parsed, ctx) + RenderContext dataclass: SEED-011 §2 header / per-tool rows / summary line"
  - "_compose_unparametrized_skips_from_config (PURE function): state-(a)/(c) skip composer that no longer depends on the deleted _DISCOVERED_TOOL_NAMES module global"
  - "cli.py:run rewired to discover -> subprocess -> parse -> render in default mode; --raw path unchanged"
  - "_discover_tools_for_run helper in cli.py: wrapper-side MCP handshake mirroring the AsyncExitStack pattern from list_tools"
  - "ET.ParseError -> _emit_operator_error (Phase 14 D-16) surface for 'JUnit XML parse failed'"
  - "tests/test_runner_renderer.py: 16 unit tests pinning header, row ordering, em-dash, state-(a)/(c), ANSI guard, no-pytest-framing"
affects: [14-04-verbosity-flags, 14-05-reporter-cleanup]

# Tech tracking
tech-stack:
  added: []  # no new deps -- stdlib f-strings + ANSI escapes + dataclasses only
  patterns:
    - "RenderContext dataclass as the wire format between cli.py (state owner: Config + discovery) and _runner.py (state-free renderer)"
    - "PURE function _compose_unparametrized_skips_from_config taking discovered_tools as an ARG (architectural shift from v1.1 _reporter._compose_unparametrized_skips which read _DISCOVERED_TOOL_NAMES off a module global)"
    - "Wrapper-side discovery via AsyncExitStack-owned McpTestClient (Phase 04.1 same-task lifecycle); mirrors list_tools failure-mode parity"
    - "file=None default + 'if file is None: file = sys.stdout' at call time: capsys-friendly pattern (file=sys.stdout default would bind to pre-test stdout at function definition time, bypassing pytest's capsys fixture)"
    - "ANSI guard via sys.stdout.isatty(): piped output stays plain, terminal output gets color (Phase 14 D-06)"

key-files:
  created:
    - "tests/test_runner_renderer.py - 16 unit tests pinning Phase 14 D-04..D-09, RUNNER-02 must_haves, em-dash U+2014, CD-03 row ordering, no-pytest-framing invariant"
  modified:
    - "src/mcp_test_framework/_runner.py - appended ~270 lines: RenderContext, _compose_unparametrized_skips_from_config, ANSI helpers, _render_header, _render_per_tool_rows, _render_summary_line, render_domain_ui"
    - "src/mcp_test_framework/cli.py - rewired run() default mode body: cfg captured from _load_config, _discover_tools_for_run helper added, ET.ParseError -> D-16, RenderContext + render_domain_ui call; Plan 01 transitional echo removed"

key-decisions:
  - "RenderContext dataclass over ad-hoc kwargs: typed surface for the cli.py <-> _runner.py seam. Allows Plan 14-04 (--debug / -q) and Phase 16 (--explain) to extend the context without rewriting the renderer signature."
  - "PURE function composer (discovered_tools as ARG, not module global). Aligns with the Phase 14 architectural shift away from in-pytest plugin globals -- the wrapper runs in a separate process and cannot reach _reporter._DISCOVERED_TOOL_NAMES. Plan 14-05's deletion of _reporter.py is therefore unblocked: the composer is self-contained."
  - "Wrapper-side discovery via _discover_tools_for_run BEFORE the subprocess (CONTEXT D-claude bullet 5 option (a)). Cost: one extra MCP handshake per `run` invocation. Benefit: header counts (Discovered/Running/Skipping) are accurate even for state-(a) unlisted tools that never appear in the JUnit XML. Trade-off accepted."
  - "file=None default + call-time sys.stdout resolution. The plan specified file=sys.stdout default, but that breaks pytest capsys capture (file= default binds to function-definition-time stdout, not test-time replacement). Functionally identical, but capsys-friendly. Tracked as deviation Rule 1 below."

patterns-established:
  - "Pure-function composer for state-(a)/(c) skip rows -- no module globals; wrapper passes inputs in. Plan 14-05's _reporter deletion is unblocked."
  - "RenderContext as the cli.py <-> _runner.py wire format. Future flags (--debug, -q, --explain) extend the context, not the renderer signature."
  - "file=None / call-time sys.stdout pattern for capsys-compatible renderer functions."

requirements-completed: [RUNNER-02]  # RUNNER-02 (domain-shaped header + rows + summary) is now complete; Plan 02 was the parser, Plan 03 is the renderer

# Metrics
duration: ~30min
completed: 2026-05-11
---

# Phase 14 Plan 03: Domain UI Renderer Summary

**Shipped the domain UI renderer that consumes `ParsedRun` (Plan 14-02) and emits the operator-facing header / per-tool rows / summary line described in SEED-011 §2 and Phase 14 D-04..D-09. Wired the renderer into `cli.py:run` (replacing the Plan 01 transitional `typer.echo(captured_stdout)`). Built state-(a)/(c) skip rows from a PURE function taking `Config.tools` + a wrapper-side discovery call -- no longer depending on the deleted `_reporter._DISCOVERED_TOOL_NAMES` module global. After this plan, `mcp-test-framework run` produces operator-shaped output; pytest framing no longer leaks under default verbosity. RUNNER-02 is complete.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-05-11
- **Completed:** 2026-05-11
- **Tasks:** 3 (Task 1 TDD RED+GREEN, Task 2 GREEN, Task 3 satisfied by Task 1 RED commit per Plan 01/02 precedent)
- **Files modified:** 2 production (`_runner.py` appended, `cli.py` default-mode body rewritten), 1 test (`test_runner_renderer.py` created)

## Accomplishments

- **Domain UI renderer delivered.** `render_domain_ui(parsed, ctx)` orchestrates the SEED-011 §2 header (MCP server, Discovered/Running/Skipping counts, Judges, Test plan), the Phase 09 CD-03 FAIL → SKIP → PASS per-tool rows, and the summary line (`Result: N PASS / M FAIL [ / K SKIP]  in T.Ts`). Stdlib f-strings + ANSI escapes only -- no new runtime dependency.
- **state-(a)/(c) composer is now PURE.** `_compose_unparametrized_skips_from_config(discovered_tools, tools_config, ran_tools)` takes discovered tools as an ARGUMENT rather than reading `_reporter._DISCOVERED_TOOL_NAMES`. This is the architectural shift that unblocks Plan 14-05's `_reporter.py` deletion: the composer no longer has a hidden cross-module dependency.
- **Wrapper-side discovery wired.** `_discover_tools_for_run(cfg)` in `cli.py` performs a one-shot MCP handshake via the same `AsyncExitStack` + `McpTestClient` pattern as `list_tools` (Phase 04.1 same-task lifecycle). Discovery runs BEFORE the subprocess so the header counts include state-(a) unlisted tools that never appear in the JUnit XML.
- **`cli.py:run` default-mode body rewritten.** The Plan 01 transitional `typer.echo(captured_stdout, nl=False)` is removed. New flow: `_load_config` → `_discover_tools_for_run` → `_runner.run_pytest_subprocess` → `_runner.parse_junit_xml` → `_runner.render_domain_ui`. `--raw` path unchanged (no discovery, no parse, no render).
- **D-16 surfaces preserved.** `ET.ParseError` is caught and surfaced via `_emit_operator_error` with summary "JUnit XML parse failed" and an operator-tone detail block pointing at `--raw` for raw pytest output.
- **Locked invariants pinned in regression tests.**
  - Em-dash U+2014 (literal `—`) is the FAIL/SKIP separator -- 4+ matches in the source, 2 matches in the test file.
  - FAIL → SKIP → PASS row ordering (Phase 09 CD-03) -- pinned by `test_render_rows_fail_skip_pass_alphabetical`.
  - State-(a) `"not selected in config"` / state-(c) `"explicit skip in config"` (Phase 13 D-12) -- pinned by `test_state_a_unlisted_renders_not_selected` and `test_state_c_default_when_skip_reason_empty`.
  - No pytest framing leaks (`test session starts`, `rootdir:`, `[<tool>]` brackets) -- pinned by `test_render_no_pytest_framing_in_default_output`.
  - ANSI codes only when stdout is a TTY -- pinned by `test_no_ansi_codes_when_not_tty`.
- **No regressions.** All 18 Plan 01 subprocess tests pass; all 24 Plan 02 parser tests pass; all 16 Plan 03 renderer tests pass; all 207 unit tests pass overall.
- **No new runtime dependency.** Stdlib `sys`, `dataclasses.field`, ANSI escapes. `pyproject.toml` untouched.

## Task Commits

1. **Task 1 RED: failing tests for renderer** -- `facd6ea` (test) -- 17 tests (1 was absorbed; final count 16 after disambiguation) fail with `ImportError` because `RenderContext` / `render_domain_ui` / `_compose_unparametrized_skips_from_config` do not yet exist on `_runner`.
2. **Task 1 GREEN: renderer + RenderContext + composer** -- `9404668` (feat) -- appended ~264 lines to `_runner.py`; all 16 RED tests turn green.
3. **Task 2: wire renderer into cli.py:run + wrapper-side discovery** -- `dcfe2eb` (feat) -- Plan 01 transitional echo removed; default-mode body rewritten with discover → parse → render flow; `_discover_tools_for_run` helper added; ET.ParseError → D-16 wired.

Task 3 (dedicated test file with named acceptance test functions) was satisfied by the Task 1 RED commit (`facd6ea`): all named test functions from the plan exist, `def test_` count is 16 (>= 12 plan minimum), Phase 13 D-12 regression pins (`"not selected in config"`, `"explicit skip in config"`) and em-dash U+2014 pin are present. No additional commit was needed -- same pattern as Plan 14-01 and Plan 14-02.

## Files Created/Modified

### Created

- **`tests/test_runner_renderer.py`** (283 lines, 16 tests) -- placed at the path the plan specifies (NOT `tests/unit/`). The file imports cleanly under the autouse `_preflight` gate when `MCPTF_CONFIG_FILE=./config-v2-worktree.yaml` is set; without that env var, the preflight blocks all `tests/` collection. The plan's acceptance grep criteria target file CONTENT (named tests + literal strings), all satisfied.

### Modified

- **`src/mcp_test_framework/_runner.py`** -- appended ~264 lines (now 730 lines total):
  - `RenderContext` dataclass: `server_cmd`, `discovered_tools`, `tools_config`, `judges`, `total_planned_cases`.
  - `_compose_unparametrized_skips_from_config(discovered_tools, tools_config, ran_tools) -> dict[str, str]`: PURE function.
  - ANSI helpers: `_ansi_enabled`, `_green`, `_red`, `_dim` (gated by `file.isatty()`).
  - `_render_header(ctx, parsed)`: 7-line SEED-011 §2 mockup.
  - `_render_per_tool_rows(parsed, unparam_skips)`: FAIL → SKIP → PASS, alphabetical within each, em-dash U+2014 separator.
  - `_render_summary_line(parsed, unparam_skips)`: `Result: N PASS / M FAIL [ / K SKIP]  in T.Ts`.
  - `render_domain_ui(parsed, ctx)`: orchestrator (header → rows → summary).
  - All renderer functions use `file=None` default + `if file is None: file = sys.stdout` at call time (capsys-friendly).
- **`src/mcp_test_framework/cli.py`**:
  - Added `_discover_tools_for_run(cfg)` helper above the `run()` command (mirrors `list_tools` AsyncExitStack pattern).
  - `run()` default-mode body: rewrote from "transitional echo" to "discover → subprocess → parse → render".
  - `cfg = _load_config(config)` (return value captured -- was previously discarded).
  - `import xml.etree.ElementTree as ET` added inside `run()` for ET.ParseError surface.
  - `_runner.render_domain_ui(parsed, ctx)` is the new rendering call site.
  - `--raw` path unchanged.
  - Docstring updated: removed the `PLAN-03 REMOVES` marker (the removal is done).

## Decisions Made

1. **PURE function `_compose_unparametrized_skips_from_config`** (architectural shift over v1.1 `_reporter._compose_unparametrized_skips`). The v1.1 version read `_DISCOVERED_TOOL_NAMES` off a module global written by `tests/conftest.py:_resolve_tool_names`. Phase 14 wraps pytest in a subprocess -- the wrapper process cannot reach the in-pytest module global. The new function takes `discovered_tools` as a positional argument; the wrapper supplies it via `_discover_tools_for_run`. Plan 14-05's deletion of `_reporter.py` is now unblocked: the composer is self-contained on `_runner.py`.
2. **Wrapper-side discovery is run BEFORE the subprocess** (CONTEXT D-claude bullet 5 option (a)). The alternative (computing state-(a) names from `Config.tools` alone) is impossible: state-(a) is "discovered AND unlisted", which requires discovery. Cost: one extra MCP handshake per `run` invocation. Benefit: header counts agree with what the runner actually executes.
3. **`RenderContext` dataclass over ad-hoc kwargs** to the renderer. Plan 14-04 (`--debug` / `-q`) and Phase 16 (`--explain`) need to extend the renderer input surface; adding fields to a dataclass is cleaner than threading more kwargs through `render_domain_ui` and its three sub-renderers.
4. **`file=None` default + call-time `sys.stdout` resolution** instead of `file=sys.stdout` default (plan-specified). Functionally identical; the change is forced by pytest `capsys`: a `file=sys.stdout` default captures the pre-test stdout at function definition time, bypassing capsys's per-test stdout replacement. Without this fix, all renderer tests that use `capsys` would fail with empty captured output even though the renderer DOES print correctly. Tracked as deviation Rule 1 below.
5. **Test file placed at `tests/test_runner_renderer.py` (the plan-specified path)**, NOT `tests/unit/test_runner_renderer.py` (the parser-plan deviation). Trade-off: tests live under the autouse `_preflight` gate, so running them requires `MCPTF_CONFIG_FILE=./config-v2-worktree.yaml`. Same situation as `tests/test_runner_subprocess.py` from Plan 14-01 -- the project's existing pattern is "subprocess + cli-surface tests live under tests/; pure-data + unit tests live under tests/unit/". Renderer tests are pure-data but the plan put them at the top-level; honoring that literally is consistent with Plan 14-01's test placement.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug / capsys compatibility] Changed renderer function `file=sys.stdout` defaults to `file=None` + call-time resolution**
- **Found during:** Task 1 GREEN verification (first test run after writing the renderer).
- **Issue:** The plan specifies `def _render_header(..., file=sys.stdout)`. When pytest `capsys` fixture replaces `sys.stdout` for capture, default parameters that captured `sys.stdout` at function-definition time (which is when the renderer module imports) still point at the PRE-capture stream. Result: all `capsys` tests showed empty captured output even though the renderer's prints were going somewhere (visible in `Captured stdout call` -- pytest's separate stdout-capture mechanism). The plan's tests cannot work with the plan's default-arg shape.
- **Fix:** Changed default to `file=None` with `if file is None: file = sys.stdout` at the top of each renderer function. This resolves `sys.stdout` at CALL time, after capsys has replaced it. All 16 renderer tests turn green.
- **Files modified:** `src/mcp_test_framework/_runner.py` (4 functions: `_render_header`, `_render_per_tool_rows`, `_render_summary_line`, `render_domain_ui`).
- **Verification:** `uv run pytest tests/test_runner_renderer.py` -- 16 passed.
- **Committed in:** `9404668` (Task 1 GREEN).

**2. [Rule 1 - Docstring scrub for acceptance grep] Removed `PLAN-03 REMOVES` marker from `cli.py:run` docstring**
- **Found during:** Task 2 acceptance-criteria verification.
- **Issue:** Plan acceptance criterion `grep -n "PLAN-03 REMOVES\|captured_stdout, nl=False" src/mcp_test_framework/cli.py returns ZERO matches`. The `PLAN-03 REMOVES` literal had moved from a code comment (deleted with the transitional echo) to a docstring sentence describing the marker -- still 1 match.
- **Fix:** Rewrote the docstring paragraph to describe the CURRENT default-mode flow ("wrapper-side MCP discovery + subprocess pytest + ... + XML parse + domain UI render. Plan 14-03 landed the renderer; the Plan 01 transitional verbatim-stdout echo is now replaced by `_runner.render_domain_ui(parsed, ctx)`."). Behavior unchanged; grep count now 0.
- **Files modified:** `src/mcp_test_framework/cli.py` (4 lines of docstring).
- **Verification:** `grep -c "PLAN-03 REMOVES" src/mcp_test_framework/cli.py` returns 0; `grep -c "captured_stdout, nl=False"` returns 0. All 18 Plan 01 subprocess tests still pass.
- **Committed in:** `dcfe2eb` (Task 2).

---

**Total deviations:** 2 auto-fixed (Rule 1 each).
- (1) was forced by the plan-spec's incompatibility with pytest's capsys default-arg binding semantics; functionally equivalent.
- (2) was a grep-target-only docstring edit (same pattern as Plan 01 SUMMARY deviation #1/#2).

**Impact on plan:** Zero scope creep. The renderer's public API surface (function names, parameter names, return types) matches the plan; only the internal default-arg shape changed for capsys compatibility.

## Issues Encountered

- **Windows worktree edit path drift.** During Task 1 GREEN, the first `Edit` call on `src/mcp_test_framework/_runner.py` (relative-path inference under Windows-on-bash worktrees) wrote to the PARENT project's file rather than the worktree's file. Symptom: imports kept failing after the edit "succeeded". Fixed by reverting the parent edit (`git checkout -- src/mcp_test_framework/_runner.py` in parent) and re-applying the Edit using the WORKTREE's absolute path. Did not affect commits -- nothing was committed to the parent. Documented here as an environmental note for future executors on Windows worktrees: use absolute paths under `.claude/worktrees/agent-...` for all Edit/Write tool calls.
- **Worktree config requirement** (same as Plans 14-01 and 14-02). `MCPTF_CONFIG_FILE=./config-v2-worktree.yaml` is required for `tests/test_runner_renderer.py` to clear the autouse `_preflight` gate. Per Plan 14-01 SUMMARY, this file is a per-worktree convenience and stays git-untracked.

## User Setup Required

None. No external service configuration required for this plan. The `config-v2-worktree.yaml` mentioned above is a per-worktree convenience for running the test suite; production code resolves config via `_load_config` exactly as in Phase 13.

## Next Phase Readiness

- **Plan 14-04 (`--debug` / `-q` flags) unblocked.** Adding `debug: bool` / `quiet: bool` to the `run()` Typer signature: `--debug` appends `parsed.per_tool[tool].failure_body` (already captured by Plan 14-02) and the captured pytest stdout AFTER the domain UI; `-q` suppresses the per-tool rows section. Both are renderer-side changes; the parser and runner are already in place.
- **Plan 14-05 (`_reporter.py` deletion) unblocked.** The state-(a)/(c) composer is now PURE and lives in `_runner.py` alongside the renderer. Removing `_reporter.py` no longer breaks the skip-row contract. Plan 14-05's remaining work: delete the plugin registration in `tests/conftest.py`, delete the file itself, retarget any remaining reporter tests as renderer tests.
- **Plan 14-04 / 14-05 compatibility note.** The `_DISCOVERED_TOOL_NAMES` cache in `_reporter.py` is still alive (in-pytest plugin), but the WRAPPER does not depend on it. `tests/conftest.py:_resolve_tool_names` still uses it for parametrize-time filtering. Plan 14-05 must migrate that cache to `_runner.py` (or remove it entirely if conftest can derive its allowlist directly from `Config.tools`).

**No blockers.** Phase 14's renderer surface is locked; Plans 04-05 plug into the seams Plan 03 left clean.

---
*Phase: 14-hybrid-runner-with-domain-ui*
*Completed: 2026-05-11*

## Self-Check: PASSED

- src/mcp_test_framework/_runner.py: FOUND
- src/mcp_test_framework/cli.py: FOUND
- tests/test_runner_renderer.py: FOUND
- .planning/phases/14-hybrid-runner-with-domain-ui/14-03-SUMMARY.md: FOUND
- facd6ea (Task 1 RED: failing renderer tests): FOUND
- 9404668 (Task 1 GREEN: renderer + RenderContext + composer): FOUND
- dcfe2eb (Task 2: cli.py wired + wrapper-side discovery): FOUND
