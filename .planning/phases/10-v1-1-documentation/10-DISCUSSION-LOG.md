# Phase 10: v1.1 documentation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-08
**Phase:** 10-v1-1-documentation
**Areas discussed:** Open-source posture for tool names, Worked-example breadth (DOC-04), CI snippet shape (DOC-06), EXTENDING.md vs README boundary

---

## Open-source posture for tool names

| Option | Description | Selected |
|--------|-------------|----------|
| Real names, no scrub | Use list_keyring_credentials, suggest_deployments etc. verbatim. README is currently homelab-coupled; the 'scrub on repo-public' deferred item handles this when/if the repo goes public. Concrete and testable today. | |
| Abstract placeholders only | `<your_tool>`, `<safe_read_tool>` etc. throughout. Pre-emptively neutral but loses concreteness; reader must mentally substitute. Forces a future re-write if homelab-mcp shape diverges from the abstraction. | ✓ |
| Real names + callout | Use real names but add a one-liner under each example: 'These are homelab-mcp tools — substitute the tool names from your `mcp-test-framework list-tools` output.' Keeps concreteness, defuses the open-source concern, costs ~3 lines. | |

**User's choice:** Abstract placeholders only
**Notes:** Tension noted: D-02 ("two-block matches reality") references the patterns in `config.example.yaml`, which is real-named. Reconciled in CONTEXT.md D-01a — `config.example.yaml` is configuration not documentation, stays real-named, and the README cross-links to it for a "real-server" reference. README/EXTENDING examples themselves are abstract.

---

## Worked-example breadth (DOC-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Single canonical tool | One block (e.g., list_keyring_credentials with judges: [clarity]). Tightest. Reader generalizes from one. ~15 lines. | |
| Three-knob walkthrough | Three small blocks demonstrating (a) skip with reason, (b) call_arguments, (c) judges subset — every TOOLCFG knob operators will reach for. Closer to a cookbook. ~40 lines. | |
| Two-block (matches reality) | Just (a) skip-with-reason and (b) judges subset — the two patterns currently in config.example.yaml. Mirrors live config so the README and the example.yaml stay in sync. call_arguments mentioned with a one-line note. ~25 lines. | ✓ |

**User's choice:** Two-block (matches reality)
**Notes:** Decisions D-02a (call_arguments → one-paragraph mention) and D-02b (reserved fields → single-sentence callout) follow from this choice. Each block must be COMPLETE (full tools.<name> entry) so operators can copy-paste in one motion (D-02c).

---

## CI snippet shape (DOC-06)

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal starter | Single job, single Python (3.14), `astral-sh/setup-uv`, `uv run mcp-test-framework run --junit-xml=results.xml`, dorny/test-reporter upload step. ~25 lines copy-paste. Optimized for 'works in 30 seconds'. | ✓ |
| Production template | Matrix Python, uv cache, separate `unit` (default) and `live` (opt-in via repository_dispatch) jobs, JUnit upload + artifact archive. Closer to what a real team ships. ~60 lines. Optimized for 'directly usable in a real project'. | |
| Minimal + commented matrix hooks | Minimal-starter shape, but with commented-out `strategy.matrix` and live-job blocks the reader uncomments to graduate. Best of both — starts simple, has the upgrade path inline. ~35 lines. | |

**User's choice:** Minimal starter
**Notes:** D-03b: snippet honors the default `addopts` exclude on live tests — does NOT exercise live tests in the CI snippet. D-03c: GHA-only (Jenkins/GitLab translation is reader's job, called out via leading comment). D-03d: action versions pinned via major-version tags (`@v6`, `@v2`), not commit SHAs.

---

## EXTENDING.md vs README boundary

| Option | Description | Selected |
|--------|-------------|----------|
| README owns schema, EXTENDING walks workflow | README has the full schema reference (every TOOLCFG field, types, defaults); EXTENDING.md's new section is a step-by-step walkthrough ('1. run list-tools  2. write a tools.<name> block  3. re-run') that LINKS BACK to README for field details. No schema duplication. | ✓ |
| Both repeat schema, different framing | README is reference (schema + 1–2 short examples); EXTENDING.md repeats the schema with deeper context (when to use each knob, common pitfalls, full multi-tool worked example). Some duplication, two complete reads. | |
| Refactor EXTENDING into seam index | Reshape EXTENDING.md into 'Every extension seam: rubric / judge / tool target / config source' — each subsection a short walkthrough + link to README for schema. Bigger restructure (touches existing rubric + judge sections). | |

**User's choice:** README owns schema, EXTENDING walks workflow
**Notes:** D-04a: no schema duplication — EXTENDING uses relative-anchor link (`../README.md#per-tool-configuration`). D-04b: EXTENDING stays narrow (3 sections only); no refactor. D-04c: EXTENDING walkthrough's worked example demonstrates ONE pattern (likely skip-with-reason); cross-references README's other block.

---

## Claude's Discretion

- Section placement order in README (CD-01) — Configuration → Per-tool config → Sample green run → Isolation → CI → Troubleshooting (suggested) but planner finalizes.
- Voice/tone (CD-02) — match existing README density; no rewrite.
- "Further reading" cross-link updates (CD-03) — at most 1-2 lines added per file.
- Snippet syntax-highlight tags (CD-04) — standard Markdown conventions.
- Plan-cut within phase (CD-05) — likely P1 README, P2 EXTENDING.md (sequential, anchor-link dependency); planner may split README further.
- Snippet correctness verification approach (CD-06) — planner picks (lifted-block YAML parse, schema-vs-ToolConfig attribute check).

## Deferred Ideas

- Scrub homelab-specific captures from `.planning/` (open-source-prep gated on repo-public trigger; not Phase 10's scope).
- Generic CI templates for Jenkins, GitLab, CircleCI (no demand signal at v1.1).
- Auto-generated docs (Sphinx, mkdocs) — explicit anti-scope per REQUIREMENTS.md.
- EXTENDING.md "every extension seam" refactor — rejected, keep narrow.
- `call_arguments` worked example — deferred until a real-config tool uses it.
- Per-rubric usage examples in README — EXTENDING.md territory, no overlap.
