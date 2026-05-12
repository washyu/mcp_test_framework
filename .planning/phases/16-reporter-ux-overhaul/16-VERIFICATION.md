---
phase: 16-reporter-ux-overhaul
verified: 2026-05-12T17:30:00Z
status: passed
score: 14/14 must-haves verified
human_uat: approved 2026-05-12 (HUMAN-UAT.md result: pass; operator confirmed during /gsd-execute-phase 16)
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 13/14
  gaps_closed:
    - "README.md's -q description matches Phase 16 D-09 (Result: line format)"
    - "README's post-run per-tool rows example matches the renderer's actual output shape (passing: header + 2-space indent)"
    - "Per-judge reasoning surfaces in domain UI tail at runtime (UX-03 / SC-3) — live-run UAT 2026-05-12 confirmed `clarity score 2 < 4. reasoning=\"...\"` after em-dash on FAIL rows"
    - "Pre-run digest's `Judges:` line accurately reports the rubrics that will run for the configured tools (UX-01 / SC-1) — closed by Plan 16-05 commits 4140a9a, 08dd336, caa199f, a246fa8: new pure helper `_compose_judges_from_tool_configs` in `_runner.py:633` honors TOOLCFG-06's None / [] / subset semantic; old buggy `getattr(tool_cfg, 'judges', []) or []` loop replaced by single helper call at `cli.py:516`; three regression tests pin None / [] / subset cases. UAT-mirror smoke confirms helper returns `['clarity', 'disambiguation', 'parameters']` for the two-tool default-judges fixture (NOT `[]`)."
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Per-judge reasoning surfaces in domain UI tail at runtime (UX-03 / SC-3)"
    expected: "Output line of the form `  <tool_name>  ✗ FAIL — clarity score 2/5: <human-readable reasoning>`. The reasoning should be intelligible to an operator (not raw JSON, not a traceback)."
    why_human: "Requires a live `mcp-test-framework run` against a real Ollama judge or a contrived failing tool. The Windows host running this verification lacks `homelab-mcp` on PATH and cannot execute live judge calls. Static evidence (failure_message field threaded from JUnit XML at `_runner.py:849`) confirms the wiring exists; the operator-facing reasoning quality / formatting is not statically verifiable. Note: this item is carried forward unchanged across both prior re-verification passes; Plan 16-04 (docs) and Plan 16-05 (digest judges-union) did not address (nor were expected to address) this live behavioral check."
---

# Phase 16: Reporter UX overhaul Verification Report

**Phase Goal:** An operator preparing to run the framework sees an unambiguous pre-run digest of what will and won't execute (eliminating pytest's misleading "N collected, M deselected" framing), and a post-run aggregation in the same domain language. Output stays single-screen-readable at homelab-mcp scale (~70 tools).
**Verified:** 2026-05-12T17:30:00Z
**Status:** human_needed
**Re-verification:** Yes — gap closure executed in Plan 16-05 (commits `4140a9a`, `08dd336`, `caa199f`, `a246fa8`).

## Re-verification Summary

The single remaining gap from the 2026-05-12 (mid-day) verification has been closed by Plan 16-05:

**G-1 (Pre-run digest `Judges:` line lying about runtime) — CLOSED.** Plan 16-05 extracted the union loop into a pure helper `_compose_judges_from_tool_configs(tools_config) -> list[str]` in `_runner.py:633` that honors TOOLCFG-06's three-way semantic:

- `judges=None` (TOOLCFG-06 default) → expands to all of `RUBRIC_IDS` (`{clarity, disambiguation, parameters}`)
- `judges=[]` (explicit opt-out) → no-op (contributes nothing)
- `judges=[...]` (subset) → literal passthrough

The buggy `getattr(tool_cfg, "judges", []) or []` loop at the former `cli.py:512-516` is fully eradicated (grep gate returns 0). The replacement is a single call `judges = _runner._compose_judges_from_tool_configs(cfg.tools)` at `cli.py:516`. Three new regression tests at `test_runner_pre_run_digest.py:223,260,284` pin the None / [] / subset cases by exercising both the helper directly and the renderer end-to-end via capsys. UAT-mirror smoke confirms the helper now returns `['clarity', 'disambiguation', 'parameters']` for the two-tool default-judges fixture (pre-fix: `[]`).

No regressions detected against truths 1-12 (existing renderer, CLI wiring, and README artifacts unchanged by Plan 16-05; only the upstream union-computation site moved). The full digest test file passes 14/14 (11 pre-existing + 3 new), no skips, no failures.

The one outstanding human-verification item (live Ollama judge run for UX-03 per-judge reasoning surface) remains pending — Plan 16-05 was scoped to digest correctness, not the runtime FAIL-row formatting check. Phase 16 status therefore stays `human_needed` rather than `passed` until the live judge check is exercised against a real `homelab-mcp` + Ollama environment.

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria + PLAN frontmatter must-haves)

| #   | Truth                                                                                                      | Status     | Evidence                                                                                                                                                                  |
| --- | ---------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | SC-1 / UX-01: Pre-run digest emitted before pytest with server / discovered / running / skipping / judges / test-plan | ✓ VERIFIED | `_render_pre_run_digest` at `_runner.py:703-773` emits 8-line block + blank; called from `cli.py:533` BEFORE `run_pytest_subprocess` at `cli.py:541`. (No regression.) |
| 2   | SC-2 / UX-02+UX-04: `--explain` produces grep-able N+5-line output at N=70                                  | ✓ VERIFIED | `_render_skipped_tools_explain` at `_runner.py:776-812`. (No regression.)                                                                                                  |
| 3   | SC-3 / UX-03: Post-run aggregates per-tool PASS/FAIL/SKIP and per-judge reasoning; v1.1 `_reporter.py` subsumed | ⚠️ PARTIAL | D-11 `--debug` per-judge breakdown block deferred to v1.3 per CONTEXT.md "Claude's Discretion" — intentional scope reduction. Per-judge reasoning surfaces via FAIL-row em-dash today. Live behavioral confirmation flagged for human verification. (Unchanged — intentional, not a regression.) |
| 4   | SC-4 / UX-05: `-q` / `--quiet` suppresses digest + per-tool rows; only summary line                         | ✓ VERIFIED | `cli.py:532` gating + `test_run_quiet_emits_exactly_one_line` passing. (No regression.) README at line 93 documents the correct emitted Result: shape.                |
| 5   | SC-5: Digest counts agree with what the runner actually executes                                            | ✓ VERIFIED | `_compose_pre_run_skip_reasons` / Phase 14 composer; AST drift guard active. **And now `_compose_judges_from_tool_configs` (Plan 16-05) pins the Judges union to TOOLCFG-06's runtime semantic.** Digest no longer lies about which rubrics fire. |
| 6   | PLAN 16-01: `CASES_PER_CONTRACT_TOOL: int = 10` module-level constant in `_runner.py`                       | ✓ VERIFIED | `_runner.py:313`. (No regression.)                                                                                                                                          |
| 7   | PLAN 16-01: `_render_pre_run_digest`, `_render_skipped_tools_explain`, `_compose_pre_run_skip_reasons` exist | ✓ VERIFIED | All three at `_runner.py:602, 703, 776`. (No regression.)                                                                                                                  |
| 8   | PLAN 16-01: `render_domain_ui` no longer calls `_render_header`                                             | ✓ VERIFIED | `render_domain_ui` at `_runner.py:908-928` calls `_render_per_tool_rows` + `_render_summary_line` only. (No regression.)                                                  |
| 9   | PLAN 16-01: Digest height ≤ 10 lines regardless of N (D-12, capsys test at N=70)                            | ✓ VERIFIED | `test_pre_run_digest_height_bounded_at_N_70` passes. (No regression.)                                                                                                      |
| 10  | PLAN 16-02: `--explain` Typer flag registered with help text mentioning `--raw` and `-q`                    | ✓ VERIFIED | `cli.py:404-414`. (No regression.)                                                                                                                                          |
| 11  | PLAN 16-02: `--explain` is wrapper-owned; never forwarded to pytest                                         | ✓ VERIFIED | `_build_pytest_args` unchanged; test stubs assert. (No regression.)                                                                                                        |
| 12  | PLAN 16-02: Phase 14 D-14 negative test inverted to assert `--explain` IS in help                           | ✓ VERIFIED | `test_run_help_lists_explain_phase16` at `test_runner_verbosity.py:139` + companion positive test. (No regression.)                                                       |
| 13  | PLAN 16-03 + 16-04: README documents `--explain` + pre-run digest + `-q` semantics correctly, matching the renderer char-for-char | ✓ VERIFIED | Verified via 11 grep gates on README. (Unchanged from prior pass.) |
| 14  | PLAN 16-05: Pre-run digest's `Judges:` line accurately reports the rubrics that will run (TOOLCFG-06 None/[]/subset semantic honored at digest time) | ✓ VERIFIED | **FLIPPED from FAILED.** Old buggy `getattr(tool_cfg, "judges", []) or []` loop eradicated from `cli.py` (grep returns 0). New helper `_compose_judges_from_tool_configs` at `_runner.py:633` expands `judges=None` to `RUBRIC_IDS`. Single helper call at `cli.py:516`. Three regression tests at `test_runner_pre_run_digest.py:223,260,284` exercise None / [] / subset via both helper-direct and renderer-end-to-end (capsys). UAT-mirror smoke: `_compose_judges_from_tool_configs({'list_keyring_credentials': ToolConfig(), 'suggest_deployments': ToolConfig()})` returns `['clarity', 'disambiguation', 'parameters']` — NOT `[]`. |

**Score:** 14/14 truths verified (13 fully VERIFIED + 1 intentionally PARTIAL per CONTEXT.md decision to defer D-11 to v1.3).

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/mcp_test_framework/_runner.py` | renderer additions (digest, explain, constant, wrapper); call-site change; **Plan 16-05: new `_compose_judges_from_tool_configs` pure helper + `RUBRIC_IDS` import** | ✓ VERIFIED | Helper at line 633 (verified by `grep _compose_judges_from_tool_configs` → 1 def). `from .rubrics import RUBRIC_IDS` at line 43 (verified by grep). Helper body honors TOOLCFG-06: `declared is None → judges_set.update(RUBRIC_IDS)`, else `judges_set.update(declared)`. |
| `src/mcp_test_framework/cli.py` | `--explain` Typer flag; pre-run digest pipeline; `-q` gating; **Plan 16-05: union loop replaced by single helper call** | ✓ VERIFIED | `judges = _runner._compose_judges_from_tool_configs(cfg.tools)` at line 516 (grep returns 1). Old `getattr(tool_cfg, "judges", []) or []` pattern absent (grep returns 0). Old `judges_set: set[str] = set()` variable absent (grep returns 0). Comment block at lines 510-515 documents TOOLCFG-06 + G-1 reference inline. |
| `tests/framework/unit/test_runner_pre_run_digest.py` | digest shape + constant pin + AST drift guard (≥ 80 lines); **Plan 16-05: 3 new tests pinning Judges-line None/[]/subset semantic** | ✓ VERIFIED | All three new tests present: `test_judges_line_lists_all_rubrics_when_judges_unset:223`, `test_judges_line_reports_none_configured_when_judges_explicitly_empty:260`, `test_judges_line_lists_subset_when_judges_explicit:284`. Import expanded to include `_compose_judges_from_tool_configs` and real `ToolConfig` (line 21, 25). Full file passes 14/14 under `MCPTF_CONFIG_FILE=config-v2-worktree.yaml uv run pytest -q`. |
| `tests/framework/unit/test_runner_explain.py` | end-to-end `--explain` tests + composition + wrapper-ownership guard (≥ 80 lines) | ✓ VERIFIED | Unchanged. |
| `tests/framework/test_runner_verbosity.py` | `-q` parity tests appended; Phase 14 negative test inverted | ✓ VERIFIED | Unchanged. |
| `README.md` | pre-run digest + `--explain` + `-q` documented, mirroring renderer char-for-char | ✓ VERIFIED | Unchanged from prior pass (Plan 16-04 closure). Plan 16-05 was source-only; no README churn (correct per its `<success_criteria>` item 5). |
| `docs/mcp_test_framework_mvp_spec.md` | spec audited, intentionally unchanged | ✓ VERIFIED | Unchanged. |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `cli.py:run` | `_runner._compose_judges_from_tool_configs(cfg.tools)` | direct call replacing the local union loop at the former lines 512-516 | ✓ **WIRED** (Plan 16-05 closure) | Verified `grep -c '_compose_judges_from_tool_configs(cfg.tools)' src/mcp_test_framework/cli.py` returns 1 (at line 516). Both downstream RenderContext builds (pre-run at line 518, post-run at ~line 577) pick up the helper's output transparently via the unchanged `judges` local. |
| `_runner._compose_judges_from_tool_configs` | `rubrics.RUBRIC_IDS` | `from .rubrics import RUBRIC_IDS` import + `judges_set.update(RUBRIC_IDS)` in helper body | ✓ **WIRED** (Plan 16-05 closure) | `grep 'from .rubrics import RUBRIC_IDS' _runner.py` returns line 43. Helper at line 654 uses `judges_set.update(RUBRIC_IDS)` for the None branch. |
| `cli.py:run` | `_runner._render_pre_run_digest(pre_run_ctx)` | direct call gated on `not quiet`, BEFORE `run_pytest_subprocess` | ✓ WIRED | Unchanged. |
| `cli.py:run` | `_runner._render_skipped_tools_explain(pre_run_ctx)` | direct call gated on `explain`, after digest | ✓ WIRED | Unchanged. |
| `_render_pre_run_digest` | `RenderContext` fields | function arg `ctx` | ✓ WIRED | Unchanged. |
| `_render_skipped_tools_explain` | `_compose_unparametrized_skips_from_config` | via `_compose_pre_run_skip_reasons` wrapper | ✓ WIRED | Unchanged. |
| `render_domain_ui` | `_render_per_tool_rows` + `_render_summary_line` ONLY | banner call-site at former line 773 deleted | ✓ WIRED | Unchanged. |
| `test_runner_pre_run_digest.py::test_cases_per_contract_tool_matches_actual_parametrize_count` | `tests/contract/test_mcp_tool_contract.py` | `ast.parse` filtering `test_*` async/sync defs | ✓ WIRED | Unchanged. |
| README.md sample output blocks | `_render_summary_line` + `_render_per_tool_rows` | literal string mirror | ✓ WIRED | Unchanged (closed by Plan 16-04). |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `_render_pre_run_digest` | `discovered_tools`, `tools_config`, `judges`, `server_cmd` | live MCP discovery + parsed YAML; **`judges` now sourced via `_compose_judges_from_tool_configs` honoring TOOLCFG-06** | ✓ Yes | ✓ FLOWING |
| `_compose_judges_from_tool_configs` | `tools_config` values' `judges` attribute | `cfg.tools` (Pydantic ToolConfig instances loaded from config.yaml via config loader) | ✓ Yes — TOOLCFG-06 None default expands to `RUBRIC_IDS`; `[]` opt-out is a no-op; subsets pass through. UAT-mirror confirms `['clarity', 'disambiguation', 'parameters']` for the two-default-tools fixture. | ✓ FLOWING |
| `_render_skipped_tools_explain` | `skipped` dict | composer over real discovered + cfg.tools | ✓ Yes | ✓ FLOWING |
| `_render_per_tool_rows` | `parsed.per_tool` | live JUnit XML | ✓ Yes | ✓ FLOWING |
| `_render_summary_line` | `parsed.per_tool`, `parsed.total_time`, `unparam_skips` | live JUnit XML | ✓ Yes | ✓ FLOWING |
| `README.md` (operator doc) | sample-output literal strings | static doc mirror of renderer output, pinned by test `test_summary_line_includes_skip_count_when_skips_present` at `test_runner_renderer.py:223` | ✓ Yes — strings mirror what tests assert the renderer emits | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior                                                                                                  | Command                                                                                                                                | Result                                                                                  | Status |
| --------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ------ |
| `_runner.py` defines `_compose_judges_from_tool_configs` | `grep -c '_compose_judges_from_tool_configs' src/mcp_test_framework/_runner.py` | `1` (def at line 633; usage in module body is via `judges_set.update(RUBRIC_IDS)`) — exceeds ≥1 floor required | ✓ PASS |
| `cli.py` calls helper at single site | `grep -c '_compose_judges_from_tool_configs(cfg.tools)' src/mcp_test_framework/cli.py` | `1` (at line 516) | ✓ PASS |
| Old buggy union loop eradicated from `cli.py` | `grep -c 'getattr(tool_cfg, "judges", \[\]) or \[\]' src/mcp_test_framework/cli.py` | `0` | ✓ PASS |
| `RUBRIC_IDS` imported into `_runner.py` | `grep -c 'from \.rubrics import RUBRIC_IDS' src/mcp_test_framework/_runner.py` | `1` (at line 43) | ✓ PASS |
| Three new regression tests present | `grep -c 'test_judges_line_' tests/framework/unit/test_runner_pre_run_digest.py` | `3` (lines 223, 260, 284) | ✓ PASS |
| Full digest test file passes | `MCPTF_CONFIG_FILE=config-v2-worktree.yaml uv run pytest tests/framework/unit/test_runner_pre_run_digest.py -q` | `14 passed in 3.62s` (11 pre-existing + 3 new) | ✓ PASS |
| UAT-mirror: default-judges two-tool fixture | `uv run python -c "from mcp_test_framework._runner import _compose_judges_from_tool_configs; from mcp_test_framework.models import ToolConfig; print(_compose_judges_from_tool_configs({'list_keyring_credentials': ToolConfig(), 'suggest_deployments': ToolConfig()}))"` | `['clarity', 'disambiguation', 'parameters']` — NOT `[]` | ✓ PASS |
| Helper body honors TOOLCFG-06 three-way semantic | Read `_runner.py:650-657` | `declared is None → judges_set.update(RUBRIC_IDS)`; else `judges_set.update(declared)` ([] is no-op; subset passes through) | ✓ PASS |
| README contains the corrected `Result:` line in both sample blocks (prior verification) | `grep -c 'Result: 20 PASS / 0 FAIL / 560 SKIP  in 4.3s' README.md` | `2` (lines 85 and 230) | ✓ PASS |
| `git log --oneline -5` shows Plan 16-05 commits on main | `git log --oneline -5` | `a246fa8` (docs), `caa199f` (test), `08dd336` (fix), `4140a9a` (feat), `a2bbdc0` (plan) — all four implementation+docs commits present | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description                                                                                                  | Status        | Evidence                                                                                                                                                                                                                                                  |
| ----------- | ----------- | ------------------------------------------------------------------------------------------------------------ | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UX-01       | 16-01, 16-02, 16-03, 16-04, **16-05** | Pre-run digest replaces "N collected, M deselected"; digest truthfully reflects what will execute | ✓ SATISFIED   | Renderer + CLI wiring + README docs + **Plan 16-05 judges-union fix restoring digest truthfulness for the TOOLCFG-06 None default case**. SC-1's "unambiguous pre-run digest" contract holds again. |
| UX-02       | 16-02, 16-03 | `--explain` flag plumbed through Typer, not forwarded to pytest                                              | ✓ SATISFIED   | Flag at `cli.py:404`; wrapper-ownership guard active; README `--explain` table row + example block accurate.                                                                                                                                              |
| UX-03       | 16-01 | Post-run aggregates per-tool PASS/FAIL/SKIP + per-judge reasoning                                                 | ⚠️ PARTIAL    | Per-tool aggregation works; per-judge reasoning surfaces via FAIL-row em-dash. D-11 `--debug` per-judge breakdown block deferred to v1.3 (intentional scope reduction per CONTEXT.md "Claude's Discretion"). Live operator-perceivable behavior flagged for human verification.                |
| UX-04       | 16-01, 16-02 | N=70 readability; digest single-screen; `--explain` ≤ N+5 grep-able                                          | ✓ SATISFIED   | `test_pre_run_digest_height_bounded_at_N_70` passes.                                                                                                                       |
| UX-05       | 16-02, 16-03, 16-04 | `-q` suppresses digest + per-tool rows; only summary line                                                    | ✓ SATISFIED   | `cli.py:532` gates digest; quiet-mode test asserts one-line output; README line 93 documents the correct emitted Result: shape.                                                          |

All 5 declared requirements present in plan frontmatter. No orphaned requirements. Plan 16-05 declared `requirements: [UX-01]` and tightened UX-01's contract by closing G-1.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `src/mcp_test_framework/_runner.py` | 742-746 vs 621-625 | Running-set predicate duplicated between `_render_pre_run_digest` and `_compose_pre_run_skip_reasons` | ⚠️ WARNING | WR-02 from code review. Two independent copies invite silent drift if the state-(b) rule ever changes. Not a behavioral bug today. (Unchanged — out of Phase 16 gap-closure scope.) |
| `src/mcp_test_framework/cli.py` | 269 | `os.environ["MCPTF_CONFIG_FILE"] = str(resolved)` side-effect mutation | ⚠️ WARNING | WR-01 from code review. Pre-existing pattern; affects test isolation under `CliRunner.invoke`. Not introduced by Phase 16. |
| `src/mcp_test_framework/_runner.py` | 758, 762, 764 | `f"{running_n:>2}"` 2-char right-justification breaks at N ≥ 100 | ℹ️ INFO | WR-03 from review. Not exercised in v1.2 (homelab-mcp ≈ 70 tools). Cosmetic-only at large N. |
| `src/mcp_test_framework/_runner.py` | 751, 766 | `Test plan: R*10 contract cases` overcounts when tools have non-default `judges` lists | ℹ️ INFO | WR-04 from review. Phase 16 D-03 accepts this — "Test plan" is the parametrize ceiling, not the runtime count. README could clarify. **Note:** Plan 16-05 closed the orthogonal judges-union bug, but the Test-plan overcount on subset judges is a separate, accepted item. |
| `tests/framework/test_runner_renderer.py` | 9-16 | Stale docstring references `tests/test_runner_renderer.py` (pre-Phase-15 path) | ℹ️ INFO | WR-05. Recovery command in comment will fail. Cosmetic. |

**Resolved since initial verification:**
- ~~`README.md:84, 92, 228` — Documented `Result:` format differs from actual emitted format (🛑 BLOCKER)~~ → **CLOSED** by Plan 16-04 commit `b1bc5dc`.
- ~~`README.md:81-82, 225-226` — Per-tool row examples missing `passing:` section headers + 2-space indent (⚠️ WARNING)~~ → **CLOSED** by Plan 16-04 commit `ef4c884`.
- ~~`cli.py:512-516` — Union loop treated `judges=None` (TOOLCFG-06 default = run all rubrics) as `[]`, producing a lying digest (🛑 BLOCKER for SC-1)~~ → **CLOSED** by Plan 16-05 commits `4140a9a`, `08dd336`, `caa199f`.

### Human Verification Required

1. **Per-judge reasoning surfaces in domain UI tail at runtime (UX-03 / SC-3)**

   **Test:** Run `mcp-test-framework run` (default mode, no `--raw`) against a real Ollama instance with a tool whose declared description fails a judge rubric. Verify that the post-run FAIL row shows the failing judge's reasoning text after the em-dash separator.
   **Expected:** Output line of the form `  <tool_name>  ✗ FAIL — clarity score 2/5: <human-readable reasoning>`. The reasoning should be intelligible to an operator (not raw JSON, not a traceback).
   **Why human:** Requires a live `mcp-test-framework run` against a real Ollama judge or a contrived failing tool. The Windows host running this verification lacks `homelab-mcp` on PATH and cannot execute live judge calls. Static evidence (failure_message field threaded from JUnit XML at `_runner.py:849`) confirms the wiring exists; the operator-facing reasoning quality / formatting is not statically verifiable.

   **Note:** This item is carried forward unchanged across two prior re-verification passes. Plan 16-04 (README format corrections) and Plan 16-05 (digest judges-union fix) were both scoped to other gaps and did not address this live behavioral check.

### Gaps Summary

**No remaining gaps.** All three 2026-05-11/12 gaps closed:

- **CR-01 BLOCKER (README Result: format) — CLOSED** via Plan 16-04 commit `b1bc5dc`. README mirrors `_render_summary_line` char-for-char.
- **IN-02 WARNING (README per-tool row shape) — CLOSED** via Plan 16-04 commit `ef4c884`. README shows flush-left `passing:` header + 2-space-indented rows.
- **G-1 BLOCKER (digest Judges: line lying about runtime) — CLOSED** via Plan 16-05 commits `4140a9a` (feat: helper), `08dd336` (fix: cli.py call site), `caa199f` (test: 3 regression tests), `a246fa8` (docs: SUMMARY). New pure helper `_compose_judges_from_tool_configs` at `_runner.py:633` honors TOOLCFG-06's None / [] / subset semantic. Old buggy `getattr(..., "judges", []) or []` pattern eradicated from `cli.py` (grep returns 0). UAT-mirror smoke confirms `['clarity', 'disambiguation', 'parameters']` for the two-tool default-judges fixture (pre-fix: `[]`).

`git log --oneline -5` confirms all four Plan 16-05 commits landed on main (`a246fa8`, `caa199f`, `08dd336`, `4140a9a`) plus the planning commit (`a2bbdc0`).

**Status: human_needed.** All 14 must-have truths now pass automated verification (13 fully VERIFIED + 1 intentionally PARTIAL by design per CONTEXT.md D-11 deferral to v1.3). The one outstanding human-verification item (live Ollama judge run for UX-03 reasoning surface) is carried forward unchanged from prior passes and is unrelated to the gap closures. Phase 16 cannot be marked `passed` until the live judge check is exercised against a real `homelab-mcp` + Ollama environment.

**Note on env_note:** The pre-existing stale `_preflight` autouse fixture guard (`src/mcp_test_framework/fixtures.py:108-125` checking `tests/unit/` instead of `tests/framework/unit/` after Phase 15's directory rename) plus the v2-config-schema gate require `MCPTF_CONFIG_FILE=config-v2-worktree.yaml` for local pytest runs on this verification host. This is a Phase 15 residue, not a Phase 16 regression — surfaced here as a follow-up note but NOT counted as a Phase 16 gap. With the env var set, the digest test file passes 14/14 cleanly. The 9 pre-existing test failures catalogued in `deferred-items.md` are similarly out-of-scope for Phase 16.

---

_Verified: 2026-05-12_
_Verifier: Claude (gsd-verifier)_
_Re-verification: gaps closed by Plan 16-04 (commits b1bc5dc, ef4c884, 7df134b) + Plan 16-05 (commits 4140a9a, 08dd336, caa199f, a246fa8)_
