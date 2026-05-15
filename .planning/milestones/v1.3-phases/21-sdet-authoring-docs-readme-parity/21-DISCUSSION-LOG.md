# Phase 21: SDET authoring docs + README parity - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-14
**Phase:** 21-sdet-authoring-docs-readme-parity
**Areas discussed:** Doc file layout, Worked example sourcing, Skip-recipe canonical form, README sample + parity enforcement

---

## Doc file layout

### Q1: Where should the SDET authoring walkthrough (DOC-SDET-01) live?

| Option | Description | Selected |
|--------|-------------|----------|
| New `docs/SDET-AUTHORING.md` | Distinct audience (test author writing scenarios) vs EXTENDING.md's current operator/judge-config focus. Clean import surface to link from README and CLAUDE.md. Mirrors the file-split pattern Phase 12 established (ERROR-STYLE.md is also its own file). | ✓ |
| Append major section to `docs/EXTENDING.md` | Single discoverable extension doc. Risk: doc grows to ~1000 lines. | |
| You decide | Defer to planner judgment based on doc-length estimate. | |

**User's choice:** New `docs/SDET-AUTHORING.md`
**Notes:** —

### Q2: Where should the codegen regen workflow (DOC-SDET-02) live?

| Option | Description | Selected |
|--------|-------------|----------|
| Section inside `docs/SDET-AUTHORING.md` | Regen is part of the SDET authoring loop. Keeps lifecycle in one place. ~80–120 lines. | ✓ |
| Separate `docs/CODEGEN.md` | Standalone reference doc. Risk: orphans regen from scenario-authoring narrative. | |
| Append to `docs/EXTENDING.md` | Mismatch — EXTENDING currently talks about extending the framework, codegen is a build step. | |

**User's choice:** Section inside `docs/SDET-AUTHORING.md`
**Notes:** —

### Q3: How should the CLAUDE.md dual-persona note be added?

| Option | Description | Selected |
|--------|-------------|----------|
| Short note in `## What This Project Is` | 1–3 sentence append to existing project description. Minimal churn, discoverable. | ✓ |
| New `## Personas` H2 section | Dedicated section, ~20–40 lines. Better grounding but heavier. | |
| Top-of-file persona-switch banner | Risks duplicating PROJECT.md persona language. | |

**User's choice:** Short note in `## What This Project Is`
**Notes:** —

### Q4: Should `docs/SDET-AUTHORING.md` absorb or link to `.planning/recipes/pytest-order.md`?

| Option | Description | Selected |
|--------|-------------|----------|
| Absorb into SDET-AUTHORING.md | Public doc owns canonical recipe. Eliminates broken-link risk; no `.planning/` paths in public docs. | ✓ |
| Link from SDET-AUTHORING.md to `.planning/recipes/pytest-order.md` | Avoids duplication but leaks `.planning/` path into a public doc — same anti-pattern Phase 12 doc scrub fixed. | |
| Both — absorb canonical, keep planning artifact for traceability | Higher maintenance — two copies can drift. | |

**User's choice:** Absorb into SDET-AUTHORING.md
**Notes:** —

---

## Worked example sourcing

### Q5: Where should the worked example come from (the file was deleted in Phase 20)?

| Option | Description | Selected |
|--------|-------------|----------|
| Lift verbatim from Phase 19-04 SUMMARY/CONTEXT | Most realistic; doc owns canonical version. | ✓ |
| Recover from git history (`git show 8cd492d~1:...`) | Higher literal fidelity; needs editorial trimming. | |
| Smaller hypothetical scenario (hello-world MCP echo) | Easier to read but loses authenticity. | |
| Two-tier: minimal in-doc + reference to Phase 19 artifact | Compromises authenticity for readability. | |

**User's choice:** Lift verbatim from Phase 19-04 SUMMARY/CONTEXT
**Notes:** —

### Q6: Should the lifted example include the upstream homelab-mcp inputSchema bug workaround?

| Option | Description | Selected |
|--------|-------------|----------|
| Include with annotation calling out the upstream bug | Teaches a real-world pattern + SEED-022 principle. | ✓ |
| Clean up — remove the workaround entirely | Cleaner but loses load-bearing example of framework-primitives principle. | |
| Keep workaround, drop the bug commentary | Pattern without explanation — looks arbitrary. | |

**User's choice:** Include with annotation calling out the upstream bug
**Notes:** —

### Q7: How should the doc handle the deleted source file?

| Option | Description | Selected |
|--------|-------------|----------|
| Treat the doc as the canonical source — no in-repo file reference | Doc is the source of truth; deletion in Phase 20 was deliberate. | ✓ |
| Include a note that the file used to ship in-tree and was removed per Phase 20 | Risks leaking planning-phase history. | |
| Link to git tag/commit where the file existed | Assumes git-history archaeology. | |

**User's choice:** Treat the doc as the canonical source — no in-repo file reference
**Notes:** —

### Q8: Structural pattern — incremental or complete-then-dissect?

| Option | Description | Selected |
|--------|-------------|----------|
| Incremental build-up | Walk through codegen → import → first test → fixture → ordering → skip. Reader can stop at any depth. | ✓ |
| Complete-then-dissect | Show full ~150-line scenario, then walk through each pattern. | |
| Pattern-first (cookbook) | Sections by pattern. Less hand-holding for first-time authors. | |

**User's choice:** Incremental build-up
**Notes:** —

---

## Skip-recipe canonical form

### Q9: What's the canonical skip recipe (replacing the killed `requires_homelab` marker)?

| Option | Description | Selected |
|--------|-------------|----------|
| `@pytest.mark.skipif(not _probe(), reason=...)` with author-defined `_probe()` | SDET writes their own `_probe()`. Framework provides ZERO probe primitives — honors SEED-022. Doc shows 2–3 concrete examples. | ✓ |
| Env-var-presence pattern only | Simpler one-liner, lower fidelity. | |
| Both — env-var primary + `_probe()` advanced | Tiered. Two patterns. | |

**User's choice:** `@pytest.mark.skipif(not _probe(), reason=...)` with author-defined `_probe()`
**Notes:** —

### Q10: How should the doc describe reason-string conventions?

| Option | Description | Selected |
|--------|-------------|----------|
| Operator-domain phrasing prescribed | Doc locks in: `reason="Proxmox host unreachable (set MCPTF_DOGFOOD_PROXMOX_HOST)"`. Mirrors Phase 14/16 domain language. | ✓ |
| Author's discretion with examples only | Loses consistency the renderer benefits from. | |
| Two patterns: terse + verbose | Adds complexity. | |

**User's choice:** Operator-domain phrasing prescribed
**Notes:** —

### Q11: How should the doc treat the deferred hello-world MCP CI fixture?

| Option | Description | Selected |
|--------|-------------|----------|
| Brief mention in a `## Future: CI-runnable scenarios` section | One short section sets expectations without overcommitting. | ✓ |
| Don't mention it — doc only covers what ships today | Risk: readers wonder how framework's own tests stay healthy across regens. | |
| Detailed roadmap-style section | Closer to PROJECT.md content than user-facing docs. | |

**User's choice:** Brief mention in a `## Future: CI-runnable scenarios` section
**Notes:** —

### Q12: Where in the doc does the skip recipe live?

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated `## Skipping when dependencies are unreachable` section after the worked example | Standalone, independently linkable. | ✓ |
| Woven into the incremental build-up as the final step | More narrative but harder to look up. | |
| Both — inline + dedicated section | More duplication risk. | |

**User's choice:** Dedicated `## Skipping when dependencies are unreachable` section after the worked example
**Notes:** —

---

## README sample + parity enforcement

### Q13: What scenario should DOC-SDET-03's README sample show?

| Option | Description | Selected |
|--------|-------------|----------|
| A minimal 2–3 test scenario | Short enough to fit a README block. | ✓ |
| Full VM-lifecycle three-test scenario | Bloats README. | |
| Output-only fragment (no test source) | Loses author-side hook. | |

**User's choice:** A minimal 2–3 test scenario
**Notes:** —

### Q14: How should char-for-char parity (DOC-SDET-03) be enforced?

| Option | Description | Selected |
|--------|-------------|----------|
| Manual snapshot at phase commit time + Phase 16 precedent comment | Run framework once during execution, paste literal output. Low friction, manual sweep when output changes. | ✓ |
| Regression test that diffs README against `_runner.py` output | High fidelity but brittle (whitespace, ANSI). | |
| Regen script | Forgettable without pre-commit hook. | |

**User's choice:** Manual snapshot at phase commit time + Phase 16 precedent comment
**Notes:** —

### Q15: Where in README.md should the SDET sample slot in?

| Option | Description | Selected |
|--------|-------------|----------|
| New `## SDET scenarios` H2 between `## Sample green run` and `## Isolation guarantee` | Natural reading order: contract pass → authored scenarios. | ✓ |
| Extend existing `## Sample green run` with an SDET subsection | Blurs operator vs SDET distinction. | |
| End-of-README appendix-style section | Less discoverable. | |

**User's choice:** New `## SDET scenarios` H2 between `## Sample green run` and `## Isolation guarantee`
**Notes:** —

### Q16: What sample test should the README's section actually show?

| Option | Description | Selected |
|--------|-------------|----------|
| Trimmed Proxmox VM lifecycle (2 tests: create + delete) | Consistent with SDET-AUTHORING.md worked example; inputSchema-bug workaround stays in SDET-AUTHORING. | ✓ |
| Fabricated minimal scenario against `list_registered_servers` | Stateless tool — doesn't demonstrate SDET sweet spot. | |
| Generic placeholder with `<your-tool>` syntax | Violates DOC-SDET-03 char-for-char parity requirement. | |

**User's choice:** Trimmed Proxmox VM lifecycle (2 tests: create + delete)
**Notes:** —

---

## Claude's Discretion

- File naming convention inside `docs/SDET-AUTHORING.md` (H2 / H3 ordering, code-block language tags) — match `docs/EXTENDING.md` conventions.
- Exact wording of the CLAUDE.md persona note within the 1–3 sentence budget.
- Whether the README sample shows the test file as a single block or splits it across "code" / "output" sub-blocks, subject to char-for-char parity holding.

## Deferred Ideas

- **Hello-world MCP server for CI-runnable scenarios** — mentioned in doc; not implemented in Phase 21.
- **Char-for-char regression test (CI-enforced README parity)** — deferred; manual snapshot precedent holds.
- **Regen script for README samples** — deferred for the same reason.
- **Per-tool `_probe()` library shipped by the framework** — REJECTED by SEED-022 (framework owns no probe primitives), not deferred.
- **`docs/EXTENDING.md` restructure for new SDET surface** — left as-is; revisit only if a follow-up doc-pass surfaces a real gap.
