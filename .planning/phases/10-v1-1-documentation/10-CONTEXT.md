# Phase 10: v1.1 documentation - Context

**Gathered:** 2026-05-08
**Status:** Ready for planning

<domain>
## Phase Boundary

A new contributor or CI engineer can adopt v1.1's new capabilities (per-tool config, isolation guarantee, JUnit XML output, adding new MCP tool targets) using **only** `README.md` and `docs/EXTENDING.md` — no source-reading required. The phase ships documentation only; no code changes.

**In scope (per ROADMAP.md and REQUIREMENTS.md):**
- DOC-04 — README "Per-tool configuration" section with worked examples for the patterns currently exercised (skip-with-reason, judges subset). Copy-pasteable.
- DOC-05 — README "Isolation guarantee" section: states "test runs do not mutate your real homelab-mcp state" and points the reader at `tests/test_isolation.py` (the ISOL-03 verification test) as proof.
- DOC-06 — README "CI integration" section with copy-pasteable GitHub Actions snippet using `--junit-xml=` and a JUnit-consuming action.
- DOC-07 — `docs/EXTENDING.md` updated with a new section describing how to add a new MCP tool target via per-tool config alone (no code change required for tools fitting the existing rubric pattern), with a worked example.

**Explicitly NOT in scope:**
- New CLI flags, new code, new tests beyond doc-snippet correctness checks.
- Scrubbing homelab-specific identifiers from `.planning/` artifacts (deferred to "if/when repo goes public" — see PROJECT.md / STATE.md deferred items list).
- Restructuring existing README sections beyond what's needed to insert the three new sections cleanly.
- README/docs translation, pluralization for non-`mcp-test-framework` console scripts, or any extension seam beyond rubric/judge/tool-target.
- v1.2+ features (xdist, OpenAI-compat backend, dynamic rubrics, agentic judge, stateful testing).
- Auto-generated docs (Sphinx, mkdocs, etc.) — handcrafted Markdown remains the contract.

</domain>

<decisions>
## Implementation Decisions

### Open-source posture for tool names (D-01)

- **D-01:** **Abstract placeholders only** in all README and EXTENDING.md examples. Use generic names like `<safe_read_tool_a>`, `<safe_read_tool_b>`, `<your_tool>` rather than real homelab-mcp tool names (`list_keyring_credentials`, `suggest_deployments`, etc.). Rationale: pre-empts the "Scrub homelab IP from README" deferred open-source-prep item (STATE.md, AR-05-12) — the README becomes neutral now so the open-source trigger does not require a re-write.
- **D-01a:** **`config.example.yaml` is the exception.** It is configuration, not documentation, and currently uses real tool names (per the safe-by-default 260507-n0g posture). Phase 10 does NOT modify `config.example.yaml`. The README's per-tool config example uses abstract names; readers who want a "real" reference look at `config.example.yaml` directly. Cross-link: the README's per-tool config section MUST include a one-line pointer like `For a complete real-server config, see config.example.yaml`.
- **D-01b:** **Reader-substitution callout.** Each abstract example is preceded by a one-line note: "Replace these tool names with the names from your `mcp-test-framework list-tools` output." Keeps the reader from being confused that `<safe_read_tool_a>` is a magic name.

### Worked-example breadth (DOC-04, D-02)

- **D-02:** **Two-block worked example** in README's Per-tool configuration section, mirroring the two patterns currently in `config.example.yaml`:
  - Block A: skip-with-reason (a tool the operator declines to exercise — e.g. an unsafe-by-default destructive tool). Demonstrates `skip: true` + `skip_reason: "..."`.
  - Block B: judges subset (a tool whose description is judged with only a subset of rubrics — e.g. clarity-only). Demonstrates `judges: [clarity]`.
- **D-02a:** `call_arguments` (the third TOOLCFG knob) gets a **one-paragraph mention** under the two blocks — not its own block. Rationale: `call_arguments` is not exercised by either currently-active tool in `config.example.yaml`, so a worked example would be synthetic. A short note ("`call_arguments: {key: value}` lets you pass fixed arguments to the tool's `call_tool` invocation. See `config.example.yaml` for shape.") is sufficient.
- **D-02b:** **Reserved fields** (`setup`, `depends_on` — TOOLCFG-03 SEED-004 forward-compat) get a single-sentence callout: "These fields are typed in the model but have no runtime semantics in v1.1; future versions will activate them additively." No example. Prevents readers from thinking they're load-bearing.
- **D-02c:** Each block shows the COMPLETE per-tool entry (the `tools.<tool_name>:` key plus all relevant subfields), not abbreviated fragments. Operators can copy a block and modify in place.

### CI integration snippet (DOC-06, D-03)

- **D-03:** **Minimal starter** GitHub Actions snippet — single job, single Python (3.14, matching `.python-version` and `pyproject.toml`'s `requires-python`), `astral-sh/setup-uv`, `uv sync`, `uv run mcp-test-framework run --junit-xml=results.xml`, JUnit upload via `dorny/test-reporter@v2` (the canonical action picked in Phase 09 CD-01). Target length: ~25 lines. Optimized for "works in 30 seconds, copy-paste".
- **D-03a:** **No matrix, no caching, no separate live-vs-unit jobs.** Operators who want those graduate by reading the GitHub Actions docs — the snippet is a starter, not a production template. Adding matrix etc. would push past 60 lines and clutter the README.
- **D-03b:** **The snippet runs the default unit slice** (`addopts = "-m 'not live_homelab and not live_ollama'"` from `pyproject.toml` is honored — Phase 9 L-05 invariant). Live tests are NOT exercised in the CI snippet. The snippet's comment block notes: "To run live tests, see `docs/EXTENDING.md`'s '<your_marker>' section" or similar — an inline reminder, not a second snippet.
- **D-03c:** **Generic CI snippet via comment.** The snippet's leading comment notes the GitHub-Actions-specific bits (job/runs-on/uses) so operators on Jenkins, GitLab CI, etc. can mentally translate. We ship ONE snippet (GitHub Actions), not multiple.
- **D-03d:** **Action version pinning** uses major-version tags (`@v6`, `@v2`) not commit SHAs. Rationale: README readability + low-stakes (CI snippet, not production secret); operators who want SHA pinning are graduating beyond the starter.

### EXTENDING.md vs README boundary (DOC-07, D-04)

- **D-04:** **README owns the schema; EXTENDING.md walks the workflow.** The README's "Per-tool configuration" section is the schema reference (every TOOLCFG field, types, defaults, the two worked blocks from D-02). EXTENDING.md's new section is a step-by-step walkthrough:
  1. Run `mcp-test-framework list-tools` to discover what the server advertises.
  2. Pick a tool to exercise; decide skip / judges / call_arguments.
  3. Add a `tools.<tool_name>` block to your config.yaml (linking back to README for field details).
  4. Re-run `mcp-test-framework run` and verify the per-tool summary line shows the expected verdict.
- **D-04a:** **No schema duplication.** EXTENDING.md does NOT repeat the field reference. It links back to the README section using a relative anchor link (e.g. `[Per-tool configuration](../README.md#per-tool-configuration)`). The walkthrough has its own concrete worked example (using abstract placeholders per D-01).
- **D-04b:** **EXTENDING.md stays narrow.** It keeps its existing two top-level sections (Add a new rubric, Swap the judge backend) and adds ONE new section ("Add a new MCP tool target"). No refactor into "every extension seam" index. The walkthrough section sits between the rubric section and the judge section, or after the judge section — Claude's discretion.
- **D-04c:** The walkthrough's worked example demonstrates **one** of the two D-02 patterns (likely skip-with-reason — closest to "I have a destructive tool I want to opt out") rather than re-doing the two-block presentation from README. The other pattern is referenced via "see README's Block B for judges-subset usage".

### Isolation guarantee (DOC-05) — Claude's discretion items below

- **D-05:** **Concrete reference to `tests/test_isolation.py`** by relative path in the README. The section says: "Run `uv run pytest tests/test_isolation.py -v` to verify on your machine — the test computes sha256 hashes of `~/.homelab_mcp/credential_registry.json`, `known_hosts`, and `migration_state.json` before and after a full session and asserts byte-identical equality." This is concrete and testable.
- **D-05a:** **Real-state-file paths** (`~/.homelab_mcp/credential_registry.json` etc.) are CONCRETE in this section even though they reference homelab-mcp internals. Rationale: ISOL-03 is *specifically* a homelab-mcp-coupled test (Phase 06 D-08); abstracting the file paths would make the verification claim opaque. The open-source-prep deferred item handles this when the repo goes public; for now, accuracy beats abstraction in this one section. Exception to D-01.
- **D-05b:** **Strong claim, narrow scope.** "Test runs do not mutate `~/.homelab_mcp/` real-state files" — this is what ISOL-03 actually verifies. We do NOT claim "test runs are perfectly hermetic" or "test runs leave zero side effects" because that overpromises (e.g., Ollama server may have request logs; the OS keyring backend null-routing depends on `PYTHON_KEYRING_BACKEND=keyring.backends.null.Null` per ISOL-04). The README section calls out the keyring null-backend dependency in a one-line note: "Test runs route the OS keyring through a null backend, so credentials are not read or written."

### Claude's Discretion (D-06)

- **CD-01:** **Section placement in README.** The 3 new sections (Per-tool configuration, Isolation guarantee, CI integration) slot into the existing structure (Prerequisites → Setup → Commands → Configuration → Sample green run → Troubleshooting → Further reading). Claude picks placement during planning. Likely shape: insert "Per-tool configuration" after "Configuration"; "Isolation guarantee" after "Sample green run"; "CI integration" before "Troubleshooting" or under a new top-level "Adopting in CI" header. Planner finalizes.
- **CD-02:** **Voice/tone** matches the existing README — concise, code-snippet-led, light prose. Don't introduce a more conversational style or a more formal style. New sections inherit the existing tone.
- **CD-03:** **"Further reading" updates.** Both README and EXTENDING.md have a "Further reading" section. Adding the new sections likely means adding 1-2 cross-links (e.g., README's Further reading links to EXTENDING.md's new tool-target walkthrough; EXTENDING.md's Further reading links to README's per-tool config schema). Planner picks exact links.
- **CD-04:** **Snippet syntax-highlight language tags.** YAML for config blocks, bash for shell, yaml for GHA. Standard Markdown fenced-code conventions; no decision needed.
- **CD-05:** **Plan-cut within the phase.** Likely shape: P1 — README new sections (DOC-04, DOC-05, DOC-06: 3 new sections + cross-links + Further reading update); P2 — EXTENDING.md new section (DOC-07: tool-target walkthrough + link-back to README schema + Further reading update). Two plans, each touching one file. P1 must precede P2 because EXTENDING links into README anchors. No parallelization possible (different files but cross-anchor dependency).
- **CD-06:** **Snippet-correctness verification.** Snippets in the README must be valid: YAML must parse (a quick `python -c "import yaml; yaml.safe_load(open('snippet.yaml'))"` smoke); the GHA snippet must be valid YAML (same). The `mcp-test-framework list-tools` and `mcp-test-framework run --junit-xml=` invocations must match the actual CLI surface (Phase 7 + Phase 9). Planner can include a verification task that lifts each fenced YAML block out of the README and parses it.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` § "Phase 10: v1.1 documentation" — phase goal, success criteria #1–#4, requirement IDs DOC-04..DOC-07
- `.planning/REQUIREMENTS.md` § DOC-04..DOC-07 — full requirement text
- `.planning/PROJECT.md` § "Current Milestone: v1.1" — anti-scope (xdist, OpenAI-compat, dynamic rubrics, agentic judge, stateful testing all deferred to v1.2+); § "Long-term Vision" → indicative milestone shape

### Predecessor phases (the surface this documentation describes)
- `.planning/phases/06-per-session-host-state-isolation/06-CONTEXT.md` — D-08 (sha256-of-real-files verification rigor), D-04 (PYTHON_KEYRING_BACKEND null routing), D-12..D-15 (`_isolated_home` fixture seam)
- `.planning/phases/07-multi-tool-discovery-and-parameterized-testing/07-CONTEXT.md` — multi-tool discovery + parametrized testing surface (the `[<tool_name>]` test ID convention DOC-04 examples reference)
- `.planning/phases/08-per-tool-config-registry/08-CONTEXT.md` — TOOLCFG schema (the schema DOC-04 documents); D-09 (`pytest.skip(reason=...)` mechanism); D-16 (required-non-empty `skip_reason`)
- `.planning/phases/09-junit-xml-output-per-tool-reporting/09-CONTEXT.md` — D-01..D-01b (`--junit-xml=PATH` CLI flag; the flag DOC-06 references); CD-01 (dorny/test-reporter as canonical CI consumer)

### Existing docs (the files being modified)
- `README.md` — currently 146 lines, sections: Prerequisites → Setup → Commands → Configuration → Sample green run → Troubleshooting → Further reading. Phase 10 inserts 3 new sections.
- `docs/EXTENDING.md` — currently 121 lines, sections: Add a new rubric → Swap the judge backend → Further reading. Phase 10 inserts 1 new section.
- `docs/mcp_test_framework_mvp_spec.md` — original MVP spec (288 lines); referenced by README's Further reading. Phase 10 may add a cross-link from new sections back to relevant spec subsections (Claude's discretion).
- `config.example.yaml` — real-named per-tool config reference; cross-linked from README per D-01a but NOT modified.

### Open-source-prep tension (informational)
- `.planning/STATE.md` § "Deferred Items" — open-source-prep items (scrub homelab IP from README; scrub homelab-specific captures from `.planning/`); both are gated on "if/when repo goes public" and remain deferred. D-01 pre-empts the README scrub for new content; existing README content is unchanged in scope.
- `.planning/phases/05-cli-flags-and-marker-config/05-SECURITY.md` AR-05-12 — original record of the README scrub item.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets (referenced by docs, not modified)
- **CLI surface to document:** `src/mcp_test_framework/cli.py` — `run` (with new `--junit-xml=PATH` flag, function-local `import pytest` per L-04), `list-tools`, `version`, `config-init`. README "Commands" section already documents the first three; DOC-04+DOC-06 reference the new flag and `list-tools` workflow.
- **Per-tool config schema:** `src/mcp_test_framework/config.py` (or wherever `ToolConfig` lives) — Pydantic model with fields `skip`, `skip_reason`, `call_arguments`, `judges`, plus reserved `setup` / `depends_on`. README's Per-tool config section reflects this shape verbatim.
- **ISOL-03 verification test:** `tests/test_isolation.py` — concrete file path for DOC-05's reference. Test computes sha256 of `~/.homelab_mcp/credential_registry.json`, `known_hosts`, `migration_state.json`.
- **JUnit XML surface:** `src/mcp_test_framework/_reporter.py` (Phase 09) + the `--junit-xml=PATH` flag wiring in `cli.py`. README CI section invokes the flag; per-tool summary mention is informational.
- **Marker definitions:** `pyproject.toml` `[tool.pytest.ini_options].markers` — `live_homelab` and `live_ollama`. README CI section mentions the default `addopts` excludes them (D-03b).

### Established patterns
- **Concise, code-snippet-led prose.** README is ~146 lines; new sections respect this density. No multi-paragraph explanations where a 3-line code block + 1-line caption suffices.
- **Heading levels.** README uses `##` for top-level sections, `###` for subsections. EXTENDING.md uses `##` for major seams. New content matches.
- **Cross-links use relative paths.** Existing README "Further reading" links to `docs/EXTENDING.md` and `docs/mcp_test_framework_mvp_spec.md` as relative paths. New cross-links match.
- **No emoji, no marketing voice.** Existing tone is engineering-document-y; new content matches.

### Integration points
- **README + config.example.yaml drift risk.** D-01a says we cross-link to config.example.yaml from the README's per-tool section. If the example.yaml drifts (new tool added, knob renamed), the README's "see config.example.yaml for a complete real-server config" pointer remains accurate but the abstract examples in the README itself may go stale. Planner adds a verification task: each TOOLCFG field documented in README must exist in `ToolConfig` (parse-then-attribute-check).
- **EXTENDING.md → README anchor links.** D-04a relies on Markdown anchors (`#per-tool-configuration`). GitHub renders these from `## Per-tool configuration`-style headings; planner verifies the anchor target exists when EXTENDING.md is written.

</code_context>

<specifics>
## Specific Ideas

- **README sections snap into existing structure**, not a top-down rewrite. The phase delivers ~150 new lines across README + EXTENDING.md combined; existing sections are unchanged.
- **Two-block worked example** (D-02) deliberately mirrors the two patterns in `config.example.yaml` — operators going from README → real-config see continuity.
- **The CI snippet "works in 30 seconds"** — D-03's design target. Anything that prevents copy-paste-and-go (matrix, branching env vars, custom action paths) is excluded.
- **"Run pytest tests/test_isolation.py to verify on your machine"** is the concrete verification claim in DOC-05 — operators who don't trust the README's prose can run it themselves.
- The `<safe_read_tool_a>` / `<safe_read_tool_b>` placeholder convention is the planner's call on exact wording, but the SHAPE is fixed: angle-bracketed snake_case tokens that look obviously placeholder.

</specifics>

<deferred>
## Deferred Ideas

- **Scrub homelab-specific captures from `.planning/`** — separately tracked deferred item (STATE.md). Phase 10 only handles README/EXTENDING.md scope. The `.planning/` scrub is gated on repo going public.
- **Generic CI templates for Jenkins, GitLab, CircleCI** — D-03c covers these via a comment in the GHA snippet. Dedicated templates are future work (no requirement, no demand signal).
- **Auto-generated docs (Sphinx, mkdocs).** Out of scope per "Out of Scope" entries in REQUIREMENTS.md. Handcrafted Markdown is the contract.
- **EXTENDING.md "every extension seam" refactor.** Considered and rejected (D-04b) — keep narrow, three sections only.
- **Per-rubric usage examples in README.** EXTENDING.md owns rubric-extension content; the README's per-tool config section only references `judges: [clarity]` syntax, not "what does the clarity rubric do" — that's existing EXTENDING.md territory.
- **Worked example for `call_arguments`** — D-02a downgrades this to a one-paragraph mention. A real worked example is deferred until a real-config tool actually uses it (no demand signal at v1.1).

</deferred>

---

*Phase: 10-v1-1-documentation*
*Context gathered: 2026-05-08*
