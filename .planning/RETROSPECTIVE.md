# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.1 — Multi-Tool + Isolation + JUnit

**Shipped:** 2026-05-08
**Phases:** 6 (06–11) | **Plans:** 17 | **Timeline:** 2 days (2026-05-07 → 2026-05-08)

### What Was Built

- **Per-session host-state isolation** (Phase 06): `_isolation.py` module + `_isolated_home` fixture; `HOME`/`USERPROFILE` redirect, env-passthrough allowlist, null keyring backend. ISOL-03 verified empirically (3/3 sha256 hashes byte-identical pre/post run; zero tempdir orphans).
- **Multi-tool discovery & parameterized testing** (Phase 07): `pytest_generate_tests` + indirect `target_tool` parametrize discover and exercise every tool the connected MCP server advertises, with `<test>[<tool>]` test IDs flowing to terminal + JUnit.
- **Per-tool config registry** (Phase 08): `tools.<name>` config blocks (skip / call_arguments / judges) with `extra="forbid"` + `version: 1`; new `mcp-test-framework config-init` Typer subcommand; forward-compat `setup:`/`depends_on:` reservations for SEED-004.
- **JUnit XML + per-tool reporting** (Phase 09): `--junit-xml=PATH` flag, new `_reporter.py` pytest plugin, 29 unit tests + 3 live tests pinning OUTPUT-01..03.
- **v1.1 documentation** (Phase 10): README sections (Per-tool config, Isolation guarantee, CI integration with copy-pasteable GHA snippet) + EXTENDING.md walkthroughs; snippet-correctness regression suite pins examples against drift.
- **v1.1 audit gap closure** (Phase 11): closed all 5 paper-only audit gaps (W-1, W-3, W-4, W-5, W-6) before archive — 25/25 requirements Complete.

### What Worked

- **Black-box rule held throughout v1.1.** `ruff TID251` + `sys.modules` guard + banned-imports test never fired a false positive; multi-tool discovery worked without ever reading homelab-mcp source.
- **Phase 06 first ordering paid off.** Isolation as a prerequisite for Phase 07's expanded spawn pressure prevented the v1.0-era "tests clobber my real homelab-mcp state" usability bug from getting strictly worse under multi-tool.
- **`pytest_generate_tests` indirect parametrize** integrated cleanly with pytest-asyncio strict mode and the existing session-scoped `mcp_client` fixture — no Phase 04.1-style anyio cancel-scope rework required.
- **Forward-compat reservations honored.** TOOLCFG-03 (`setup:`/`depends_on:`) and TOOLCFG-04 (string judge IDs) keep SEED-003/SEED-004 paths additive, not breaking. The seed/branch discipline from v1.0 carried into v1.1 cleanly.
- **Phase 11 as a planned gap-closure phase** (not retrofitted) kept the v1.1 audit-clean state without requiring a v1.1.1 patch milestone.

### What Was Inefficient

- **Worktree path-confusion bug surfaced in Phase 11 wave 1.** All 4 parallel executor agents wrote to the orchestrator worktree path instead of their own worktrees. Files were disjoint so nothing was lost, but plan 11-03's commits initially landed only on its agent worktree branch — recovered via `git cherry-pick` from dangling commits after that branch was prematurely deleted. Risk-free this time (docs-only); would be costly with source conflicts.
- **Auto-extracted accomplishments from `summary-extract`** were uneven (multiple `null` and a "1." numbered-list fragment slipped into MILESTONES.md before manual rewrite). One-liner field discipline in plan SUMMARY frontmatter would help downstream archiving.
- **Quick-task filename convention drift** (`260506-qxs-PLAN.md` vs canonical `PLAN.md`) caused the milestone-close audit to flag an actually-complete task as `[missing]`. Trivial rename fix, but a noisy false alarm.
- **Post-merge test gate hit a non-deterministic LLM judge flake** (`test_description_disambiguation[suggest_deployments]` score 3 vs threshold 4) on phase-11 close — added an option to investigate-or-continue cycle that wasn't really informative since Phase 11 made zero source changes.

### Patterns Established

- **Audit-driven gap-closure phase** (Phase 11) at end of milestone: run `/gsd-audit-milestone` before `/gsd-complete-milestone`; any paper-only drift becomes its own scoped phase rather than blocking archive or being deferred as tech debt.
- **Plant-Seed for Long-term Vision items**: SEED-001..005 now sit dormant with explicit trigger conditions; they auto-surface as v1.2+ scope candidates without polluting the active backlog.
- **Per-session sha256-verified isolation** as the empirical acceptance signal for any "test runs don't mutate user state" claim. Stronger than mtimes (D-09 strengthening).
- **Forward-compat reservations in config schemas** (`extra="forbid"` + ignored-but-reserved fields) — locks the strict shape today while keeping seed activations additive.

### Key Lessons

1. **Audit before close, close paper gaps in-milestone.** The W-1..W-6 gap-closure phase added one day to the milestone and saved a v1.1.1 patch milestone plus the integrity-loss risk of an "almost audit-clean" archive.
2. **Parallel executor agents in worktrees can drift to the orchestrator's CWD.** Whenever a wave parallelizes 3+ executors, verify post-wave that each agent's commits actually live on its own worktree branch — don't rely on the harness alone. (Recovery via git reflog + cherry-pick worked, but the dangling-commit window is real.)
3. **Cross-platform parity decisions need explicit Branch B documentation.** WR-04 (POSIX `USER` vs Windows `USERNAME`) was a one-paragraph rationale, but landing it in EXTENDING.md (not just the source comment) prevents future contributors from "fixing" a deliberately-narrow allowlist.
4. **Plan SUMMARY frontmatter `one_liner:` field discipline matters at archive time.** When plans omit it, downstream `summary-extract` produces null entries that the milestone CLI dumps verbatim into MILESTONES.md.

### Cost Observations

- **Model mix:** primarily Opus 4.7 orchestrator + Opus 4.7 executors (inherited via `model_profile: inherit`). Verifier and code-reviewer at same tier.
- **Sessions:** ~5–6 distinct work sessions across the 2-day milestone (Phase 06 keyring recon → Phase 07 multi-tool → Phase 08 config registry → Phase 09 JUnit/reporter → Phase 10 docs → Phase 11 cleanup).
- **Notable:** Phase 11 wave-1 parallel executor recovery (cherry-pick after worktree branch deletion) was the only material non-happy-path cost. Everything else hit the standard discuss → plan → execute → verify rhythm.

---

## Milestone: v1.3 — Homelab Scenario Testing

**Shipped:** 2026-05-15
**Phases:** 9 (17, 18, 19, 20, 21, 21.1, 22, 23, 24) | **Plans:** 42 | **Timeline:** 3 days (2026-05-12 → 2026-05-15)

(v1.2 close didn't backfill RETROSPECTIVE.md — its detail lives in [milestones/v1.2-ROADMAP.md](milestones/v1.2-ROADMAP.md) and the Cross-Milestone Trends tables below.)

### What Was Built

- **Schema-driven codegen** (Phase 17): `mcp-test-framework gen-sdet-classes` introspects a live MCP server and writes typed `<Tool>Params` (Pydantic from `inputSchema`) + `<Tool>Response` (typed when `outputSchema` declared, stub-subclass of `ToolResponse` otherwise) + `_REGISTRY` per server slug. `ToolResponse` base provides uniform `.raw`/`.data`/`.text`/`.is_error` regardless of schema declaration.
- **SDET test surface + typed errors** (Phase 18): `tests/sdet/` discovery scope, `mcp_session` + `tool(name)` fixtures, `--sdet` CLI flag with full composability (`-q`, `--explain`, `--debug`, `--raw`, `--with-framework`), `ToolCallError` typed exception with `.tool`/`.code`/`.message`/`.raw`, em-dash failure detail surfacing in default-mode FAIL rows, structured `--- ToolCallError dump ---` block in the `--debug` appendix.
- **Stateful primitives + domain UI integration** (Phase 19): yield-fixture cleanup-on-failure contract pinned by `test_state_cleanup_on_failure.py` (counter+xfail strict), `HomelabConfig`/`HomelabProxmoxConfig` sub-models, `_render_per_tool_rows` extended with synthetic `<group>::<row_label>` scenario keys, pytest-order recipe absorbed into `docs/SDET-AUTHORING.md`.
- **v1.3 scope correction — SEED-022 reframe** (Phase 20): deleted SUT-specific dogfood (`test_proxmox_vm_lifecycle.py`, `test_basic_call.py`) from `tests/sdet/`; PREFLIGHT-01/02 dropped from REQUIREMENTS.md; CLEANUP-DOGFOOD-01 / CODEGEN-COVERAGE-01 / REQ-SCRUB-01 added; mock-fixture codegen unit tests replace the killed live-Proxmox coverage. Zero `src/` changes.
- **SDET authoring docs + README parity** (Phase 21): `docs/SDET-AUTHORING.md` (11 H2s, worked example, codegen regen, ordering, skip recipe, ToolCallError handling), README §SDET-scenarios with char-for-char renderer parity (operator-approved FAIL-polarity override), CLAUDE.md dual-persona note.
- **SDET generated output relocation** (Phase 21.1, INSERTED): `cfg.sdet.generated_root` as REQUIRED config field with no env override; both write (`gen-sdet-classes`) and load (`mcp_session`) consume it; `mcp_session` switched from `import_module` to `spec_from_file_location` with `submodule_search_locations`; **`src/mcp_test_framework/sdet/generated/` deleted (60 files)** — SEED-022 structurally enforced.
- **Planning-ID scrub** (Phase 22): operator-facing `--help` and entire `src/mcp_test_framework/` tree show 0 hits for the locked planning-ID regex; regression test `test_no_planning_ids_in_src.py` pinned; no `# noqa` allowlist (D-04).
- **Test suite debt cleanup** (Phase 23, INSERTED): closed 12 fails + 1 error in `tests/framework/` via Config(sdet=_SDET_STUB) propagation, `parents[2]→parents[3]` mechanical bump post Phase 15 folder split, README banned-token semantic rewrite, missing `tests/contract/test_mcp_tool_contract.py` restore. Close-gate green at 575 passed / 0 failed / 0 errored. Zero `src/` changes.
- **Tool-call serializer fix** (Phase 24, INSERTED): `_tool_factory.py:101` switched to `model_dump(mode="json", exclude_unset=True)`; SDET-omitted optionals stay off the wire while explicit `field=None` still flows null (SEED-022 user-intent discriminator); 3 payload-asserting tests + renamed kwargs-spy test lock all three behaviors; framework suite now 578 passed.

### What Worked

- **Codegen-first ordering paid off.** Phase 17's seam (typed `<Tool>Params`/`<Tool>Response` + `_REGISTRY` + `ToolWrapper`) was the structural anchor every downstream phase hung off. Phases 18–21 imported the generated classes without the stringly-typed alternative ever surfacing as tech debt.
- **SEED-022 reframe caught a scope drift mid-flight.** Phase 19's `requires_homelab(proxmox=True)` marker factory baked SUT subsystem knowledge into framework API. Phase 20 retroactively deleted the SUT-specific dogfood + replaced it with mock-fixture codegen tests, then Phase 21.1 structurally enforced the principle by deleting `src/.../sdet/generated/`. The framework's `src/` tree now contains zero SUT-specific code — a stronger invariant than v1.0's black-box rule (no SUT imports) because it also forbids SUT-specific outputs.
- **Operator-approved FAIL-sample override (Phase 21 Plan 21-02).** Live Proxmox run hit upstream homelab-mcp `inputSchema` bug on `create_proxmox_vm`. Operator chose option (a) at the checkpoint to embed FAIL output verbatim — char-for-char doc-mirroring contract preserved, SEED-022 teaching strengthened (framework surfaces upstream contract bugs as real test failures rather than masking them).
- **Phase 23 INSERTED as test-debt cleanup.** Phase 20 UAT surfaced 12 pre-existing test failures the v1.2 folder split + v2 schema migration had left behind. Inserting Phase 23 between Phase 22 and Phase 24 isolated the serializer change's ripple cleanly — Phase 24 inherited a green suite.
- **Plan 24-02 regen-failed contract for live-UAT.** Proxmox keyring was unreachable from the agent's PowerShell subprocess. Plan 24-02 explicitly authored a partial-completion contract: Tasks 1+2 (SDET-AUTHORING soften + REQUIREMENTS row) committed; Task 3 (README PASS-sample re-capture) deferred to STATE.md `live-uat` row. This pattern is reusable for future live-stack-dependent doc captures.
- **`exclude_unset=True` over `exclude_none=True` for serializer.** SEED-022 user-intent discriminator: distinguish SDET-omitted (`unset`) from SDET-explicitly-null (`set`). `exclude_none` would mask upstream null-handling bugs; `exclude_unset` lets the framework's default path stay clean while preserving the SDET's ability to explicitly test null-handling.

### What Was Inefficient

- **PREFLIGHT-01/02 scope misjudged at v1.3 framing.** Original requirements baked SUT subsystem knowledge into framework API. Required a mid-milestone reframe (Phase 20) + a follow-on structural enforcement (Phase 21.1). The reframe was clean but cost ~1 phase of churn. Catch the SEED-022 violation at v1.3 scoping next time — anything named `requires_<subsystem>(...)` is a flag.
- **Phase 23 INSERTED, not planned.** Pre-existing `tests/framework/` debt from v1.2's folder split surfaced as a Phase 20 UAT blocker. Could have been caught earlier by running `tests/framework/` green-gate at v1.2 close. Add to v1.2-style milestone-close gates.
- **REQUIREMENTS.md traceability table went stale.** Most v1.3 entries showed `Pending` despite VERIFICATION-evidenced `Complete`. Plans use inconsistent frontmatter (`requirements:` vs `requirements-completed:`); 11 of 29 REQ-IDs were missing from any plan's `requirements-completed:` array. The audit caught it; bulk-flip happened at close. Tighten plan-frontmatter discipline next milestone.
- **ROADMAP.md Progress table drift.** Showed Phase 19 as `0/4 Not started` and Phase 21 as `1/4 In Progress` while both phases had completed days earlier. Mechanical issue with how `gsd-execute-phase` writes back; flag for v1.4 tooling fix.
- **Live-UAT cycles.** Phase 19 → Phase 20 reframe and Phase 21 polarity override both originated in live-Proxmox runs that hit operator-environment constraints. A hello-world MCP fixture (deferred-item L182) would have caught these earlier; promote in v1.4.

### Patterns Established

- **SEED-022 (framework primitives only) — structurally enforced.** The framework's `src/` tree now contains zero SUT-specific code; codegen output is operator-controlled via `cfg.sdet.generated_root`. Any future "the framework should know about subsystem X" proposal is automatically a violation — re-scope to a generic primitive or push into SDET-side recipe.
- **Hybrid mock-fixture + live-gated testing (Phase 20 + Phase 21.1).** Synthetic tool lists driven through the codegen pipeline into `tmp_path` give CI-safe coverage of the codegen mechanism; live-gated tests (`@pytest.mark.live_homelab`) cover end-to-end against the real SUT.
- **Documented regen-failed partial-completion contract** (Plan 24-02 L429-L447). Reusable template for any phase plan that depends on a live external service the agent can't reach.
- **`exclude_unset=True` serializer discriminator** for user-intent semantics in tool wrappers. SDET-omitted ≠ SDET-explicitly-null; let upstream see the difference.
- **char-for-char renderer parity in README docs** (Phase 16 / SEED-008 doc-mirroring contract, extended through v1.3). Output blocks in README are the runner's actual emission (with HTML-comment "re-snapshot when format changes" cues for future maintainers); snippet-correctness tests pin against drift.

### Key Lessons

1. **Catch SEED-022 violations at scoping, not mid-flight.** `requires_<subsystem>(...)` API surfaces are the canonical tell. Anything that names a specific external SUT is suspect; if a framework primitive needs to know which subsystem is reachable, the framework boundary has moved too far. v1.3 cost a Phase 20 reframe + Phase 21.1 structural enforcement to walk this back.
2. **A 9-phase milestone in 3 days requires inserted phases (21.1, 23, 24).** Scope discoveries during execution are normal at this density; planning for them via INSERTED-phase capacity beats trying to land the original 5-phase plan unchanged.
3. **REQUIREMENTS.md traceability is the audit signal.** Stale `Pending` checkboxes hide real coverage; the audit-milestone 3-source cross-reference (VERIFICATION + SUMMARY + traceability) caught all v1.3 drift, but the noise threshold rises every milestone. Enforce plan-frontmatter `requirements-completed:` consistency in v1.4.
4. **Operator override gates are working.** Phase 21 Plan 21-02 demonstrated the value of an explicit human-verify checkpoint — operator chose option (a) on PASS/FAIL polarity in real-time, the override was recorded in 21-VERIFICATION.md frontmatter, and verification flowed cleanly with the deviation acknowledged. Keep using human-verify checkpoints for live-stack runs.

### Cost Observations

- **Model mix:** primarily Opus 4.7 orchestrator + Opus 4.7 executors. Verifier and integration-checker mostly on Sonnet 4.6 per config defaults.
- **Sessions:** ~7-9 distinct work sessions across the 3-day milestone, with Phase 19 → 20 reframe + Phase 21 override forming two natural session boundaries.
- **Notable:** Phase 23 + Phase 24 + Phase 21.1 are all INSERTED phases — 3 of 9 (33%). The discuss → plan → execute → verify cycle ran ~9 times in 3 days; tight loops, not always clean.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 7 (incl. 02.1, 04.1 inserts) | 22 | First end-to-end MVP; introduced the discuss-phase / plan-check / verify-work rhythm |
| v1.1 | 6 (incl. 11 gap-closure) | 17 | Added explicit gap-closure phase pattern; multi-tool generalization without breaking the black-box rule |
| v1.2 | 5 | 30 | Operator-first refactor: domain UI replaces pytest framing; `tools:` becomes opt-in allowlist; config v1→v2 migration; CLEAN-03 closed via /gsd-quick |
| v1.3 | 9 (incl. 21.1, 23, 24 inserts) | 42 | SDET persona added; codegen surface + SEED-022 structural enforcement (`src/.../sdet/generated/` deleted); regen-failed partial-completion contract pattern |

### Cumulative Quality

| Milestone | Source LOC | Reqs Satisfied | Audit-Clean at Close |
|-----------|-----------|----------------|----------------------|
| v1.0 | ~3,562 | 29/29 | ✓ |
| v1.1 | ~5,784 | 25/25 (54/54 cumulative) | ✓ (after Phase 11) |
| v1.2 | ~7,700 | 31/31 (85/85 cumulative) | ✓ (CLEAN-03 closed via /gsd-quick post-audit) |
| v1.3 | ~6,098 src / ~19,137 src+tests | 27/29 satisfied + 2 partial-by-design (114/114 cumulative; 2 close-by-design on live-UAT) | tech_debt (operator-approved deferrals tracked) |

### Top Lessons (Verified Across Milestones)

1. **Audit before archive.** v1.0's audit caught WR-05 (SIGINT handler) before close. v1.1's audit caught W-1..W-6 paper drift. v1.2's audit caught CLEAN-03 (3-line patch via /gsd-quick). v1.3's audit surfaced REQUIREMENTS.md traceability staleness + 2 operator-approved live-UAT deferrals. Four for four — the rhythm is established.
2. **Black-box discipline scales, SEED-022 extends it.** v1.0 forbade SUT imports. v1.1–v1.2 generalized to N-tools-per-server without softening it. v1.3 added the structural-enforcement layer: framework `src/` contains zero SUT-specific code (output paths, generated artifacts, preflight markers all live outside the framework boundary). Each milestone tightened the boundary; none softened it.
3. **Insert-phase pattern is load-bearing.** v1.0 used 02.1 + 04.1; v1.1 used 11; v1.2 used 0; v1.3 used 21.1 + 23 + 24. The capability is critical for milestones with surface area > ~5 phases — mid-flight scope discoveries are normal, not exceptional.
4. **Plan-frontmatter discipline rots over time.** v1.0's `requirements-completed:` arrays were clean. By v1.3, 11 of 29 REQ-IDs were missing from any plan's array despite being VERIFIED in their phase VERIFICATION.md. Either tighten the field's enforcement in plan-checker, or accept that traceability table requires bulk-flip at close.
5. **Operator-as-checkpoint pattern works for live-stack-dependent decisions.** Phase 21 Plan 21-02's `checkpoint:human-verify` gate let the operator choose option (a) on PASS/FAIL polarity when the live Proxmox run revealed an upstream contract bug. Override recorded in VERIFICATION.md frontmatter; verification flowed clean. Use freely for any phase whose acceptance depends on operator-environment-only state.
