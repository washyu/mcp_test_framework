# Phase 12: Doc & persona foundation - Context

**Gathered:** 2026-05-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Reshape the user-facing surface of the repo so an operator who didn't write the MCP server they're testing can browse the docs, run `config-init`, get a runnable scaffold, and read every operator-visible error message in operator terms. Strip planning provenance (phase numbers, plan IDs, internal spec IDs) from `README.md`, `config.example.yaml`, `.env.example`, `docs/EXTENDING.md`. Generic placeholder tool names in `config.example.yaml`; homelab-mcp-flavored config preserved at `examples/homelab-mcp.yaml`. `mcp-test-framework list-tools` now shows `inputSchema` summaries so the operator can construct calls without reading SUT source.

**In scope:** CLEAN-01..06, PERSONA-01..03 (9 requirements). Doc/example cleanup, persona reframe, `config-init` completeness, `list-tools` UX, operator-grade error messages.

**Out of scope:** Phase 13's runtime changes (opt-in tools allowlist, schema v2 migration, drop `.env`/env-overlay). Phase 12 anticipates them in scaffold output and ERROR-STYLE.md but does not flip runtime semantics.

</domain>

<decisions>
## Implementation Decisions

### config-init posture
- **D-01:** `config-init` emits a **v1-header, v2-style content** config — `version: 1` (loadable by today's runtime) but populated as Phase 13 will want it. Phase 13's v1→v2 conversion becomes a header bump + flipping the unlisted-default; NOT a regenerate-from-scratch. Configs generated in Phase 12 survive Phase 13 with minimal edit.
- **D-02:** `tools:` block contains **all discovered tools, each with `skip: true` and `skip_reason: "review and remove skip to enable"`**. Operator reads through and removes `skip` from tools they want to test. Zero tools run until operator opts in; safest default.
- **D-03:** **Drop `target.tool_name` entirely.** Removed from `config-init` output, removed from all docs. Phase 13 v2 schema removes the field from the Pydantic Config model and emits a deprecation/migration message for v1 configs that still carry it. Multi-tool discovery + opt-in `tools:` allowlist already says exactly what runs; the `target` field is redundant. Focus-one-tool workflow = separate `focus-toolname.yaml` + `--config` (no CLI flag replacement).
- **D-04:** `config-init` against an unreachable MCP server **fails loud with a PERSONA-03-style error** (no `--offline` mode, no placeholder fallback). Error names the actionable next step (e.g., "verify it runs with: `uvx <cmd>`").

### list-tools UX at N=70
- **D-05:** Default per-tool render = **name + 1-line truncated description + one-line param signature** (`(host: str, port: int, *, timeout: int = 30)`). Required params before kwargs. ~3-4 lines per tool, ~280 lines total at N=70.
- **D-06:** `--full` flag adds **full description (untrimmed) + per-parameter descriptions** from `inputSchema`. Stays human-readable; does NOT dump raw JSON.
- **D-07:** `--json` (machine-readable, unchanged from v1.1) stays separate. Two orthogonal flags: `--full` = verbosity, `--json` = format.
- **D-08:** `--name PATTERN` substring filter, case-insensitive. Composes with `--full` and `--json`. Drill-in to one tool = `list-tools --name list_keyring_credentials --full`.
- **D-09:** Default sort order **stays alphabetical** (`D-list-4` v1.0 contract preserved). Sort is not the lever for managing scale; filtering is.

### Doc cleanup + examples/ shape
- **D-10:** **Per-section semantic rewrite**, not regex strip. Each affected line is rewritten in operator terms; spec IDs that anchored explanatory content (e.g., `README.md:96-97` "Reserved for v1.5+ stateful testing (TOOLCFG-03)" → "Reserved for stateful testing (future); runtime no-op today.") are removed and the sentence rewritten to stand alone.
- **D-11:** `examples/` is a **one-file directory + brief README** (`examples/homelab-mcp.yaml` + `examples/README.md`, 10-20 lines explaining the convention). Sets the convention without overcommitting.
- **D-12:** PERSONA-01 README addition = **top-of-README short framing paragraph + link**. 3-5 sentences near Core Value: "The framework treats your MCP server as a black box — you don't need to read its source. `list-tools` shows you the parameter shapes; `config-init` scaffolds the suite. Designed for operators testing servers they didn't author." Walkthrough lives in `docs/EXTENDING.md` (added as part of this phase).
- **D-13:** `config.example.yaml` shows **3 placeholder tool entries demonstrating pattern variations**: `<safe_read_tool_a>` (minimal opt-in, just `skip: false`), `<safe_read_tool_b>` (opt-in + `call_arguments` showing how to pre-fill required params), `<destructive_tool_c>` (`skip: true` + `skip_reason` demonstrating skip-with-reason). Brief comment block at top explains v2-style opt-in semantics.
- **D-14:** `config.example.yaml` and `config-init` output are **deliberately different files with different purposes**. `config.example.yaml` = static, hand-curated TEMPLATE with placeholder names, comments, 3 pattern variations — reads like documentation. `config-init` output = dynamic, generated against a live server with REAL discovered tool names, all `skip: true`, `skip_reason: "review and remove skip to enable"`. README/CLEAN-04 links to BOTH.

### Error message scope + style
- **D-15:** All four error surfaces in scope for Phase 12: **config load failures, MCP server spawn failures, judge connect failures, missing-config / missing-tool errors**.
- **D-16:** **Style guide locked upfront in `docs/ERROR-STYLE.md`** (or new section in `EXTENDING.md`). Rules: (1) operator terms only, no spec IDs, no internal jargon (TOOLCFG/D-/CD-/etc); (2) name the actionable next step inline (`run X to recover`); (3) one-line summary + multi-line detail block, NOT a wall of text; (4) preserve exit codes (don't change behavior, only words). Each rewritten message references the guide; future phases (13-16) inherit the guide automatically.
- **D-17:** **SAFE-03 (no-config failsafe) and SAFE-06 (v1→v2 migration) reference messages are pre-drafted in Phase 12's ERROR-STYLE.md**. Phase 13 implements them verbatim. Locks the most consequential operator-visible messages while persona context is fresh; gives Phase 13 a no-debate copy-paste target.

### Claude's Discretion
- Plan ordering within Phase 12 (e.g., whether `config-init` work lands before or after the README rewrite). Suggested sequence: ERROR-STYLE.md first → config-init rewrite (drives example.yaml shape) → docs sweep → list-tools work → persona section.
- Specific wording of the persona-framing paragraph and the placeholder tool-name suffixes (a/b/c naming).
- Whether `examples/README.md` and `docs/ERROR-STYLE.md` are new files or sections grafted into existing files — pick whichever produces the cleanest doc tree.
- Whether the `--name` filter in `list-tools` is glob-style or pure substring — pure substring (case-insensitive) is the default unless a clear reason to do globs emerges in research.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/REQUIREMENTS.md` §CLEAN, §PERSONA — the 9 locked requirements for this phase
- `.planning/PROJECT.md` "Current Milestone: v1.2 Operator-First Design" — milestone framing, v1.2 locked decisions, anti-vision
- `.planning/ROADMAP.md` Phase 12 row — goal, depends-on, success criteria
- `.planning/STATE.md` "v1.2 roadmapping decisions (2026-05-09)" — sequencing rationale (why CLEAN+PERSONA merged into one phase, why this lands first)

### Files affected by this phase
- `README.md` — CLEAN-01 sweep + CLEAN-04 link to examples + PERSONA-01 framing paragraph
- `docs/EXTENDING.md` — CLEAN-01 sweep + PERSONA-01 walkthrough section + ERROR-STYLE codification
- `config.example.yaml` — CLEAN-02 genericize (3 pattern-variation entries with placeholder names)
- `.env.example` — CLEAN-06 reframe (env vars for CI secrets only, not config)
- `src/mcp_test_framework/cli.py` (`list-tools`, `config-init`, `_load_config`) — PERSONA-02 inputSchema rendering, CLEAN-05 self-contained scaffold, drop `target.tool_name` emit, PERSONA-03 error rewrites
- `src/mcp_test_framework/config.py` — error message rewrites at config load surfaces

### Files created by this phase
- `examples/homelab-mcp.yaml` — CLEAN-03 (move current config.example.yaml content here)
- `examples/README.md` — CLEAN-03 convention doc
- `docs/ERROR-STYLE.md` (or new section in `docs/EXTENDING.md`) — style guide + SAFE-03 / SAFE-06 reference messages

### Cross-phase coupling (forward refs into Phase 13)
- Phase 13 PLAN must remove `target.tool_name` from the Pydantic Config model and emit a deprecation/migration message for v1 configs that still carry the field (D-03)
- Phase 13 PLAN must implement SAFE-03 and SAFE-06 messages **verbatim** from Phase 12's ERROR-STYLE.md reference messages (D-17)
- Phase 13's v1→v2 schema bump must be a header bump + flipping the unlisted-default — NOT a regenerate-from-scratch — because Phase 12 configs are already v2-shape content (D-01, D-02)

### Pre-existing context worth re-reading
- `docs/mcp_test_framework_mvp_spec.md` — authoritative MVP spec (preserved verbatim per PROJECT.md)
- `docs/EXTENDING.md` v1.1 sections (per-tool config, isolation guarantee, env passthrough allowlist) — already operator-grade, set the bar for Phase 12's additions
- Memory: `project_output_ergonomics_at_scale.md`, `project_vibe_coded_persona.md`, `project_doc_scrub_planning_artifacts.md`, `project_genericize_example_config.md`, `feedback_scaffold_completeness.md` — all directly informed gray area selection

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_list_tools_async` in `src/mcp_test_framework/cli.py:320` — already returns `list[Tool]` from the live MCP session. PERSONA-02 inputSchema rendering reuses this; only the formatter (`_format_tools_text`) changes.
- `_format_tools_json` in `src/mcp_test_framework/cli.py` — `--json` machine-readable shape stays as-is; PERSONA-02 work is purely on the human-readable side.
- `config-init` body (`src/mcp_test_framework/cli.py:219-298`) — already runs `_list_tools_async` + emits YAML. CLEAN-05 + D-02 add: every discovered tool emitted as a `tools.<name>: { skip: true, skip_reason: ... }` block; `target:` no longer emitted; ollama/mcp_server/judge_timeout_seconds top-level sections fully populated (not deltas relying on env defaults).
- `_load_config` (`src/mcp_test_framework/cli.py:65-88`) — single seam where ValidationError propagates today; PERSONA-03 error rewrites land here for the config-load surface.

### Established Patterns
- Banned-imports test (`tests/`) and snippet-correctness regression suite (v1.1 Phase 10) demonstrate the "lock contracts mechanically" pattern. ERROR-STYLE.md adopting this pattern (banned-token grep test) is on the table for late-phase plans but not committed in D-16; defer-or-add decision left to plan-phase.
- Per-tool config registry (`tools.<name>` blocks with `extra="forbid"` + `version: 1`) is the schema `config-init` must populate. v2-style content under v1 header means `version: 1` literal but content already opt-in shape.
- Typer command pattern (`@app.command(...)`) for CLI surface — `--name` and `--full` additions on `list-tools` follow the existing flag conventions.

### Integration Points
- `list-tools` formatter (`_format_tools_text`) — single function rewrite for D-05/D-06/D-08 (default shape, --full, --name filter applied before render).
- `config-init` template emit — adjusts the YAML scaffold to match D-01/D-02/D-03 (no target:, all-skip-true tools block, full top-level sections, opt-in semantics comment).
- Error-emitting sites across `cli.py` and `config.py` — each gets PERSONA-03 rewrite per ERROR-STYLE.md rules.

</code_context>

<specifics>
## Specific Ideas

- Persona-framing line lifted from discussion: "The framework treats your MCP server as a black box — you don't need to read its source. `list-tools` shows you the parameter shapes; `config-init` scaffolds the suite. Designed for operators testing servers they didn't author."
- Placeholder tool naming convention from CLEAN-02: `<safe_read_tool_a>`, `<your_tool_name>` — extend to `<safe_read_tool_b>`, `<destructive_tool_c>` for the 3-entry config.example.yaml pattern (D-13).
- ERROR-STYLE one-line summary + multi-line detail shape, with action verb opening the action line: "run `mcp-test-framework config-init -o config.yaml` to generate a starter config" — matches the bar set by the existing 260507-j6i "MCP server command not on PATH" message.
- `config-init` output's per-tool `skip_reason` text: `"review and remove skip to enable"` — short, action-imperative, matches operator workflow.

</specifics>

<deferred>
## Deferred Ideas

### Cross-phase tasks (Phase 13)
- Remove `target.tool_name` from the Pydantic Config model; emit deprecation/migration message for v1 configs that still carry the field
- Implement SAFE-03 and SAFE-06 error messages verbatim from Phase 12's ERROR-STYLE.md reference drafts
- v1→v2 schema bump = header + flip-unlisted-default (NOT regenerate); explicitly preserve compatibility with Phase 12 configs

### v1.3+ todos (post-milestone)
- `list-tools` sort grouping (safe-to-call heuristic, name-prefix sections like `## get_*`, `## list_*`) if N=70 alphabetical scrolls become a pain point in practice
- ERROR-STYLE.md banned-token enforcement test (mechanical regression guard for the style guide) — flagged in D-16 alternatives but not committed; revisit if drift is observed during v1.3+ phases
- Multi-config workflow ergonomics — if focus-one-tool via separate `focus-*.yaml + --config` (D-03) becomes a pain point, consider a `--only TOOL_NAME` CLI flag (rejected for v1.2 to keep config the single source of truth)

### Out of phase scope (already deferred at scoping)
- Color / TTY-aware rendering for `list-tools` — explicit out-of-scope per REQUIREMENTS.md "Out of Scope" table
- Live-progress streaming — out-of-scope per REQUIREMENTS.md
- Automated planning-artifact regression guard — explicitly deferred per v1.2 locked decision

</deferred>

---

*Phase: 12-doc-persona-foundation*
*Context gathered: 2026-05-08*
