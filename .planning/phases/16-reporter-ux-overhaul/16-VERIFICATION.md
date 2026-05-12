---
phase: 16-reporter-ux-overhaul
verified: 2026-05-11T00:00:00Z
status: gaps_found
score: 11/13 must-haves verified
overrides_applied: 0
gaps:
  - truth: "README.md's -q description matches Phase 16 D-09 (suppresses digest + per-tool rows; emits only the Result: line)"
    status: failed
    reason: "README documents the Result: summary line as `Result: N passed, M failed, S skipped` (lowercase verbs, comma-separated, no timing). Actual emitted format from `_render_summary_line` at src/mcp_test_framework/_runner.py:898 is `Result: N PASS / M FAIL [/ S SKIP]  in T.Ts` (uppercase verbs, slash-separated, includes timing). A CI consumer following the README literally to grep `passed,` / `failed,` / `skipped` will fail to match the actual output. The `-q` table row at README:92 quotes the wrong format an operator would parse for a single-line CI summary."
    artifacts:
      - path: "README.md:84"
        issue: "Sample output block shows `Result: 20 passed, 0 failed, 560 skipped` — not what the renderer emits."
      - path: "README.md:92"
        issue: "`-q` flag row references `Result: N passed, M failed, S skipped` — wrong format for the documented CI grep target."
      - path: "README.md:228"
        issue: "Second sample output block (under Sample green run) shows the same incorrect Result: format."
    missing:
      - "Update README.md:84, 92, 228 to use the actual emitted format `Result: N PASS / M FAIL / S SKIP  in T.Ts` — OR update the prose so operators parse on `Result:` prefix only without quoting the verb shape."
      - "Same root cause flagged as CR-01 BLOCKER in 16-REVIEW.md (2026-05-11); not addressed by any subsequent commit before phase close-out."
  - truth: "README's post-run per-tool rows example matches the renderer's actual output shape"
    status: partial
    reason: "Per-tool rows in the README samples (README.md:81-82, 109-110, 225-226) are rendered flush-left without the `failures:` / `skipped:` / `passing:` section headers and without the 2-space leading indent that `_render_per_tool_rows` at _runner.py:843-870 actually emits. The actual output is `passing:\\n  <tool>  ✓ PASS` (verified at runtime); the README shows `<tool>  ✓ PASS` flush-left, no section header. This is the IN-02 code-review item; minor severity but operator-facing surface and is the must_have artifact-shape that README documents."
    artifacts:
      - path: "README.md:81-82"
        issue: "Per-tool rows rendered without section headers and without 2-space indent."
      - path: "README.md:109-110"
        issue: "Same shape mismatch in --explain example."
      - path: "README.md:225-226"
        issue: "Same shape mismatch in 'Sample green run' block."
    missing:
      - "Insert `passing:` (or `failures:`/`skipped:` as appropriate) section headers before each row block and indent rows by 2 spaces to match actual renderer output."
human_verification:
  - test: "Per-judge reasoning surfaces in domain UI tail at runtime (UX-03 / SC-3)"
    expected: "When a contract test fails because a judge returns score < 4, the FAIL row in the post-run rows shows the judge's reasoning text after the em-dash separator (`  <tool>  ✗ FAIL — clarity score 2/5: <reasoning>`)."
    why_human: "Requires a live `mcp-test-framework run` against a real Ollama judge or a contrived failing tool — preflight requires `homelab-mcp` on PATH; cannot be exercised on this verification host. Static evidence (failure_message field threaded from JUnit XML at _runner.py:849) suggests it works, but the operator-facing reasoning quality / formatting is not statically verifiable."
---

# Phase 16: Reporter UX overhaul Verification Report

**Phase Goal:** An operator preparing to run the framework sees an unambiguous pre-run digest of what will and won't execute (eliminating pytest's misleading "N collected, M deselected" framing), and a post-run aggregation in the same domain language. Output stays single-screen-readable at homelab-mcp scale (~70 tools).
**Verified:** 2026-05-11T00:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria + PLAN frontmatter must-haves)

| #   | Truth                                                                                                      | Status     | Evidence                                                                                                                                                                  |
| --- | ---------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | SC-1 / UX-01: Pre-run digest emitted before pytest with server / discovered / running / skipping / judges / test-plan | ✓ VERIFIED | `_render_pre_run_digest` at `_runner.py:703-773` emits 8-line block + blank; called from `cli.py:533` BEFORE `run_pytest_subprocess` at `cli.py:541`. Runtime smoke produces canonical banner + `MCP server:` / `Discovered:` / `Running:` / `Skipping:` / `Judges:` / `Test plan:` rows. Banner string `"=" * 40` (40 equals signs) locked. |
| 2   | SC-2 / UX-02+UX-04: `--explain` produces grep-able N+5-line output at N=70                                  | ✓ VERIFIED | `_render_skipped_tools_explain` at `_runner.py:776-812` emits `Skipping (N):` header + N alphabetized lines + blank = N+2 ≤ N+5. `--explain` registered at `cli.py:404-414`; wired at `cli.py:538-539`. Runtime smoke at N=70 confirmed 11 split chunks (= 10 content lines + trailing newline) for the digest; explain block is N+2 lines beyond. Em-dash U+2014 separator present in source + runtime output. |
| 3   | SC-3 / UX-03: Post-run aggregates per-tool PASS/FAIL/SKIP and per-judge reasoning; v1.1 `_reporter.py` subsumed | ⚠️ PARTIAL | `_render_per_tool_rows` at `_runner.py:820-870` emits FAIL → SKIP → PASS sections alphabetized within each. FAIL rows append `failure_message` (which carries judge reasoning) after em-dash. `_reporter.py` already subsumed by Phase 14. **D-11 `--debug` per-judge breakdown block explicitly deferred to v1.3** per CONTEXT.md "Claude's Discretion" — this is an intentional in-phase scope reduction. The phase's interpretation: per-judge reasoning visible via FAIL-row em-dash (today) satisfies UX-03's "aggregates per-judge reasoning into the domain UI's tail"; the per-judge breakdown block under `--debug` is the v1.3 polish. Live behavioral confirmation flagged for human verification. |
| 4   | SC-4 / UX-05: `-q` / `--quiet` suppresses digest + per-tool rows; only summary line                         | ✓ VERIFIED | `cli.py:532` gates `_render_pre_run_digest` + `_render_skipped_tools_explain` on `not quiet`. `test_run_quiet_emits_exactly_one_line` (`test_runner_verbosity.py:301`) asserts exactly one non-empty `Result:` line. Test passes (37/37 pass in pre-run-digest + explain + verbosity suites). |
| 5   | SC-5: Digest counts agree with what the runner actually executes                                            | ✓ VERIFIED | `_compose_pre_run_skip_reasons` at `_runner.py:602-628` delegates to `_compose_unparametrized_skips_from_config` (same Phase 14 composer used post-run). Running set computed from same state-b predicate (`name in tools_config and not getattr(tools_config[name], "skip", False)`) used by both digest and post-run composer call. `test_cases_per_contract_tool_matches_actual_parametrize_count` AST-counts the contract file and asserts equality with `CASES_PER_CONTRACT_TOOL` constant — drift guard prevents silent skew. WR-02 (duplicated predicate in two places) is a maintenance smell, not a behavioral bug — both copies produce identical results today. |
| 6   | PLAN 16-01: `CASES_PER_CONTRACT_TOOL: int = 10` module-level constant in `_runner.py`                       | ✓ VERIFIED | `_runner.py:313`: `CASES_PER_CONTRACT_TOOL: int = 10`. Importable; runtime probe confirms value 10. |
| 7   | PLAN 16-01: `_render_pre_run_digest`, `_render_skipped_tools_explain`, `_compose_pre_run_skip_reasons` exist at module scope | ✓ VERIFIED | All three symbols at `_runner.py:602, 703, 776`. Importable. Smoke-test outputs match locked shape. |
| 8   | PLAN 16-01: `render_domain_ui` no longer calls `_render_header`                                             | ✓ VERIFIED | `render_domain_ui` at `_runner.py:908-928` calls `_render_per_tool_rows` + `_render_summary_line` only; no `_render_header` invocation. Runtime smoke confirms `"MCP Test Framework" not in render_domain_ui(...) output`. |
| 9   | PLAN 16-01: Digest height ≤ 10 lines regardless of N (D-12, capsys test at N=70)                            | ✓ VERIFIED | `test_pre_run_digest_height_bounded_at_N_70` passes; runtime N=70 probe yields 11 split chunks = 10 content lines + trailing newline. |
| 10  | PLAN 16-02: `--explain` Typer flag registered with help text mentioning `--raw` and `-q`                    | ✓ VERIFIED | `cli.py:404-414` registers `--explain` with help text covering both `--raw` and `-q` / `--quiet`. `uv run mcp-test-framework run --help` confirms the flag appears with the documented composition prose. |
| 11  | PLAN 16-02: `--explain` is wrapper-owned; never forwarded to pytest                                         | ✓ VERIFIED | `_build_pytest_args` (read-only per Plan 16-02 scope) does not reference `--explain`. Subprocess stub in `test_runner_explain.py` enforces `assert "--explain" not in argv` on every test invocation. |
| 12  | PLAN 16-02: Phase 14 D-14 negative test inverted to assert `--explain` IS in help                           | ✓ VERIFIED | `test_run_help_lists_explain_phase16` at `test_runner_verbosity.py:139` (renamed from `test_run_help_does_not_list_explain`); assertion inverted. Companion positive test `test_run_help_lists_explain_flag` lives at `test_runner_explain.py:83`. |
| 13  | PLAN 16-03: README documents `--explain` + pre-run digest + `-q` semantics correctly                        | ✗ FAILED   | README has `--explain` (12 occurrences) and a digest example block — but the `Result:` line is wrong format. Documented: `Result: N passed, M failed, S skipped`; actual: `Result: N PASS / M FAIL [/ S SKIP]  in T.Ts`. CI consumers following the README cannot grep what the renderer emits. Same root cause flagged as CR-01 BLOCKER in 16-REVIEW.md. See Gaps Summary. |

**Score:** 11/13 truths verified; 1 partial (UX-03 — scope-reduced by design), 1 failed (README format drift).

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/mcp_test_framework/_runner.py` | renderer additions (digest, explain, constant, wrapper); call-site change | ✓ VERIFIED | All four symbols present; `render_domain_ui` shrunk to rows + summary; `_render_header` preserved as internal helper per Plan 16-01 SUMMARY (IN-05 review note: candidate for deletion if no future plan uses it). |
| `src/mcp_test_framework/cli.py` | `--explain` Typer flag; pre-run digest pipeline; `-q` gating | ✓ VERIFIED | Flag at `:404`, pre-run wiring at `:518-539`, `not quiet` gate at `:532`. Pre-run `RenderContext` built BEFORE subprocess; post-parse `RenderContext` rebuilt with `parsed.total_cases` for summary. |
| `tests/framework/unit/test_runner_pre_run_digest.py` | digest shape + constant pin + AST drift guard (≥ 80 lines) | ✓ VERIFIED | 211 lines, 11 test functions present (constant pin, AST parametrize match, small-N + N=70 height bounds, judge empty-list fallback, 4 composer state-(a)/(c) tests). |
| `tests/framework/unit/test_runner_explain.py` | end-to-end `--explain` tests + composition + wrapper-ownership guard (≥ 80 lines) | ✓ VERIFIED | 290 lines, 11 test functions present (help registration, alphabetized listing, post-digest pre-pytest ordering, `-q --explain` no-op, `--raw --explain` bypass, `--with-framework` suffix, default mode hint suppression, double-banner check). |
| `tests/framework/test_runner_verbosity.py` | `-q` parity tests appended; Phase 14 negative test inverted | ✓ VERIFIED | `test_run_help_lists_explain_phase16` (renamed in place), `test_run_quiet_emits_exactly_one_line`, `test_run_quiet_suppresses_pre_run_digest` all present. |
| `README.md` | pre-run digest + `--explain` + `-q` documented | ⚠️ ORPHANED | All Phase 16 surface is documented, but the documented `Result:` summary line format does not match the actual emitted format (CR-01 BLOCKER). Artifact exists and is wired; content drift makes the documentation a stub for the CI-grep use case. |
| `docs/mcp_test_framework_mvp_spec.md` | spec audited, intentionally unchanged | ✓ VERIFIED | Plan 16-03 documents zero-diff justification (spec is silent on operator output shape; no `--explain` flag-matrix to amend; no obsolete pytest collection framing to remove). Acceptable per plan Step 7. |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `cli.py:run` | `_runner._render_pre_run_digest(pre_run_ctx)` | direct call gated on `not quiet`, BEFORE `run_pytest_subprocess` | ✓ WIRED | `cli.py:532-537` gates on `not quiet`, calls at `:533`; `run_pytest_subprocess` follows at `:541`. Pattern `if not quiet:\\n    _runner._render_pre_run_digest` matches. |
| `cli.py:run` | `_runner._render_skipped_tools_explain(pre_run_ctx)` | direct call gated on `explain`, after digest | ✓ WIRED | `cli.py:538-539`. Pattern `if explain:\\n    _runner._render_skipped_tools_explain` matches. |
| `_render_pre_run_digest` | `RenderContext` fields (discovered_tools, tools_config, judges, server_cmd) | function arg `ctx` | ✓ WIRED | All four fields accessed at `_runner.py:739, 742, 745, 749, 750, 756`. |
| `_render_skipped_tools_explain` | `_compose_unparametrized_skips_from_config` | via `_compose_pre_run_skip_reasons` wrapper | ✓ WIRED | `_runner.py:798` calls `_compose_pre_run_skip_reasons`, which at `:626` delegates to `_compose_unparametrized_skips_from_config(...)`. NOTE: wrapper passes the computed `running` set as `ran_tools` (deviation from plan's literal `ran_tools=set()` spec; rationale documented in Plan 16-01 SUMMARY Deviations §1 — passes smoke test that pure `ran_tools=set()` would fail). Behaviorally correct. |
| `render_domain_ui` | `_render_per_tool_rows` + `_render_summary_line` ONLY | banner call-site at former line 773 deleted | ✓ WIRED | `_runner.py:908-928` calls only the two row/summary renderers. No `_render_header` invocation. Smoke confirms `"MCP Test Framework" not in render_domain_ui(...) output`. |
| `test_runner_pre_run_digest.py::test_cases_per_contract_tool_matches_actual_parametrize_count` | `tests/contract/test_mcp_tool_contract.py` | `ast.parse` filtering `test_*` async/sync defs | ✓ WIRED | Test at `test_runner_pre_run_digest.py:65`; passes — AST count equals constant `10`. Drift guard active. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `_render_pre_run_digest` | `discovered_tools`, `tools_config`, `judges`, `server_cmd` | `ctx: RenderContext` populated at `cli.py:518-524` from real `_discover_tools_for_run(cfg)` and `_load_config(config)` outputs | ✓ Yes — live MCP discovery + parsed YAML | ✓ FLOWING |
| `_render_skipped_tools_explain` | `skipped` dict | `_compose_pre_run_skip_reasons` → `_compose_unparametrized_skips_from_config` over real `discovered_tools` + `cfg.tools` | ✓ Yes | ✓ FLOWING |
| `_render_per_tool_rows` (unchanged) | `parsed.per_tool` | `parse_junit_xml(tmp_xml)` after live `run_pytest_subprocess` | ✓ Yes — Phase 14 surface unchanged | ✓ FLOWING |
| `_render_summary_line` | `parsed.per_tool`, `parsed.total_time`, `unparam_skips` | live JUnit XML | ✓ Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior                                                                                                  | Command                                                                                                                                                                                                              | Result                                                                                  | Status |
| --------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ------ |
| `--explain` flag registered in `run --help`                                                               | `uv run mcp-test-framework run --help`                                                                                                                                                                                | Lists `--explain` with composition prose covering `--raw` and `-q`                      | ✓ PASS |
| `CASES_PER_CONTRACT_TOOL` importable + equals 10                                                          | `uv run python -c "from mcp_test_framework._runner import CASES_PER_CONTRACT_TOOL; assert CASES_PER_CONTRACT_TOOL == 10"`                                                                                            | `CASES_PER_CONTRACT_TOOL = 10`                                                          | ✓ PASS |
| `_render_pre_run_digest` at N=70 emits ≤ 10 content lines                                                 | runtime probe with 70 discovered tools, 2 running                                                                                                                                                                    | 11 split chunks (= 10 content + trailing newline). Banner present, no t02 inline.       | ✓ PASS |
| `_render_skipped_tools_explain` emits alphabetized em-dash lines                                          | runtime probe with skipped `[alpha, gamma]`                                                                                                                                                                          | `Skipping (2):` header, alpha < gamma, U+2014 separator confirmed                       | ✓ PASS |
| `render_domain_ui` no longer emits banner                                                                 | runtime probe                                                                                                                                                                                                        | Output does NOT contain `MCP Test Framework`; `Result: 1 PASS / 0 FAIL  in 4.3s` present | ✓ PASS |
| Phase 16 test suites pass                                                                                 | `MCPTF_CONFIG_FILE=config-v2-worktree.yaml uv run pytest tests/framework/unit/test_runner_pre_run_digest.py tests/framework/unit/test_runner_explain.py tests/framework/test_runner_verbosity.py -q`                | 37 passed in 4.97s                                                                       | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description                                                                                                  | Status        | Evidence                                                                                                                                                                                                                                                  |
| ----------- | ----------- | ------------------------------------------------------------------------------------------------------------ | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UX-01       | 16-01, 16-02, 16-03 | Pre-run digest replaces "N collected, M deselected"                                                          | ✓ SATISFIED   | `_render_pre_run_digest` + cli.py wiring + README documents the digest. NOTE: REQUIREMENTS.md UX-01 lists `defaulting count` as a third bucket — Plan 16 D-04 intentionally drops this (two buckets only); REQUIREMENTS.md wording amendment deferred (CONTEXT.md §deferred line 204). |
| UX-02       | 16-02, 16-03 | `--explain` flag plumbed through Typer, not forwarded to pytest                                              | ✓ SATISFIED   | Flag at `cli.py:404`; wrapper-ownership guard in test stub `assert "--explain" not in argv`; `_build_pytest_args` unchanged.                                                                                                                              |
| UX-03       | 16-01 | Post-run aggregates per-tool PASS/FAIL/SKIP + per-judge reasoning                                                 | ⚠️ PARTIAL    | Per-tool aggregation works; per-judge reasoning surfaces via FAIL-row em-dash. D-11 `--debug` per-judge breakdown block deferred to v1.3 (intentional scope reduction). Live operator-perceivable behavior flagged for human verification.                |
| UX-04       | 16-01, 16-02 | N=70 readability; digest single-screen; `--explain` ≤ N+5 grep-able                                          | ✓ SATISFIED   | `test_pre_run_digest_height_bounded_at_N_70` passes (digest ≤ 10 content lines). `_render_skipped_tools_explain` produces N+2 lines.                                                                                                                       |
| UX-05       | 16-02, 16-03 | `-q` suppresses digest + per-tool rows; only summary line                                                    | ✓ SATISFIED   | `cli.py:532` gates digest; `test_run_quiet_emits_exactly_one_line` asserts exactly one non-empty line. README documents the gate (but documented Result-line shape is wrong — see CR-01 BLOCKER below).                                                  |

All 5 declared requirements present in plan frontmatter. No orphaned requirements — REQUIREMENTS.md maps UX-01..05 to Phase 16, all five are claimed by at least one plan.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `README.md` | 84, 92, 228 | Documented `Result:` format differs from actual emitted format | 🛑 BLOCKER | CI consumers using documented format will fail to parse output. This is the must_have truth "README's -q description matches Phase 16 D-09" — the documented format is part of the operator contract. |
| `README.md` | 81-82, 109-110, 225-226 | Per-tool row examples missing `failures:`/`skipped:`/`passing:` section headers + 2-space indent | ⚠️ WARNING | Operators may not recognize their actual output as matching the documented sample. Cosmetic mismatch; renderer still works correctly. (Code-review IN-02.) |
| `src/mcp_test_framework/_runner.py` | 742-746 vs 621-625 | Running-set predicate duplicated between `_render_pre_run_digest` and `_compose_pre_run_skip_reasons` | ⚠️ WARNING | WR-02 from code review. Two independent copies invite silent drift if the state-(b) rule ever changes. Not a behavioral bug today. |
| `src/mcp_test_framework/cli.py` | 269 | `os.environ["MCPTF_CONFIG_FILE"] = str(resolved)` side-effect mutation | ⚠️ WARNING | WR-01 from code review. Pre-existing pattern flagged at Phase 16 review; affects test isolation under `CliRunner.invoke`. Not introduced by Phase 16. |
| `src/mcp_test_framework/_runner.py` | 758, 762, 764 | `f"{running_n:>2}"` 2-char right-justification breaks at N ≥ 100 | ℹ️ INFO | WR-03 from review. Not exercised in v1.2 (homelab-mcp ≈ 70 tools). Cosmetic-only at large N. |
| `src/mcp_test_framework/_runner.py` | 751, 766 | `Test plan: R*10 contract cases` overcounts when tools have non-default `judges` lists | ℹ️ INFO | WR-04 from review. Phase 16 D-03 accepts this — "Test plan" is the parametrize ceiling, not the runtime count. README could clarify. |
| `tests/framework/test_runner_renderer.py` | 9-16 | Stale docstring references `tests/test_runner_renderer.py` (pre-Phase-15 path) | ℹ️ INFO | WR-05. Recovery command in comment will fail. Cosmetic. |

### Human Verification Required

1. **Per-judge reasoning surfaces in domain UI tail at runtime (UX-03 / SC-3)**

   **Test:** Run `mcp-test-framework run` (default mode, no `--raw`) against a real Ollama instance with a tool whose declared description fails a judge rubric. Verify that the post-run FAIL row shows the failing judge's reasoning text after the em-dash separator.
   **Expected:** Output line of the form `  <tool_name>  ✗ FAIL — clarity score 2/5: <human-readable reasoning>`. The reasoning should be intelligible to an operator (not raw JSON, not a traceback).
   **Why human:** Requires a live `mcp-test-framework run` against a real Ollama judge or a contrived failing tool. The Windows host running this verification lacks `homelab-mcp` on PATH (per env_note) and cannot execute live judge calls. Static evidence (failure_message field threaded from JUnit XML at `_runner.py:849`) confirms the wiring exists; the operator-facing reasoning quality / formatting is not statically verifiable.

### Gaps Summary

**Two gaps prevent goal achievement, both rooted in documentation drift introduced by Plan 16-03:**

1. **CR-01 BLOCKER — README documents wrong `Result:` summary line format.** The README's sample output blocks (line 84 and line 228) and the `-q` flag table row (line 92) all quote the summary line as `Result: N passed, M failed, S skipped` — lowercase verbs, comma-separated, no timing. But `_render_summary_line` at `_runner.py:898` actually emits `Result: N PASS / M FAIL [/ S SKIP]  in T.Ts` — uppercase verbs, slash-separated, includes timing. Verified at runtime: `Result: 1 PASS / 0 FAIL  in 4.3s`. Test suite pins the actual format at `test_runner_renderer.py:223` (`assert "Result: 2 PASS / 1 FAIL / 1 SKIP" in out`). This blocks the must_have truth "README.md's -q description matches Phase 16 D-09" — the documented format is operator-facing and the documented CI-grep target. CR-01 was flagged in `16-REVIEW.md` (2026-05-11) as BLOCKER and not addressed by any subsequent commit before phase close-out.

2. **IN-02 WARNING — README per-tool row examples render flush-left without section headers.** The README samples at lines 81-82, 109-110, 225-226 show per-tool rows as `<tool>  ✓ PASS` flush-left, with no `passing:` (or `failures:` / `skipped:`) section header preceding them. Actual renderer at `_runner.py:843-870` emits a section header followed by 2-space-indented rows: `passing:\n  <tool>  ✓ PASS`. This is the IN-02 review item; less load-bearing than CR-01 but still operator-facing.

**Root cause:** Plan 16-03's `<action>` Step 2 prescribed a canonical example output block that did not match the actual renderer output (the plan author appears to have invented the `Result:` shape rather than reading `_render_summary_line`). The executor copied the plan's example verbatim into README. No reconciliation pass against the actual renderer occurred.

**Recommended fix:** Update README.md to mirror actual emitted output. Either:

- Replace `Result: 20 passed, 0 failed, 560 skipped` with `Result: 20 PASS / 0 FAIL / 560 SKIP  in <T>s` (matching the renderer), AND insert `passing:` (or per-verdict) section headers + 2-space indents before per-tool row blocks; OR
- Add explicit prose in the README's `-q` section explaining that operators should grep on the `Result:` prefix only without quoting the verb-shape — and drop the misleading sample.

The fix is mechanical and isolated to README.md. The code is correct; only the documentation is wrong. This should land as a single `docs(16-04)` follow-up commit before the v1.2 milestone closes, or be tracked as an explicit known-gap in the v1.2 release notes.

**Note on env_note:** The pre-existing stale `_preflight` autouse fixture guard (`src/mcp_test_framework/fixtures.py:108-125` checking `tests/unit/` instead of `tests/framework/unit/` after Phase 15's directory rename) prevents end-to-end test execution on this verification host. This is a Phase 15 residue, not a Phase 16 regression — surfaced here as a follow-up note but NOT counted as a Phase 16 gap. The 9 pre-existing test failures catalogued in `deferred-items.md` (test_tool_config × 4, test_cli_errors × 1, test_migration_doc × 4) are similarly out-of-scope for Phase 16.

---

_Verified: 2026-05-11_
_Verifier: Claude (gsd-verifier)_
