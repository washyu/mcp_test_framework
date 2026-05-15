# Phase 22: Scrub requirement-ID leaks from src/ - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-14
**Phase:** 22-scrub-requirement-id-leaks-from-src
**Areas discussed:** Scope of leak, Internal-comment policy, Allowlist policy, Regression-prevention test

---

## Scope of leak

| Option | Description | Selected |
|--------|-------------|----------|
| All three buckets (TAG-NN + D-NN + Phase NN) | Treat 'planning provenance' as one category — scrubbing only TAG-NN leaves residue ("Phase 13 D-08: LOCKED…") that still reads as leakage. Semantic rewrite per Phase 12 D-10 either rebuilds the sentence or drops it. | ✓ |
| TAG-NN + D-NN, keep 'Phase NN' anchors | Scrub the cryptic IDs but keep 'Phase NN' as historical breadcrumbs for git-blame archaeology. | |
| TAG-NN only (ROADMAP regex) | Strict reading of the success criteria. Faster to land, but leaves the 'D-08' / 'Phase 13' residue. | |

**User's choice:** All three buckets
**Notes:** Three buckets co-occur in most sites — `# Phase 13 D-08: LOCKED SAFE-06 message body…` contains all three. Scrubbing only TAG-NN would leave residue that still reads as planning leakage. Decision drives D-01 in CONTEXT.md.

---

## Internal-comment policy

| Option | Description | Selected |
|--------|-------------|----------|
| Rewrite-or-drop, per-site judgment | Pure-provenance comments dropped; rationale-bearing comments rewritten to preserve the constraint + surviving doc anchor without planning IDs. Mirrors Phase 12 D-10. | ✓ |
| Always rewrite — preserve every comment in prose | Stricter. Safer for archaeology but balloons comment volume. | |
| Always drop — scrub aggressively | Treat all planning-anchored comments as scaffolding. Loses load-bearing rationale at some sites. | |

**User's choice:** Rewrite-or-drop, per-site judgment
**Notes:** Two flavors identified during discussion — pure-provenance (e.g., `# Phase 17 CODEGEN-05: tool(name) factory dispatches against this.`) where the planning ref is the whole point, and rationale-bearing (e.g., `# Phase 13 D-08: LOCKED SAFE-06 message body, copied verbatim from ERROR-STYLE.md spec`) where the constraint matters. Decision drives D-02 / D-03 in CONTEXT.md.

---

## Allowlist policy

| Option | Description | Selected |
|--------|-------------|----------|
| Hard zero — no planning IDs in src/ | Rephrase always preserves what the ID gestured at. Easier to verify, no slippery slope. SEED-022 referenced by content, not ID. | ✓ |
| Allow named exceptions with justification | Reserve an escape hatch (e.g., SEED-022) with a # noqa-style inline justification comment. Complicates the regression test. | |
| You decide | Defer to executor judgment per-site. | |

**User's choice:** Hard zero — no planning IDs in src/
**Notes:** SEED-022 specifically discussed as a candidate exception (load-bearing framework-primitives principle). User confirmed the rephrase preserves the *meaning* ("framework wraps tool calls; SDET decides what to call") which is the load-bearing part — the ID itself is never load-bearing. Decision drives D-04 in CONTEXT.md.

---

## Regression-prevention test

| Option | Description | Selected |
|--------|-------------|----------|
| Pytest gate, TAG-NN + D-NN regex | Mechanical regex catches the two precise leak shapes. 'Phase NN' relies on review discipline in the scrub PR itself. | ✓ |
| Pytest gate, all three buckets | Add `Phase \d+(\.\d+)?\b` to the regex. Stronger guarantee but risks false-positives in legitimate operator-facing text. | |
| No CI gate — review discipline only | Skip the test. Trust PR review. Cheapest, but Phase 22 will eventually rot back. | |

**User's choice:** Pytest gate, TAG-NN + D-NN regex
**Notes:** Phase NN deliberately excluded from the regex because legitimate operator-facing prose (error messages, doc strings) can reference phase numbers. The one-time scrub catches the residue; TAG-NN/D-NN anchors typically appear alongside Phase NN, so future regressions get caught by the former. Decision drives D-05 / D-06 in CONTEXT.md.

---

## Claude's Discretion

- Plan granularity (single sweep vs split by area) — planner picks
- Per-site rewrite wording — executor judgment per site
- Treatment of `# Phase 14 GAP 1 from 14-HUMAN-UAT.md` style refs (UAT-anchored) — default drop, rewrite only if the surviving comment becomes nonsensical

## Deferred Ideas

- Phase NN regression-gate addition — reconsider if `Phase NN` drift is observed post-merge
- `docs/*.md` spot-fix sweep — if Phase 22 scrub surfaces leakage outside `src/`, capture as a quick task rather than expanding scope
- SEED-022 → README/CLAUDE.md surfacing — if the scrub reveals the principle is referenced from `src/`, that's a signal it should live in operator-facing docs (backlog idea)
