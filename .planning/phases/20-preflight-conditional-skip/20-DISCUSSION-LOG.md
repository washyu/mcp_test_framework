# Phase 20: Preflight + conditional skip - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-13
**Phase:** 20-preflight-conditional-skip
**Areas discussed:** Reachability mechanism, Subsystem coverage scope, Session preflight interaction, Close Phase 19 D-02 here

> **Note:** All four selected areas collapsed into a single architectural reframe driven by the user. The framework's identity as a generic MCP test framework is incompatible with `requires_homelab(...)` (or any flavor of framework-owned subsystem-specific reachability), so the original Phase 20 deliverable was scrapped and the phase pivoted to closing the loose ends produced by that reframe.

---

## Reachability mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Probe via MCP tool call | Inside @requires_homelab, do a quick get_proxmox_node_status / list_proxmox_resources call. Reuses mcp_session + Phase 18 infra. Risk: roundtrip can blow sub-second budget. | |
| Direct TCP socket probe | Add `homelab.proxmox.host` mcptf config knob; socket.create_connection((host, 8006), timeout=0.5). Sub-second by construction. Cost: duplicates config. | |
| Read host from mcp_server.env | Parse PROXMOX_HOST from config.mcp_server.env. No new config. Cost: leaks an env-var convention. | |
| Hybrid: MCP-call with socket pre-check | Socket if host configured; MCP-call fallback otherwise. | |
| Other (free-text) | "the framework shouldn't be focused on a proxmox server since this is supposed to be a generic mcp test framework we are just using it to test the homelab mcp" | ✓ |

**User's choice:** Reframe — the framework should not contain Proxmox-specific code at all.
**Notes:** This invalidates `requires_homelab(proxmox=True)` as an API. The whole premise of named-subsystem keyword args presumes the framework knows about specific SUT subsystems.

---

## Marker shape (follow-up)

| Option | Description | Selected |
|--------|-------------|----------|
| Framework owns only what it has config for | @requires_mcp_server + @requires_ollama only. Proxmox is SDET-side via stock skipif. | |
| Generic registry pattern | @requires_subsystems(...) + SDET-registered probe callables. | |
| Drop per-subsystem flavor | One primitive: @requires(probe_callable, reason). Framework wraps as skipif with sub-second timeout enforcement. | |
| Other | (User dismissed; clarified next.) | |

**User's choice:** None — clarified in next exchange that the framework should ship NOTHING for this.
**Notes:** "again the framework is a generic MCP test framework if i were to test a MCP that works on the context memory it wouldn't need a proxmox check. IF the mcp has an external dependency the tester can add that check to there test code."

---

## Framework primitive (follow-up)

| Option | Description | Selected |
|--------|-------------|----------|
| One generic decorator + timeout helper | @requires(probe_callable, reason, timeout=0.5). Framework-owned wrapper. | |
| Just a timeout helper, no decorator | probe_with_timeout(callable, seconds=0.5) -> bool; SDET uses with stock skipif. | |
| Nothing in mcptf — docs-only | @pytest.mark.skipif already does this. Phase becomes pure recipe doc. | |
| Other (free-text) | "nothing they can add that them selfs the framework should only be concerned about wrapping the tool calls and any parameter/body calls and return values." | ✓ |

**User's choice:** Framework ships nothing for reachability/preflight. Pytest's stock @pytest.mark.skipif is sufficient; SDET writes their own probes.
**Notes:** Sharpens SEED-022. Locks D-01 / D-02 in CONTEXT.md.

---

## Phase 20 scope (post-reframe)

| Option | Description | Selected |
|--------|-------------|----------|
| Cancel Phase 20 entirely | Remove from ROADMAP; drop PREFLIGHT-01/02; v1.3 becomes 5 phases. | |
| Rewrite Phase 20 as REQUIREMENTS scrub + dogfood SDET-side fix | Keep slot, pivot to: rewrite requirements; close Phase 19 D-02 by SDET-side skipif probe + modify-step substitution; zero src/ changes. | ✓ |
| Fold dogfood SDET fix into Phase 21 docs | Cancel Phase 20; recipe + dogfood touch-up land in Phase 21. v1.3 becomes 4 phases. | |
| Other | | |

**User's choice:** Option 2 (selected as `2`).
**Notes:** Phase 20 keeps its slot but pivots entirely. Closes Phase 19 D-02 inside Phase 20.

---

## Modify-step substitution + Probe shape (batched)

| Option | Description | Selected |
|--------|-------------|----------|
| Lifecycle action (start → stop) | manage_proxmox_vm IS a lifecycle-action tool — replace cores=2 with start/stop sequence. | |
| Different config-mutating tool | Find a tool that actually mutates VM config (clone? update_device_config?). | |
| Drop modify step | Two-step dogfood: create → delete only. | |
| Other (free-text) | "are these dogfood steps for making sure the framework generated code works? if so do they need to be baked in to the test code for this project over all? ... if we were to run this in a github action it would fail since it wouldn't have access to my proxmox system. so we should just have tests that validate that the code was generated. did all the tools in the SUT got wrapped, did the parameters/body/results classes get generated. and leave the do they work for the uat for now. we might have to add a quick hello world type of mcp in the project for ci/cd check ... but it is out of scope for now." | ✓ |
| Probe-shape options | Socket-from-env / socket-from-mcptf-config / MCP-tool-call / Other | |
| Probe-shape free-text | "no proxmox hardcoded tests in this framework" | ✓ |

**User's choice:** Substantially deeper reframe than the dogfood-substitution question anticipated. The dogfood-as-shipped-test is itself wrong; the actual framework concern is "did codegen wrap everything correctly," which is testable without a live SUT. Hello-world MCP for CI is the future answer; out of scope for Phase 20.
**Notes:** This forced a final scope question (next).

---

## Final Phase 20 scope confirmation

| Option | Description | Selected |
|--------|-------------|----------|
| Remove tests/sdet/test_proxmox_vm_lifecycle.py | Delete the Proxmox-hardcoded dogfood entirely. | ✓ |
| Keep tests/sdet/test_basic_call.py | Annotate live-MCP-only; document inline skipif recipe. | (not explicitly selected — deferred to planner per CONTEXT D-06) |
| Drop PREFLIGHT-01/02 from REQUIREMENTS.md | Replace with deferred "hello-world MCP" entry; v1.3 REQ count 21→19. | ✓ |
| Add 1-2 codegen-internal-coherence self-tests | Static (no live MCP): every generated module has matching Params/Response; _REGISTRY is exhaustive against its directory. | (not selected — replaced with mock-fixture approach below) |
| Other (free-text) | "we can just add mock unit tests for this — pass a hardcoded tool list and parameter response and body thingies and see if we generate the correct wrappers." | ✓ |

**User's choice:** Three confirmed (delete dogfood, drop PREFLIGHT-01/02, mock-fixture-driven codegen unit tests). The static-coherence option was implicitly replaced by the user's mock-fixture suggestion (closer to "test the codegen pipeline end-to-end with synthetic input" than "introspect already-generated artifacts"). test_basic_call.py disposition was not addressed — captured as Claude's Discretion in CONTEXT D-06.
**Notes:** Locks D-04, D-07–D-10, D-11 in CONTEXT.md.

---

## Claude's Discretion

- **Mock-fixture file location and naming** — user gave the principle ("hardcoded tool list + params/response, verify wrappers generated correctly"); planner picks the file structure.
- **Synthetic tool count** — three is enough to cover the codegen branches user cares about (required scalars / optional defaults / arrays / outputSchema-present-or-absent); planner can adjust.
- **REQUIREMENTS.md ID names** (CLEANUP-DOGFOOD-01 / CODEGEN-COVERAGE-01 / REQ-SCRUB-01) — placeholder; planner finalizes consistent with existing convention.
- **`tests/sdet/test_basic_call.py` disposition** (CONTEXT D-06) — three options spelled out; planner picks based on what looks cleanest after the deletion.

## Deferred Ideas

- **Hello-world MCP server for CI/CD coverage** — captured in CONTEXT `<deferred>`. User explicitly said "out of scope for now." Future-phase candidate; activation trigger likely surfaces at v1.3 close retrospective.
- **Operator-UAT-only Proxmox dogfood recipe** — rolls into Phase 21 (`docs/SDET-AUTHORING.md`); the architectural patterns from Phase 19's CONTEXT lift into doc prose.
- **Phase 19 D-02 substitution** — RESOLVED by the deletion (D-04). Marked resolved-by-deletion in STATE.md.
- **Upstream homelab-mcp inputSchema bug** — UNCHANGED status (still Open in deferred items table); upstream fix, not a framework concern.

---

*Phase: 20-preflight-conditional-skip*
*Discussion log: 2026-05-13*
