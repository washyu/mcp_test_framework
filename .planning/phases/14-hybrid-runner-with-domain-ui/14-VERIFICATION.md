---
phase: 14-hybrid-runner-with-domain-ui
verified: 2026-05-11T00:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: none
  previous_score: n/a
  gaps_closed: []
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Run `MCPTF_CONFIG_FILE=$(pwd)/config-v2-worktree.yaml uv run pytest tests/test_runner_live_smoke.py -m live_homelab --no-header` against a live homelab-mcp server + Ollama"
    expected: "All 3 live smoke tests pass: domain header strings present, --junit-xml=PATH populated, --raw emits pytest framing"
    why_human: "tests/test_runner_live_smoke.py spawns a real `uv run mcp-test-framework run` subprocess, which needs a reachable MCP server and Ollama. Marker live_homelab is skipped by default; agent cannot exercise"
  - test: "Run `uv run mcp-test-framework run` against the configured homelab-mcp"
    expected: "Operator output begins with header (`========================================`, `MCP Test Framework`, `MCP server:`, `Discovered:`, `Running:`, `Skipping:`, `Judges:`, `Test plan:`), per-tool rows (FAIL→SKIP→PASS, em-dash on detail), ends with `Result: N PASS / M FAIL [/ K SKIP]  in T.Ts`. No `=== test session starts ===`, no `[<tool>]` parametrize suffixes leak"
    expected: "Exit codes: 0 (all pass), 1 (failures), 2 (config), 130 (Ctrl+C)"
    why_human: "End-to-end visual verification against the live server; cannot be programmatically asserted without a live SUT"
  - test: "Run `uv run mcp-test-framework run -q` and `--debug` and `-q --debug` against live homelab-mcp"
    expected: "-q prints only `Result: ...`; --debug appends `--- raw pytest output ---` then captured stdout/stderr after the domain UI; `-q --debug` prints summary then appendix (no header)"
    why_human: "Operator-perceptible verbosity ladder; unit tests pin the helpers but the live composition is visual"
---

# Phase 14: hybrid-runner-with-domain-ui Verification Report

**Phase Goal:** An operator running `mcp-test-framework run` sees output in MCP-domain language (server, tools, judges, verdicts) without pytest's collection / deselection / dot-progress framing. Pytest remains the orchestration engine internally, but its output is invisible to the operator by default.

**Verified:** 2026-05-11
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md success criteria + PLAN must_haves)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Operator sees domain-shaped report: header (server, discovered/running/skipping, judges, test-plan totals), per-tool rows with `✓`/`✗`/`–` and failure reasoning, summary line. No pytest framing (`=== test session starts ===`, `.`/`F` markers, `[<param>]` suffixes) leaks | VERIFIED (unit) / human_needed (live) | `_render_header` emits all 7 header labels (grep confirms 17 literal-string hits in `_runner.py`); `_render_per_tool_rows` orders FAIL→SKIP→PASS; em-dash U+2014 appears 4× in `_runner.py`; `tests/test_runner_renderer.py::test_render_no_pytest_framing_in_default_output` passes |
| 2 | `mcp-test-framework run --raw` forwards all flags verbatim to pytest, equivalent to `uv run pytest tests/` modulo the config pre-flight gate | VERIFIED | `cli.py:433-446` raw branch calls `_runner.run_pytest_subprocess(raw=True)` which uses inherit-stdio subprocess; pre-flight `_load_config(config)` runs at line 429 BEFORE the raw branch; `tests/test_runner_subprocess.py::test_run_raw_also_calls_load_config_before_subprocess` passes; `tests/test_runner_verbosity.py::test_run_raw_ignores_quiet_and_debug` passes |
| 3 | Verbosity ladder: `-q` → summary-only, default → domain UI, `--debug` → adds raw pytest output + tracebacks. Each rung adds info; none re-shapes the layer below | VERIFIED (rungs implemented; --explain DEFERRED to Phase 16 per D-14) | `cli.py:506-516`: `if quiet: render_summary_only else render_domain_ui; if debug: render_debug_appendix`. `tests/test_runner_verbosity.py` 13/13 pass including `test_run_quiet_plus_debug_renders_summary_then_appendix` and `test_run_help_does_not_list_explain`. `--explain` is owned by Phase 16 per CONTEXT D-14 — not a Phase 14 gap |
| 4 | `--junit-xml=PATH` continues to receive XML at PATH (v1.1 OUTPUT-01 contract preserved); wrapper consumes its own internal tempfile | VERIFIED | `_runner.py:204-211` `shutil.copy(tmp, junit_xml)` fan-out after subprocess exits; `tests/test_runner_subprocess.py::test_run_pytest_subprocess_preserves_operator_junit_xml` passes; `--junit-xml` flag still in `run --help` |
| 5 | Exit codes preserved: 0 (all pass), 1 (test failures), 2 (config/collection errors), 130 (SIGINT) | VERIFIED | `_runner._map_exit_code` maps 5→0 (no tests collected) with warning; others pass through. `cli.py:443-446` and `518-521` raise `typer.Exit(code=mapped)`. `KeyboardInterrupt` is never caught (verified via `grep -n "except KeyboardInterrupt" src/mcp_test_framework/_runner.py` returns 0). `_load_config` raises `typer.Exit(2)` on SAFE-* errors. `tests/test_runner_subprocess.py::test_map_exit_code_*` (5 tests) all pass |

**Score:** 5/5 truths verified (all unit/wiring evidence present; live behavior routed to human_needed)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/mcp_test_framework/_runner.py` | Subprocess dispatch + parser + renderer + verbosity helpers + migrated cache | VERIFIED | 872 lines; exports `run_pytest_subprocess`, `_map_exit_code`, `_dispatch_default_mode_or_error`, `parse_junit_xml`, `ParsedRun`, `ToolVerdict`, `_extract_tool_name`, `_strip_pytest_skipped_prefix`, `_format_skip_reasons`, `_SKIP_REASON_CAP`, `_REASON_NOT_SELECTED`, `_REASON_EXPLICIT_DEFAULT`, `RenderContext`, `_compose_unparametrized_skips_from_config`, `_render_header`, `_render_per_tool_rows`, `_render_summary_line`, `render_domain_ui`, `render_summary_only`, `render_debug_appendix`, `_DISCOVERED_TOOL_NAMES`, `_set_discovered_tool_names`, `_build_pytest_args`, `_emit_operator_error` |
| `src/mcp_test_framework/cli.py:run` | Rewritten run() delegating to `_runner.run_pytest_subprocess`; exposes `--raw`, `--debug`, `-q`/`--quiet`; preserves `_load_config` pre-flight | VERIFIED | `cli.py:348-527`. `pytest.main` not referenced (`grep -n pytest.main src/mcp_test_framework/cli.py` returns 0). `_load_config(config)` at `cli.py:429` BEFORE either branch. `run --help` lists `--raw`, `--debug`, `-q/--quiet`, `--junit-xml`, `--config`. Does NOT list `--explain` (D-14 honored) |
| `src/mcp_test_framework/_reporter.py` | Should NOT exist after Plan 14-05 deletion | VERIFIED | File missing (confirmed via `test -f`); `grep -rn _reporter src/mcp_test_framework/` returns no files; regression pin `tests/test_runner_subprocess.py::test_reporter_module_no_longer_importable` passes |
| `tests/conftest.py` | No `_reporter` plugin registration; imports cache from `_runner`; preserves `_resolve_tool_names` allowlist filter | VERIFIED | `pytest_plugins = ["mcp_test_framework.fixtures"]` at `conftest.py:18`; `from mcp_test_framework import _runner as _r` at `conftest.py:25`; `_resolve_tool_names` reads `_r._DISCOVERED_TOOL_NAMES` and writes via `_r._set_discovered_tool_names(...)`. The literal substring `_reporter` does not appear anywhere in `conftest.py` |
| `tests/fixtures/junit-*.xml` | 4 hand-written JUnit XML fixtures (all-pass, one-fail-with-reasoning, all-skip, mixed) | VERIFIED | All 4 present: `junit-all-pass.xml`, `junit-one-fail-with-reasoning.xml`, `junit-all-skip.xml`, `junit-mixed.xml`. Each parses cleanly via `xml.etree.ElementTree.parse` (parser tests round-trip them) |
| `tests/test_runner_subprocess.py` | Subprocess dispatch + exit-code + regression pins | VERIFIED | 21 tests; all 21 pass |
| `tests/unit/test_runner_parser.py` | Parser + locked constants + aggregation | VERIFIED | 24 tests; all 24 pass |
| `tests/test_runner_renderer.py` | Header/rows/summary + em-dash + state-(a)/(c) composer | VERIFIED | 16 tests; all 16 pass |
| `tests/test_runner_verbosity.py` | -q / --debug / orthogonality / no-explain | VERIFIED | 13 tests; all 13 pass |
| `tests/unit/test_runner_migration.py` | SAFE-01 allowlist + CR-01 IPC tests, retargeted to `_runner._DISCOVERED_TOOL_NAMES` seam | VERIFIED | 5 tests; all 5 pass. Tests patch `mcp_test_framework._runner._DISCOVERED_TOOL_NAMES` (correct path) — confirms the Phase 14 critical-instruction "SAFE-01 allowlist tests patch the right import path" is met |
| `tests/test_runner_live_smoke.py` | Live integration smoke for the new domain UI + --junit-xml + --raw | EXISTS / human_needed | File present (3 tests, all `pytest.mark.live_homelab`); cannot be exercised without a real homelab-mcp server. Routed to human verification |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `cli.py:run` (raw branch) | `_runner.run_pytest_subprocess(raw=True)` | function call after `_load_config` | WIRED | `cli.py:438` after gate at `cli.py:429` |
| `cli.py:run` (default branch) | `_runner.run_pytest_subprocess(raw=False)` | function call after `_load_config` + `_discover_tools_for_run` | WIRED | `cli.py:454` after gate + wrapper-side discovery |
| `cli.py:run` | `_runner.parse_junit_xml(tmp_xml)` | XML parse inside try/finally | WIRED | `cli.py:468` with `ET.ParseError` surfacing via `_emit_operator_error("JUnit XML parse failed", ...)` (D-16) |
| `cli.py:run` | `_runner.render_domain_ui` / `render_summary_only` / `render_debug_appendix` | verbosity-aware dispatch | WIRED | `cli.py:506-516`: if/else on `quiet`, then conditional `debug` appendix |
| `cli.py:_load_config` | `MCPTF_CONFIG_FILE` env export | os.environ assignment | WIRED | Phase 13 CR-01 channel intact; `tests/unit/test_runner_migration.py::test_cr01_resolver_writes_mcptf_config_file_env_var` passes |
| `tests/conftest.py:_resolve_tool_names` | `_runner._DISCOVERED_TOOL_NAMES` | live module attribute import | WIRED | `from mcp_test_framework import _runner as _r` at line 25; reads `_r._DISCOVERED_TOOL_NAMES`; writes via `_r._set_discovered_tool_names(...)`; SAFE-01 tests patch via the same path |
| `_runner.run_pytest_subprocess` | `subprocess.run([sys.executable, "-m", "pytest", ...])` | stdlib subprocess | WIRED | `_runner.py:195-201` (default) and `_runner.py:166` (raw); `pytest.main` is never invoked (grep confirms) |
| `_runner.run_pytest_subprocess` (default) | `shutil.copy(tmp, operator_junit_xml)` | post-subprocess fan-out | WIRED | `_runner.py:204-211`; operator-supplied `--junit-xml=PATH` populated independently of the wrapper's tempfile (D-02 / RUNNER-05) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `render_domain_ui` | `parsed: ParsedRun` | `parse_junit_xml(tmp_xml)` reading pytest's JUnit XML | YES (XML written by real pytest subprocess in default mode; round-tripped through 4 hand-written fixtures in tests) | FLOWING |
| `render_domain_ui` | `ctx.discovered_tools` | `_discover_tools_for_run(cfg)` (one-shot MCP handshake via `McpTestClient`) | YES (real MCP server discovery via `client.list_tools()`); fixture-tested with `_basic_ctx(discovered=...)` | FLOWING |
| `render_domain_ui` | `ctx.tools_config` | `cfg.tools` from `_load_config(config)` (Pydantic-validated YAML) | YES | FLOWING |
| `render_domain_ui` | `ctx.judges` | `union(tool_cfg.judges for tool_cfg in cfg.tools.values())` | YES (derived from real config; `_basic_ctx(judges=["clarity"])` exercises it in unit tests) | FLOWING |
| `_resolve_tool_names` | `_DISCOVERED_TOOL_NAMES` | `asyncio.run(_discover_tools(config))` via `_r._set_discovered_tool_names` | YES (real MCP handshake when None; unit tests patch directly) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| CLI loads cleanly | `uv run mcp-test-framework --help` | Subcommands listed: `config-init`, `list-tools`, `run`, `tool-config-template`, `version` | PASS |
| `run --help` lists all flags | `uv run mcp-test-framework run --help` | Lists `--config`, `--junit-xml`, `--raw`, `--debug`, `--quiet`/`-q`. Does NOT list `--explain` | PASS |
| Phase-14 test suite green | `MCPTF_CONFIG_FILE=... uv run pytest tests/test_runner_subprocess.py tests/test_runner_renderer.py tests/test_runner_verbosity.py tests/unit/test_runner_parser.py tests/unit/test_runner_migration.py --confcutdir=tests/unit` | 79 passed in 11.05s | PASS |
| 3 regression pins for `_reporter` deletion | `uv run pytest tests/test_runner_subprocess.py::test_reporter_module_no_longer_importable ::test_runner_owns_discovery_cache ::test_plugins_list_does_not_register_reporter` | 3 passed | PASS |
| SAFE-01 allowlist tests patch correct path | `uv run pytest tests/unit/test_runner_migration.py` | 5 passed (incl. 3 SAFE-01 + 2 CR-01) | PASS |
| Full non-live test suite | `MCPTF_CONFIG_FILE=$(pwd)/config-v2-worktree.yaml uv run pytest tests/ -k "not live_homelab and not live_ollama" --ignore=tests/test_tool_config.py` | 257 passed, 10 skipped, 12 deselected, 1 failed (`tests/smoke/test_mcp_client_teardown_regression.py` — pre-existing baseline failure from same v1/v2 config schema mismatch; reproduces via child pytest's default config.example.yaml load; not caused by Phase 14) | PASS (Phase 14 has 0 regressions) |
| Live integration smoke | `uv run pytest tests/test_runner_live_smoke.py -m live_homelab` | Requires live MCP server + Ollama | SKIP (routed to human) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| RUNNER-01 | 14-01 | Wrap pytest invocation; capture JUnit XML internally; render MCP-domain UI | SATISFIED | `_runner.run_pytest_subprocess` uses `subprocess.run([sys.executable, "-m", "pytest", ...])`, captures via tempfile JUnit XML, `cli.py:run` delegates to `_runner.render_domain_ui` |
| RUNNER-02 | 14-02, 14-03, 14-05 | Domain UI shape (header + rows + summary); no pytest framing leaks | SATISFIED | `_render_header` + `_render_per_tool_rows` + `_render_summary_line` in `_runner.py`; `tests/test_runner_renderer.py::test_render_no_pytest_framing_in_default_output` passes; em-dash U+2014 verbatim |
| RUNNER-03 | 14-01 | `--raw` escape hatch forwards all flags to pytest verbatim | SATISFIED | `cli.py:run --raw` branch bypasses renderer; `_load_config` still runs as pre-flight (D-11) |
| RUNNER-04 | 14-04 | Verbosity ladder: `-q` summary-only / default UI / `--explain` (Phase 16) / `--debug` raw output | PARTIALLY SATISFIED (`--explain` is owned by Phase 16 per CONTEXT D-14; intentionally NOT registered in Phase 14) | `-q`, default, and `--debug` rungs all present + tested; `--explain` deferred to Phase 16 (UX-02). This is NOT a Phase 14 gap — it is an explicit boundary decision documented in CONTEXT and validated by `test_run_help_does_not_list_explain` |
| RUNNER-05 | 14-01 | `--junit-xml=PATH` continues to emit XML at PATH; wrapper uses separate internal tempfile | SATISFIED | `_runner.py:204-211` `shutil.copy(tmp, junit_xml)` fan-out; `tests/test_runner_subprocess.py::test_run_pytest_subprocess_preserves_operator_junit_xml` passes |
| RUNNER-06 | 14-01 | Exit codes preserved: 0 / 1 / 2 / 130 | SATISFIED | `_map_exit_code` maps 0→0, 1→1, 2→2, 5→0+warning; KeyboardInterrupt never caught (grep confirms); `tests/test_runner_subprocess.py::test_map_exit_code_*` × 5 pass |

All 6 requirement IDs declared in PLAN frontmatter are accounted for. No orphaned requirements (REQUIREMENTS.md lines 126-131 list RUNNER-01..06 as Phase 14; all match).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/mcp_test_framework/_runner.py` | 30 | `import os  # noqa: F401  -- reserved for future env-passthrough hooks` | Info | Reserved import; intentional |
| n/a | n/a | No TODO/FIXME/PLACEHOLDER/empty-stub patterns found in Phase 14 source or test files | n/a | n/a |

No blockers, no warnings.

### Human Verification Required

1. **Live domain UI rendering** — operate `uv run mcp-test-framework run` against a real homelab-mcp server. Expected: header (7 labels), per-tool rows in FAIL→SKIP→PASS order, `Result: N PASS / M FAIL [/ K SKIP] in T.Ts` summary, no pytest framing. Why human: live SUT required.

2. **Verbosity ladder visual check** — operate `run -q`, `run --debug`, `run -q --debug`, `run --raw`. Expected per CONTEXT specifics + SEED-011 §2. Why human: verbosity transitions are perception-level.

3. **Live integration smoke suite** — `MCPTF_CONFIG_FILE=$(pwd)/config-v2-worktree.yaml uv run pytest tests/test_runner_live_smoke.py -m live_homelab`. Expected: all 3 tests pass. Why human: requires live MCP server.

### Gaps Summary

No gaps. All 5 Success Criteria from ROADMAP.md are satisfied in the codebase; all 6 RUNNER requirement IDs trace to verifiable code; the deletion of `_reporter.py` and migration of `_DISCOVERED_TOOL_NAMES` to `_runner.py` is intact and pinned by 3 regression tests; the cli.py:run path threads `_load_config` → `_discover_tools_for_run` → `_runner.run_pytest_subprocess` → `_runner.parse_junit_xml` → renderer (`render_domain_ui` / `render_summary_only` / `render_debug_appendix`) exactly as the plans specified.

The Phase 14 critical instructions from the verifier prompt are individually confirmed:
- `_reporter.py` deletion landed — file missing, regression pin passes.
- Cache migration to `_runner.py` is intact — `_DISCOVERED_TOOL_NAMES` + `_set_discovered_tool_names` exported; conftest.py imports from `_runner`.
- `cli.py:run` invokes `_runner.run_pytest_subprocess` (not `pytest.main`); routes through the domain UI renderer by default; exposes `--raw`/`-q`/`--quiet`/`--debug`; preserves the Phase 13 `_load_config` pre-flight gate on both paths.
- SAFE-01 allowlist tests patch `mcp_test_framework._runner._DISCOVERED_TOOL_NAMES` (correct path) and pass.
- 79 Phase-14 tests pass under `--confcutdir=tests/unit`.
- Pre-existing baseline failures in `tests/test_tool_config.py` (and the secondary `tests/smoke/test_mcp_client_teardown_regression.py` failure caused by the child pytest's default config.example.yaml load) are documented and NOT Phase 14 regressions.

The only remaining items are live-SUT visual smoke checks — routed to `human_needed` per the verifier contract.

---

*Verified: 2026-05-11*
*Verifier: Claude (gsd-verifier)*
