# Phase 16: Reporter UX overhaul - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace pytest's misleading "N collected, M deselected" framing with a domain-shaped **pre-run digest** emitted BEFORE the subprocess pytest call, plumb a `--explain` Typer flag that expands the digest's `Skipping (N)` hint into one line per skipped tool, and confirm `-q` quiet-mode parity. Phase 14's post-run per-tool rows + summary line stays — Phase 16 moves the *header* portion from post-run to pre-run and adds the `--explain` expansion.

**In scope:** UX-01..05 (5 requirements). Pre-run digest renderer in `_runner.py`; `--explain` Typer flag in `cli.py:run`; a pure pre-run skip-reason composer (state-(a)/(c) reasons computable from `cfg.tools` + discovered tools, no pytest needed); a `cases_per_tool` module constant in `_runner.py` for the pre-run "Test plan" line; quiet-mode verification that `-q` suppresses both digest and `--explain` output; tests pinning the digest shape, `--explain` shape, and `-q` parity.

**Out of scope:**
- **N=70 polish for the `Running:` inline names list.** Operator-selected scopes are small in practice (homelab-mcp's safe-by-default selection enables 2 tools out of 58). Long-running-list wrapping/truncation is deferred — the `Skipping (N) (use --explain to list)` hint already solves the N=70 case for the high-cardinality bucket. If a future homelab grows past ~10 selected tools and the digest becomes visually unwieldy, revisit in v1.3.
- **Per-judge scores on PASS rows** (SEED-011 §2 mockup `✓ PASS (clarity 5/5)`). Phase 16 keeps PASS rows minimal (`✓ PASS`). Per-judge breakdown lives under `--debug` only — a small extension to Phase 14's `render_debug_appendix` that itemizes per-tool judge scores parsed from JUnit XML before the raw-stdout block.
- **JUnit XML embedding of the digest.** Digest is stdout-only; JUnit XML stays Phase 14's pytest-native shape (testsuite/testcase elements). CI consumers parse JUnit normally and read stdout for the operator-shaped view.
- **"Defaulting" bucket** (REQUIREMENTS.md UX-01 mentions it; SEED-008 mockup shows `Defaulting: 0`). Dropped in this phase — see D-04 below. The (a)/(c) state distinction lives in the per-tool reason text under `--explain`, not in headline counts. UX-01's wording becomes obsolete on this point.
- **Live per-tool progress streaming** (SEED-011 §5 v1.3 candidate). Batch render unchanged.
- **`rich` library upgrade.** Stdlib + ANSI stays. Phase 14 D-06 carried forward.

**Hard dependency:** Phase 14 must be complete (it is — shipped 2026-05-11). Phase 16 modifies `_runner.py`'s `_render_header` (split into a pre-run digest function) and adds new functions; it does NOT touch Phase 14's `parse_junit_xml`, `_render_per_tool_rows`, `_render_summary_line`, `_compose_unparametrized_skips_from_config`, or the subprocess/exit-code spine.

**Hard dependency:** Phase 15 must be complete (it is — shipped 2026-05-12). The contract surface `tests/contract/` is the operator default; the pre-run digest's "Test plan: N contract cases" line counts contract cases only under default scope. With `--with-framework`, append "+ framework self-tests" (no number, per D-03 below).

**Sequencing note:** This is the final phase of v1.2 "Operator-First Design". After Phase 16 lands, v1.2 closes.

</domain>

<decisions>
## Implementation Decisions

### Pre-run vs post-run structure (UX-01)
- **D-01: Digest BEFORE pytest. Post-run prints per-tool rows + summary ONLY — no second header.** The wrapper has all the digest's inputs available pre-run: `_discover_tools_for_run(cfg)` (already called at `cli.py:490`), `cfg.tools` (the allowlist), `cfg.mcp_server.command/args`, and the union of judges across configured tools. Move Phase 14's `_render_header` content into a new function `_render_pre_run_digest(ctx)` and call it BEFORE `run_pytest_subprocess`. Drop the `_render_header` call site inside `render_domain_ui`; that function shrinks to `per_tool_rows + summary_line` only.
- **D-02:** **Crash semantics.** If pytest exits without writing the JUnit XML (Phase 14 D-16), the operator already saw the digest before the crash — `_dispatch_default_mode_or_error` then surfaces the operator-tone error pointing at `--raw`. No regression; the digest is more useful pre-crash than post-crash anyway.

### Test-plan count source (UX-01)
- **D-03: Compute pre-run as `running_tools × cases_per_tool`.** Cases-per-tool = 10 (5 schema validators + 4 judge dimensions + 1 output conformance, per the parametrized contract in `tests/contract/test_mcp_tool_contract.py`). Add `CASES_PER_CONTRACT_TOOL: int = 10` as a module constant in `_runner.py`; a unit test in `tests/framework/unit/test_runner_pre_run_digest.py` pins the constant and a separate test counts the parametrized cases in the contract file and asserts equality (so the constant cannot silently drift from the test it represents). Under default scope: `Test plan: 20 contract cases` (2 running × 10). With `--with-framework`: `Test plan: 20 contract cases + framework self-tests` (no number — framework count is high-churn and not worth pre-computing). The post-run summary line still uses `parsed.total_cases` from JUnit XML for the real number.

### "Defaulting" bucket (UX-01)
- **D-04: Two buckets only: `Running` and `Skipping`. Drop `Defaulting` from the digest.** SEED-008's mockup and REQUIREMENTS.md UX-01 wording include `Defaulting:` as a third count; the three Phase-13 states (a unlisted / b listed / c skip:true) collapse cleanly into two operator-perceivable buckets where the (a)/(c) distinction is visible in the per-tool reason text under `--explain`. This is a deliberate divergence from UX-01's literal wording — note the obsolescence in the verification step so the requirement is read as "running count, skipping count, judges, test-plan totals". The locked skip-reason constants (`"not selected in config"` for state (a), `"explicit skip in config"` for state (c), Phase 13 D-12) remain unchanged — they carry the bucket distinction inside `--explain` output, not in headline counts.

### --explain output (UX-02)
- **D-05: `--explain` expands ONLY the `Skipping (N)` hint.** Format: one line per skipped tool, `  <tool_name>  — <reason>`, sorted alphabetically. Skip reasons sourced from `_compose_unparametrized_skips_from_config(discovered_tools, cfg.tools, ran_tools=∅)` (Phase 14's existing pure composer, called with `ran_tools=∅` pre-run since pytest hasn't run yet). The `Running:` line and the `Judges:` line stay as-is — no per-tool judges-per-tool expansion table. Per-tool judges visibility is deferred (would land under `--debug` or a separate v1.3 flag if requested).
- **D-06: `--explain` renders INLINE AFTER the digest, BEFORE pytest runs.** Output order: digest header (`=====` lines through `Test plan: N`) → blank line → `Skipping (N):` block with sorted one-line-per-tool list → blank line → pytest runs silently → per-tool rows + summary line. Operator sees the full pre-run state in one scroll-up; no need to scroll past results to find the explanation.
- **D-07: `--explain` is OWNED by the Typer wrapper (`cli.py:run`), not forwarded to pytest.** Phase 14 D-14 deferred the flag itself to Phase 16; this phase registers it. The flag's only effect is to call the new `_render_skipped_tools_explain(ctx)` function inside `cli.py:run` between the digest and the subprocess. The flag is NOT in `_build_pytest_args` — pytest never sees it.
- **D-08: `--explain` composes orthogonally with `--with-framework`, `--debug`, `--raw`, `-q`, and `--junit-xml=PATH`.** Composition rules:
  - `--explain --with-framework`: explain expansion lists skipped tools (state a/c) on the SUT side; framework tests are unaffected (they have no per-tool skip semantics).
  - `--explain --raw`: no digest, no explain output. `--raw` bypasses the domain UI entirely (Phase 14 D-11); `--explain` is a wrapper-side flag. The Typer help text for `--explain` must say "ignored under `--raw`".
  - `--explain --debug`: explain renders pre-run; debug appendix renders post-run after per-tool rows + summary. Both surfaces visible.
  - `-q --explain`: quiet wins. Per D-09, `-q` suppresses the digest AND `--explain` expansion AND per-tool rows. Only the summary line prints. UX-05 trumps UX-02.
  - `--explain --junit-xml=PATH`: orthogonal; XML emission unchanged.

### Quiet mode (UX-05)
- **D-09: `-q` suppresses the pre-run digest AND `--explain` expansion AND per-tool rows.** Only the post-run summary line emits. Mirrors Phase 14 D-12's `render_summary_only` shape; extend it so the pre-run path also short-circuits when `quiet=True`. Implementation: in `cli.py:run`, gate the `_render_pre_run_digest(ctx)` call and the `_render_skipped_tools_explain(ctx)` call on `not quiet`. The `render_summary_only(parsed, ctx)` call after pytest stays as today. UX-05's "mirrors v1.1's quiet-mode parity" is satisfied if `mcp-test-framework run -q` emits exactly one line (the `Result: …` line).

### Per-tool row layout (UX-03)
- **D-10: PASS rows stay minimal: `  <tool_name>  ✓ PASS`. FAIL rows stay `  <tool_name>  ✗ FAIL — <reason>` (Phase 14 D-08). SKIP rows stay `  <tool_name>  – SKIP — <reason>`.** No per-judge scores on PASS rows. Phase 14's `_render_per_tool_rows` is untouched. UX-03's "aggregates per-judge reasoning into the domain UI's tail" is satisfied by the existing failure-reasoning surface (the failing judge's reasoning is what comes out of `JudgeResult.reasoning` and gets surfaced verbatim in `<failure message=...>` then rendered after the em-dash on the FAIL row).
- **D-11: `--debug` gains a per-judge breakdown block.** Extend `render_debug_appendix` to emit, BEFORE the existing `--- raw pytest output ---` block, a `--- per-judge scores ---` block listing for each tool with FAIL: `<tool_name>: <judge_name> <score>/5 — <reasoning>` (one line per judge per failing tool). Skipped under `--debug` only — does not appear in default output. Source: extract from JUnit `<failure message="…">` text (the existing surface) or from per-test parametrize IDs if the contract tests use `[<tool>-<judge>]` (verify during planning). If the scores aren't easily parseable from the existing XML, this becomes Claude's discretion: defer to a v1.3 phase rather than touching the contract test's failure-message shape.

### N=70 readability (UX-04)
- **D-12: Digest height is bounded.** Lines: 3 (banner) + 1 (server) + 1 (discovered) + 1 (running) + 1 (skipping) + 1 (judges) + 1 (test plan) + 1 (closing banner) + 1 (blank) = ≤ 10 lines regardless of N. The `Skipping:` line uses the `(use --explain to list)` hint — never inline expansion. The `Running:` line stays inline (status quo from Phase 14); operator scopes are small in practice (homelab-mcp's safe-by-default config selects 2 of 58, not 50). The `Judges:` line is the union of judges across all configured tools — typically 1-3 across the framework; bounded by the rubric set (`src/mcp_test_framework/rubrics.py`).
- **D-13: `--explain` output footprint = N+5 lines max at N=70.** Format: 1 header line `Skipping (N):` + N tool lines + 1 trailing blank ≈ N+2. Each tool line is `  <tool_name>  — <reason>` and stays grep-able (one tool per line; no wrapping). Reason text may be long (e.g., `"side effects on homelab inventory: bulk discovery writes"`); UX-04 allows lines to wrap visually if a terminal narrows below the reason's width but the data is still grep-friendly. Optional column-aligned name padding (`tool_name.ljust(name_width)`) for visual scan-ability — same pattern as Phase 14's `_render_per_tool_rows`.

### Reuse, no new modules
- **D-14: No new module file.** All new functions land in `src/mcp_test_framework/_runner.py` next to the existing renderer:
  - `_render_pre_run_digest(ctx: RenderContext, file=None) -> None` — the new pre-run digest function (replaces post-run `_render_header` usage; the old function may be kept as an internal helper or deleted depending on test coupling, but its CALL SITE inside `render_domain_ui` is removed per D-01).
  - `_render_skipped_tools_explain(ctx: RenderContext, file=None) -> None` — the `--explain` expansion.
  - `CASES_PER_CONTRACT_TOOL: int = 10` — module constant for the pre-run test-plan count (D-03).
  - `_compose_pre_run_skip_reasons(discovered_tools, tools_config) -> dict[str, str]` — thin wrapper around `_compose_unparametrized_skips_from_config(discovered_tools, tools_config, ran_tools=set())` to make the pre-run intent explicit at the call site.

### Claude's Discretion
- **Plan ordering within Phase 16.** Suggested sequence: (1) Module constants + pre-run digest renderer + skip-reason composer wrapper in `_runner.py`, with unit tests against fixture configs at small N and N=70 to pin the layout (UX-01, UX-04). (2) `--explain` Typer flag in `cli.py:run` + the explain renderer + composition tests (`--explain --raw` is a no-op; `--explain -q` is a no-op; `--explain --with-framework` works) (UX-02). (3) `-q` quiet-mode pre-run suppression + a parity test that `-q` emits exactly one line (UX-05). (4) `--debug` per-judge breakdown block — only if XML extraction is straightforward (otherwise defer with a note) (UX-03 partial). (5) Documentation refresh: README.md "Run the test suite" section, `docs/mcp_test_framework_mvp_spec.md` if it references the post-run header.
- **Whether to delete the old `_render_header` function entirely** or keep it as a tested internal helper for renderer-shape regression tests. Recommend: rename to `_render_post_run_recap` if kept, OR delete and rename `_render_pre_run_digest` to `_render_digest` since there's only one digest now. Either is defensible; the test suite's existing reporter-shape regressions should pin whichever name lands.
- **Where the `Test plan: N contract cases + framework self-tests` text wraps** when `--with-framework` and N is wide. Single-line is fine for v1.2.
- **Exact format of the `--debug` per-judge breakdown** if D-11 implementation lands. Suggest matching SEED-011 §2 mockup: `<tool>: clarity 5/5 — "<reasoning>"`. If extraction is fiddly, ship without (defer to v1.3) and document the gap.
- **Whether to add a `--no-explain` inverse flag.** Probably no — default is already "no explain"; Typer's `--explain/--no-explain` paired flag is overkill for this surface.
- **Whether the digest's banner string `"========================================"` (40 equals signs) becomes a module constant.** Cosmetic; if it's referenced in regression tests, pinning it as a constant in `_runner.py` keeps drift visible.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/REQUIREMENTS.md` §UX-01..05 (lines 65–69) — the 5 locked requirements. **NOTE:** UX-01's literal "defaulting count" wording is intentionally obsoleted by D-04; the verification step records this divergence.
- `.planning/ROADMAP.md` Phase 16 row (lines 120–135 and 43) — goal, depends-on, 5 success criteria
- `.planning/PROJECT.md` — milestone v1.2 framing (Operator-First Design)
- `.planning/STATE.md` — current position (Phase 15 complete 2026-05-12)

### SEED-008 — primary design spec for this phase
- `.planning/seeds/SEED-008-reporter-ux-overhaul.md` — full motivation, output-shape mockup at §"Proposed Output Shape", `--explain` mockup, open design questions (this CONTEXT.md resolves them: flag name `--explain`, quiet behavior per D-09, JUnit XML embedding NO per D-04's stdout-only stance), breadcrumbs at §"Breadcrumbs"

### SEED-011 — Phase 14 header mockup that Phase 16 polishes
- `.planning/seeds/SEED-011-hybrid-runner-domain-ui.md` §2 — original header mockup; Phase 16 keeps the shape but moves it pre-run

### Phase 14 forward-refs (LOCKED — implement against, do not modify)
- `.planning/phases/14-hybrid-runner-with-domain-ui/14-CONTEXT.md` §D-07 (header shape), §D-08 (em-dash separator + failure_message surface), §D-12 (`-q` summary-only), §D-13 (`--debug` appendix shape), §D-14 (`--explain` deferred to Phase 16) — Phase 16's authority surface
- `src/mcp_test_framework/_runner.py:534-548` (`RenderContext`) — the dataclass Phase 16 reuses; no new fields needed (discovered_tools, tools_config, judges, server_cmd already cover the pre-run digest's inputs)
- `src/mcp_test_framework/_runner.py:622-659` (`_render_header`) — the function whose content moves into a new `_render_pre_run_digest` and whose call site inside `render_domain_ui` (line 773) is removed
- `src/mcp_test_framework/_runner.py:553-592` (`_compose_unparametrized_skips_from_config`) — Phase 14's pure composer; reused pre-run with `ran_tools=set()` per D-05/D-14
- `src/mcp_test_framework/_runner.py:793-813` (`render_summary_only`) — `-q` path; extend per D-09 by gating digest + explain on `not quiet` in `cli.py:run`
- `src/mcp_test_framework/_runner.py:816-866` (`render_debug_appendix`) — `--debug` path; extend per D-11 with per-judge breakdown block

### Phase 15 forward-refs (LOCKED — do not modify in Phase 16)
- `.planning/phases/15-operator-vs-framework-test-surface-split/15-CONTEXT.md` §D-03 — `--with-framework` argv shape; pre-run digest's `Test plan` line reads this state via the `with_framework` bool in `cli.py:run`
- `src/mcp_test_framework/_runner.py:102-108` (`_build_pytest_args` post-Phase-15) — read-only; informs the pre-run digest's scope but doesn't change

### Phase 13 forward-refs (LOCKED — do not modify)
- `.planning/phases/13-config-safety-opt-in-tool-selection/13-CONTEXT.md` §D-12 — locked skip-reason constants `"not selected in config"` / `"explicit skip in config"`; these are the per-tool reason text under `--explain`
- `src/mcp_test_framework/_runner.py:305-306` — the constants themselves; do not rename, do not reword

### Wrapper integration
- `src/mcp_test_framework/cli.py:343-566` (the `run` Typer command) — where `--explain` Typer flag registers (after `--with-framework` per D-08); where `_render_pre_run_digest` is called pre-subprocess; where `_render_skipped_tools_explain` is called between digest and subprocess; where `-q` gates pre-run rendering per D-09
- `src/mcp_test_framework/cli.py:490` (`_discover_tools_for_run(cfg)`) — already runs pre-subprocess; its output feeds the pre-run digest's `Discovered:` count

### Files affected by this phase
- `src/mcp_test_framework/_runner.py` — new constants + new pre-run renderer + new explain renderer + extended `--debug` appendix (D-11 if XML extraction is feasible)
- `src/mcp_test_framework/cli.py:343-566` — `--explain` Typer flag registration; reorder rendering calls so digest fires pre-subprocess and `-q` gates pre-run output
- `tests/framework/unit/test_runner_pre_run_digest.py` (new) — pins digest shape; pins `CASES_PER_CONTRACT_TOOL` constant against the contract test's actual parametrize count
- `tests/framework/unit/test_runner_explain.py` (new) — pins `--explain` output shape + sort order + composition with other flags
- `tests/framework/test_runner_verbosity.py` (existing) — extend with `-q` parity test (one-line output) and `-q --explain` no-op test
- `README.md` — verify "Run the test suite" section mentions the new pre-run digest + `--explain`; update if it documents the old post-run header
- `docs/mcp_test_framework_mvp_spec.md` — verify it doesn't pin the post-run header order; update if it does

### v1.1 / v1.2 contracts preserved by this phase
- Em-dash `—` (U+2014) separator inside FAIL/SKIP reason lines and `--explain` lines — Phase 09 SC-3 / Phase 14 D-08 locked
- ANSI guard via `sys.stdout.isatty()` — Phase 14 D-06; pre-run digest uses the same `_ansi_enabled`/`_dim`/`_red`/`_green` helpers (digest has no color today but the banner could become bold under TTY — Claude's discretion)
- Quiet-mode parity with v1.1 — Phase 14 D-12; Phase 16 extends it to also suppress pre-run digest + explain
- Stdlib only, no new deps — Phase 14 D-06 / Phase 15 unchanged
- SAFE-03 fail-loud on no-config — Phase 13 D-03; the pre-flight gate runs before the pre-run digest renders, so a missing config still errors before any digest output

### Memory references (operator-first context)
- `project_pre_run_tool_summary.md` — the original motivation (pytest's "N collected, M deselected" is misleading at homelab-mcp scale)
- `project_output_ergonomics_at_scale.md` — N=70 backdrop; evaluate digest at homelab-mcp's full surface, not at N=1
- `feedback_phase_scope_intent.md` — title = scope; Phase 16's title is "Reporter UX overhaul", not "Reporter rewrite" — the renderer/parser/subprocess spine is fixed
- `project_v1_1_skip_bug.md` — the dependency precondition that makes the digest's `Skipping (N)` count truthful (v1.1.1 hotfix shipped + SEED-006 / Phase 13 opt-in inversion shipped; counts now agree with what actually runs)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`_compose_unparametrized_skips_from_config`** at `src/mcp_test_framework/_runner.py:553-592`. This is a PURE function taking `(discovered_tools, tools_config, ran_tools)`. Phase 14 calls it post-run with `ran_tools = set(parsed.per_tool.keys())`. Phase 16 calls it pre-run with `ran_tools = set()` — every discovered-but-not-allowlisted tool comes back as either a state-(a) "not selected in config" reason or a state-(c) "explicit skip in config" reason. The function is idempotent and side-effect free, so two calls (pre-run for `--explain`, post-run for `_render_per_tool_rows`) cost only the dict construction.
- **`RenderContext`** at `_runner.py:534-548`. All five fields (`server_cmd`, `discovered_tools`, `tools_config`, `judges`, `total_planned_cases`) already exist. Phase 16 doesn't need a new dataclass; it just calls `_render_pre_run_digest(ctx)` with the same `ctx` that Phase 14 constructs at `cli.py:532-538`. The only field Phase 16 might revisit is `total_planned_cases`: today it's set from `parsed.total_cases` post-run; D-03 computes it pre-run as `running_count × CASES_PER_CONTRACT_TOOL`. Two options at planning: (i) set `total_planned_cases` pre-run, OR (ii) ignore the field and have the digest compute on the fly. Both work; pick whichever makes the call site at `cli.py:532` clean.
- **`_discover_tools_for_run(cfg)`** at `cli.py:288-340`. Already called at `cli.py:490` BEFORE `run_pytest_subprocess`. Returns `list[str]` of tool names. Its output feeds both the pre-run digest and the post-run renderer. No new discovery work needed.
- **`_render_header`** at `_runner.py:622-659`. Phase 16 either splits it (one `_render_pre_run_digest` for pre-run use, deprecate the old call site at `render_domain_ui:773`) or renames it. The 8-line layout is locked to SEED-011 §2 / Phase 14 D-07 — do not redesign it.
- **`_ansi_enabled` / `_dim` / `_red` / `_green`** at `_runner.py:600-614`. Pre-run digest can use these for the banner if a TTY is detected. ANSI guard is universal.

### Established Patterns
- **`file=None → sys.stdout at call time`** pattern (every renderer at `_runner.py:622, 670, 728, 759, 796, 838`). Pre-run digest function MUST follow it so `capsys` test capture works. Do not default `file=sys.stdout` at signature time — that captures the pre-test stdout before pytest's `capsys` swaps it.
- **One-line-per-tool grep-able output**. Phase 14's per-tool rows are grep-able (`<tool>  ✗ FAIL — <reason>`). `--explain` lines should follow the same convention: `<tool>  — <reason>` (two-space-em-dash-two-space separator, but Phase 14's per-tool rows use `  ✓ PASS` etc., so `--explain` may want `  — ` for consistency or `  ` for visual separation. Pick during planning; pin in test).
- **Sorted alphabetical ordering** for grouped output (Phase 09 CD-03 / Phase 14 line 679–681 use `sorted()` for failures/skips/passes). `--explain` follows the same — `sorted(skipped_dict.keys())` for the line order.
- **U+2014 em-dash literal**. Source file uses `—` directly, not `—`. UTF-8 source encoding is the project default; Phase 14's `cli.py:451-461` reconfigures stdout to utf-8 with errors='replace' on Windows before any render so the em-dash always writes safely.

### Integration Points
- `cli.py:run` flow (target post-Phase-16):
  1. `_load_config(config)` — pre-flight gate (Phase 13 D-03)
  2. If `--raw`: `run_pytest_subprocess(raw=True, ...)`, exit code map, raise. (No digest, no explain — `--raw` bypasses Phase 16 entirely.)
  3. `discovered_tools = _discover_tools_for_run(cfg)` (Phase 14)
  4. Build `RenderContext` (Phase 14; same shape — `total_planned_cases` may be pre-computed via D-03)
  5. **NEW** If `not quiet`: `_render_pre_run_digest(ctx)`
  6. **NEW** If `not quiet and explain`: `_render_skipped_tools_explain(ctx)`
  7. `rc, tmp_xml, captured_stdout, captured_stderr = run_pytest_subprocess(raw=False, ...)`
  8. `_dispatch_default_mode_or_error(tmp_xml, rc, captured_stderr)` (Phase 14 D-16)
  9. `parsed = parse_junit_xml(tmp_xml)` (Phase 14)
  10. If `quiet`: `render_summary_only(parsed, ctx)` — single Result: line
      Else: `render_domain_ui(parsed, ctx)` — per-tool rows + summary (NO header — moved to step 5)
  11. If `debug`: `render_debug_appendix(captured_stdout, captured_stderr, parsed)` — optionally extended with per-judge block (D-11)
  12. Exit-code map + raise
- The `render_domain_ui` function at `_runner.py:755-775` needs ONE call-site removal: line 773's `_render_header(ctx, parsed, file=file)`. Everything else in that function stays.

</code_context>

<specifics>
## Specific Ideas

- **Digest banner is locked to 40 equal signs** matching Phase 14's `"=" * 40` (lines 650, 652 of `_runner.py`). Regression tests should pin the literal string.
- **`Skipping (N) (use --explain to list)` hint when `--explain` IS passed**: the hint string should NOT appear under `--explain` (it would lie — the list is right there inline). Render `Skipping:    56` without the parenthetical hint when `explain=True`. Test pins both shapes.
- **`Skipping (N):` block header under `--explain`**: matches SEED-008 mockup `Skipped (56):`. Pick one of `Skipping (56):` / `Skipped (56):` and pin it in test. Recommend `Skipping (56):` for tense-agreement with the digest's `Skipping:` row above it.
- **Two-tool homelab-mcp config.example.yaml** is the canonical small-N test fixture. At N=2 running / N=56 skipping, the digest is exactly the SEED-008 mockup shape. Pin the digest output against `config.example.yaml` as an end-to-end fixture test in `tests/framework/test_runner_live_smoke.py` (or a new equivalent).
- **`--explain` reason text is the operator's `skip_reason` if set, else the locked default constant.** Phase 13 D-12's two-state defaulting (state-a → `"not selected in config"`, state-c → `"explicit skip in config"` unless `skip_reason` is non-empty) is implemented in `_compose_unparametrized_skips_from_config` lines 588–591. Pre-run `--explain` reuses this; no new defaulting logic.

</specifics>

<deferred>
## Deferred Ideas

### Cross-phase tasks (v1.3 candidates)
- **`Running:` line N=70 polish.** Inline names list at large N. Not exercised in v1.2's typical operator workflow (homelab-mcp default selection = 2 tools); revisit if/when an operator config selects ≥ 10 tools.
- **Per-tool judges-per-tool expansion table under `--explain`** (SEED-008 mockup §"Judges per tool"). Today Phase 16 ships `--explain` as skipped-only. A future `--explain --judges` or `--judges` flag could expose per-tool judge mapping if operators ask.
- **Per-judge scores on PASS rows** (SEED-011 §2 mockup `✓ PASS (clarity 5/5)`). Defer to v1.3 unless `--debug` per-judge block (D-11) proves the extraction pattern works cheaply, in which case promote to default PASS rows in v1.3.
- **JUnit XML embedding of the digest** (`<system-out>` or `<properties>`). Phase 16 ships stdout-only per D-04 stance carry-forward. Revisit if/when a real CI consumer (Jenkins, Buildkite, Azure DevOps) asks for it.
- **`rich` library upgrade.** Stdlib + ANSI is the v1.2 baseline. Phase 16 inherits the constraint.
- **Live per-tool progress streaming.** SEED-011 §5 v1.3 candidate. Batch render unchanged in Phase 16.
- **xdist parallelism** — SEED-002 / v1.3 cohort.
- **OpenAI-compat judge backend** — SEED-005 / v1.3 cohort.
- **Per-judge model config** — SEED-012 / dormant.

### Out of scope at scoping
- **CI workflow file updates.** No `.github/workflows/`-style files in this repo; Phase 16 ships the digest contract and CI adapts independently.
- **REQUIREMENTS.md UX-01 wording amendment.** D-04 obsoletes the "defaulting count" phrase. A doc-scrub quick-task can amend it post-Phase-16 (or it stays as the historical record and the divergence is documented in this CONTEXT.md only).
- **`mcp-test-framework explain` standalone command** (no pytest run; just digest + explain). Could be valuable as a config-validation surface, but Phase 16 is purely a UX overhaul of `run`. Defer to a follow-up if requested.

</deferred>

---

*Phase: 16-reporter-ux-overhaul*
*Context gathered: 2026-05-11*
