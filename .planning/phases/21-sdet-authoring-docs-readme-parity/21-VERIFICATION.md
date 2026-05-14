---
phase: 21-sdet-authoring-docs-readme-parity
verified: 2026-05-14T00:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 1
overrides:
  - must_have: "README ## SDET scenarios sample renders a PASSING 2-test run (2 PASS / 0 FAIL) with char-for-char renderer parity"
    reason: "Re-scoped at the human-verify checkpoint (Plan 21-02 Task 2). The live Proxmox run surfaced the upstream homelab-mcp inputSchema bug on both create_proxmox_vm and delete_proxmox_vm (Phase 19-04's prediction that create was safe did not hold). The operator chose option (a): embed the FAIL output verbatim, reframing the section to highlight the SEED-022 narrative ('framework primitives; SDET owns safety — the framework surfaces upstream contract bugs as real test failures instead of masking them'). The doc-mirroring contract (Phase 16 / SEED-008) is preserved char-for-char — the output is the runner's actual emission, just for a FAIL case rather than a PASS case. README intro paragraph explicitly frames the failure as expected framework behavior; closing paragraph routes the reader to docs/SDET-AUTHORING.md for the _CpuBumpManageVmParams workaround. Deviation documented in 21-02-SUMMARY.md and 21-04-SUMMARY.md."
    accepted_by: "washyu (operator at Plan 21-02 checkpoint:human-verify gate)"
    accepted_at: "2026-05-13T00:00:00Z"
---

# Phase 21: SDET Authoring Docs + README Parity Verification Report

**Phase Goal:** Ship the user-facing documentation for the SDET persona surface built across Phases 17-19, with three deliverables: (1) `docs/SDET-AUTHORING.md` as canonical authoring walkthrough, (2) README `## SDET scenarios` H2 with renderer-parity sample, (3) CLAUDE.md dual-persona routing note.

**Verified:** 2026-05-14
**Status:** passed (with one approved operator override on the README sample's PASS/FAIL polarity)
**Re-verification:** No — initial verification

## Goal Achievement

Phase 21 promised four discrete outcomes. All four are present in the codebase and substantively correct. The one deviation from the original plan (FAIL sample in README instead of PASS sample) was approved by the operator at the planned human-verify gate and is covered by an explicit override above.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A new SDET reading `docs/SDET-AUTHORING.md` learns to: regen codegen, import Params/Response, write the first `tool().call()` test, add a module-scope yield fixture, order tests across files, skip when dependencies are unreachable — without consulting any `.planning/` file. | VERIFIED | `docs/SDET-AUTHORING.md` exists (461 lines). Contains 11 H2 sections in canonical order (Prerequisites, Regenerating codegen, Importing generated Params and Response classes, Writing your first test, Sharing state across tests with a module-scope yield fixture, The inputSchema workaround, Ordering across files, Skipping when dependencies are unreachable, Failure handling: ToolCallError, Future: CI-runnable scenarios, Further reading). All code blocks compile-readable (Python with `python` language tag, bash with `bash`). Zero `.planning/` path leaks (Grep `\.planning/` → 0 matches in docs/SDET-AUTHORING.md). Zero emoji. Reader can follow the doc end-to-end and produce a runnable `tests/sdet/test_<name>.py` file. |
| 2 | Codegen regeneration workflow (DOC-SDET-02) is documented inside `docs/SDET-AUTHORING.md`, not split off into a separate CODEGEN.md. | VERIFIED | `## Regenerating codegen` section at line 27 of docs/SDET-AUTHORING.md. Covers when to regen (schema changes upstream), the command (`uv run mcp-test-framework gen-sdet-classes`), the overwrite scope (`src/mcp_test_framework/sdet/generated/<server_slug>/` only), the "do not hand-edit" header convention, the change-detection signal (mypy/pyright surface type drift), and the import surface as the stable contract across regens. D-02 honored — no separate `docs/CODEGEN.md` was created. |
| 3 | README has a `## SDET scenarios` H2 located between `## Sample green run` and `## Isolation guarantee` with renderer parity to the framework's actual output. | VERIFIED (override applied to PASS/FAIL polarity) | `## SDET scenarios` at README line 260; `## Sample green run` at line 213; `## Isolation guarantee` at line 433 — D-15 ordering correct. Section contains: intro paragraph framing the SEED-022 narrative around the FAIL sample, HTML-comment renderer-source pointer at line 274 (`<!-- mirrors _runner.py output — re-run the framework when output format changes (Phase 21 D-14) -->`), Python source code block (lines 276-342), literal `text`-fenced runner output block (lines 344-418) with the bare-group-header + indented-per-test-row shape from `_render_per_tool_rows`, cross-link to `docs/SDET-AUTHORING.md` (line 423), and invocation pointer to `## Commands` (line 430). The output block is char-for-char the runner's emission for a FAIL case (override accepted by operator). |
| 4 | CLAUDE.md routes Claude entering the repo to `docs/SDET-AUTHORING.md` for SDET-flavored questions. | VERIFIED | `CLAUDE.md` line 19 (single paragraph) appended to existing `## What This Project Is` section. Mentions the SDET persona name, the `--sdet` flag, the `mcp_test_framework.sdet` import surface (`mcp_session`, `tool()`, `ToolCallError`), the `tests/sdet/` discovery scope, and ends with a markdown link to `docs/SDET-AUTHORING.md`. D-03 honored — no new H2 added; 3 sentences total (at budget upper bound). |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docs/SDET-AUTHORING.md` | New canonical SDET authoring doc with 10+ H2 sections, worked example, skip recipe, codegen-regen section | VERIFIED | 461 lines. 11 H2 sections. Contains literal `from mcp_test_framework.sdet.generated.homelab_mcp import` (4 instances), `from mcp_test_framework.sdet import mcp_session, tool, ToolCallError`, `SEED-022`, `project_framework_primitives_sdet_safety_principle` (2 instances), `_CpuBumpManageVmParams` (3 instances), `extra="allow"` (2 instances), `gen-sdet-classes`, `mypy/pyright`, `ProxmoxVmLifecycleState`, `@pytest_asyncio.fixture(scope="module", loop_scope="session")`, `@pytest.mark.order(1)` + `@pytest.mark.order(2)` (pytest-order recipe absorbed verbatim per D-04), `tests/sdet/test_provision.py` + `tests/sdet/test_drive.py` (worked example), `@pytest.mark.skipif`, `socket.create_connection`, `MCPTF_DOGFOOD_PROXMOX_HOST`, 3 `_probe()` definitions (canonical TCP probe + env-only + async MCP capability), operator-domain reason string `"Proxmox host unreachable (set MCPTF_DOGFOOD_PROXMOX_HOST)"`, H3 subheadings `### Worked example`, `### Why this is not framework-internal`, `### Reason-string convention`, `### Other probe shapes`. Zero `.planning/` references in body. |
| `README.md` `## SDET scenarios` section + `## Further reading` link | New H2 between Sample green run and Isolation guarantee; Further reading bullet | VERIFIED (FAIL-sample override applied) | New H2 at line 260. Section contains Python source block and literal text output block per Phase 19-03 `_render_per_tool_rows` shape (bare group header `proxmox_vm_lifecycle` + indented per-test rows `✗ create_returns_pending_vm` and `✗ delete_returns_ok` + `Result: 0 PASS / 2 FAIL / 58 SKIP  in 6.2s` line). No `_readme_sample` temp-suffix leakage. The `## Further reading` H2 at line 492 lists the new doc at line 496: `` - [`docs/SDET-AUTHORING.md`](docs/SDET-AUTHORING.md) -- author SDET scenarios: codegen regen, module-scope fixtures, cross-file ordering, conditional skip recipe. `` Five total markdown link references to docs/SDET-AUTHORING.md in README. |
| `CLAUDE.md` dual-persona note | 1-3 sentence append to existing `## What This Project Is` (no new H2) | VERIFIED | Single paragraph appended at line 19, between MVP-narrowness paragraph (line 17) and `## Tooling` H2 (line 21). Contains literal `SDET`, `mcp_test_framework.sdet`, and markdown link `(docs/SDET-AUTHORING.md)`. No `## Personas` or `## SDET Persona` H2 added. 3 sentences (D-03 upper bound). |
| `tests/sdet/` baseline restored | Only `__init__.py` + `conftest.py` (Phase 20 baseline; Plan 21-02 Task 4 cleanup) | VERIFIED | `ls tests/sdet/` returns: `__init__.py`, `__pycache__/`, `conftest.py`. The temp Plan 21-02 file `tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py` was deleted via `git rm` (commit `6b77fe5`). Phase 20-04 final state restored. |
| `.planning/recipes/pytest-order.md` preserved | Stays as planning artifact even after absorption (D-04 contract) | VERIFIED | File still exists in repo (verified via grep over `.planning/`); D-04 contract honored — public doc does not cross-link to it, planning artifact is preserved. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `docs/SDET-AUTHORING.md` | `src/mcp_test_framework/sdet/generated/homelab_mcp` | Literal import statement in worked example | WIRED | 4 instances of `from mcp_test_framework.sdet.generated.homelab_mcp import` across the doc (imports + first-test + module-fixture worked example + workaround section). Reader can copy-paste import lines and they resolve against actual codegen output. |
| `docs/SDET-AUTHORING.md` | SEED-022 principle (in-repo memory file) | Load-bearing commentary on inputSchema workaround | WIRED | Two explicit references to the memory file name `project_framework_primitives_sdet_safety_principle.md`, plus one to `SEED-022`. Reader entering the `## The inputSchema workaround` section (line 222) and the `## Skipping when dependencies are unreachable` section (line 325) is routed to the canonical principle statement. |
| `README.md ## Further reading` | `docs/SDET-AUTHORING.md` | Markdown link bullet | WIRED | Bullet present at line 496 with literal markdown link `[\`docs/SDET-AUTHORING.md\`](docs/SDET-AUTHORING.md)` between the existing `docs/EXTENDING.md` bullet and the `.planning/PROJECT.md` bullet. |
| `README.md ## SDET scenarios` | `docs/SDET-AUTHORING.md` | Markdown link in section body | WIRED | Two in-section links: line 271 (intro paragraph routing reader to the workaround pattern) and line 423 (closing paragraph routing to the full walkthrough). |
| `README.md ## SDET scenarios` output block | `src/mcp_test_framework/_runner.py` `_render_per_tool_rows` | Char-for-char snapshot of renderer output | WIRED (override-accepted polarity) | Output block at lines 344-418 reproduces the runner's actual emission: pre-run digest banner, `MCP Test Framework (SDET)` header, `Discovered:` / `Running:` / `Skipping:` / `Judges:` lines, the per-tool `skipped:` block listing tools not selected in config, the bare group header `proxmox_vm_lifecycle` followed by two indented `✗` rows with em-dash failure detail (Phase 16 detail pattern), and the `Result:` line. HTML-comment pointer at line 274 cues future maintainers to re-snapshot when renderer output changes. |
| `CLAUDE.md ## What This Project Is` | `docs/SDET-AUTHORING.md` | Inline markdown link in appended paragraph | WIRED | Single link at line 19 closes the appended paragraph. Claude entering the repo reads CLAUDE.md first and has a direct routing signal. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DOC-SDET-01 | 21-01, 21-04 | "Authoring a scenario test for your MCP server" walkthrough in docs/SDET-AUTHORING.md. Uses VM lifecycle scenario as worked example. Covers fixture patterns, ordering, preflight markers, response typing degradation. | SATISFIED | docs/SDET-AUTHORING.md ships full walkthrough using Proxmox VM lifecycle (create/modify/delete) as worked example. Module-scope yield fixture pattern shown with ProxmoxVmLifecycleState dataclass + try/yield/finally teardown. Cross-file ordering recipe absorbed verbatim from `.planning/recipes/pytest-order.md` as `## Ordering across files` H2. Skip recipe with 3 _probe() variants. ToolResponse typing degradation pattern explained (`.raw`/`.data`/`.text`/`.is_error` uniform regardless of outputSchema declaration). |
| DOC-SDET-02 | 21-01, 21-03, 21-04 | Codegen regeneration workflow documented: when to regen (after homelab-mcp schema changes), what gets overwritten, the import surface as the stable contract, mypy/pyright as change-detection mechanism. | SATISFIED | `## Regenerating codegen` H2 at docs/SDET-AUTHORING.md line 27 covers all four sub-points. Reader learns the command, the overwrite scope, the do-not-hand-edit convention, the typecheck-as-drift-detector signal, and the import-surface-as-stable-contract idea. |
| DOC-SDET-03 | 21-02, 21-04 | README sample section showing one scenario file and its operator-side output. Char-for-char parity with renderer (Phase 16 doc-mirroring pattern from SEED-008 closure). | SATISFIED (with override on PASS/FAIL polarity) | README `## SDET scenarios` H2 at line 260 shows a 2-test Proxmox VM lifecycle scenario with literal renderer output. Char-for-char parity is preserved — the output block reproduces what the runner actually emitted in the live Proxmox run on 2026-05-13. The plan originally specified a PASS sample; the run produced a FAIL because the upstream homelab-mcp inputSchema bug hit create_proxmox_vm as well as manage_proxmox_vm. Operator chose to embed the FAIL output (option a at the human-verify gate), reframing the section to highlight the SEED-022 narrative. The doc-mirroring contract (char-for-char with renderer) is honored — only the polarity changed. See override entry in frontmatter for full accept rationale. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | — | — | Doc-only phase. No TODO/FIXME/placeholder comments in deliverables. Two Python-style `...` ellipsis markers appear inside docs/SDET-AUTHORING.md code blocks (line 362, end of skip-recipe example) — these are intentional "fill in your test body" markers standard in authoring docs, not stubs. No empty implementations, no console.log-only handlers, no hardcoded empty data in any user-visible artifact (doc-only phase has no rendered data to flow). |

### Data-Flow Trace (Level 4)

Not applicable — Phase 21 is doc-only. No artifacts render dynamic data; no APIs were created or modified. The Step 4b trace is skipped per the verifier prompt (`SKIPPED — no runnable entry points produced by this phase`).

### Behavioral Spot-Checks

Not applicable — Phase 21 produced no runnable code. Spot-checks SKIPPED per Step 7b constraints (doc-only phase). The closest behavioral check that DID run during execution is the live Proxmox sample run captured at the Plan 21-02 human-verify gate, whose output is now embedded char-for-char in README — that run materially demonstrated the framework's surface (and surfaced the upstream contract bug the override discusses).

### Cross-Cutting Invariants

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| Zero src/ changes | `git diff --name-only dca7af5..HEAD -- src/` returns empty | empty | PASS |
| Doc-only phase contract | Only docs/, README.md, CLAUDE.md, and .planning/ changes | `git diff --name-only dca7af5..HEAD` shows: .planning/REQUIREMENTS.md, .planning/ROADMAP.md, .planning/STATE.md, four .planning/phases/21-.../21-XX-SUMMARY.md files, CLAUDE.md, README.md, docs/SDET-AUTHORING.md | PASS |
| README .planning/ leak count unchanged from baseline | 1 (existing `.planning/PROJECT.md` bullet) | 1 | PASS |
| docs/SDET-AUTHORING.md zero .planning/ leaks | 0 | 0 | PASS |
| tests/sdet/ at Phase 20-04 baseline | `__init__.py` + `conftest.py` only | `__init__.py` + `__pycache__/` + `conftest.py` | PASS |

### Human Verification Required

(none — all goal-achievement checks resolved programmatically; the override deviation was already human-accepted at the Plan 21-02 checkpoint and does not require re-confirmation)

### Gaps Summary

No gaps blocking goal achievement. Phase 21 delivers all three promised artifacts (docs/SDET-AUTHORING.md, README `## SDET scenarios` H2, CLAUDE.md dual-persona note). Cross-linking is bidirectional between README, CLAUDE.md, and docs/SDET-AUTHORING.md. The doc-mirroring contract (Phase 16 / SEED-008) is preserved char-for-char — the README output block is the runner's actual emission for the live Proxmox sample run captured on 2026-05-13.

The single deviation from the original plan (FAIL sample instead of PASS sample in README's `## SDET scenarios`) was made at the planned `checkpoint:human-verify` gate in Plan 21-02 with explicit operator approval. The deviation is goal-neutral: a new SDET arriving at the repo still gets a complete authoring walkthrough; an operator browsing README still sees the SDET scope in renderer-faithful form; Claude entering the repo still routes SDET questions to the canonical doc. In fact, the FAIL polarity strengthens the SEED-022 framing the framework's design depends on — the operator now sees a real example of the framework doing its job (surfacing upstream contract bugs as test failures rather than masking them). Override recorded in frontmatter for traceability.

### Observations for v1.3 close

Two non-blocking notes worth carrying forward:

1. **inputSchema bug breadth.** Phase 19-04's Finding 2 predicted only `manage_proxmox_vm` was affected; the Plan 21-02 live run showed `create_proxmox_vm` and `delete_proxmox_vm` are also affected. Future SDET-sample work that requires a live SUT should plan for this from the start (or use a cheaper substitute tool for the sample). Already flagged in 21-04-SUMMARY.md as a v1.3 close follow-up.
2. **Hello-world MCP fixture priority.** Every doc phase requiring a live SUT run is at risk of this same re-scope cycle. The deferred hello-world MCP fixture (Phase 20 reframe deferred-items table) may warrant promotion up the roadmap. Already flagged in 21-04-SUMMARY.md.

---

*Verified: 2026-05-14*
*Verifier: Claude (gsd-verifier, goal-backward verification mode)*
