# Phase 16: Reporter UX overhaul - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-11
**Phase:** 16-reporter-ux-overhaul
**Areas discussed:** Pre-run vs post-run structure, "Defaulting" bucket meaning, --explain output design, N=70 readability + render polish

---

## Pre-run vs post-run structure

| Option | Description | Selected |
|--------|-------------|----------|
| Digest pre-run, rows + result post-run | Full digest before pytest; per-tool rows + summary after. Single source of truth. | ✓ |
| Digest pre-run AND post-run recap | Digest twice (or condensed second time) for scrolled-up operators. | |
| Digest pre-run only; minimal post-run | Smallest footprint; departs from Phase 14's per-tool rows shape. | |

**User's choice:** Digest pre-run, rows + result post-run.
**Notes:** Cleanest single-source-of-truth; reuses Phase 14's existing `_render_per_tool_rows` and `_render_summary_line` unchanged. Crash semantics handled by Phase 14 D-16 — operator sees the digest before any crash error.

### Follow-up: Test-plan count source

| Option | Description | Selected |
|--------|-------------|----------|
| Computed: running_tools × cases_per_tool | Module constant `CASES_PER_CONTRACT_TOOL = 10`. With --with-framework: append "+ framework self-tests (~107)" or precise count via collect-only. | |
| pytest --collect-only -q pre-flight | Always exact count; adds ~0.3-0.8s startup overhead + parse step. | |
| Computed for contract; defer framework count | Pre-run: "20 contract cases" computed. With --with-framework: "+ framework self-tests" (no number). Post-run summary shows real totals. | ✓ |

**User's choice:** Computed for contract; defer framework count.
**Notes:** Avoids collect-only round-trip and framework-count maintenance burden. `CASES_PER_CONTRACT_TOOL = 10` becomes a module constant in `_runner.py` with a unit test that introspects the contract test and asserts equality so drift is visible.

---

## "Defaulting" bucket meaning

| Option | Description | Selected |
|--------|-------------|----------|
| Unlisted = Defaulting; skip:true = Skipping | Three buckets map to Phase 13's three states. (a) unlisted → Defaulting; (c) skip:true → Skipping. | |
| Defaulting = framework-default judges | Orthogonal to skip/run state. Counts tools running WITHOUT a per-tool `judges` override. | |
| Drop 'Defaulting' from the digest | Two buckets only: Running + Skipping. (a)/(c) distinction lives in skip-reason text under --explain. Updates UX-01 wording. | ✓ |

**User's choice:** Drop 'Defaulting' from the digest.
**Notes:** Deliberate divergence from REQUIREMENTS.md UX-01's literal "defaulting count" wording. The locked skip-reason constants (`"not selected in config"` for state a, `"explicit skip in config"` for state c) carry the distinction inside `--explain` output. CONTEXT.md D-04 flags this obsolescence so the verification step records it.

---

## --explain output design

### Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Skipped only (one line per skipped tool) | `--explain` expands ONLY the Skipping hint. Running and Judges lines unchanged. Closest to SEED-008 mockup. | ✓ |
| Skipped + per-tool judges | Also expands Running line into a judges-per-tool table. | |
| Skipped + running names + judges | Full expansion (everything verbose). Largest footprint. | |

**User's choice:** Skipped only.
**Notes:** Per-tool judges-per-tool expansion table is deferred (could surface under a future `--judges` flag or `--explain --judges` if operators ask). Phase 16 ships the minimal explain surface.

### Location

| Option | Description | Selected |
|--------|-------------|----------|
| Inline after digest, before pytest runs | Pre-run digest → blank → Skipping (N): block → blank → pytest. One scroll-up for full pre-run state. | ✓ |
| After post-run summary (end of output) | Result first; explain at the end as reference detail. Requires scrolling. | |
| Both: inline pre-run AND end-of-run reminder | Most discoverable; introduces visual repetition. | |

**User's choice:** Inline after digest, before pytest runs.

---

## N=70 readability + render polish

### Long 'Running' list

| Option | Description | Selected |
|--------|-------------|----------|
| Truncate to first K + '... (M more)' | K=5 keeps digest single-line. Full list under --explain (extend explain to running too). | |
| Wrap with continuation indent | Multi-line at wide N; no info hidden but digest height varies. | |
| Always require --explain past K | Symmetric with Skipping line; most aggressive hiding. | |
| Inline always (status quo) | Phase 14 behavior. Defer N=70 running-list polish to a future phase. | ✓ |

**User's choice:** Inline always (status quo).
**Notes:** Operator-selected scopes are small in practice (homelab-mcp safe-by-default = 2 of 58 running). The Skipping line's `(use --explain to list)` hint already solves the N=70 case for the high-cardinality bucket. Running-list polish deferred to v1.3 if/when an operator scope grows past ~10 tools and the digest becomes visually unwieldy.

### Per-judge scores on rows

| Option | Description | Selected |
|--------|-------------|----------|
| Extract scores; show on PASS rows too | SEED-011 §2 mockup verbatim: `✓ PASS (clarity 5/5)`. Most informative. | |
| Keep PASS minimal; per-judge breakdown only under --debug | PASS stays `✓ PASS`. --debug appendix gains a per-judge block. Lowest implementation risk. | ✓ |
| Show scores on FAIL only; PASS stays bare | Middle ground: per-judge data where it matters (failures). | |

**User's choice:** Keep PASS minimal; per-judge breakdown only under --debug.
**Notes:** Default PASS rows stay `✓ PASS`. UX-03's "aggregates per-judge reasoning into the domain UI's tail" is satisfied by the existing FAIL row's `— <reason>` surface (Phase 14 D-08). Per-judge expansion lives under `--debug` (Phase 16 D-11); if XML extraction proves fiddly, that part defers to v1.3 without blocking the rest of the phase.

### JUnit XML embedding of the digest

| Option | Description | Selected |
|--------|-------------|----------|
| No — stdout only | Digest stdout-only; JUnit XML stays pytest's native shape. Smallest surface. | ✓ |
| Yes — add to <system-out> | Inject digest text into testsuite/system-out. CI tools surface it inline. | |
| Yes — add as <properties> | More machine-parseable; requires defining a property schema. | |

**User's choice:** No — stdout only.
**Notes:** Phase 16 keeps Phase 14's "wrapper owns digest, pytest owns XML" separation. Revisit if/when a real CI consumer asks for embedded digest.

---

## Claude's Discretion

Captured in CONTEXT.md §"Claude's Discretion" block under `<decisions>`. Highlights:

- Plan ordering within Phase 16 (suggested 5-plan sequence).
- Whether to delete `_render_header` or keep it as a tested internal helper (with a rename).
- Exact format of `--debug` per-judge breakdown block (D-11).
- Whether the digest banner `"="*40` becomes a module constant.
- Whether to add a `--no-explain` inverse Typer flag (probably no).

---

## Deferred Ideas

Captured in CONTEXT.md `<deferred>` block. Highlights:

- v1.3: Running-list N=70 polish, per-tool judges-per-tool expansion under --explain, per-judge scores on PASS rows, JUnit XML embedding, `rich` library upgrade, live per-tool progress streaming.
- Post-phase quick-task candidate: amend REQUIREMENTS.md UX-01 wording to drop "defaulting count" (D-04 divergence).
- `mcp-test-framework explain` standalone command (no pytest run; just digest + explain) — defer to a follow-up if requested.

---

*Phase: 16-reporter-ux-overhaul*
*Discussion log: 2026-05-11*
