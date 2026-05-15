# Phase 22: Scrub requirement-ID leaks from src/ - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove planning-system provenance from `src/mcp_test_framework/` so neither operators (via `--help`) nor future maintainers (via `grep src/`) see planning artifacts shipped inside the package. Source-code analog of the v1.2 doc scrub (Phase 12 CLEAN-01..04), applied with the same Phase 12 D-10 rule — semantic rewrite, not regex strip — and extended to cover decision-anchor (`D-NN`) and historical (`Phase NN`) refs in addition to the named-acronym IDs in the ROADMAP success criterion.

**In scope:**
- 5 user-visible Typer command docstrings rendered by `--help` (`run`, `list-tools`, `version`, `gen-sdet-classes`, `_emit_yaml_scaffold`)
- ~58 internal references across module docstrings, decision-anchor comments, inline annotations
- Three planning-artifact shapes: `TAG-NN` (e.g., `CLI-01`, `SAFE-03`), `D-NN` decision anchors, `Phase NN` historical prefixes
- One regression-prevention pytest test under `tests/framework/unit/`

**Out of scope:**
- `.planning/` content (planning artifacts belong there, by design)
- `tests/` content (test code can name the planning IDs it pins; scrub is `src/`-only)
- `docs/` content (the v1.2 CLEAN sweep already covered docs; spot fixes go via a separate quick task if surfaced)
- Behavior changes (this is pure documentation/comment editing — Phase 17 unit tests still pass unchanged)
- Phase 23 + Phase 24 work (test-debt cleanup and serializer fix are their own phases)

</domain>

<decisions>
## Implementation Decisions

### Scope of leak

- **D-01:** Scrub all three planning-artifact shapes: (a) `TAG-NN` named-acronym IDs per the ROADMAP regex (`CLI|PERSONA|CODEGEN|SAFE|RUNNER|UX|ISOL|JUNIT|SURFACE|TEST|CLEAN|DOC|UI|SDET|STATE|PREFLIGHT|SCRUB|RELOC`), (b) `D-NN` decision anchors (227 hits across `src/`), (c) `Phase NN(.M)?` historical prefixes (193 hits). The buckets co-occur in most sites — scrubbing only TAG-NN leaves residue ("Phase 13 D-08: LOCKED message body…") that still reads as planning leakage to a new reader.

### Comment-rewrite policy

- **D-02:** Phase 12 D-10 ("semantic rewrite, not regex strip") carries forward and applies per-site. Distinguish two comment flavors:
  - **Pure-provenance** (e.g., `# Phase 17 CODEGEN-05: tool(name) factory dispatches against this.`) → drop the line entirely; the code names itself.
  - **Rationale-bearing** (e.g., `# Phase 13 D-08: LOCKED SAFE-06 message body, copied verbatim from ERROR-STYLE.md spec`) → rewrite to preserve the constraint and cite the surviving doc anchor (`docs/ERROR-STYLE.md`) without planning IDs.
- **D-03:** When a comment pointed at a `.planning/` doc that no longer needs to ship visibility (PLAN.md, SUMMARY.md, REQUIREMENTS row), drop the anchor — those docs are not part of the shipped surface. Surviving anchors are `docs/*.md`, `README.md`, `CLAUDE.md`, and the SDET-AUTHORING walkthrough.

### Allowlist policy

- **D-04:** Hard zero — no planning IDs in `src/`, no allowlist, no inline `# noqa` justifications. The rephrase always preserves the *content* the ID gestured at; load-bearing principles (e.g., SEED-022's framework-primitives rule) get referenced by their meaning ("framework wraps tool calls and nothing else"), not their ID. Easier to verify, no slippery slope.

### Regression-prevention test

- **D-05:** Add `tests/framework/unit/test_no_planning_ids_in_src.py` that greps `src/mcp_test_framework/` with the locked regex `(CLI|PERSONA|CODEGEN|SAFE|RUNNER|UX|ISOL|JUNIT|SURFACE|TEST|CLEAN|DOC|UI|SDET|STATE|PREFLIGHT|SCRUB|RELOC)-\d+|\bD-\d+\b` and fails on any hit. Runs as part of the standard `tests/framework/` suite (composes with `mcp-test-framework run --with-framework` and direct `uv run pytest tests/framework/`).
- **D-06:** Phase NN prefix protection is **not** in the regex — `Phase \d+` legitimately appears in operator-facing prose (error messages, doc strings, changelog references). The Phase NN scrub is a one-time discipline executed inside the Phase 22 PR; drift afterward is low-risk because TAG-NN/D-NN anchors typically appear *with* a Phase NN prefix, and the regex catches the former.
- **D-07:** Skip `.pyc` cache cleanup — the framework's stale `__pycache__` will regenerate on the next `pytest` / `uv run` and inherit the scrubbed source. No special handling in plans.

### Claude's Discretion

- Plan granularity — single sweep plan vs split by area (`cli.py` user-visible, `sdet/` internals, `_runner.py` + `_isolation.py`, regression test). Planner chooses; the work is mechanical enough that a single PLAN with multiple tasks is also defensible.
- Per-site rewrite wording — executor reads each site, picks "drop" or "rewrite" per D-02, and decides the surviving anchor (if any) without re-asking the user.
- Treatment of `# Phase 14 GAP 1 from 14-HUMAN-UAT.md` style refs — these point at `.planning/` UAT docs; default to drop unless the surviving comment becomes nonsensical, in which case rewrite citing what the gap fixed (e.g., "console encoding gap on Windows cp1252").

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase-22 source-of-truth

- `.planning/ROADMAP.md` §"Phase 22: Scrub requirement-ID leaks from src/" — Goal, Scope (5 user-visible + 58 internal), Success Criteria #1–#4, locked regex.
- `.planning/phases/12-doc-persona-foundation/12-CONTEXT.md` §"Doc cleanup + examples/ shape" D-10 — "Per-section semantic rewrite, not regex strip" rule; load-bearing precedent for D-02 / D-03.

### Surviving doc anchors comments may cite

- `docs/ERROR-STYLE.md` — operator-visible error-message style guide; replaces `SAFE-03` / `SAFE-06` / `PERSONA-03` anchor references.
- `docs/SDET-AUTHORING.md` — SDET surface walkthrough; replaces `SDET-NN` / `CODEGEN-NN` / `RELOC-NN` anchor references.
- `README.md` — operator-facing surface description; replaces `CLI-NN` / `PERSONA-NN` anchor references.
- `CLAUDE.md` — repo guidance; replaces dual-persona `DOC-SDET-NN` references.

### Project-level principle

- `.planning/REQUIREMENTS.md` — SCRUB-SRC-01 (to be formalized at plan-phase per ROADMAP "TBD" marker).
- SEED-022 (framework-primitives principle, captured in user memory and `.planning/STATE.md` Decisions log) — referenced by meaning ("framework wraps tool calls; SDET decides what to call"), not by ID.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`tests/framework/unit/` layout** (per Phase 20 CODEGEN-COVERAGE-01 work) — a clean home for pure-data assertion tests like the D-05 regression gate; no live MCP, CI-safe, composes with the existing test-collection scope.
- **`tests/conftest.py` framework markers** — the regression test inherits the same `not live_homelab and not live_ollama` `addopts` posture from `pyproject.toml`; no marker plumbing needed.

### Established Patterns

- **Phase 12 D-10 "semantic rewrite, not regex strip"** — load-bearing precedent. Operator-facing docs were rewritten file-by-file in the v1.2 CLEAN sweep; this phase applies the same rule to `src/` comments.
- **Comment-density convention** (from broader codebase scan) — current `src/` comments are heavy on planning rationale relative to most Python projects. Scrub will materially reduce comment volume; this is the intent, not a regression.
- **Typer command docstring rendering** — `--help` reads the function docstring directly. Rewrites must preserve the operator's mental model of what the command does (verbs, key flags, exit codes), not just strip IDs.

### Integration Points

- **`src/mcp_test_framework/cli.py`** — 24 hits including 5 user-visible Typer docstrings (`run` line ~460, `list-tools` ~698, `version` ~938, `gen-sdet-classes` ~957, `_emit_yaml_scaffold` ~1320). Highest-impact single file; the only file where `--help` text changes are operator-perceptible.
- **`src/mcp_test_framework/sdet/`** — 33+ hits across `__init__.py`, `session.py`, `_tool_factory.py`, `response.py`, `errors.py`, `_codegen.py`. Internal-only; rewrites are dev-facing.
- **`src/mcp_test_framework/_runner.py`, `_isolation.py`, `fixtures.py`, `config.py`, `models.py`, `schema_validator.py`, `mcp_client.py`** — remaining ~25 hits; lighter density per file.

</code_context>

<specifics>
## Specific Ideas

- Phase 12 D-10 is the load-bearing precedent — when in doubt about a rewrite, mirror what the CLEAN sweep did for README/EXTENDING.md.
- The regression test (D-05) goes in `tests/framework/unit/` so it composes with the existing test-collection scope (per Phase 20 CODEGEN-COVERAGE-01 layout precedent); no separate CI pipeline change.
- The regex in D-05 is the **locked single-source-of-truth** for what counts as a leak — the test itself documents the policy.

</specifics>

<deferred>
## Deferred Ideas

- **Phase NN regression gate** — Adding `Phase \d+(\.\d+)?\b` to the D-05 regex would close the third leak shape, but false-positives on operator-facing prose make it not worth the noqa-mechanism complexity at this phase. Reconsider if `Phase NN` drift is observed post-merge.
- **docs/ spot-fix sweep** — If the scrub surfaces leakage in `docs/*.md` files (the v1.2 CLEAN pass was thorough but not exhaustive), capture as a quick task rather than expanding Phase 22 scope.
- **SEED-022 → README/CLAUDE.md surfacing** — The framework-primitives principle is currently a `.planning/`-only artifact. If the scrub reveals that principle is referenced from `src/`, that's a signal it should also live in operator-facing docs. Out of scope here; capture as a backlog idea if it surfaces.

</deferred>

---

*Phase: 22-scrub-requirement-id-leaks-from-src*
*Context gathered: 2026-05-14*
