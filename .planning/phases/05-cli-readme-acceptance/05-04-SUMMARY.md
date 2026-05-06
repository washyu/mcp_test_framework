---
phase: 05-cli-readme-acceptance
plan: 04
subsystem: docs
tags: [docs, readme, extending, env-vars, configuration]

# Dependency graph
requires:
  - phase: 05-cli-readme-acceptance
    plan: 01
    provides: Typer `app`, `_load_config(path)` helper, `version` command at src/mcp_test_framework/cli.py (one-shot examples in README cite this surface)
  - phase: 05-cli-readme-acceptance
    plan: 02
    provides: `run` Typer command (CLI-01) -- README's `### Run the test suite` section documents this surface verbatim
  - phase: 05-cli-readme-acceptance
    plan: 03
    provides: `list-tools` Typer command with --json (CLI-02) -- README's `### List MCP server tools` section documents this surface
  - phase: 04-fixtures-test-cases
    provides: Rubric base class + ClarityRubric/DisambiguationRubric/ParametersRubric in src/mcp_test_framework/rubrics.py -- EXTENDING.md Recipe 1 references the base class
  - phase: 03-ollama-judge
    provides: Judge Protocol in src/mcp_test_framework/judge_protocol.py + JudgeResult shape in src/mcp_test_framework/ollama_judge.py -- EXTENDING.md Recipe 2 references both
  - phase: 01-foundation-pure-data-core
    provides: Config sub-models in src/mcp_test_framework/models.py + .env.example -- README env-var table mirrors .env.example contents and uses Pydantic defaults

provides:
  - "README.md (replaced) -- quickstart-focused user docs covering setup, three CLI commands, env-var precedence, and Windows troubleshooting"
  - "docs/EXTENDING.md (new) -- two extension recipes (rubric subclassing, judge backend swap) with copy-pasteable code samples"
  - "Verified .env.example<->README env-var sync (artifact: .planning/phases/05-cli-readme-acceptance/05-04-SYNC-CHECK.txt)"
  - "TODO Plan 05 marker in README's `## Sample green run` section -- Plan 05-05 will replace with a real captured pytest excerpt"
  - "DOCS-01 closed (README + extension docs scope of phase 5)"
affects: [05-05-acceptance]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Quickstart README + sibling EXTENDING.md split -- README stays readable in one sitting; extension content lives in docs/ where it can grow"
    - "Manual .env.example<->README env-var table sync, captured as a verifiable text artifact (no auto-generation from Pydantic for MVP -- Plant-Seed candidate)"
    - "TODO marker convention for cross-plan handoffs -- `<!-- TODO Plan 05 -->` inside a fenced block lets the next plan replace exact content without restructuring the README"

key-files:
  created:
    - "docs/EXTENDING.md - 121-line extension guide with rubric and judge-backend recipes (Rubric subclass + @pytest.fixture, Judge Protocol implementation + @pytest_asyncio.fixture override)"
    - ".planning/phases/05-cli-readme-acceptance/05-04-SYNC-CHECK.txt - 22-line artifact capturing .env.example<->README env-var diff (8 OK rows + MCPTF_CONFIG_FILE OK + precedence OK + 0 MISSING)"
  modified:
    - "README.md - replaced 12-line stub with 124-line quickstart doc covering all 9 required H2 sections (Prerequisites, Setup, Commands, Configuration, Sample green run, Troubleshooting (Windows), Further reading) plus H1 + project one-liner preserved"

key-decisions:
  - "Pydantic defaults in the README 'Default' column, .env.example example values cited inline in 'Purpose' -- distinguishes the in-code default (MCP_SERVER_COMMAND=homelab-mcp) from the .env.example zero-install starter (MCP_SERVER_COMMAND=uvx) without forcing one to lie"
  - "Sample green run section ships with a TODO Plan 05 marker plus a generic placeholder block (rather than no block) -- gives Plan 05-05 a clean drop-in slot and ensures the section heading exists today for any reader running the suite manually"
  - "Manual sync between .env.example and README env-var table verified by sync-check artifact -- no auto-generation from Pydantic for MVP per CONTEXT.md <deferred>"

patterns-established:
  - "Pattern: TODO marker inside a fenced block (`<!-- TODO Plan NN: ... -->`) for cross-plan handoffs in user-facing docs -- subsequent plan replaces the marker line + the placeholder content beneath it; section heading stays stable"
  - "Pattern: Sync-check artifact for cross-file invariants -- when two files (.env.example + README env-var table) must stay aligned, ship a one-shot bash check whose output is committed alongside the change; reviewer reads the artifact instead of doing the diff manually"

requirements-completed: [DOCS-01]

# Metrics
duration: 2 min 21 sec
completed: 2026-05-06
---

# Phase 5 Plan 04: README + EXTENDING Summary

**Replaces the 12-line README stub with a 124-line quickstart doc (3 CLI commands + 9-row env-var table + Windows troubleshooting) and ships docs/EXTENDING.md with rubric-subclass and judge-backend-swap recipes. DOCS-01 closed.**

## Performance

- **Duration:** ~2 min 21 sec
- **Started:** 2026-05-06T23:14:23Z
- **Completed:** 2026-05-06T23:16:44Z
- **Tasks:** 3
- **Files modified:** 3 (1 replaced, 2 created)

## Accomplishments

- README.md replaced: 12 lines -> 124 lines, 7 H2 sections matching the plan's required structure (Prerequisites, Setup, Commands, Configuration, Sample green run, Troubleshooting (Windows), Further reading); H1 + project one-liner preserved verbatim.
- All three CLI commands documented with one-shot examples: `run` (with `--config` and pytest-args forwarding via `--`), `list-tools` (with `--json`), and `version`. Each example matches the live shape from Plans 05-01..05-03.
- Env-var table covers all 8 vars from `.env.example` plus `MCPTF_CONFIG_FILE` (the optional YAML overlay path documented as a comment in `.env.example`). Defaults are sourced from `models.py` (Pydantic) and `.env.example` example values are cited in the Purpose column when they differ.
- Precedence sentence "**CLI flag > env var > `.env` > YAML overlay > default**" present per CONTEXT.md.
- Windows troubleshooting section ships the canonical `taskkill /F /IM homelab-mcp.exe` recovery line plus two adjacent issues (uv-sync script-shim regen, MCP_SERVER_COMMAND/ARGS misconfiguration leading to `[WinError 2]`).
- `## Sample green run` section ships with a `<!-- TODO Plan 05 -->` marker inside a fenced block + a generic placeholder so Plan 05-05 has a clean drop-in slot.
- docs/EXTENDING.md created: 121 lines, 3 H2 sections (`Add a new description-quality rubric`, `Swap the judge backend`, `Further reading`). Recipe 1 is a complete copy-pasteable Rubric subclass + session-scoped fixture + judge-driven test. Recipe 2 is a complete Judge Protocol implementation + `@pytest_asyncio.fixture` override that shadows the framework's `judge` fixture.
- The `runtime_checkable` signature-shape caveat from `judge_protocol.py:31-37` is documented in EXTENDING.md so users hit a clear "shape mismatch will fail at call time" mental model.
- `.env.example` <-> README env-var table sync verified: artifact at `.planning/phases/05-cli-readme-acceptance/05-04-SYNC-CHECK.txt` shows 8 OK rows + MCPTF_CONFIG_FILE OK + precedence OK + 0 MISSING; `git diff --quiet .env.example` confirms .env.example was not edited.
- DOCS-01 (README + extension docs) requirement complete.

## Task Commits

Each task was committed atomically on the main working tree (sequential executor):

1. **Task 1: Replace README.md with quickstart-focused content** - `ed9fcd5` (docs)
2. **Task 2: Create docs/EXTENDING.md with two extension recipes** - `1812127` (docs)
3. **Task 3: Verify .env.example and README env-var table are in sync** - `795ffb1` (docs)

## Files Created/Modified

- `README.md` (REPLACED) - 12 lines -> 124 lines. H1 (`# mcp_test_framework`) + project one-liner preserved verbatim from the stub. Replaces the "Phase 5 stub" pointer note with: ## Prerequisites, ## Setup (`git clone` + `cp .env.example .env` + `uv sync`), ## Commands (3 H3 subsections each with a fenced bash example), ## Configuration (precedence sentence + 9-row env-var table + dotenv/YAML/PowerShell paragraph), ## Sample green run (TODO Plan 05 marker + placeholder block), ## Troubleshooting (Windows) (3 bullets), ## Further reading (3 markdown links: spec, EXTENDING, PROJECT).
- `docs/EXTENDING.md` (NEW) - 121 lines. Intro paragraph names both seams (Rubric base + Judge Protocol). Recipe 1 mirrors `fixtures.py` rubric-as-fixture pattern (`SafetyRubric` subclass + `rubric_safety` session-scoped fixture + `test_description_safety`); explains `_HARDENING_PREAMBLE`/`_SCORE_ANCHOR_TEMPLATE` auto-wrap and the `score >= 4` pass threshold. Recipe 2 implements `OpenAIJudge` satisfying the `Judge` Protocol + a `@pytest_asyncio.fixture(loop_scope="session", scope="session")` override; calls out `runtime_checkable`'s attribute-only check and notes that signature drift fails at call time, not at registration.
- `.planning/phases/05-cli-readme-acceptance/05-04-SYNC-CHECK.txt` (NEW) - 22 lines. Captures the env-var inventory from `.env.example`, the per-var presence check against the README's ## Configuration section, the MCPTF_CONFIG_FILE row presence check, and the precedence-sentence presence check. All checks return `OK:`; zero `MISSING:` lines.

## Decisions Made

- **Pydantic defaults in the README 'Default' column; .env.example example values cited inline.** The plan's interfaces block flagged a real discrepancy: `MCP_SERVER_COMMAND` defaults to `homelab-mcp` in `models.py` but `.env.example` ships `uvx` as a zero-install starter, and `MCP_SERVER_ARGS` defaults to `[]` in `models.py` but `.env.example` ships `["homelab-mcp"]`. Showing only the Pydantic default would mislead users who copy `.env.example` verbatim; showing only the `.env.example` value would mislead users who edit `.env.example` minimally. The compromise is: Default column = Pydantic default (the in-code truth that takes effect when env is unset), Purpose column = "`.env.example` ships `<value>` ..." (so users see why their copy starts with a different value).
- **Sample green run ships with placeholder + TODO marker, not absent.** The section heading + a placeholder block exist today (rather than the section being empty or absent) so any reader running the suite manually before Plan 05-05 lands sees a roughly-shaped expectation, and so the next plan has a precisely-shaped slot to drop the captured output into. The TODO marker is inside the fenced block (`<!-- TODO Plan 05: replace this block ... -->`) so it remains visible in rendered markdown; Plan 05-05 will replace the marker line + the generic placeholder beneath it without restructuring.
- **Manual sync verified by an artifact instead of an automated test.** CONTEXT.md `<deferred>` explicitly lists "Auto-generate env-var docs from the Pydantic Config model" as a Plant-Seed candidate ("if/when the field count grows past ~10 or drift causes a real bug"). For the MVP, a one-shot bash sync check whose output is committed (`.planning/phases/05-cli-readme-acceptance/05-04-SYNC-CHECK.txt`) is the lighter-weight path: the reviewer reads 22 lines instead of approving an auto-generation pipeline.

## Deviations from Plan

None - plan executed exactly as written. No bugs found, no missing critical functionality, no blocking issues, no architectural changes needed.

The plan's `<action>` blocks for Tasks 1 and 2 already specified the exact required H2/H3 structure, table contents, and code samples; the implementation is a direct transcription. Task 3's bash recipe needed one POSIX-shell adjustment (the `awk "/^## Configuration$/,/^## /"` range pattern matches the start line itself on both sides, collapsing the range to a single line) -- I switched to a stateful `awk` (`/^## Configuration$/{flag=1; print; next} flag && /^## /{flag=0} flag`) so the section body is captured correctly. The artifact contents and verification semantics are unchanged; the fix is purely a shell-recipe correctness adjustment, not a deviation from the plan's intent.

## Issues Encountered

One minor shell-recipe issue, resolved inline:

| Issue | Where | Resolution |
|---|---|---|
| `awk "/^## Configuration$/,/^## /"` collapsed the range to one line because the start anchor itself satisfies the end pattern | Task 3 sync-check artifact generation | Switched to stateful awk that sets a flag on the start line and clears it on the next `^## ` heading; captured 20 README lines for the per-var grep. Final artifact contains zero `MISSING:` rows. |

## Authentication Gates

None - all work was local file authoring (markdown + a sync-check artifact). No external services touched.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Plan 05-05 (acceptance UAT)** has its DOCS-01 verification target ready: README.md exists with 9 H2 sections (counting H1 + 7 H2 sections + the H3 subsections under Commands), all 8 .env.example vars + MCPTF_CONFIG_FILE are documented, the Windows troubleshooting line is in place, and EXTENDING.md ships with both recipes. The `<!-- TODO Plan 05 -->` marker in `## Sample green run` is the precise slot for Plan 05-05 to replace with a captured 10-15 line excerpt of `uv run mcp-test-framework run` output.
- The CLI surface and the user-facing docs are now both stable and aligned. Plan 05-05 only needs to: (1) run the suite live against homelab-mcp + Ollama, (2) capture the green-run output, (3) replace the README marker, (4) execute the OPS-03 manual UAT (Ctrl+C `list-tools` -> `Get-Process homelab-mcp` returns no matches), and (5) sign off SC#1..SC#6.
- No further README or EXTENDING.md edits are anticipated for this phase outside the Plan 05-05 sample-output replacement.

## Self-Check: PASSED

- File `README.md` exists at 124 lines (>= 100) -> verified
- File `docs/EXTENDING.md` exists at 121 lines (>= 60) -> verified
- File `.planning/phases/05-cli-readme-acceptance/05-04-SYNC-CHECK.txt` exists, contains 8 OK env-var rows + OK MCPTF_CONFIG_FILE + OK precedence sentence + 0 MISSING rows -> verified
- All Task 1 grep acceptance criteria pass (H1 + 7 H2 + 8 env vars + MCPTF_CONFIG_FILE + taskkill + EXTENDING link + spec link + TODO Plan 05 + precedence + 3 CLI cmds; FAQ=0, badge=0) -> verified
- All Task 2 grep acceptance criteria pass (H1 + 2 H2 recipes + Rubric/Judge imports + JudgeResult + @pytest.fixture + @pytest_asyncio.fixture + score >= 4 + runtime_checkable; rich=0) -> verified
- All Task 3 sync-check criteria pass (`grep -q "^MISSING:" SYNC-CHECK.txt` returns false; `git diff --quiet .env.example` returns true) -> verified
- Commit `ed9fcd5` (Task 1: README) -> FOUND in `git log --oneline`
- Commit `1812127` (Task 2: EXTENDING.md) -> FOUND in `git log --oneline`
- Commit `795ffb1` (Task 3: sync-check artifact) -> FOUND in `git log --oneline`

---
*Phase: 05-cli-readme-acceptance*
*Completed: 2026-05-06*
