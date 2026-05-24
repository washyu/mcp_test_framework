# Phase 32: Surface-shim removals — CLI + package + fixtures + discovery - Context

**Gathered:** 2026-05-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Delete every v1.4-introduced `sdet`-flavored surface shim across the operator-visible surfaces — package import (`mcp_test_framework.sdet`), Typer CLI flag (`--sdet`), Typer CLI command (`gen-sdet-classes`), test-discovery fallback (`tests/sdet/`), unprefixed fixtures (the six aliases in `_plugin.py` L433–502: `config`, `judge`, `target_tool`, `rubric_clarity`, `rubric_disambiguation`, `rubric_parameters`), and legacy console-script entry-point (`mcp-test-framework`). Each removal surfaces an operator-tone migration error pointing at the post-v1.4 name (`mcp_test_framework.test_code`, `--test-code`, `gen-test-classes`, `tests/test_code/`, `mcp_*`-prefixed fixtures, `mcp-contracts`).

> **NOTE (post-research correction, 2026-05-24):** ROADMAP.md §Phase 32 SC#4 names four fixtures (`config` / `judge` / `client` / `target_tool`). The actual SHIM-07 surface in `_plugin.py` L433–502 is **six** fixtures; `client` is NOT one of them. Ground truth for plan 32-05 lives in this CONTEXT.md (six fixtures enumerated above); the ROADMAP SC#4 wording is imprecise reference text and stays as-is. The post-v1.4 prefixed names are: `mcp_config`, `mcp_judge`, `mcp_target_tool`, `mcp_rubric_clarity`, `mcp_rubric_disambiguation`, `mcp_rubric_parameters`. Lands AFTER Phase 31 so the migration-error paths reference the already-cleaned config surface (no `MCPTF_CONFIG_FILE` / `sdet:` / v1-schema verbiage anywhere).

**In scope:** SHIM-01 (sdet package import), SHIM-02 (`--sdet` CLI flag), SHIM-03 (`gen-sdet-classes` CLI command), SHIM-06 (`tests/sdet/` auto-discovery), SHIM-07 (unprefixed fixtures), SHIM-08 (`mcp-test-framework` console-script).

**Out of scope (different phases):** SHIM-04/05 + V1DROP-01..04 (Phase 31, complete), BUCKET-01..05 (Phase 33), ISOL-01..06 (Phase 34), SHIM-09 regression-gate capstone (Phase 35).

</domain>

<decisions>
## Implementation Decisions

### Plan decomposition

- **D-01:** 1:1 per SHIM — **six plans, six commits**. Mirrors Phase 31 cadence; atomic rollback per surface; each plan stays small and reviewable. Canonical plan list:
  - `32-01` — SHIM-01: `mcp_test_framework.sdet` package import shim removal
  - `32-02` — SHIM-02: `--sdet` Typer flag removal
  - `32-03` — SHIM-03: `gen-sdet-classes` Typer command removal
  - `32-04` — SHIM-06: `tests/sdet/` discovery-fallback removal
  - `32-05` — SHIM-07: unprefixed fixture-alias removal
  - `32-06` — SHIM-08: `mcp-test-framework` console-script removal
- **D-02:** Internal plan-execution order is interchangeable (all six removals are orthogonal — no shared module-load or fixture-graph dependencies between them). Recommend canonical numeric order 01→06 unless research surfaces a coupling.

### Claude's Discretion (recommended defaults — planner free to revisit with research)

Defaults chosen to match Phase 31's loud-and-friendly operator-tone pattern (D-04 / D-11 in `31-CONTEXT.md`). Each is overridable at plan time; flagged here so the planner can revisit before the plan is locked.

- **D-03 (SHIM-01 mechanism — `sdet` package import):** Keep `src/mcp_test_framework/sdet/__init__.py` as a **hard-raise migration shim** rather than deleting the directory outright. The module immediately raises `ModuleNotFoundError` (or `ImportError` with the same shape) carrying an operator-tone three-part message naming `mcp_test_framework.test_code` as the replacement. Rationale: success criterion #1 explicitly requires "operator-tone message pointing at `mcp_test_framework.test_code`" — Python's stock `ModuleNotFoundError: No module named 'mcp_test_framework.sdet'` does NOT carry that pointer. Alternative (clean delete of the directory): considered, rejected because it fails the SC#1 pointer requirement. **RESEARCH-FOR-PLAN:** verify that raising at module-load time fires reliably on every supported import path (`import mcp_test_framework.sdet`, `from mcp_test_framework.sdet import X`, `from mcp_test_framework import sdet`); test against Python 3.14's lazy-import machinery if applicable. Phase 35 SHIM-09 regression gate must grandfather the single surviving `sdet/` directory match for v1.5 (clean-delete EOL deferred to v1.6).

- **D-04 (SHIM-02/03 mechanism — Typer flag + command):** Register the legacy `--sdet` flag and `gen-sdet-classes` command as **hidden intercepts** that raise an operator-tone `typer.BadParameter` / `typer.UsageError` naming the post-v1.4 replacement (`--test-code` / `gen-test-classes`). Rationale: success criterion #2 requires the UsageError to NAME the new flag/command — Typer's stock "No such option: --sdet" / "No such command: gen-sdet-classes" do not carry that pointer. Alternative (clean removal of registration): considered, rejected for SC#2 pointer requirement. **RESEARCH-FOR-PLAN:** confirm Typer 0.25.x supports hidden options/commands with `hidden=True` + custom callback; verify error surface is consistent with Phase 31's `_emit_operator_error` three-part shape so the operator sees the same message texture across config + CLI surfaces.

- **D-05 (SHIM-06 mechanism — `tests/sdet/` discovery):** **Loud collection-time detection** — if `tests/sdet/` exists and contains any `test_*.py` files, fire an operator-tone error at `pytest_collectstart` (or equivalent plugin hook) pointing at `tests/test_code/` as the new location. Silently stop discovering the path either way. Rationale: success criterion #4 says "no longer auto-discovered" (minimum bar = silent removal), but loud detection catches the operator-mid-migration footgun consistent with Phase 31's pattern (last DeprecationWarning at D-06; targeted error mapper at D-04). Alternative (silent removal — let pytest find zero tests under tests/sdet/ silently): considered, acceptable per minimum SC bar but inconsistent with the SHIM-04 / SHIM-05 loud-and-friendly precedent. **RESEARCH-FOR-PLAN:** decide warning-vs-error severity (warn-and-skip vs hard-fail collection); precedent from Phase 31 D-06 was warn-only, so leaning warn. Confirm the right plugin hook (`pytest_collectstart` vs `pytest_configure`); avoid double-firing if both `tests/sdet/` and `tests/test_code/` exist. Reference the 12 `# noqa: sdet-rename-shim` markers in `src/mcp_test_framework/_runner.py` + `fixtures.py` + `_reporter.py` (all need scrubbing in the same plan).

- **D-06 (SHIM-07 mechanism — unprefixed fixtures):** **Stub-raise fixtures**, not clean delete. Keep the six unprefixed fixture names registered in `_plugin.py` L433–502; replace each body with `pytest.fail(MSG, pytrace=False)` carrying an operator-tone message naming the `mcp_`-prefixed equivalent. Drop the prefixed-fixture parameter from each stub so the real fixture's session-scoped setup does NOT run before failing. Rationale: success criterion #4 explicitly requires "fail at fixture-resolution time with the prefixed names surfaced in the error" — pytest's stock "fixture 'config' not found" does fuzzy-match but does not guarantee surfacing the prefixed name as the canonical alternative. Alternative (clean delete): considered, fails SC#4 explicit-pointer requirement. **RESEARCH RESOLVED (32-RESEARCH.md §SHIM-07):** mechanism = `pytest.fail(MSG, pytrace=False)` with prefixed-fixture parameter dropped. The full SHIM-07 surface is six aliases (NOT four as SC#4 wording implies): `config`→`mcp_config`, `judge`→`mcp_judge`, `target_tool`→`mcp_target_tool`, `rubric_clarity`→`mcp_rubric_clarity`, `rubric_disambiguation`→`mcp_rubric_disambiguation`, `rubric_parameters`→`mcp_rubric_parameters`. `client` named in SC#4 does NOT exist in `_plugin.py` and is dropped from plan scope. EOL: v1.6 capstone deletes the stub-raises entirely; Phase 35 SHIM-09 regression gate must grandfather the six fixture names for v1.5.

- **D-07 (SHIM-08 mechanism — `mcp-test-framework` console-script):** Keep the `[project.scripts] mcp-test-framework = "..._deprecated_script:main"` entry in `pyproject.toml` and convert `_deprecated_script.py` from its current DeprecationWarning-emitting wrapper into a **hard-raise migration shim** that immediately prints an operator-tone three-part message naming `mcp-contracts` and exits non-zero (suggested exit code: 2, matching Typer's UsageError). Rationale: success criterion #3 says "cannot start the framework" — a hard-raise on first invocation satisfies that while preserving the loud-and-friendly migration-error pattern. Alternative (delete the `[project.scripts]` entry): considered, rejected because it gives operators only a shell-level "command not found" with zero pointer to `mcp-contracts`. **RESEARCH-FOR-PLAN:** confirm exit code expectations against `tests/framework/`; ensure the printed message renders via stdout vs stderr consistent with Phase 31 D-08's formatwarning visibility upgrade (loud, prefixed, separable from pytest's noise). EOL: v1.6 capstone deletes the `[project.scripts]` entry + `_deprecated_script.py` file entirely; Phase 35 SHIM-09 regression gate must grandfather both for v1.5.

- **D-08 (shared `_emit_legacy_surface_pointer` helper — RESEARCH-FOR-PLAN):** SHIM-01/02/03/06/07/08 all emit structurally identical operator-tone migration messages (legacy name → post-v1.4 name → next step). Phase 31 D-04 already raised the question of factoring `_emit_operator_error_for_validation_error` out of `cli.py` into a shared module so `_plugin.py` could call the same path. Phase 32 has the SAME pressure across six surfaces. Recommend the planner research the Phase 31 outcome (did `_operator_errors.py` get created? did the cli.py mapper stay private?) and either reuse / extend the existing helper or extract a new `_emit_legacy_surface_pointer(legacy=, replacement=, next_step=)` helper to keep all six SHIM messages textually consistent and grep-able. Not a blocker for any single plan; cuts duplication across all six. **HARD CONSTRAINT:** every emitted message must conform to `docs/ERROR-STYLE.md` three-part shape (summary / detail / next_step) and pass the regression checks in `tests/framework/unit/test_error_style.py`.

- **D-09 (regression-test placement):** Each Phase 32 plan ships its own positive test under `tests/framework/unit/` asserting (a) the legacy surface raises/fails as expected with the expected operator-tone message, and (b) the post-v1.4 replacement still works end-to-end. Phase 35 SHIM-09 capstone is the cross-surface regression-gate sweep (grep + import probes); Phase 32's per-plan tests are the loud-failure assertions that pin each migration message's text. Avoid duplicating SHIM-09's regex-sweep work in Phase 32 plans.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope + locked requirements
- `.planning/ROADMAP.md` §"Phase 32" — locked success criteria #1-4 (sdet package ModuleNotFoundError with pointer, Typer UsageError naming `--test-code` / `gen-test-classes`, legacy console-script cannot start framework, `tests/sdet/` not auto-discovered + unprefixed fixture failure surfaces prefixed names).
- `.planning/REQUIREMENTS.md` §"SHIM" — atomic requirements SHIM-01, SHIM-02, SHIM-03, SHIM-06, SHIM-07, SHIM-08 with traceability table; one-milestone deprecation window expiring at v1.5 is explicitly locked.
- `.planning/STATE.md` §"Decisions" 2026-05-23 — Phase 32 is the "orthogonal mechanical phase" after Phase 31; lists SHIM-07 stub-vs-delete as a planner-decision flag.

### Phase 31 precedent (load-bearing for D-03..D-08)
- `.planning/phases/31-config-surface-cleanup-drop-mcptf-config-file-cfg-sdet-alias/31-CONTEXT.md` — Phase 31's D-01..D-12 establish the operator-tone error texture, the `_emit_operator_error` three-part shape, the plugin-as-canonical-operator-surface pattern, and the formatwarning visibility upgrade — all directly reusable in Phase 32.
- `.planning/phases/31-*/31-SUMMARY-*.md` (six files) — verify what actually shipped for the shared `_operator_errors` extraction (D-04) so Phase 32 can reuse the helper rather than duplicate.

### Operator-error contract (shape + tone the rewrites must match)
- `docs/ERROR-STYLE.md` — operator-tone three-part error shape (summary / detail / next_step), pinned by `tests/framework/unit/test_error_style.py`. Every Phase 32 migration message MUST conform.
- `docs/LIBRARY-MODE.md` — names the post-v1.4 surfaces (`mcp_test_framework.test_code`, prefixed fixtures, `mcp-contracts` console-script); the pointer text in every Phase 32 message must agree with what these docs say.
- `docs/TEST-CODE-AUTHORING.md` — operator-facing walkthrough of the test-code authoring surface (`tests/test_code/`, `mcp_session`, `tool()`); destination of the SHIM-06 + SHIM-07 pointer messages.
- `README.md` — references the post-v1.4 names; sweep for any surviving `sdet`/`mcp-test-framework`/`--sdet`/`gen-sdet-classes` mentions in the same plan that removes them.

### Code touch-points (scout-verified during discussion)
- `src/mcp_test_framework/sdet/__init__.py` — 26-line re-export shim with `warnings.warn(DeprecationWarning, stacklevel=2)` + re-exports of `ToolCallError`, `ToolResponse`, `mcp_session`, `tool`. SHIM-01 target (D-03).
- `src/mcp_test_framework/cli.py` — Typer CLI entry-point; verify `--sdet` flag registration (SHIM-02 / D-04) + `gen-sdet-classes` command registration (SHIM-03 / D-04). Phase 31 left this file freshly edited — grep for current `sdet`/`SDET` references.
- `src/mcp_test_framework/_runner.py` L109, L141-143, L608, L797, L1271, L1285 — `tests/sdet/` dual-discovery fallback (SHIM-06 / D-05). Eight `# noqa: sdet-rename-shim` markers.
- `src/mcp_test_framework/fixtures.py` L130, L135, L153, L206 — `tests/sdet/` references in fixture path-validation (SHIM-06 / D-05). Four `# noqa: sdet-rename-shim` markers.
- `src/mcp_test_framework/_reporter.py` L219 — `tests/sdet/` reference in collection-source detection (SHIM-06 / D-05).
- `src/mcp_test_framework/_plugin.py` L12 (docstring naming the six aliases), L379, L392 (`mcp_target_tool` references), L433-502 (six unprefixed alias fixtures with DeprecationWarning bodies — verified via research: `config`, `judge`, `target_tool`, `rubric_clarity`, `rubric_disambiguation`, `rubric_parameters`). SHIM-07 target (D-06). Note: SC#4's `client` is NOT among the actual aliases; the four-name SC#4 list is imprecise reference text. Plan 32-05 enumerates all six.
- `pyproject.toml` L19-25 — `[project.scripts]` block with `mcp-contracts` + `mcp-test-framework` entries; legacy script wired to `mcp_test_framework._deprecated_script:main`. SHIM-08 target (D-07).
- `src/mcp_test_framework/_deprecated_script.py` — current DeprecationWarning-emitting wrapper; D-07 converts to hard-raise.

### Memory + carry-forward context (the WHY behind several decisions)
- Memory `feedback_phase_scope_intent.md` — Phase 32 is mechanical removal; resist any sub-agent reframing of D-03/D-04/D-05/D-06/D-07 as cross-cutting refactors. Each plan stays on its single surface.
- Memory `project_deprecation_warning_visibility.md` — Phase 25 finding; relevant if D-07's hard-raise message reuses Phase 31 D-08's formatwarning override or domain-UI banner.
- Memory `project_framework_primitives_sdet_safety_principle.md` — SEED-022; migration messages must NOT drift toward SUT-specific guidance.
- Memory `project_v1_3_close_push_and_scrub.md` — context for why every `# noqa: sdet-rename-shim` marker in src/ must be scrubbed alongside the surface removal it grandfathers (markers exist precisely because the shim is alive; they MUST die together).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Phase 31 `_emit_operator_error` three-part helper** — established texture (summary / detail / next_step) at the cli.py error-mapper. D-08 leans on extracting / extending this helper so all six Phase 32 migration messages share the same emit path. Phase 31 D-04 already flagged the question; verify the actual outcome before deciding.
- **`_plugin.py:pytest_configure`** — Phase 31 D-06/D-07 made this the canonical operator-error surface for config-load failures. Phase 32 SHIM-06 / SHIM-07 can register their hooks under the same plugin (no separate plugin file needed).
- **`warnings.formatwarning` override (Phase 31 D-08)** — if Phase 31 shipped a domain-UI-prefixed formatter, Phase 32 D-05 (the `tests/sdet/` warn-on-presence) inherits it for free.

### Established Patterns
- **Operator-tone error contract** — three-part shape pinned by `tests/framework/unit/test_error_style.py`. Every D-03..D-07 message must conform; new migration-message tests (D-09) extend the same fixture file.
- **`# noqa: sdet-rename-shim` markers** — convention from v1.4 phase 25: every shim source line carries this marker. Phase 32 plans MUST scrub the marker alongside the line it grandfathers; orphan markers are a regression vector.
- **Hidden Typer intercept** — Typer supports `hidden=True` on commands and `hidden=True` on `typer.Option`. D-04 uses this pattern to keep `--sdet` / `gen-sdet-classes` discoverable to legacy users while excluded from `--help`.
- **Stub-raise fixture** — the inverse of Phase 25's deprecation-aliasing pattern. The fixture name stays registered (so pytest's fixture resolver finds it), but the body raises immediately. Preserves the surface for the migration error without serving any real value.

### Integration Points
- **`_plugin.py` ↔ `cli.py` shared error surface** — Phase 31 D-04 RESEARCH-FOR-PLAN flag; Phase 32 D-08 has the same pressure. Whichever shared module emerged from Phase 31, Phase 32 imports it.
- **`pyproject.toml` `[project.scripts]` ↔ `_deprecated_script.py`** — D-07 keeps the wiring but inverts the body. The console-script's main() goes from "deprecation-warn + delegate" to "hard-raise + exit nonzero".
- **`pytest_collectstart` ↔ `_runner.py` discovery path-list** — D-05 hooks at collection time; the existing `tests/test_code` / `tests/sdet` path-pair in `_runner.py` L1285 is the surface to scrub + replace with a `tests/sdet` legacy-presence detector.

</code_context>

<specifics>
## Specific Ideas

- Phase 31's CONTEXT.md is the textural reference for every Phase 32 migration message — three-part shape, no SUT-specific guidance, no migration-doc cross-reference (the migration doc was deleted in V1DROP-01), pointer-only-to-the-new-name. Treat 31-CONTEXT.md as a load-bearing reference, not just history.
- The six SHIMs are MECHANICALLY orthogonal — no shared fixture-graph, no shared module-load order between any two. Plan-decomposition D-01 / D-02 chose 1:1 specifically to preserve this independence in commit history. Sub-agents that propose "consolidate SHIM-06 + SHIM-07 because both are pytest" or "merge SHIM-01 + SHIM-08 because both are import-surface" should be redirected — each plan stays on its single surface.
- The shared-helper extraction (D-08) is a FOOTPRINT-REDUCTION nice-to-have, not a per-plan blocker. If Phase 31 already shipped `_operator_errors.py`, every Phase 32 plan imports it. If Phase 31 did not, the first Phase 32 plan (32-01 SHIM-01) extracts it AND uses it; subsequent plans import it. Avoid stalling 32-02..32-06 waiting for the extraction.

</specifics>

<deferred>
## Deferred Ideas

- **v1.6 capstone clean-deletion** — every surviving surface from Phase 32 (the `sdet/` directory, the `--sdet` + `gen-sdet-classes` hidden intercepts, the six stub-raise fixtures, the `_deprecated_script.py` + its `[project.scripts]` entry) is grandfathered for v1.5 by Phase 35 SHIM-09. v1.6 capstone deletes them outright (no migration message; just `ModuleNotFoundError`, stock Typer UsageError, fixture-not-found, shell command-not-found). Capture as v1.5 close deferral.
- **`docs/MIGRATION-v1-to-v2.md`-style content archival for the v1.4→v1.5 shim retirement** — the SHIM-01..08 migration story might warrant a single-line `CHANGELOG.md` entry or `.planning/MILESTONES.md` v1.4 footnote. Out of Phase 32 scope; nice-to-have for historical record.
- **Phase 35 SHIM-09 regression-gate grandfathering list** — the gate must explicitly allow: the single `sdet/` directory (D-03), the two hidden Typer intercepts (D-04), the six unprefixed fixture names (D-06), the `mcp-test-framework` `[project.scripts]` entry (D-07), the `_deprecated_script.py` file (D-07), and the `tests/sdet/` warn-on-presence path-string in `_plugin.py` (D-05). Forward to the Phase 35 planner so the gate is calibrated correctly.

### Reviewed Todos (not folded)

None — `gsd-sdk query todo.match-phase 32` returned `todo_count: 0`; no todos to review.

</deferred>

---

*Phase: 32-Surface-shim removals — CLI + package + fixtures + discovery*
*Context gathered: 2026-05-24*
