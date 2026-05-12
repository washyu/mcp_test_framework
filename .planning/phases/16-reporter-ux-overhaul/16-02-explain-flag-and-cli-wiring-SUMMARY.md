---
phase: 16-reporter-ux-overhaul
plan: 02
subsystem: cli
tags:
  - reporter
  - ux
  - cli
  - explain-flag
  - pre-run-digest
requires:
  - Plan 16-01 (CASES_PER_CONTRACT_TOOL, _render_pre_run_digest, _render_skipped_tools_explain, _compose_pre_run_skip_reasons)
  - Phase 14 (RenderContext, run_pytest_subprocess, _dispatch_default_mode_or_error, render_domain_ui, render_summary_only, render_debug_appendix)
  - Phase 13 (_REASON_NOT_SELECTED, _REASON_EXPLICIT_DEFAULT)
provides:
  - --explain Typer flag on `mcp-test-framework run`
  - Pre-run rendering pipeline (digest -> optional explain -> subprocess -> post-run rows + summary)
  - test_runner_pre_run_digest.py regression suite (11 tests)
  - test_runner_explain.py end-to-end suite (11 tests)
  - Inverted Phase 14 D-14 negative test + two new -q parity tests in test_runner_verbosity.py
affects:
  - src/mcp_test_framework/cli.py (run command body restructured pre-subprocess)
  - tests/framework/test_runner_verbosity.py (Phase 14 negative test inverted; two Plan 16-01 interim assertions flipped back)
tech-stack:
  added: []
  patterns:
    - "Typer flag declaration idiom (between --with-framework and pytest_args)"
    - "Quiet-mode gating: if not quiet: render; if explain: render_extra"
    - "Subprocess stub assertion as wrapper-ownership guard (assert flag not in argv)"
    - "AST-counted drift guard linking module constant to actual test surface"
key-files:
  created:
    - tests/framework/unit/test_runner_pre_run_digest.py
    - tests/framework/unit/test_runner_explain.py
  modified:
    - src/mcp_test_framework/cli.py
    - tests/framework/test_runner_verbosity.py
decisions:
  - "Plan 16-02: --explain owned by Typer wrapper, never forwarded to pytest (D-07 enforced by subprocess stub assert)"
  - "Plan 16-02: pre-run RenderContext built BEFORE subprocess with total_planned_cases=0; rebuilt post-parse with parsed.total_cases for the summary line"
  - "Plan 16-02: Phase 14 D-14 negative test renamed in place (test_run_help_does_not_list_explain -> test_run_help_lists_explain_phase16) preserving the regression breadcrumb"
metrics:
  duration_minutes: 6
  completed_date: 2026-05-12
---

# Phase 16 Plan 02: --explain flag and CLI wiring Summary

Wires Plan 16-01's renderer additions through the Typer CLI. Default-mode `mcp-test-framework run` now emits the pre-run digest BEFORE pytest's subprocess starts; `--explain` adds an inline `Skipping (N):` block between digest and subprocess; `-q` suppresses both. The Phase 14 D-14 deferral negative test inverts in place, and two Plan 16-01 interim banner-absence assertions flip back to banner-present. 22 new tests pin the surface; 4 existing verbosity tests pass unchanged after the audit.

## What Changed

### `src/mcp_test_framework/cli.py`

- **New Typer Option `--explain`** registered between `with_framework` (line 394-403) and `pytest_args` (line 404). Help text covers `--raw` and `-q`/`--quiet` interactions per D-08.
- **Pre-run rendering block** inserted between discovery (line 490) and `run_pytest_subprocess`. Builds a `pre_run_ctx` with `total_planned_cases=0`, then under `not quiet` calls `_runner._render_pre_run_digest(pre_run_ctx, with_framework=with_framework, explain=explain)`; under `not quiet and explain` calls `_runner._render_skipped_tools_explain(pre_run_ctx)`.
- **RenderContext rebuilt post-parse** with `parsed.total_cases` so the summary line's count source remains JUnit-derived. `discovered_tools`, `tools_config`, `judges`, `server_cmd` shared between pre_run_ctx and the post-run ctx.
- **`--raw` short-circuit at line 481 unchanged.** D-08 composition rule (`--raw` ignores `--explain`) is enforced by the short-circuit running BEFORE the pre-run digest block; no explicit gate needed.

### Before/after execution order in `run()`

| Step                          | Before (Plan 16-01)        | After (Plan 16-02)                                     |
| ----------------------------- | -------------------------- | ------------------------------------------------------ |
| 1. `_load_config(config)`     | same                       | same                                                   |
| 2. `--raw` short-circuit      | same                       | same                                                   |
| 3. `_discover_tools_for_run`  | yes                        | yes                                                    |
| 4. Build RenderContext        | post-subprocess only       | **pre-subprocess (pre_run_ctx) AND post-parse (ctx)** |
| 5. `_render_pre_run_digest`   | not called                 | **pre-subprocess, gated on `not quiet`**              |
| 6. `_render_skipped_tools_explain` | not called            | **pre-subprocess, gated on `not quiet and explain`**  |
| 7. `run_pytest_subprocess`    | yes                        | yes                                                    |
| 8. `_dispatch_default_mode_or_error` | yes                | yes                                                    |
| 9. `parse_junit_xml`          | yes                        | yes                                                    |
| 10. `render_domain_ui` / `render_summary_only` | yes (banner absent due to Plan 16-01 call-site removal) | yes (unchanged: post-run rows + summary line only) |
| 11. `render_debug_appendix`   | yes                        | yes                                                    |
| 12. Exit-code map + raise     | yes                        | yes                                                    |

### `tests/framework/unit/test_runner_pre_run_digest.py` (NEW, 11 tests)

- `test_cases_per_contract_tool_constant_locked` — pins `CASES_PER_CONTRACT_TOOL == 10` (D-03)
- `test_cases_per_contract_tool_matches_actual_parametrize_count` — AST-counts `test_*` (sync or async) functions at module scope of `tests/contract/test_mcp_tool_contract.py` and asserts equality with the constant. Either side drifting breaks the build.
- `test_pre_run_digest_emits_banner_and_label_block` — pins banner (40 equals signs), 5 label rows, Test plan line shape.
- `test_pre_run_digest_test_plan_uses_constant` — `Test plan: {running_n * CASES_PER_CONTRACT_TOOL}` formula.
- `test_pre_run_digest_height_bounded_at_small_N` — D-12: ≤ 11 split chunks at N=1.
- `test_pre_run_digest_height_bounded_at_N_70` — D-12: ≤ 11 split chunks at homelab-mcp's full N=70 surface; sanity-asserts that `tool_02` (third skipped tool) does NOT leak inline.
- `test_pre_run_digest_handles_empty_judges` — pins `Judges:      (none configured)` fallback.
- 4 `_compose_pre_run_skip_reasons` tests covering state-(a) unlisted, all-running empty case, state-(c) explicit default reason, state-(c) custom skip_reason override.

### `tests/framework/unit/test_runner_explain.py` (NEW, 11 tests)

- `test_run_help_lists_explain_flag` + `test_run_help_explain_mentions_raw_and_quiet_interactions` — pins D-07 help registration + D-08 composition documentation.
- `test_run_explain_lists_skipped_tools_alphabetically` — `Skipping (2):` header, em-dash `—` separator, sort order `beta < gamma`, state-(a) reason verbatim.
- `test_run_explain_renders_after_digest_before_pytest` — D-06 ordering: `digest_idx < explain_idx < result_idx`.
- `test_run_quiet_with_explain_is_noop` — D-09: `-q --explain` emits only `Result:`.
- `test_run_raw_with_explain_is_bypassed` — D-08: `--raw --explain` emits no digest, no Skipping block.
- `test_run_explain_with_with_framework_emits_suffix` — D-03/D-08: `--explain --with-framework` shows `+ framework self-tests` continuation + `Skipping (1):` block.
- `test_run_default_emits_digest_without_explain_block` — D-01: default shows hint, no Skipping block.
- `test_run_default_post_run_has_no_second_banner` — banner appears exactly once (no Plan 16-01 leftover).
- `test_run_default_includes_explain_hint` + `test_run_explain_suppresses_hint` — WARNING 4: hint string conditional on `--explain` state.
- **D-07 wrapper-ownership guard:** the `_stub_subprocess_writing_xml` helper asserts `"--explain" not in argv` on every invocation; any test invoking the stub fails loudly if --explain leaks to pytest.

### `tests/framework/test_runner_verbosity.py` (MODIFIED)

- **Phase 14 negative test renamed in place** (Option 1 per plan):
  - Old: `test_run_help_does_not_list_explain` asserting `--explain` absent from help.
  - New: `test_run_help_lists_explain_phase16` asserting `--explain` IS in help. Preserved as a regression breadcrumb naming the phase that owns the flag.
- **Two Plan 16-01 interim-state assertions flipped back to banner-present** (per Plan 16-01 SUMMARY's "Plan 16-02 Hooks" §2-§3):
  - `test_run_default_renders_full_domain_ui` (line ~219 in pre-task state): `"MCP Test Framework" not in result.output` → `"MCP Test Framework" in result.output`.
  - `test_run_debug_appends_appendix_after_domain_ui` (line ~239 in pre-task state): ordering check rewritten from `Result:` vs appendix to `MCP Test Framework` (banner) vs appendix. Banner is now pre-pytest and appendix is post-pytest, so `banner_idx < appendix_idx` is more directly true than the interim `Result:`-vs-appendix proxy.
- **Two new -q parity tests appended:**
  - `test_run_quiet_emits_exactly_one_line` — D-09 / UX-05: exactly one non-empty `Result:` line.
  - `test_run_quiet_suppresses_pre_run_digest` — D-09: no `MCP Test Framework`, no `Discovered:`, no `use --explain to list` under `-q`.

### Banner-position-dependent test audit (BLOCKER 2, Step A.5)

Per the plan's enumerated audit table, the following call sites in `test_runner_verbosity.py` were re-checked against the post-Plan-16-02 codebase:

| Line (post-task) | Function                                                | Assertion shape                | Status |
| ---------------- | ------------------------------------------------------- | ------------------------------ | ------ |
| 54               | `test_render_summary_only_prints_only_summary_line`     | `"MCP Test Framework" not in out` (render_summary_only direct call — no CLI) | UNCHANGED — passes (renderer body doesn't emit banner) |
| 197 (was 199)    | `test_run_quiet_renders_summary_only`                   | `"MCP Test Framework" not in result.output` | UNCHANGED — passes (`-q` suppresses pre-run digest per D-09) |
| 214 (was 216)    | `test_run_default_renders_full_domain_ui`               | FLIPPED to `in` | UPDATED — passes (banner is back pre-pytest) |
| 238-243 (was 236-244) | `test_run_debug_appends_appendix_after_domain_ui` | FLIPPED to `header_idx < appendix_idx` | UPDATED — passes |
| 263 (was 262)    | `test_run_quiet_plus_debug_renders_summary_then_appendix` | `"MCP Test Framework" not in result.output` | UNCHANGED — passes |
| 289 (was 289)    | `test_run_raw_ignores_quiet_and_debug`                  | `"MCP Test Framework" not in result.output` | UNCHANGED — passes |

All 15 tests in `tests/framework/test_runner_verbosity.py` pass post-Plan-16-02. Only the two flagged Plan 16-01 interim assertions were updated.

## Commits

| Task | Commit  | Description                                                                |
| ---- | ------- | -------------------------------------------------------------------------- |
| 1    | 1427602 | feat(16-02): register --explain flag and wire pre-run digest in cli.py     |
| 2    | 9d3343b | test(16-02): pin pre-run digest shape + CASES_PER_CONTRACT_TOOL drift guard |
| 3    | 3e11058 | test(16-02): end-to-end --explain flag tests with sort order + composition |
| 4    | f4dacf5 | test(16-02): invert Phase 14 explain-not-in-help + flip interim banner assertions + add -q parity |

## Verification

- `uv run mcp-test-framework run --help | grep --explain` returns the registered flag entry mentioning `--raw` and `-q`/`--quiet`. PASS.
- `uv run pytest tests/framework/unit/test_runner_pre_run_digest.py -v` — 11 passed. PASS.
- `uv run pytest tests/framework/unit/test_runner_explain.py -v` — 11 passed. PASS.
- `uv run pytest tests/framework/test_runner_verbosity.py -v` — 15 passed (was 13 pre-task; +2 new -q parity tests; -1 renamed Phase 14 D-14 deferral test now lists --explain). PASS.
- Plan task-1 verification block (regex pattern matches + `_build_pytest_args` does not contain `"--explain"`) — printed `OK`. PASS.
- Contract collection unaffected: `uv run pytest tests/contract/ --collect-only -q` collects 20 tests (10 cases × 2 default-allowlisted tools). PASS.
- Full `tests/framework/` surface: 302 passed, 1 skipped, 1 xfailed, 15 deselected, 9 failed. The 9 failures are the SAME pre-existing failures documented in Plan 16-01's `deferred-items.md` (test_tool_config × 4, test_cli_errors × 1, test_migration_doc × 4). Plan 16-02 introduces ZERO new test failures.

## Deviations from Plan

None. All four tasks executed exactly as written. The plan's acceptance criteria match the as-shipped code:

- `--explain` Typer Option registered (1 match in cli.py).
- `_render_pre_run_digest` call site count = 1.
- `_render_skipped_tools_explain` call site count = 1.
- `if not quiet:` followed by `_render_pre_run_digest` within 5 lines: confirmed.
- `if explain:` followed by `_render_skipped_tools_explain` on next line: confirmed.
- WARNING 3: framework suffix emits INSIDE `_render_pre_run_digest` (from Plan 16-01). `grep -c "+ framework self-tests" src/mcp_test_framework/cli.py` returns 0 (only the test file references that string).
- WARNING 4: cli.py passes `explain=explain` into the digest call. `grep -n "explain=explain" src/mcp_test_framework/cli.py` returns 1 match.
- BLOCKER 2: banner-position audit completed, all 15 verbosity tests pass; only the two interim flagged assertions needed updates.

## Deferred Issues

Same as Plan 16-01: 9 pre-existing test failures (test_tool_config × 4, test_cli_errors × 1, test_migration_doc × 4) tracked in `.planning/phases/16-reporter-ux-overhaul/deferred-items.md`. Unchanged by Plan 16-02.

## Threat Flags

None. The plan's threat model accepted T-16-02-01 (`tools_config[t].skip_reason` echoed to stdout — identical surface to Phase 14's post-run skip rows) and T-16-02-02 (`server_cmd` echoed pre-run — identical surface to Phase 14's `_render_header`). No new trust boundaries introduced. The `--explain` flag is wrapper-owned and never forwarded to the pytest subprocess; the subprocess stub's `assert "--explain" not in argv` enforces this at test time.

## Self-Check: PASSED

**Files exist:**

- src/mcp_test_framework/cli.py — FOUND (modified)
- tests/framework/unit/test_runner_pre_run_digest.py — FOUND (created)
- tests/framework/unit/test_runner_explain.py — FOUND (created)
- tests/framework/test_runner_verbosity.py — FOUND (modified)

**Symbols + flags importable:**

- `mcp-test-framework run --help` lists `--explain` — FOUND
- `from mcp_test_framework._runner import CASES_PER_CONTRACT_TOOL, _render_pre_run_digest, _render_skipped_tools_explain, _compose_pre_run_skip_reasons` — FOUND
- `_build_pytest_args` does NOT include `--explain` — VERIFIED

**Commits exist:**

- 1427602 (Task 1) — FOUND
- 9d3343b (Task 2) — FOUND
- 3e11058 (Task 3) — FOUND
- f4dacf5 (Task 4) — FOUND
