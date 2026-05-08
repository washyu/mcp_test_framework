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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 7 (incl. 02.1, 04.1 inserts) | 22 | First end-to-end MVP; introduced the discuss-phase / plan-check / verify-work rhythm |
| v1.1 | 6 (incl. 11 gap-closure) | 17 | Added explicit gap-closure phase pattern; multi-tool generalization without breaking the black-box rule |

### Cumulative Quality

| Milestone | Source LOC | Reqs Satisfied | Audit-Clean at Close |
|-----------|-----------|----------------|----------------------|
| v1.0 | ~3,562 | 29/29 | ✓ |
| v1.1 | ~5,784 | 25/25 (54/54 cumulative) | ✓ (after Phase 11) |

### Top Lessons (Verified Across Milestones)

1. **Audit before archive.** v1.0's audit caught WR-05 (SIGINT handler) before close. v1.1's audit caught W-1..W-6 paper drift before close. Both milestones shipped audit-clean — the rhythm is established.
2. **Black-box discipline scales.** v1.0 proved the rule on a single tool; v1.1 generalized to N-tools-per-server without softening it. Mechanical enforcement (lint + runtime guard + banned-imports test) made the discipline cheap to keep.
3. **Insert-phase pattern works for in-flight scope changes.** v1.0 used 02.1 + 04.1 inserts; v1.1 didn't need any. The capability is ready for v1.2's likely scope shifts.
