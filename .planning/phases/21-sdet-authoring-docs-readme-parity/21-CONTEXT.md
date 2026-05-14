# Phase 21: SDET authoring docs + README parity - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 21 ships the user-facing documentation for the SDET persona surface built across Phases 17–19, with three deliverables:

1. **`docs/SDET-AUTHORING.md`** — single new doc covering the scenario-authoring lifecycle: regen codegen → import `<Tool>Params` / `<Tool>Response` → write a test calling `tool().call()` → add a module-scope yield fixture → add ordering → add the skip recipe. Codegen regen workflow lives as a section inside this doc (not a separate `CODEGEN.md`). The Phase 19 `.planning/recipes/pytest-order.md` cross-file ordering recipe is absorbed verbatim as an `## Ordering across files` section.
2. **README.md `## SDET scenarios` section** — new H2 between `## Sample green run` and `## Isolation guarantee`. Trimmed Proxmox VM-lifecycle scenario (2 tests: create + delete) shown char-for-char with renderer output. Mirrors the Phase 16 doc-mirroring pattern.
3. **CLAUDE.md dual-persona note** — short 1–3 sentence append to existing `## What This Project Is` section.

Doc-only phase. **Zero `src/` changes.** Worked example is lifted verbatim from Phase 19-04 artifacts because Phase 20 deleted the in-tree dogfood file (the doc becomes the canonical home for the scenario).

</domain>

<decisions>
## Implementation Decisions

### Doc Layout
- **D-01:** `docs/SDET-AUTHORING.md` is a new single-file doc — NOT appended to `docs/EXTENDING.md`. The SDET test-author audience is distinct from EXTENDING.md's current operator/judge-config audience.
- **D-02:** Codegen regeneration workflow (DOC-SDET-02) lives as a section INSIDE `docs/SDET-AUTHORING.md` (no separate `docs/CODEGEN.md`). Regen is part of the SDET authoring loop — author writes scenario, schema changes upstream, author reruns `gen-sdet-classes`, mypy/pyright flag drift. Keeping the lifecycle in one place matches the natural authoring flow.
- **D-03:** CLAUDE.md gets a 1–3 sentence note appended to the existing `## What This Project Is` section. Pattern: `v1.3 added the SDET persona as a second first-class user. Operator runs the contract pass; SDET authors scenarios in tests/sdet/. See docs/SDET-AUTHORING.md.` No new `## Personas` H2 — minimal churn, discoverable where Claude looks first.
- **D-04:** `.planning/recipes/pytest-order.md` is **absorbed** into `docs/SDET-AUTHORING.md` as an `## Ordering across files` section. The public doc owns the canonical version. Eliminates broken-link risk and prevents `.planning/` paths leaking into public docs (same anti-pattern the v1.2 Phase 12 doc scrub addressed). The original `.planning/recipes/pytest-order.md` stays as a planning artifact but is NOT cross-linked from public docs.

### Worked Example Sourcing
- **D-05:** The worked example is lifted verbatim from `.planning/phases/19-stateful-primitives-domain-ui-integration/19-04-SUMMARY.md` and `.planning/phases/19-stateful-primitives-domain-ui-integration/19-CONTEXT.md` (Proxmox VM lifecycle scenario). The doc becomes the new canonical home for this scenario — no `see tests/sdet/...` link, since Phase 20 deliberately deleted the in-tree file to keep the framework SUT-agnostic.
- **D-06:** The `_CpuBumpManageVmParams(ManageProxmoxVmParams)` subclass with `extra="allow"` pattern (the inputSchema-bug workaround) is INCLUDED in the doc WITH an annotation explaining: (1) the upstream homelab-mcp inputSchema bug it works around (optional fields declared `type:string` but defaulted to `null`), (2) why the framework does NOT mask this with `exclude_none=True` (SEED-022 — framework primitives, SDET owns safety). This is a load-bearing teaching moment for the framework-primitives principle, not editorial noise.
- **D-07:** Doc structure is **incremental build-up**, not complete-then-dissect. Walk the reader through: regen codegen → import `Params`/`Response` → write the first test that calls `tool().call()` → add the module-scope fixture → add yield/teardown → add cross-file ordering → add the skip recipe. Reader can stop at any depth; matches the natural authoring flow.
- **D-08:** No "this file used to ship in-tree" footnote. The doc is the source of truth; the deletion in Phase 20 was deliberate (framework ships SUT-agnostic). Readers copy code from the doc into their own `tests/sdet/test_<name>.py`. Avoids leaking planning-phase history.

### Skip Recipe (replacing the killed `requires_homelab` marker)
- **D-09:** Canonical recipe is `@pytest.mark.skipif(not _probe(), reason=...)` with an **author-defined** `_probe()` callable. Framework provides ZERO probe primitives — honors SEED-022 (framework primitives, SDET owns safety). The doc shows 2–3 concrete `_probe()` examples: env-var presence check, TCP reachability with timeout, MCP capability check.
- **D-10:** Reason-string convention is **prescribed** in operator-domain phrasing: `reason="Proxmox host unreachable (set MCPTF_DOGFOOD_PROXMOX_HOST)"` — names the missing dependency AND the env var to set. Mirrors the Phase 14/16 operator-output domain language so SKIP rows from `_render_per_tool_rows` read consistently.
- **D-11:** Skip recipe lives in a **dedicated `## Skipping when dependencies are unreachable` section AFTER the worked example**. Worked example stays focused on the happy path; skip recipe is independently linkable from README/CLAUDE.md and easier to maintain.
- **D-12:** Deferred hello-world MCP CI fixture (per Phase 20 D-06 disposition note) is mentioned in a **brief `## Future: CI-runnable scenarios` section** at the end of the doc. One short paragraph setting expectations: today, scenarios that require live infrastructure SKIP in CI; a future hello-world MCP server is planned as the home for CI-runnable scenarios that exercise every codegen-generated wrapper without operator infrastructure. Also referenced in passing in the skip-recipe section.

### README Sample + Char-for-Char Parity (DOC-SDET-03)
- **D-13:** README sample is a **minimal 2–3 test scenario**, not the full VM lifecycle. Demonstrates: import a `Params`/`Response`, write a test, get a row in operator output. Skips fixtures + ordering — those live in `SDET-AUTHORING.md`.
- **D-14:** Char-for-char parity is enforced via **manual snapshot at phase commit time + comment pointer**. Run `mcp-test-framework run --sdet` against the README sample test once during Phase 21 execution; paste literal output into the README block; add a comment near the sample noting the renderer source (`# mirrors _runner.py output — re-run the framework when output format changes`). Same approach Phase 16 used for the existing `## Sample green run`. No regression test, no regen script — accepts that future renderer changes need a manual sweep.
- **D-15:** Sample placement is a **new `## SDET scenarios` H2 between `## Sample green run` and `## Isolation guarantee`**. Follows the natural README reading order: operator sees the contract pass first, then learns about authored scenarios.
- **D-16:** The actual sample test source is a **trimmed Proxmox VM lifecycle (2 tests: `create` + `delete`)** — consistent with the `docs/SDET-AUTHORING.md` worked example so the reader's mental model carries between docs. The `modify` test is omitted from the README sample (the inputSchema-bug workaround stays exclusively in `SDET-AUTHORING.md`).

### Claude's Discretion
- File naming convention inside `docs/SDET-AUTHORING.md` (H2 / H3 ordering, code-block language tags, etc.) is the planner's call subject to matching `docs/EXTENDING.md` conventions.
- Exact wording of the CLAUDE.md persona note (within the 1–3 sentence budget) is the planner's call.
- Whether the README sample shows the test file as a single block or splits it across "code" / "output" sub-blocks is the planner's call, subject to char-for-char parity holding for the output block.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 21 source artifacts (worked example + recipe)
- `.planning/phases/19-stateful-primitives-domain-ui-integration/19-04-SUMMARY.md` — Phase 19 Plan 04 dogfood VM-lifecycle scenario source-of-truth: module-scope yield fixture, `ProxmoxVmLifecycleState` dataclass, three file-ordered async tests, `_CpuBumpManageVmParams(extra='allow')` workaround, range-aware VMID allocator, strand sweep. **The worked example for `docs/SDET-AUTHORING.md` is lifted verbatim from here.**
- `.planning/phases/19-stateful-primitives-domain-ui-integration/19-CONTEXT.md` — Phase 19 decisions: module-scope fixture pattern, STATE-03 cross-test state passing, cleanup-on-failure contract.
- `.planning/recipes/pytest-order.md` — cross-file ordering recipe; absorbed into `docs/SDET-AUTHORING.md` as the `## Ordering across files` section.
- `.planning/phases/20-preflight-conditional-skip/20-04-SUMMARY.md` — Phase 20 D-06 disposition note for Phase 21 docs (skip-recipe rationale + hello-world MCP CI fixture deferral).
- `.planning/phases/20-preflight-conditional-skip/20-CONTEXT.md` — Phase 20 reframe context: `requires_homelab` killed per SEED-022, why the framework owns no probe primitives.

### Doc conventions and renderer parity
- `docs/EXTENDING.md` — existing extension doc; `docs/SDET-AUTHORING.md` should match its H2/H3 style and code-block conventions.
- `docs/ERROR-STYLE.md` — Phase 12 doc-style precedent for new standalone docs.
- `docs/MIGRATION-v1-to-v2.md` — recent migration-style doc precedent.
- `README.md` §`## Sample green run` — the Phase 16 doc-mirroring pattern (char-for-char parity with renderer); DOC-SDET-03 inherits this exact pattern.
- `src/mcp_test_framework/_runner.py` `_render_per_tool_rows` — the renderer whose output the README sample must mirror char-for-char (see Phase 19-03 SUMMARY for scenario-block rendering shape).
- `src/mcp_test_framework/_runner.py` `_render_scenario_pre_run_digest` — Phase 19 scenario pre-run digest (relevant when the SDET sample run shows scenario discovery).

### Requirements + roadmap
- `.planning/REQUIREMENTS.md` §DOC — DOC-SDET-01, DOC-SDET-02, DOC-SDET-03 requirement rows.
- `.planning/ROADMAP.md` Phase 21 entry — phase goal, scope summary.

### Cross-phase context (skip recipe + framework-primitives principle)
- Memory file `project_framework_primitives_sdet_safety_principle.md` (SEED-022) — framework does no tool-safety reasoning; SDET decides what to call. **Load-bearing for the skip-recipe section's framing.**
- `.planning/phases/18-sdet-test-surface-typed-errors/18-CONTEXT.md` — `mcp_session`, `tool(name)`, `ToolCallError` design context (consumed by the worked example).
- `.planning/phases/17-schema-driven-codegen-surface/17-CONTEXT.md` — codegen design (Params/Response classes, regen workflow, generated-file location) consumed by the codegen-regen section.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/sdet/conftest.py` — Phase 18 JUnit `user_properties` hook for `ToolCallError`; the doc references its existence so readers know it's the wiring under their authored tests. Doc does NOT instruct readers to modify it.
- `src/mcp_test_framework/sdet/generated/homelab_mcp/` — concrete generated Params/Response classes the worked example imports from. The doc shows actual import paths (`from mcp_test_framework.sdet.generated.homelab_mcp import CreateProxmoxVmParams, CreateProxmoxVmResponse`).
- `src/mcp_test_framework/sdet/session.py` + `_tool_factory.py` — exported `mcp_session` and `tool(name)` symbols the doc references for the SDET authoring API.
- `src/mcp_test_framework/sdet/errors.py` — `ToolCallError` typed exception class surfaced in the failure-handling section.

### Established Patterns
- **Phase 16 doc-mirroring (README ↔ renderer)** — README sample blocks must quote literal `_runner.py` output, char-for-char (whitespace + ANSI). The `## Sample green run` section is the precedent the new `## SDET scenarios` section mirrors exactly. Re-snapshot manually when renderer output changes.
- **Single new doc per major capability** — `docs/EXTENDING.md` (v1.0), `docs/ERROR-STYLE.md` (v1.2), `docs/MIGRATION-v1-to-v2.md` (v1.2) — each is its own file, not appended to a kitchen-sink doc. `docs/SDET-AUTHORING.md` follows this pattern.
- **Incremental authoring narrative** — `docs/EXTENDING.md` walks `discover → scaffold → opt-in → run` as a stepwise flow. The SDET authoring doc uses the same incremental shape.

### Integration Points
- README's existing `## Further reading` already lists doc files — `docs/SDET-AUTHORING.md` adds itself there.
- README's `## Commands > Run the test suite` block already documents `--sdet` (added in Phase 18) — the new SDET sample H2 cross-links to it for the invocation.
- CLAUDE.md's `## What This Project Is` section is the touchpoint for the persona note; no other section of CLAUDE.md changes.

</code_context>

<specifics>
## Specific Ideas

- The doc's `## Ordering across files` section absorbs `.planning/recipes/pytest-order.md` verbatim (the recipe was authored explicitly to be Phase 21 content per the Phase 19 SUMMARY).
- The inputSchema-bug commentary in the worked example must reference SEED-022 by principle name (or cite memory file `project_framework_primitives_sdet_safety_principle.md`) — without it, the `extra='allow'` pattern looks arbitrary.
- The README sample's literal output block must include the leading scenario-group header (per Phase 19-03 `_render_per_tool_rows` shape: bare group header + indented per-test rows), not just the per-test rows.
- The skip-recipe `_probe()` examples should at least include: (1) env-var presence (`os.environ.get("MCPTF_DOGFOOD_PROXMOX_HOST")`), (2) TCP `socket.create_connection((host, 22), timeout=2)` with try/except, (3) optional: MCP capability check via `mcp_session` if the doc finds room.

</specifics>

<deferred>
## Deferred Ideas

- **Hello-world MCP server for CI-runnable scenarios** — covered as a deferred item in the project state (per Phase 20 reframe). Phase 21 mentions it in a `## Future: CI-runnable scenarios` section but does NOT implement it. Future v1.x phase per the existing deferred-items log.
- **Char-for-char regression test (CI-enforced README parity)** — surfaced during D-14 discussion as an alternative to manual snapshots. Deferred — Phase 16 manual-snapshot precedent holds for v1.3. Revisit if README drift becomes a recurring problem.
- **Regen script for README samples (`scripts/regen-readme-samples.py`)** — same domain as the above; deferred for the same reason.
- **Per-tool `_probe()` library** — the question whether the framework should ship a small library of reusable `_probe()` helpers came up implicitly. **Rejected by SEED-022** at this point; the framework owns no probe primitives. Author-defined `_probe()` is the canonical pattern. Not deferred — rejected.
- **`docs/EXTENDING.md` update for the new SDET surface** — left as-is; if any SDET-relevant operator-side knob exists in EXTENDING.md it stays there, but the doc is not re-restructured. If a follow-up doc-pass surfaces a real gap, that's a v1.4 hygiene item.

</deferred>

---

*Phase: 21-sdet-authoring-docs-readme-parity*
*Context gathered: 2026-05-14*
