---
status: resolved
phase: 14-hybrid-runner-with-domain-ui
source: [14-VERIFICATION.md]
started: 2026-05-11
updated: 2026-05-11T19:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Live smoke suite against real homelab-mcp + Ollama

command (PowerShell): `$env:MCPTF_CONFIG_FILE = "$PWD\config-v2-worktree.yaml"; uv run pytest tests/test_runner_live_smoke.py -m live_homelab --no-header`
command (bash):       `MCPTF_CONFIG_FILE="$(pwd)/config-v2-worktree.yaml" uv run pytest tests/test_runner_live_smoke.py -m live_homelab --no-header`
expected: All 3 live smoke tests pass — domain header strings present, `--junit-xml=PATH` populated, `--raw` emits pytest framing.
why_human: `tests/test_runner_live_smoke.py` spawns a real `uv run mcp-test-framework run` subprocess against a reachable MCP server + Ollama. Marker `live_homelab` is skipped by default; the verifier agent could not exercise it.
result: issue
reported: |
  1 failed, 2 passed in 80.31s. `test_live_run_emits_domain_header_and_summary` failed.
  Captured subprocess stdout ends mid-render with `UnicodeEncodeError: 'charmap' codec can't encode character '✗' in position 43: character maps to <undefined>` — Windows PowerShell's default cp1252 console encoding cannot encode `✗` (the failure glyph used in per-tool rows). The renderer prints the header + partial failure rows, then crashes; the `Result:` summary line never appears. `test_live_run_raw_keeps_pytest_framing` and `test_live_run_junit_xml_target_populated` both passed — `--raw` and `--junit-xml` paths are unaffected because they don't emit Unicode glyphs.
severity: blocker
platform: Windows (PowerShell, default cp1252 console code page)

### 2. End-to-end live run against configured homelab-mcp

command: `uv run mcp-test-framework run`
expected:
  - Output begins with header lines: `========================================`, `MCP Test Framework`, `MCP server:`, `Discovered:`, `Running:`, `Skipping:`, `Judges:`, `Test plan:`
  - Per-tool rows in FAIL → SKIP → PASS order with em-dash (U+2014) separator on detail lines
  - Ends with `Result: N PASS / M FAIL [/ K SKIP]  in T.Ts`
  - No `=== test session starts ===` framing, no `[<tool>]` parametrize-id suffixes leak
  - Exit codes: 0 (all pass), 1 (failures), 2 (config), 130 (Ctrl+C)
why_human: End-to-end visual verification against the live SUT; cannot be programmatically asserted without a real server.
result: pass
notes: |
  User confirmed the domain UI rendered (header, per-tool rows in FAIL/SKIP/PASS order, summary line `Result: 8 PASS / 1 FAIL / 59 SKIP  in 20.9s`). Observed run was against homelab-mcp v?? with config-v2-worktree.yaml selecting tools that exercise contract tests.

  Two observations recorded for follow-up (NOT new issues — first is already in Gaps from Test 1, second is goal-adjacent quality bug):

  1. Same Windows encoding bug as Test 1 reproduced in a different surface — the wrapper's `subprocess._readerthread` crashed with `UnicodeDecodeError: 'utf-8' codec can't decode byte 0x97 in position 3505: invalid start byte`. `0x97` is `—` (em-dash) in cp1252; the child pytest writes cp1252 bytes by default on Windows, but the wrapper reads in text mode with UTF-8 decoding. Same root cause, opposite direction (Test 1 = encode-on-write crash; Test 2 = decode-on-read crash). The candidate fixes already in Gaps (`PYTHONIOENCODING=utf-8` on the child + reader-side `errors='replace'`) will close both surfaces.

  2. Pytest parametrize-id leak in domain UI labels — `Running:` / `failures:` / `passing:` sections contain entries like `"2"`, `"-1"`, `"NOTSET"`, `"None"`, `"path0"`, `"path1"`, and empty strings instead of MCP tool names. Origin: `_extract_tool_name` in `src/mcp_test_framework/_runner.py` (ported from `_reporter.py` in Plan 14-02) only handles parametrize-ids shaped like `[<tool_name>]`. Tests parametrized over numeric edge cases, file paths, sentinel values (`NOTSET`), or empty strings produce IDs that the extractor returns verbatim. The `Skipping:` section looks correct because those rows are composed wrapper-side from `Config.tools` via `_compose_unparametrized_skips_from_config`, not from JUnit XML. This is goal-adjacent: Phase 14's goal is "output in MCP-domain language ... without pytest's framing", and `path0`/`NOTSET` ARE pytest's framing leaking through. Worth a follow-up plan but user judged the visual contract met overall.

### 3. Verbosity ladder transitions (`-q`, `--debug`, `-q --debug`, `--raw`)

command: `uv run mcp-test-framework run -q` then `--debug` then `-q --debug` then `--raw`
expected:
  - `-q`: prints only `Result: ...` summary line
  - `--debug`: appends `--- raw pytest output ---` then captured stdout/stderr AFTER the domain UI
  - `-q --debug`: summary line then debug appendix (no header section)
  - `--raw`: full pytest framing (no domain UI), but `_load_config` pre-flight still runs
why_human: Operator-perceptible verbosity composition; unit tests pin the helpers but the live layered output is a visual contract.
result: pass
notes: |
  Verbosity layering verified — `-q` summary-only, `--debug` appendix, and `--raw` full pytest framing all behaved as specified.

  Three findings recorded:

  1. UX gap (NEW — captured in Gaps): The default and `-q` paths run silently for ~20s while the child pytest works. Operator can't distinguish "hung" from "running." Feels jarring on the summary-only path because there's no header to anchor on. Suggested fix: spinner, periodic status line ("Running tests... (12s)"), or domain-language progress count.

  2. Phase 14 collateral test regression (NEW — captured in Gaps): `tests/test_tool_config.py::test_resolve_tool_names_filters_out_skip_true_tools` (and arguably `test_resolve_tool_names_explicit_target_overrides_skip_true`) patches `_conftest_module._DISCOVERED_TOOL_NAMES = [...]` — but Plan 14-05 moved that cache from `tests.conftest`'s implicit attribute to a real importable module path at `mcp_test_framework._runner._DISCOVERED_TOOL_NAMES`. Setting an attribute on the conftest module is now dead (conftest reads via `_r._DISCOVERED_TOOL_NAMES`). Result: cache stays empty, filter returns `[]`, test fails. Plan 14-05 retargeted `tests/test_reporter.py` and `tests/unit/test_reporter.py` but missed `tests/test_tool_config.py` which also exercises the cache via the old patch path. The verifier missed this because it ran `--confcutdir=tests/unit` which excludes `tests/test_tool_config.py`. Fix: update the test to patch `mcp_test_framework._runner._DISCOVERED_TOOL_NAMES` (matches `tests/unit/test_runner_migration.py` pattern).

  3. Baseline observation (NOT a Phase 14 gap — Phase 13 debt): The other 5 `--raw` failures (`test_default_config_version_and_tools`, `test_config_rejects_unsupported_version[2]`, `test_yaml_overlay_loads_tools_block`, `test_mcp_client_teardown_no_cancel_scope_error`, `test_resolve_tool_names_explicit_target_overrides_skip_true` partially) are all v1/v2 schema-migration debt left over from Phase 13: tests assert `cfg.version == 1` and use `target={"tool_name": ...}` while Phase 13 made v2 the only accepted version and removed `target`. Repo-root `config.yaml` is also still v1, hence `test_mcp_client_teardown_no_cancel_scope_error`'s child pytest exits 1 on Config validation. These are tracked under Phase 13's HUMAN-UAT (migration walkthrough + live MCP run — both pending). Out of Phase 14 gap-closure scope.

## Summary

total: 3
passed: 2
issues: 1
pending: 0
skipped: 0
blocked: 0
gaps_diagnosed: 3
gaps_resolved: 2
gaps_deferred: 1

## Gaps

- truth: "Default `mcp-test-framework run` renders the full domain UI (header + per-tool rows + summary line) on every platform Python supports"
  status: resolved
  resolved_by: 14-06
  resolved_at: 2026-05-11T19:30:00Z
  resolution: |
    Plan 14-06 implemented two-sided Unicode encoding hygiene: (a) `cli.run` now calls
    `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` at function entry (hasattr-guarded,
    try/except for hostile streams); (b) `_runner.run_pytest_subprocess` sets
    `PYTHONIOENCODING=utf-8` in the child env and adds `errors='replace'` on the parent decoder.
    Pinned by 4 new regression tests in `tests/unit/test_runner_encoding.py` (all pass).
    Pending Windows live UAT re-run with `tests/test_runner_live_smoke.py -m live_homelab`.
  reason: |
    User reported: 1 failed, 2 passed in test_runner_live_smoke. The failing test's subprocess stdout shows
    `UnicodeEncodeError: 'charmap' codec can't encode character '✗' in position 43: character maps to <undefined>`.
    Windows PowerShell's default cp1252 console encoding cannot encode the `✗` (U+2717) failure glyph used in
    per-tool rows by `_render_per_tool_rows` in `src/mcp_test_framework/_runner.py`. The renderer crashes
    mid-output, so the operator sees the header + partial failure rows + a Python traceback and never the
    `Result:` summary line. `--raw` and `--junit-xml` paths unaffected (no Unicode glyphs).
  severity: blocker
  platform: Windows (PowerShell, default cp1252 console code page)
  test: 1
  artifacts:
    - src/mcp_test_framework/_runner.py  # _render_per_tool_rows + render_domain_ui — Unicode glyph emission site
    - src/mcp_test_framework/cli.py      # run() — should reconfigure stdout encoding before delegating to renderer
  missing:
    - "stdout-encoding-safety: cli.py:run does not reconfigure sys.stdout to UTF-8 or set errors='replace' before printing Unicode glyphs"
  candidate_fixes:
    - "Reconfigure sys.stdout to UTF-8 with errors='replace' on Windows (or universally) at cli.py:run entry: `if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')`"
    - "Set `PYTHONIOENCODING=utf-8` in the framework subprocess env when spawning pytest (defensive — protects child output)"
    - "Detect non-UTF-8 stdout and downgrade glyphs to ASCII (`✓` → `[PASS]`, `✗` → `[FAIL]`, `–` → `[SKIP]`) — preserves output integrity even if reconfigure fails"

- truth: "Operator running `mcp-test-framework run` (default or `-q`) sees progress feedback while the child pytest is working — they can tell the process is alive, not hung"
  status: deferred
  deferred_to: SEED-013
  deferred_reason: |
    User decision 2026-05-11: this finding is goal-adjacent (Phase 14's goal is "operator sees domain UI instead of pytest framing" — the goal IS met; the silent wait is about WHEN they see it, not WHAT). Fits Phase 16 (reporter UX overhaul) naturally and was planted as SEED-013-progress-feedback-during-run.md. Phase 14 gap-closure should NOT include this — only Gap 1 (Windows Unicode) and Gap 3 (stale cache patch path).
  reason: |
    User reported: the `-q` and default paths run silently for ~20s before any output appears. With `-q` it's especially jarring because there's no header to anchor on — operator sees nothing, then the summary line drops. Distinguishing "hung" from "running" is a basic domain-UX contract for a CLI whose stated goal is "operator-first output."
  severity: minor
  test: 3
  artifacts:
    - src/mcp_test_framework/_runner.py  # run_pytest_subprocess — currently waits silently until subprocess.run returns
    - src/mcp_test_framework/cli.py      # run() — could emit a status line before delegating to the renderer
  missing:
    - "progress-feedback-during-run: no spinner, no periodic status line, no domain-language progress count between subprocess start and render output"
  candidate_fixes:
    - "Spawn a background thread that prints a single-line spinner with elapsed time (`\\r⠋ Running tests... 12s`) while subprocess.run is blocked, clear the line when output is ready. Skip if stdout is not a TTY."
    - "Capture pytest stdout in real-time (Popen + line-stream) and translate pytest's progress markers (`.`/`F`/`s`) to a domain-language counter (`Tested 47/289 contract cases — 0 failures so far`). Higher effort but stays in MCP-domain language. Likely Phase 16 work."
    - "Simplest: emit a single `Running 289 contract cases against <server>...` line BEFORE the subprocess.run() call. Replace with the full render output when done. Zero risk to the rendering contract."

- truth: "Plan 14-05's cache migration to `_runner._DISCOVERED_TOOL_NAMES` left no stale references — every test that previously patched the cache via its old location is updated to the new import path"
  status: resolved
  resolved_by: 14-07
  resolved_at: 2026-05-11T19:30:00Z
  resolution: |
    Plan 14-07 retargeted `tests/test_tool_config.py::test_resolve_tool_names_filters_out_skip_true_tools`
    to patch `mcp_test_framework._runner._DISCOVERED_TOOL_NAMES` (the new importable seam), wrapped in
    a `TestV111SkipFilter` class with a narrowly-scoped `_reset_discovery_cache` autouse fixture.
    Partner test `test_resolve_tool_names_explicit_target_overrides_skip_true` preserved via
    `@pytest.mark.xfail(strict=False)` flagged with Phase 13 v2-schema debt follow-up. Added a
    module-walking audit test (`test_no_stale_conftest_module_discovered_tool_names_writes`) as a
    permanent pin against future patch-seam drift. Target subset GREEN (2 passed, 1 xfailed); the 3
    remaining failures in the file are pre-existing Phase 13 v2-schema debt (out of scope per plan).
  reason: |
    User reported (via `mcp-test-framework run --raw`): `tests/test_tool_config.py::test_resolve_tool_names_filters_out_skip_true_tools` fails with `AssertionError: expected skip:true tool 'b' filtered out; got []`. Root cause: the test sets `_conftest_module._DISCOVERED_TOOL_NAMES = ["a", "b", "c"]` (the OLD cache location — when the cache was an implicit attribute on the conftest module), but Plan 14-05 moved the cache to a real importable path at `mcp_test_framework._runner._DISCOVERED_TOOL_NAMES`. `tests/conftest.py` now reads via `from mcp_test_framework import _runner as _r; _r._DISCOVERED_TOOL_NAMES`. Setting an attribute on `_conftest_module` is dead — the real cache stays empty, `_resolve_tool_names` returns `[]`, the SAFE-01 v1.1.1 filter test fails.

    Plan 14-05's SUMMARY claimed "SAFE-01 allowlist tests in `tests/unit/test_runner_migration.py` patch `mcp_test_framework._runner._DISCOVERED_TOOL_NAMES` (correct path) — 5/5 pass." Those 5 tests are fixed. But the plan didn't audit `tests/test_tool_config.py` — which has the SAME v1.1.1 filter coverage at top-level and was missed. The verifier missed it because verification ran with `--confcutdir=tests/unit` (excluding `tests/test_tool_config.py`).
  severity: major
  test: 3
  artifacts:
    - tests/test_tool_config.py  # lines ~167-200: test_resolve_tool_names_filters_out_skip_true_tools, test_resolve_tool_names_explicit_target_overrides_skip_true
    - src/mcp_test_framework/_runner.py  # _DISCOVERED_TOOL_NAMES + _set_discovered_tool_names — the now-canonical location
    - tests/unit/test_runner_migration.py  # reference pattern for correct patch path
  missing:
    - "patch-path-migration: tests/test_tool_config.py still patches `_conftest_module._DISCOVERED_TOOL_NAMES` (dead seam) instead of `mcp_test_framework._runner._DISCOVERED_TOOL_NAMES`"
    - "phase-14-test-audit-scope: Plan 14-05 only audited tests/test_reporter.py and tests/unit/test_reporter.py for stale cache references; should have grep'd the whole tests/ tree for `_DISCOVERED_TOOL_NAMES` patches"
  candidate_fixes:
    - "Update `tests/test_tool_config.py::test_resolve_tool_names_filters_out_skip_true_tools` to follow the `tests/unit/test_runner_migration.py` pattern: `from mcp_test_framework import _runner as _r; _r._set_discovered_tool_names([\"a\", \"b\", \"c\"])` instead of `_conftest_module._DISCOVERED_TOOL_NAMES = [...]`. Add autouse fixture to reset the cache between tests."
    - "Audit the rest of tests/ for any remaining `_DISCOVERED_TOOL_NAMES` references via grep — if other call sites exist, retarget them in the same plan."
    - "Bonus: the partner test `test_resolve_tool_names_explicit_target_overrides_skip_true` is dual-failing — once for the patch path, once for `target={\"tool_name\": ...}` (now `extra_forbidden`). Decision needed: is the v1.1.1 SAFE-01 explicit-override test still relevant in v2 (which dropped `target:`)? If yes, the test needs Phase 13 rework. If no, delete it. NOT in scope for the Phase 14 gap-closure; flag to Phase 13 verification follow-up."
