---
phase: 16-reporter-ux-overhaul
verified: 2026-05-12T00:00:00Z
status: human_needed
score: 13/13 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 11/13
  gaps_closed:
    - "README.md's -q description matches Phase 16 D-09 (Result: line format)"
    - "README's post-run per-tool rows example matches the renderer's actual output shape (passing: header + 2-space indent)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Per-judge reasoning surfaces in domain UI tail at runtime (UX-03 / SC-3)"
    expected: "When a contract test fails because a judge returns score < 4, the FAIL row in the post-run rows shows the judge's reasoning text after the em-dash separator (`  <tool>  ✗ FAIL — clarity score 2/5: <reasoning>`)."
    why_human: "Requires a live `mcp-test-framework run` against a real Ollama judge or a contrived failing tool — preflight requires `homelab-mcp` on PATH; cannot be exercised on this verification host. Static evidence (failure_message field threaded from JUnit XML at _runner.py:849) suggests it works, but the operator-facing reasoning quality / formatting is not statically verifiable."
---

# Phase 16: Reporter UX overhaul Verification Report

**Phase Goal:** An operator preparing to run the framework sees an unambiguous pre-run digest of what will and won't execute (eliminating pytest's misleading "N collected, M deselected" framing), and a post-run aggregation in the same domain language. Output stays single-screen-readable at homelab-mcp scale (~70 tools).
**Verified:** 2026-05-12T00:00:00Z
**Status:** human_needed
**Re-verification:** Yes — gap closure executed in Plan 16-04 (commits `b1bc5dc`, `ef4c884`, `7df134b`).

## Re-verification Summary

Two gaps from the initial 2026-05-11 verification have been closed by Plan 16-04:

1. **CR-01 BLOCKER (Gap 1) — CLOSED.** README.md lines 85, 93, 230 now document the renderer's actual `Result:` line shape (`Result: N PASS / M FAIL [/ S SKIP]  in T.Ts`, uppercase verbs, slash-separated, double-space-before-`in`, includes timing). The old `Result: N passed, M failed, S skipped` form is completely absent from README.md.
2. **IN-02 WARNING (Gap 2) — CLOSED.** README.md lines 81-83 and 226-228 now show a flush-left `passing:` section header followed by 2-space-indented per-tool rows, matching `_render_per_tool_rows` at `_runner.py:866-870`. The adjacent prose at line 244 was reworded from `560 skipped cases` to `560 SKIP cases` so terminology matches the new verb shape.

No regressions detected against truths 1-12 (all source code unchanged; only README.md modified across two non-orchestrator commits). Truth 3 (UX-03 partial — D-11 per-judge breakdown deferred to v1.3 per CONTEXT.md "Claude's Discretion") remains as a documented intentional scope reduction; not downgraded.

The original human-verification item (live Ollama judge run) remains pending — the docs fix did not address it (nor was it expected to), so the phase status is `human_needed` rather than `passed`. All automated checks now pass.

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria + PLAN frontmatter must-haves)

| #   | Truth                                                                                                      | Status     | Evidence                                                                                                                                                                  |
| --- | ---------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | SC-1 / UX-01: Pre-run digest emitted before pytest with server / discovered / running / skipping / judges / test-plan | ✓ VERIFIED | `_render_pre_run_digest` at `_runner.py:703-773` emits 8-line block + blank; called from `cli.py:533` BEFORE `run_pytest_subprocess` at `cli.py:541`. (No regression — source unchanged since initial verification.) |
| 2   | SC-2 / UX-02+UX-04: `--explain` produces grep-able N+5-line output at N=70                                  | ✓ VERIFIED | `_render_skipped_tools_explain` at `_runner.py:776-812`. (No regression.)                                                                                                  |
| 3   | SC-3 / UX-03: Post-run aggregates per-tool PASS/FAIL/SKIP and per-judge reasoning; v1.1 `_reporter.py` subsumed | ⚠️ PARTIAL | D-11 `--debug` per-judge breakdown block deferred to v1.3 per CONTEXT.md "Claude's Discretion" — intentional scope reduction. Per-judge reasoning surfaces via FAIL-row em-dash today. Live behavioral confirmation flagged for human verification. (Unchanged from initial verification — intentional, not a regression.) |
| 4   | SC-4 / UX-05: `-q` / `--quiet` suppresses digest + per-tool rows; only summary line                         | ✓ VERIFIED | `cli.py:532` gating + `test_run_quiet_emits_exactly_one_line` passing. (No regression.) README at line 93 now documents the correct emitted Result: shape.                |
| 5   | SC-5: Digest counts agree with what the runner actually executes                                            | ✓ VERIFIED | `_compose_pre_run_skip_reasons` / Phase 14 composer; AST drift guard active. (No regression.)                                                                              |
| 6   | PLAN 16-01: `CASES_PER_CONTRACT_TOOL: int = 10` module-level constant in `_runner.py`                       | ✓ VERIFIED | `_runner.py:313`. (No regression.)                                                                                                                                          |
| 7   | PLAN 16-01: `_render_pre_run_digest`, `_render_skipped_tools_explain`, `_compose_pre_run_skip_reasons` exist | ✓ VERIFIED | All three at `_runner.py:602, 703, 776`. (No regression.)                                                                                                                  |
| 8   | PLAN 16-01: `render_domain_ui` no longer calls `_render_header`                                             | ✓ VERIFIED | `render_domain_ui` at `_runner.py:908-928` calls `_render_per_tool_rows` + `_render_summary_line` only. (No regression.)                                                  |
| 9   | PLAN 16-01: Digest height ≤ 10 lines regardless of N (D-12, capsys test at N=70)                            | ✓ VERIFIED | `test_pre_run_digest_height_bounded_at_N_70` passes. (No regression.)                                                                                                      |
| 10  | PLAN 16-02: `--explain` Typer flag registered with help text mentioning `--raw` and `-q`                    | ✓ VERIFIED | `cli.py:404-414`. (No regression.)                                                                                                                                          |
| 11  | PLAN 16-02: `--explain` is wrapper-owned; never forwarded to pytest                                         | ✓ VERIFIED | `_build_pytest_args` unchanged; test stubs assert. (No regression.)                                                                                                        |
| 12  | PLAN 16-02: Phase 14 D-14 negative test inverted to assert `--explain` IS in help                           | ✓ VERIFIED | `test_run_help_lists_explain_phase16` at `test_runner_verbosity.py:139` + companion positive test. (No regression.)                                                       |
| 13  | PLAN 16-03 + 16-04: README documents `--explain` + pre-run digest + `-q` semantics correctly, matching the renderer char-for-char | ✓ VERIFIED | **FLIPPED from FAILED.** README.md line 85 + line 230 contain `Result: 20 PASS / 0 FAIL / 560 SKIP  in 4.3s` (exactly what `_render_summary_line` at `_runner.py:898` emits, including the double space before `in`). Line 93 documents `Result: N PASS / M FAIL [/ S SKIP]  in T.Ts` with explicit prose on the bracketed-SKIP-segment + double-space-before-`in` quirks. Lines 81-83 and 226-228 show `passing:` flush-left section header + 2-space-indented rows (`  list_keyring_credentials  ✓ PASS`, `  suggest_deployments       ✓ PASS`), matching `_render_per_tool_rows` at `_runner.py:866-870`. Line 244 prose updated `560 skipped cases` → `560 SKIP cases`. Old comma-separated lowercase format completely absent. |

**Score:** 13/13 truths verified (12 fully VERIFIED + 1 intentionally PARTIAL per CONTEXT.md decision to defer D-11 to v1.3).

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/mcp_test_framework/_runner.py` | renderer additions (digest, explain, constant, wrapper); call-site change | ✓ VERIFIED | Unchanged since initial verification (gap closure was docs-only). |
| `src/mcp_test_framework/cli.py` | `--explain` Typer flag; pre-run digest pipeline; `-q` gating | ✓ VERIFIED | Unchanged since initial verification. |
| `tests/framework/unit/test_runner_pre_run_digest.py` | digest shape + constant pin + AST drift guard (≥ 80 lines) | ✓ VERIFIED | Unchanged since initial verification. |
| `tests/framework/unit/test_runner_explain.py` | end-to-end `--explain` tests + composition + wrapper-ownership guard (≥ 80 lines) | ✓ VERIFIED | Unchanged since initial verification. |
| `tests/framework/test_runner_verbosity.py` | `-q` parity tests appended; Phase 14 negative test inverted | ✓ VERIFIED | Unchanged since initial verification. |
| `README.md` | pre-run digest + `--explain` + `-q` documented, mirroring renderer char-for-char | ✓ VERIFIED | **FLIPPED from ORPHANED.** Plan 16-04 closed the format-drift gap. All six Plan 16-04 edit sites verified at lines 81-83, 85, 93, 226-228, 230, 244. |
| `docs/mcp_test_framework_mvp_spec.md` | spec audited, intentionally unchanged | ✓ VERIFIED | Unchanged since initial verification. |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `cli.py:run` | `_runner._render_pre_run_digest(pre_run_ctx)` | direct call gated on `not quiet`, BEFORE `run_pytest_subprocess` | ✓ WIRED | Unchanged. |
| `cli.py:run` | `_runner._render_skipped_tools_explain(pre_run_ctx)` | direct call gated on `explain`, after digest | ✓ WIRED | Unchanged. |
| `_render_pre_run_digest` | `RenderContext` fields | function arg `ctx` | ✓ WIRED | Unchanged. |
| `_render_skipped_tools_explain` | `_compose_unparametrized_skips_from_config` | via `_compose_pre_run_skip_reasons` wrapper | ✓ WIRED | Unchanged. |
| `render_domain_ui` | `_render_per_tool_rows` + `_render_summary_line` ONLY | banner call-site at former line 773 deleted | ✓ WIRED | Unchanged. |
| `test_runner_pre_run_digest.py::test_cases_per_contract_tool_matches_actual_parametrize_count` | `tests/contract/test_mcp_tool_contract.py` | `ast.parse` filtering `test_*` async/sync defs | ✓ WIRED | Unchanged. |
| **README.md sample output blocks** | **`_render_summary_line` + `_render_per_tool_rows`** | **literal string mirror** | ✓ **WIRED** (gap closure) | **Plan 16-04 must_have key_link.** README quotes the exact strings the renderer emits, char-for-char including whitespace quirks. Verified via 11 grep gates. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `_render_pre_run_digest` | `discovered_tools`, `tools_config`, `judges`, `server_cmd` | live MCP discovery + parsed YAML | ✓ Yes | ✓ FLOWING |
| `_render_skipped_tools_explain` | `skipped` dict | composer over real discovered + cfg.tools | ✓ Yes | ✓ FLOWING |
| `_render_per_tool_rows` | `parsed.per_tool` | live JUnit XML | ✓ Yes | ✓ FLOWING |
| `_render_summary_line` | `parsed.per_tool`, `parsed.total_time`, `unparam_skips` | live JUnit XML | ✓ Yes | ✓ FLOWING |
| `README.md` (operator doc) | sample-output literal strings | static doc mirror of renderer output, pinned by test `test_summary_line_includes_skip_count_when_skips_present` at `test_runner_renderer.py:223` | ✓ Yes — strings mirror what tests assert the renderer emits | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior                                                                                                  | Command                                                                                                                                | Result                                                                                  | Status |
| --------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ------ |
| README contains the corrected `Result:` line in both sample blocks                                        | `grep -c 'Result: 20 PASS / 0 FAIL / 560 SKIP  in 4.3s' README.md`                                                                     | `2` (lines 85 and 230)                                                                  | ✓ PASS |
| README `-q` table row documents the bracketed-SKIP-segment shape                                          | `grep -c 'Result: N PASS / M FAIL \[/ S SKIP\]  in T.Ts' README.md`                                                                    | `1` (line 93)                                                                            | ✓ PASS |
| README contains zero occurrences of the old comma-separated lowercase format                              | `grep -E 'Result: .* passed, .* failed' README.md` + `grep 'N passed, M failed, S skipped' README.md` + `grep '0 failed, 560 skipped'` | `0` / `0` / `0`                                                                          | ✓ PASS |
| README per-tool row examples have the `passing:` section header on its own line                           | `grep -n '^passing:$' README.md` (Bash); content check shows lines 81 + 226                                                            | `81:passing:` and `226:passing:` confirmed via content grep                              | ✓ PASS |
| README per-tool rows indented exactly 2 spaces                                                            | content grep on `list_keyring_credentials` / `suggest_deployments`                                                                     | `82:  list_keyring_credentials  ✓ PASS` and `83:  suggest_deployments       ✓ PASS` (and analogous at 227-228) | ✓ PASS |
| README adjacent prose reworded `skipped` → `SKIP` (560 SKIP cases)                                        | `grep '560 SKIP cases' README.md` + `grep '560 skipped cases' README.md`                                                                | `1` / `0`                                                                                | ✓ PASS |
| `--explain` placeholder unchanged in `--explain` example block                                            | `grep '(pytest subprocess runs here, then per-tool rows + Result: line)' README.md`                                                    | `1` (line 121)                                                                           | ✓ PASS |
| `git diff --stat HEAD~3..HEAD` shows only README + orchestrator artifacts; no source / test files touched | `git diff --stat HEAD~3..HEAD`                                                                                                          | README.md (20 lines), STATE.md, ROADMAP.md, 16-04-SUMMARY.md — no `_runner.py`, no `cli.py`, no test files | ✓ PASS |
| Renderer source-of-truth still matches README documentation                                                | Read `_runner.py:898` and `test_runner_renderer.py:223`                                                                                 | `f"Result: {n_pass} PASS / {n_fail} FAIL{skip_segment}  in {parsed.total_time:.1f}s"` and test pin `"Result: 2 PASS / 1 FAIL / 1 SKIP"` + `"in 8.3s"` — README mirrors char-for-char | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description                                                                                                  | Status        | Evidence                                                                                                                                                                                                                                                  |
| ----------- | ----------- | ------------------------------------------------------------------------------------------------------------ | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UX-01       | 16-01, 16-02, 16-03, 16-04 | Pre-run digest replaces "N collected, M deselected"                                                          | ✓ SATISFIED   | Renderer + CLI wiring + README docs. README sample blocks now match renderer output. UX-01's literal "defaulting count" wording remains intentionally obsoleted by Phase 16 D-04 (deferred amendment noted in CONTEXT.md). |
| UX-02       | 16-02, 16-03 | `--explain` flag plumbed through Typer, not forwarded to pytest                                              | ✓ SATISFIED   | Flag at `cli.py:404`; wrapper-ownership guard active; README `--explain` table row + example block accurate.                                                                                                                                              |
| UX-03       | 16-01 | Post-run aggregates per-tool PASS/FAIL/SKIP + per-judge reasoning                                                 | ⚠️ PARTIAL    | Per-tool aggregation works; per-judge reasoning surfaces via FAIL-row em-dash. D-11 `--debug` per-judge breakdown block deferred to v1.3 (intentional scope reduction per CONTEXT.md "Claude's Discretion"). Live operator-perceivable behavior flagged for human verification.                |
| UX-04       | 16-01, 16-02 | N=70 readability; digest single-screen; `--explain` ≤ N+5 grep-able                                          | ✓ SATISFIED   | `test_pre_run_digest_height_bounded_at_N_70` passes.                                                                                                                       |
| UX-05       | 16-02, 16-03, 16-04 | `-q` suppresses digest + per-tool rows; only summary line                                                    | ✓ SATISFIED   | `cli.py:532` gates digest; quiet-mode test asserts one-line output; README line 93 now documents the correct emitted Result: shape (the operator-contract artifact that drove the gap closure).                                                          |

All 5 declared requirements present in plan frontmatter. No orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `src/mcp_test_framework/_runner.py` | 742-746 vs 621-625 | Running-set predicate duplicated between `_render_pre_run_digest` and `_compose_pre_run_skip_reasons` | ⚠️ WARNING | WR-02 from code review. Two independent copies invite silent drift if the state-(b) rule ever changes. Not a behavioral bug today. (Unchanged from initial verification — out of Phase 16 gap-closure scope.) |
| `src/mcp_test_framework/cli.py` | 269 | `os.environ["MCPTF_CONFIG_FILE"] = str(resolved)` side-effect mutation | ⚠️ WARNING | WR-01 from code review. Pre-existing pattern flagged at Phase 16 review; affects test isolation under `CliRunner.invoke`. Not introduced by Phase 16. |
| `src/mcp_test_framework/_runner.py` | 758, 762, 764 | `f"{running_n:>2}"` 2-char right-justification breaks at N ≥ 100 | ℹ️ INFO | WR-03 from review. Not exercised in v1.2 (homelab-mcp ≈ 70 tools). Cosmetic-only at large N. |
| `src/mcp_test_framework/_runner.py` | 751, 766 | `Test plan: R*10 contract cases` overcounts when tools have non-default `judges` lists | ℹ️ INFO | WR-04 from review. Phase 16 D-03 accepts this — "Test plan" is the parametrize ceiling, not the runtime count. README could clarify. |
| `tests/framework/test_runner_renderer.py` | 9-16 | Stale docstring references `tests/test_runner_renderer.py` (pre-Phase-15 path) | ℹ️ INFO | WR-05. Recovery command in comment will fail. Cosmetic. |

**Resolved since initial verification:**
- ~~`README.md:84, 92, 228` — Documented `Result:` format differs from actual emitted format (🛑 BLOCKER)~~ → **CLOSED** by Plan 16-04 commit `b1bc5dc`.
- ~~`README.md:81-82, 225-226` — Per-tool row examples missing `passing:` section headers + 2-space indent (⚠️ WARNING)~~ → **CLOSED** by Plan 16-04 commit `ef4c884`.

### Human Verification Required

1. **Per-judge reasoning surfaces in domain UI tail at runtime (UX-03 / SC-3)**

   **Test:** Run `mcp-test-framework run` (default mode, no `--raw`) against a real Ollama instance with a tool whose declared description fails a judge rubric. Verify that the post-run FAIL row shows the failing judge's reasoning text after the em-dash separator.
   **Expected:** Output line of the form `  <tool_name>  ✗ FAIL — clarity score 2/5: <human-readable reasoning>`. The reasoning should be intelligible to an operator (not raw JSON, not a traceback).
   **Why human:** Requires a live `mcp-test-framework run` against a real Ollama judge or a contrived failing tool. The Windows host running this verification lacks `homelab-mcp` on PATH and cannot execute live judge calls. Static evidence (failure_message field threaded from JUnit XML at `_runner.py:849`) confirms the wiring exists; the operator-facing reasoning quality / formatting is not statically verifiable.

   **Note:** This item is carried forward unchanged from the initial verification. Plan 16-04 was a documentation-only gap closure and did not address (nor was it expected to address) this live behavioral check.

### Gaps Summary

**No remaining gaps.** Both 2026-05-11 gaps closed by Plan 16-04:

- **CR-01 BLOCKER (Gap 1) — CLOSED** via commit `b1bc5dc`. README.md lines 85, 93, 230 now mirror `_render_summary_line` at `_runner.py:898` char-for-char (including the double-space-before-`in` and the conditional `SKIP` segment notation `[/ S SKIP]`). Verified via 6 grep gates (`Result: 20 PASS / 0 FAIL / 560 SKIP  in 4.3s` count = 2; `Result: N PASS / M FAIL [/ S SKIP]  in T.Ts` count = 1; old comma-separated lowercase forms count = 0).
- **IN-02 WARNING (Gap 2) — CLOSED** via commit `ef4c884`. README.md lines 81-83 and 226-228 now show flush-left `passing:` section header + 2-space-indented rows, matching `_render_per_tool_rows` at `_runner.py:866-870`. Verified via 5 grep gates (`passing:` header at lines 81 and 226; indented rows at 82/83 and 227/228; old flush-left forms count = 0). Adjacent prose at line 244 reworded `560 skipped cases` → `560 SKIP cases` for terminology consistency.

`git diff --stat HEAD~3..HEAD` confirms only README.md (20 lines changed) plus orchestrator artifacts (STATE.md, ROADMAP.md, 16-04-SUMMARY.md) were touched — no source code or test changes, exactly as Plan 16-04 prescribed.

**Status: human_needed.** All 13 must-have truths now pass automated verification (12 fully VERIFIED + 1 intentionally PARTIAL by design per CONTEXT.md D-11 deferral to v1.3). The one outstanding human-verification item (live Ollama judge run for UX-03 reasoning surface) is unchanged from the initial verification and is unrelated to the gap closure. Phase 16 cannot be marked `passed` until the live judge check is exercised against a real `homelab-mcp` + Ollama environment.

**Note on env_note:** The pre-existing stale `_preflight` autouse fixture guard (`src/mcp_test_framework/fixtures.py:108-125` checking `tests/unit/` instead of `tests/framework/unit/` after Phase 15's directory rename) prevents end-to-end test execution on this verification host. This is a Phase 15 residue, not a Phase 16 regression — surfaced here as a follow-up note but NOT counted as a Phase 16 gap. The 9 pre-existing test failures catalogued in `deferred-items.md` are similarly out-of-scope for Phase 16.

---

_Verified: 2026-05-12_
_Verifier: Claude (gsd-verifier)_
_Re-verification: gaps closed by Plan 16-04 (commits b1bc5dc, ef4c884, 7df134b)_
