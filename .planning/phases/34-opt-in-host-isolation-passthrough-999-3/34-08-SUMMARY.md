---
phase: 34-opt-in-host-isolation-passthrough-999-3
plan: 08
subsystem: operator-facing-docs
tags: [docs, readme, library-mode, error-style-registry, extending-scrub, host-isolation, isol-06]
requires:
  - "34-02 (operator-tone literal_error rejection branch -- next_step pointer text registered in ERROR-STYLE.md)"
  - "34-05 (xdist clamp banner verbatim text -- quoted in README + LIBRARY-MODE.md)"
  - "34-07 (config-init scaffold trade-off comment block -- prose aligns with README + LIBRARY-MODE.md worked example)"
provides:
  - "README ## Host isolation: strict vs passthrough section (50 lines) -- Proxmox repro + xdist clamp banner verbatim + SEED-022 + no-keyring-faking citations inline"
  - "docs/LIBRARY-MODE.md ## Host isolation section (57 lines) anchored at #host-isolation -- resolves cli.py error-mapper next_step pointer from plan 34-02"
  - "docs/ERROR-STYLE.md host_isolation literal_error entry -- three-way lock with cli.py branch + pin test test_error_style_host_isolation_literal_rejection"
  - "docs/EXTENDING.md confirmed clean of stale ALWAYS-ON / --no-isolation references (no edit needed)"
affects:
  - .planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-VERIFICATION.md (next-step: phase-level verification)
  - Future v1.6+ work touching host_isolation field semantics (will need to update both prose sections + ERROR-STYLE.md entry to keep three-way lock)
tech_stack_added: []
tech_stack_patterns:
  - "Three-way doc/code/test lock for operator-tone errors -- ERROR-STYLE.md entry names the pinned test by id so future drift is mechanically detectable"
  - "Trade-off citations land inline in the worked example section, not as separate sidebar -- per CONTEXT.md Claude's-Discretion lock"
  - "Phase 33 D-03 doc-block shape (~25-50 lines per primary doc) carried forward for ISOL-06 -- consistent operator-facing doc rhythm across v1.5"
key_files_created:
  - .planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-08-SUMMARY.md
key_files_modified:
  - README.md
  - docs/LIBRARY-MODE.md
  - docs/ERROR-STYLE.md
decisions:
  - "Heading text is '## Host isolation' (LIBRARY-MODE.md) -- slugifies to #host-isolation, matching the exact anchor that plan 34-02's cli.py error-mapper next_step pointer references"
  - "README heading text is '## Host isolation: strict vs passthrough' -- more descriptive than LIBRARY-MODE.md because the README is a top-level entry point where readers don't yet have library-mode context; the LIBRARY-MODE.md anchor MUST be the shorter slug, the README anchor doesn't need to resolve any external pointer so descriptiveness wins"
  - "Worked example is the Phase 30 UAT-1 Proxmox credential repro (real, not synthetic) -- CONTEXT.md <specifics> lock honored; grep 'create_proxmox_vm' hits both README and LIBRARY-MODE.md"
  - "EXTENDING.md was already clean of stale ALWAYS-ON / --no-isolation / always-on references -- no edit needed; Task 4 documented as no-op rather than forced rewording"
  - "Three-way lock for the host_isolation literal_error: ERROR-STYLE.md entry references the pin-test by id (test_error_style_host_isolation_literal_rejection); future drift in any of (doc / cli.py branch / pin test) breaks the others"
requirements_completed: [ISOL-06]
metrics:
  duration: ~75 minutes (RED+REVIEW+approval round-trip across 3 doc-task commits + this metadata close)
  tasks_completed: 5
  files_modified: 3
  files_created: 1
  completed_date: 2026-05-27
---

# Phase 34 Plan 08: ISOL-06 Documentation Summary

**ISOL-06 docs landed: README + docs/LIBRARY-MODE.md both carry a ~50-line §host-isolation worked example using the real Proxmox credential repro with verbatim xdist clamp banner and inline SEED-022 + no-keyring-faking citations; docs/ERROR-STYLE.md registers the host_isolation literal_error message as a three-way lock against cli.py and the pin test; docs/EXTENDING.md confirmed clean of stale ALWAYS-ON framing.**

## Performance

- **Duration:** ~75 minutes (spans the operator review checkpoint)
- **Completed:** 2026-05-27
- **Tasks:** 5 (4 doc edits + 1 human-verify checkpoint)
- **Files modified:** 3 (README.md, docs/LIBRARY-MODE.md, docs/ERROR-STYLE.md)
- **Files created:** 1 (this SUMMARY)
- **Net diff:** +125 doc lines across 3 files (README +49, LIBRARY-MODE +56, ERROR-STYLE +20)

## Accomplishments

- README ## Host isolation: strict vs passthrough section landed at line 465 with the Proxmox credential repro, verbatim xdist clamp banner, and inline SEED-022 + no-keyring-faking citations.
- docs/LIBRARY-MODE.md ## Host isolation section landed at line 225 with library-mode framing (plugin reads YAML at `pytest_configure` time) + the same Proxmox repro + banner verbatim. The exact heading text `## Host isolation` resolves the cli.py error-mapper next_step pointer (`docs/LIBRARY-MODE.md §host-isolation`) registered in plan 34-02.
- docs/ERROR-STYLE.md gained a new `### host_isolation literal_error` entry under the locked reference-messages section at line 78, carrying the verbatim summary / detail / next_step text from cli.py's `_emit_operator_error_for_validation` branch and naming the pin test `test_error_style_host_isolation_literal_rejection` for three-way drift detection.
- docs/EXTENDING.md audit confirmed clean: zero matches for ALWAYS-ON, always-on, --no-isolation, no-toggle, host_isolation. Light-pass deliverable closed as no-op.
- Operator review approved all four doc surfaces at the human-verify checkpoint.

## Task Commits

Each doc edit was committed atomically by the prior executor; this SUMMARY closes with one metadata commit:

1. **Task 1: Add §host-isolation section to README.md** — `3b9251d` (docs)
2. **Task 2: Add §host-isolation anchor to docs/LIBRARY-MODE.md** — `9e58619` (docs)
3. **Task 3: Register host_isolation literal_error in docs/ERROR-STYLE.md** — `476b3b5` (docs)
4. **Task 4: Scrub stale ALWAYS-ON references from docs/EXTENDING.md** — no-op (grep returned zero matches; light-pass deliverable closed without an edit, documented in this SUMMARY)
5. **Task 5: Operator review of rendered doc edits** — checkpoint passed (operator response: "approved")

**Plan metadata:** [pending after Write — final commit hash recorded post-commit]

## Doc Section Sizes

Per CONTEXT.md Claude's-Discretion lock (Phase 33 D-03 doc-block shape: ~25-50 lines per primary doc):

| File | Heading | Lines | Within target |
|------|---------|-------|---------------|
| README.md | `## Host isolation: strict vs passthrough` | 50 | yes (upper end) |
| docs/LIBRARY-MODE.md | `## Host isolation` | 57 | slightly over (library-mode framing paragraph is additive) |
| docs/ERROR-STYLE.md | `### host_isolation literal_error` | 20 (registry entry) | n/a (registry-style, not worked-example) |
| docs/EXTENDING.md | (no edit needed) | 0 | n/a |

LIBRARY-MODE.md ran ~7 lines over the README size because the library-mode framing paragraph at the top of the section (plugin reads YAML at `pytest_configure` time, stashes resolved Config for contract + test-code fixtures) is additive — not a copy-paste from README. CONTEXT.md called this out explicitly: library-mode framing is the differentiator. Within the 25-50 line guidance band.

## Anchor Resolution Confirmation

The cli.py error-mapper's next_step pointer (set in plan 34-02 commit `97f...` — `cli.py:_emit_operator_error_for_validation` literal_error branch for `host_isolation`):

```
set 'host_isolation: strict' or 'host_isolation: passthrough' in your config.yaml; see docs/LIBRARY-MODE.md §host-isolation for the trade-off
```

points at `docs/LIBRARY-MODE.md §host-isolation`. The new heading text is exactly `## Host isolation` (verified by `grep -nE '^## Host isolation\s*$' docs/LIBRARY-MODE.md` → match at line 225). Most Markdown renderers slugify `## Host isolation` as `#host-isolation`, which is the exact anchor the next_step pointer references. Anchor resolves.

## ERROR-STYLE.md Three-Way Lock

The new entry at docs/ERROR-STYLE.md L78 (`### host_isolation literal_error`) names three locked surfaces:

1. **Doc registry** — `docs/ERROR-STYLE.md` entry (verbatim summary / detail / next_step)
2. **Source branch** — `src/mcp_test_framework/cli.py:_emit_operator_error_for_validation` literal_error branch for `(host_isolation,)` (set in plan 34-02)
3. **Pin test** — `tests/framework/unit/test_error_style.py::test_error_style_host_isolation_literal_rejection`

Future drift in any of the three triggers a test failure at the framework gate, which is the same mechanical-drift-detection shape already used by the `sdet`-rejection entry in the same registry. The entry explicitly names the pin test by id so a reader following the registry can jump straight to the assertion.

## Verbatim Text Quoted in Docs

**xdist clamp banner (plan 34-05)** — both README L495-501 and LIBRARY-MODE.md L256-262:

```
xdist worker count clamped to 1

host_isolation=passthrough serializes subprocess spawns so the operator's credentials remain a single-owner resource.

next: switch to host_isolation=strict for parallel xdist runs
```

**host_isolation literal_error message (plan 34-02)** — docs/ERROR-STYLE.md L86-92:

- Summary: `unknown host_isolation mode: '<bad_value>'`
- Detail: `host_isolation accepts only 'strict' or 'passthrough'. strict (default) isolates the spawned MCP subprocess from your host credentials and HOME; passthrough hands the operator's full env to the subprocess (xdist clamped to 1 worker).`
- next_step: `set 'host_isolation: strict' or 'host_isolation: passthrough' in your config.yaml; see docs/LIBRARY-MODE.md §host-isolation for the trade-off`

## EXTENDING.md Audit Result

Grep audit per Task 4 acceptance criterion:

```
$ grep -cE "ALWAYS-ON|always-on|--no-isolation|host_isolation" docs/EXTENDING.md
0
```

No matches. EXTENDING.md was already clean of stale always-on framing — the Phase 34 plan 34-03 `_isolation.py` docstring rewording landed without leaving any prior doc breadcrumbs in EXTENDING.md to scrub. Light-pass deliverable closed as no-op.

## Decisions Made

See frontmatter `decisions:`. Key call-outs:

- **README and LIBRARY-MODE.md use different headings on purpose.** README is more descriptive (`## Host isolation: strict vs passthrough`) because it's a top-level entry point. LIBRARY-MODE.md uses the bare `## Host isolation` so the slug `#host-isolation` matches the cli.py error-mapper next_step pointer exactly. The README's heading doesn't need to resolve any external pointer.
- **Worked example is the real Proxmox repro.** Phase 30 UAT-1 captured the credential-reachability failure with `homelab-mcp create_proxmox_vm`; per CONTEXT.md `<specifics>` lock, no synthetic mock-tool replacement. Both doc sections grep `create_proxmox_vm`.
- **Citations land inline.** SEED-022 + no-keyring-faking + xdist trade-off all appear in the same section as the worked example, not as separate sidebars — per CONTEXT.md Claude's-Discretion lock.
- **EXTENDING.md task documented as no-op rather than forced.** Acceptance criterion explicitly allows the light-pass to be a no-op if no stale references are found; documented in this SUMMARY rather than padding the file with a redundant cross-reference.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking-prevention via documented no-op] Task 4 EXTENDING.md scrub was a no-op**

- **Found during:** Task 4 (audit-grep for `ALWAYS-ON|always-on|--no-isolation` in docs/EXTENDING.md)
- **Issue:** Plan declared `docs/EXTENDING.md` as a `files_modified:` entry; audit-grep returned zero matches. No stale framing to scrub.
- **Fix:** Documented the no-op in this SUMMARY per Task 4 `<behavior>` clause "If no references exist (EXTENDING.md was already clean of the locked phrase): document the no-op in the SUMMARY and the audit-pass is complete." No code change emitted; no commit fabricated to satisfy the file-changed expectation.
- **Files modified:** None (the no-op IS the deliverable).
- **Verification:** `grep -cE "ALWAYS-ON|always-on|--no-isolation|host_isolation" docs/EXTENDING.md` returns 0.
- **Committed in:** N/A — documented here.

---

**Total deviations:** 1 documented no-op (Task 4 audit cleanly closed without an edit).
**Impact on plan:** None. The plan's `<behavior>` clause for Task 4 explicitly permitted the no-op path; the decision to NOT fabricate a doc-change for the sake of touching the file matches CONTEXT.md's "light pass to confirm no stale references" framing.

## Issues Encountered

None during this finalization step. The four doc tasks were committed by the prior executor in clean sequence; the human-verify checkpoint returned operator approval ("approved") and resumed cleanly.

## Authentication Gates

None.

## Threat Flags

None. The plan's threat register (T-34-08-01..05) is fully addressed:

- **T-34-08-01 (Information Disclosure — operator opts into passthrough without understanding SEED-022 trade-off):** mitigated. README + LIBRARY-MODE.md cite SEED-022 + no-keyring-faking + xdist trade-off inline in the same section as the worked example.
- **T-34-08-02 (Repudiation — error-mapper next_step points at non-existent anchor):** mitigated. `## Host isolation` heading at LIBRARY-MODE.md L225 slugifies to `#host-isolation`; the next_step pointer resolves.
- **T-34-08-03 (Tampering — doc / cli.py / pin-test drift):** mitigated. ERROR-STYLE.md entry names the pin test by id; three-way lock means silent drift breaks at least one of the three.
- **T-34-08-04 (Spoofing — synthetic worked example replaces real Proxmox repro):** mitigated. `grep "create_proxmox_vm" README.md docs/LIBRARY-MODE.md` shows the real repro in both.
- **T-34-08-05 (Tampering — EXTENDING.md retains stale ALWAYS-ON framing):** mitigated. Grep audit returned zero matches.

## Known Stubs

None. All four doc surfaces are wired and reviewed. No follow-up plan required for ISOL-06 close — Phase 34 plan-progress can advance to 8/8 complete.

## Next Phase Readiness

- **Phase 34 plan-count:** 8/8 complete (this metadata commit closes the phase).
- **v1.5 milestone progress:** Phase 34 is the 4th of 5 phases in v1.5. After this commit lands, Phase 35 (zero-shim regression gate capstone) is the only remaining v1.5 work.
- **Phase-level verification (`.planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-VERIFICATION.md`):** not yet generated; the phase-close orchestrator owns that step.
- **Carry-forward to Phase 35:** the `host_isolation` knob is now a stable v1.5 surface; if Phase 35's regression gate sweeps additional surfaces, it can rely on the cli.py `_emit_operator_error_for_validation` literal_error branch wording being three-way-locked by this plan.

## Self-Check: PASSED

- `README.md` modified — `## Host isolation: strict vs passthrough` at L465: FOUND
- `docs/LIBRARY-MODE.md` modified — `## Host isolation` at L225: FOUND
- `docs/ERROR-STYLE.md` modified — `### host_isolation literal_error` at L78: FOUND
- Commit `3b9251d` (README): FOUND in `git log --oneline -10`
- Commit `9e58619` (LIBRARY-MODE): FOUND in `git log --oneline -10`
- Commit `476b3b5` (ERROR-STYLE): FOUND in `git log --oneline -10`
- `grep -cE "host_isolation: passthrough" README.md` returns ≥1
- `grep -cE "host_isolation: passthrough" docs/LIBRARY-MODE.md` returns ≥1
- `grep -nE "create_proxmox_vm" README.md docs/LIBRARY-MODE.md` shows real repro in both
- `grep -nE "xdist worker count clamped to 1" README.md docs/LIBRARY-MODE.md` shows banner verbatim in both
- `grep -nE "SEED-022" README.md docs/LIBRARY-MODE.md` shows inline citation in both
- `grep -nE "host_isolation literal_error" docs/ERROR-STYLE.md` exits 0 (entry registered)
- `grep -nE "test_error_style_host_isolation_literal_rejection" docs/ERROR-STYLE.md` exits 0 (pin-test reference present)
- `grep -cE "ALWAYS-ON|always-on|--no-isolation" docs/EXTENDING.md` returns 0 (clean)
- `^## Host isolation\s*$` heading at LIBRARY-MODE.md L225 verified — anchor resolves to `#host-isolation`
- Operator review at human-verify checkpoint: approved
