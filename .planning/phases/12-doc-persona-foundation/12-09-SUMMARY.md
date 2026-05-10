---
phase: 12-doc-persona-foundation
plan: 09
subsystem: docs
tags: [docs, config-discovery, gap-closure, decision-lock, seed-006-forward-pointer]

# Dependency graph
requires:
  - phase: 12-doc-persona-foundation
    provides: "Plan 12-07 README CI-secret paragraph; Plan 12-08 --command/--arg flags + EXTENDING uvx/pipx subsection; existing test_doc_scrub.py + test_config.py patterns"
provides:
  - "README.md quickstart code blocks consistently pair `mcp-test-framework run|list-tools|config-init` with `--config config.yaml`"
  - "README.md prose paragraph at ~lines 90-93 now contains BOTH 12-07's CI-secret framing AND 12-09's no-cwd-auto-discovery sentence"
  - "docs/EXTENDING.md walkthrough Step 1 + 'Add a new MCP tool target' Steps 1, 4 pair invocations with `--config config.yaml`"
  - "docs/EXTENDING.md Step 2 prose mention switched from bare `config-init -o config.yaml` to bootstrap form (`--command uvx --arg homelab-mcp -o config.yaml`)"
  - "tests/unit/test_doc_scrub.py: parametrized regression test asserting all fenced-code-block invocations in README + EXTENDING pair with --config / --help / --command (or are output-style lines)"
  - "tests/unit/test_config.py: decision-lock test naming BOTH halves of SEED-006 (no cwd auto-discovery + no fail-loud) with explicit forward pointer"
affects: ["Phase 13 / SEED-006 (v1.2 cwd auto-discovery + fail-loud redesign — has clear delete-and-replace target test)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Decision-lock test pattern: assertion messages name BOTH halves of a coupled v1.2 redesign so a future contributor flipping either half gets a precise diagnostic, not generic 'test failed'"
    - "Doc-only TDD with parametrized fenced-code-block sweep: regex over fenced blocks, exemption set is {--config, --help, --command, output-style prefixes}"
    - "Cross-plan paragraph co-ownership via APPEND-only contract: 12-07 writes the body, 12-09 appends one sentence; merge order enforced via coordinates_with frontmatter"

key-files:
  created: []
  modified:
    - "README.md"
    - "docs/EXTENDING.md"
    - "tests/unit/test_doc_scrub.py"
    - "tests/unit/test_config.py"

key-decisions:
  - "Option C (doc-only) executed exactly per UAT diagnosis. Option A (cwd auto-discovery in config.py) explicitly DEFERRED to Phase 13 / SEED-006 — would reopen the LOCKED CONTEXT.md decision."
  - "EXTENDING Step 2 line 38 (prose) chose Option A from the plan's two options: replaced bare `config-init -o config.yaml` with the bootstrap form `config-init --command uvx --arg homelab-mcp -o config.yaml`. Smaller diff than Option B (delete + cross-reference), keeps Step 2 self-contained, and aligns the canonical walkthrough recipe with Plan 12-08's new uvx/pipx subsection."
  - "Decision-lock test covers BOTH halves of SEED-006 in a single test with half-naming failure messages. The two halves are coupled in the v1.2 redesign (the redesign that adds cwd auto-discovery is the same redesign that adds fail-loud-on-missing-config), so locking them together produces a single forward pointer rather than two divergent ones."
  - "Test only enforces `--config` pairing in FENCED CODE BLOCKS, not prose. Prose mentions like 'Re-run `uv run mcp-test-framework run`' inside step-list narration are not enforced by the test, but were swept by Task 2 for narrative consistency. The test scope (code blocks only) is intentional — it's the operator copy-paste surface."
  - "README CI snippet line 193 (the prose comment line in the YAML code block) was also fixed for consistency — the comment line itself sat inside a fenced YAML block, so the test caught it alongside the actual `- run:` line."

patterns-established:
  - "Co-owned paragraph append pattern: a downstream plan can extend an upstream plan's paragraph with a single appended sentence, enforced by a self-check that BOTH plans' substrings ('CI-secret' from 12-07, 'auto-discover' from 12-09) appear in the merged paragraph"
  - "Decision-lock test naming: when locking a CONTEXT.md decision (rather than a numbered requirement), tag the plan with `decision-lock` in frontmatter and document the forward pointer (SEED-006) in the test's docstring so the next contributor can find the redesign target without archaeology"

requirements-completed: [CLEAN-01, PERSONA-01, decision-lock]

# Metrics
duration: ~4min
completed: 2026-05-10
---

# Phase 12 Plan 09: config.yaml discovery doc additions Summary

**Closed UAT gap 3 via Option C (doc-only): every operator-facing CLI invocation in README + EXTENDING fenced code blocks now pairs with `--config config.yaml`, the README prose paragraph at ~lines 90-93 grew a no-cwd-auto-discovery sentence on top of Plan 12-07's CI-secret framing, and a new decision-lock test in test_config.py names BOTH halves of SEED-006 (no auto-discovery + no fail-loud) as the v1.2 redesign target.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-05-10T06:08Z
- **Completed:** 2026-05-10T06:12Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- README quickstart code blocks (Run-the-test-suite block, List-tools block, CI snippet) now consistently pair `mcp-test-framework run|list-tools|config-init` invocations with `--config config.yaml`. An operator copy-pasting from quickstart no longer hits the silent-fail mental model that flagless invocation auto-discovers cwd config.
- README prose paragraph at ~lines 90-93 now reads as a three-sentence paragraph: (1) Plan 12-07's "generate via config-init" + (2) Plan 12-07's "env vars are CI-secret only" + (3) THIS plan's "no cwd auto-discovery; --config or MCPTF_CONFIG_FILE required". Two-plan co-ownership preserved via APPEND-only contract.
- docs/EXTENDING.md walkthrough Step 1 + "Add a new MCP tool target" Steps 1, 4 sweep complete; Step 2 prose `config-init` invocation switched from bare to bootstrap form (`--command uvx --arg homelab-mcp -o config.yaml`).
- New parametrized regression test `test_doc_invocations_consistently_pair_with_config` in tests/unit/test_doc_scrub.py asserts every fenced-code-block invocation in README + EXTENDING carries `--config`, `--help`, or `--command` (or is a pytest-output-style line in README's Sample green run block). Both parametrized cases (README, EXTENDING) flipped RED→GREEN after Task 2 sweep.
- New decision-lock test `test_no_cwd_config_yaml_auto_discovery_and_no_fail_loud` in tests/unit/test_config.py locks BOTH halves of SEED-006 with half-naming failure messages so a future contributor flipping either half gets a precise diagnostic.
- 26 tests pass across test_config.py + test_doc_scrub.py (12 existing config + 1 new lock + 11 existing doc-scrub + 2 new parametrized cases). src/mcp_test_framework/config.py and src/mcp_test_framework/cli.py are unchanged by this plan (verified `git diff` empty).

## Task Commits

Each task was committed atomically (TDD RED→GREEN cycle on tasks 1-2; decision-lock pattern on task 3):

1. **Task 1 (RED): add --config consistency regression guard to test_doc_scrub** — `284ca11` (test)
2. **Task 2 (GREEN): consistently pair CLI invocations with --config across README and EXTENDING** — `8598174` (docs)
3. **Task 3 (decision-lock): lock no-cwd-auto-discovery + no-fail-loud contract with SEED-006 forward pointer** — `266105a` (test)

## Files Created/Modified

- `README.md` — four edits (all in fenced code blocks plus one prose paragraph append):
  - Lines 44-46 (Run-the-test-suite block): paired both bare `run` invocations with `--config config.yaml` (middle line already had `--config ./config.yaml`).
  - Lines 59-60 (List-tools block): paired both `list-tools` invocations with `--config config.yaml`.
  - Lines 90-93 (Configuration prose paragraph, CO-OWNED with Plan 12-07): appended one sentence ("The framework does not auto-discover a `config.yaml` in the current directory; the path must be explicit (via `--config` or the `MCPTF_CONFIG_FILE` env var).") to the END of 12-07's paragraph. Self-check: paragraph now contains BOTH "CI-secret" (12-07) and "auto-discover" (12-09).
  - Line 193 (prose comment inside YAML CI snippet code block) AND line 206 (the `- run:` line itself): paired the `run --junit-xml=results.xml` invocation with `--config config.yaml`.
- `docs/EXTENDING.md` — five edits (all in prose, satisfying the narrative-consistency requirement of `must_haves.outcomes` even though the parametrized test only enforces fenced code blocks):
  - Step 1 line 22 (prose): `mcp-test-framework list-tools` → `mcp-test-framework list-tools --config config.yaml` plus a parenthetical pointer to Step 2 bootstrap recipe for operators on a fresh checkout.
  - Step 1 line 32 (prose): `mcp-test-framework list-tools --full --name keyring` → `mcp-test-framework list-tools --config config.yaml --full --name keyring`.
  - Step 2 line 38 (prose): `mcp-test-framework config-init -o config.yaml` → `mcp-test-framework config-init --command uvx --arg homelab-mcp -o config.yaml` (Option A from plan; Option B deleted + cross-referenced was the alternative). The bootstrap form aligns with Plan 12-08's new uvx/pipx subsection and is exempt from `--config` pairing because the config file does not yet exist at bootstrap time.
  - "Add a new MCP tool target" Step 1 (line 213): paired with `--config config.yaml`.
  - "Add a new MCP tool target" Step 4 (line 216): paired with `--config config.yaml`.
- `tests/unit/test_doc_scrub.py` — appended one new parametrized test function `test_doc_invocations_consistently_pair_with_config[README, EXTENDING]`. The test walks each file's fenced code blocks, regex-matches `mcp-test-framework (run|list-tools|config-init)\b`, and asserts each match line carries `--config`, `--help`, or `--command` (with README-only exemption for pytest-output-style prefixes). Failure message names the file, line number, and offending line text plus a remediation hint.
- `tests/unit/test_config.py` — appended one new test function `test_no_cwd_config_yaml_auto_discovery_and_no_fail_loud`. The test (a) writes a `config.yaml` in the autouse-chdir'd `tmp_path` with a sentinel `mcp_server.command` value, (b) calls `Config()` and proves it does not raise (locks SEED-006 half 2: no fail-loud), (c) asserts the sentinel did NOT bleed in (locks SEED-006 half 1: no cwd auto-discovery), (d) asserts the model default `homelab-mcp` landed instead. Failure messages explicitly name WHICH half flipped if either assertion fails.

## Decisions Made

- **Test scope is fenced code blocks only** — not prose. The plan's `<interfaces>` block specifies "extract fenced code blocks" and the operator copy-paste surface IS code blocks. Prose mentions in step-list narration ("Re-run `uv run mcp-test-framework run`") were swept by Task 2 for narrative consistency, but the regression test only enforces the code-block contract. This keeps the test focused on the actual broken-mental-model surface.
- **EXTENDING line 38 chose Option A (replace with bootstrap form), not Option B (delete + cross-reference)**. Smaller diff, keeps Step 2 self-contained, preserves the four-step narrative. Option B would have required a forward reference to Plan 12-08's uvx/pipx subsection; Option A folds the bootstrap recipe directly into the canonical step.
- **README CI snippet prose comment (line 193) was also fixed** — the line `# (`uv run mcp-test-framework run --junit-xml=results.xml`) is portable.` sits inside the YAML fenced code block, so the parametrized test caught it. Fixed for consistency with the actual `- run:` line on 206.
- **Decision-lock test couples both SEED-006 halves into a single test** rather than two separate tests. The v1.2 redesign couples them (the redesign that adds cwd auto-discovery is the same redesign that adds fail-loud), so locking them together produces a single forward pointer with half-naming diagnostics. If the redesign lands one half at a time, the test fails with a message identifying which half flipped first — the contributor knows to update the test deliberately rather than blindly fix the failure.
- **No edits to src/mcp_test_framework/config.py or src/mcp_test_framework/cli.py** — verified by empty `git diff`. The plan's `<scope_guardrails>` explicitly forbid runtime config-loading changes; those are Phase 13 / SEED-006 work.

## Deviations from Plan

None — plan executed exactly as written. The Task 2 sweep matched the plan's enumerated offending lines (with the trivial observation that EXTENDING's bare invocations sat in prose, not fenced code blocks, so the regression test passed for EXTENDING after Plan 12-08's earlier code-block cleanup landed; the prose-edit sweep happened anyway for narrative-consistency-of-walkthrough reasons per `must_haves.outcomes`).

The Task 3 test is degenerate-RED-GREEN by design (locks current behavior, passes immediately on trunk). Plan acknowledges this in the behavior block; not a deviation.

## Issues Encountered

- The Task 1 RED state was asymmetric: README failed (6 offending lines in fenced code blocks), EXTENDING passed (no offending lines in fenced code blocks — Plan 12-08 had already cleaned the only EXTENDING code block invocation when adding the uvx/pipx subsection). This was a benign discovery, not a problem; the plan's `<behavior>` block correctly described the test's scope (fenced code blocks), and the EXTENDING prose-mention sweep in Task 2 was driven by narrative-consistency goals, not the test contract. The test's GREEN state on EXTENDING from the start means future EXTENDING code-block additions are protected; prose-mention regressions remain a manual-review concern (acceptable per plan scope).

## User Setup Required

None — pure documentation reconciliation + new tests. No environment changes; backwards-compatible (existing `--config config.yaml` invocations are unchanged).

## Cross-plan Coordination

Per plan frontmatter `coordinates_with: ["12-07", "12-08"]`:

- **12-07 (already landed before this plan):** This plan APPENDED ONE sentence to the END of 12-07's CI-secret paragraph at README ~lines 90-93. Did NOT replace the paragraph; did NOT touch 12-07's CI-secret framing. Self-check verified the merged paragraph contains BOTH "CI-secret" (12-07) AND "auto-discover" (12-09) substrings.
- **12-08 (already landed before this plan):** This plan's Task 1 regression test EXEMPTS lines containing `--command` (the bootstrap form per Plan 12-08's new uvx/pipx subsection in EXTENDING Step 2). The exemption was specified in the plan's `<interfaces>` block and is documented in the test's docstring. EXTENDING Step 2 line 38's switch from bare `-o config.yaml` to `--command uvx --arg homelab-mcp -o config.yaml` aligns with Plan 12-08's bootstrap recipe.
- **test_doc_scrub.py end-of-file appends:** Plan 12-08 appended `test_extending_step2_mentions_uvx_pipx_bootstrap_flags` at end-of-file. This plan appended `test_doc_invocations_consistently_pair_with_config` AFTER it. No line collision; both end-of-file appends.

## Forward Notes

- **Out of scope (deferred / acknowledged):**
  - **Option A (cwd auto-discovery in config.py):** Would reopen the LOCKED CONTEXT.md decision. v1.2 redesign work, tracked under SEED-006. The new decision-lock test in test_config.py is the explicit delete-and-replace target for that redesign.
  - **SEED-006 fail-loud-on-missing-config:** Same v1.2 redesign target as cwd auto-discovery; coupled into the same lock test for the same delete-and-replace contract.
  - **SEED-006 .env precedence reform (Component 5):** Phase 13 work. This plan does not address `.env` beats `--config` (project memory `project_dotenv_silently_beats_config`) — that's a separate Phase 13 / SEED-006 component.
  - **Prose-mention --config consistency in EXTENDING:** Test only enforces fenced code blocks. Prose mentions were swept in Task 2 for narrative consistency but are not protected from future regression. Acceptable per plan scope (operator copy-paste happens from code blocks; prose is descriptive).

## UAT gap-3 truth status

The UAT gap-3 truth ("Framework auto-discovers a `config.yaml` at the cwd / repo root without requiring an explicit `--config` flag or `MCPTF_CONFIG_FILE` env var") is NOT directly satisfied — the runtime behavior remains locked per CONTEXT.md. What this plan satisfies is the strict subset of the gap that is in phase 12 scope per the UAT diagnosis (Option C):

- **Docs no longer ACTIVELY TEACH the broken mental model.** Every README/EXTENDING fenced-code-block invocation pairs with `--config config.yaml` (or `--command` for the bootstrap exemption per Plan 12-08); operators copy-pasting from quickstart succeed first time.
- **Current behavior is LOCKED by the new decision-lock test** covering BOTH halves of SEED-006 (cwd auto-discovery AND fail-loud), with explicit forward pointers naming both halves. Prevents accidental flips and gives the v1.2 redesign a precise delete-and-replace target with half-naming failure diagnostics.

The full code-side fix (Option A — cwd auto-discovery + fail-loud) remains Phase 13 / SEED-006 scope per project memory `project_config_discovery_and_safety` and `<scope_guardrails>`.

## Self-Check

- File checks:
  - `README.md` modified — FOUND
  - `docs/EXTENDING.md` modified — FOUND
  - `tests/unit/test_doc_scrub.py` modified — FOUND
  - `tests/unit/test_config.py` modified — FOUND
  - `src/mcp_test_framework/config.py` unchanged — VERIFIED (`git diff` empty)
  - `src/mcp_test_framework/cli.py` unchanged — VERIFIED (`git diff` empty)
- Commit checks:
  - `284ca11` (Task 1 RED) — FOUND
  - `8598174` (Task 2 GREEN) — FOUND
  - `266105a` (Task 3 decision-lock) — FOUND
- Verification command (`uv run pytest tests/unit/test_config.py tests/unit/test_doc_scrub.py -v`): 26 passed.
- Paragraph self-check (README ~lines 90-93 contains BOTH "CI-secret" and "auto-discover"): VERIFIED.

## Self-Check: PASSED

## Next Phase Readiness

- Phase 12 wave 1 (12-07, 12-08, 12-09) complete. UAT gaps 1, 2, 3 all closed via the in-scope subset documented in the UAT diagnosis (Option C for gap 3; full PRIMARY+SECONDARY+DOC for gap 2; full doc reconciliation for gap 1).
- Phase 13 / SEED-006 has a clear delete-and-replace test target (`test_no_cwd_config_yaml_auto_discovery_and_no_fail_loud`) when the v1.2 cwd-auto-discovery + fail-loud redesign lands.
- Plan 12-09 declared `coordinates_with: ["12-07", "12-08"]` to enforce merge order; both upstream plans landed before this one in the same wave, so the appendage and exemption contracts held.

---
*Phase: 12-doc-persona-foundation*
*Completed: 2026-05-10*
