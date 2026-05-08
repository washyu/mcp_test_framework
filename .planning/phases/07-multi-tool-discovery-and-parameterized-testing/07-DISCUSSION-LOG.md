# Phase 07: Multi-tool discovery & parameterized testing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-07
**Phase:** 07-multi-tool-discovery-and-parameterized-testing
**Areas discussed:** Default tool, Verify step, Test IDs, Args-required, Runtime

---

## Direction (meta-question after initial multi-select returned "[No preference]")

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-decide and write CONTEXT.md | Claude makes recommended calls on all 4 gray areas with no further questions | |
| Walk through one area at a time | Each gray area asked as its own focused question with recommendation first | ✓ |
| Skip discuss — go straight to /gsd-plan-phase | Phase scope locked; researcher + planner decide implementation | |
| One gray area only — the default | Decide just whether unset target.tool_name means "all tools"; defer the rest | |

**User's choice:** Walk through one area at a time.
**Notes:** Re-invoked the command after the initial multi-select returned a non-committal answer; clarifying the discussion shape was the right reset.

---

## Default behavior when target.tool_name is unset

| Option | Description | Selected |
|--------|-------------|----------|
| Run all discovered tools (Recommended) | Unset/empty target.tool_name → parametrize over every advertised tool. Existing v1.0 users with TARGET_TOOL_NAME set keep single-tool behavior unchanged. | ✓ |
| Keep single-tool default, all-tools opt-in | Preserve "list_registered_servers" as default; require an explicit sentinel (e.g. target.all_tools=true) to opt into multi-tool. | |
| Drop the default entirely — require opt-in | No default value; misconfig fails fast at preflight. Breaks v1.0 zero-config experience. | |

**User's choice:** Run all discovered tools — but with the request "We should have an option to generate the opt config part and allow the user to delete tools from the list so I guess the first option with a verify step."
**Notes:** Triggered the Verify-step follow-up below.

---

## Verify-before-running affordance

| Option | Description | Selected |
|--------|-------------|----------|
| `list-tools` is the verify step (Recommended) | Keep v1.0's `mcp-test-framework list-tools` as the inventory view. Phase 07 ships the multi-tool run; Phase 08 ships the skip-list for curation. No new CLI code in Phase 07. | |
| Add `discover --emit-config` in Phase 07 | New flag/subcommand emits a starter `tools:` YAML block to stdout. Cost: commits Phase 07 to the TOOLCFG-01 schema before Phase 08 actually scopes it. | |
| Defer config-generator to Phase 08 | Phase 07 ships multi-tool run + `list-tools` as inventory view. Phase 08 ships per-tool config schema AND a `config-init` command that emits a starter tools: block matching that schema. Cleanest split. | ✓ |

**User's choice:** Defer config-generator to Phase 08.
**Notes:** Avoids dependency inversion (Phase 07 committing to Phase 08's schema); the existing v1.0 `list-tools` CLI already serves as the inventory view.

---

## Test ID convention

| Option | Description | Selected |
|--------|-------------|----------|
| Always `test_X[<tool_name>]` (Recommended) | Single-item parametrize list when target.tool_name is set; multi-item when unset. One code path; uniform IDs across pytest output and Phase 09 JUnit XML. | ✓ |
| Bare IDs when single-tool, bracketed when multi | Skip parametrize when target.tool_name is set — keep v1.0's bare `test_X` IDs. Two code paths; JUnit dashboards must handle both shapes. | |

**User's choice:** Always `test_X[<tool_name>]` (Recommended).
**Notes:** Accepts that v1.0's bare IDs change in single-tool mode — fine since v1.0 is shipped and v1.1 explicitly generalizes the surface.

---

## Tools with non-empty inputSchema.required

| Option | Description | Selected |
|--------|-------------|----------|
| Fail visibly (Recommended) | TEST-08/09/10 call_tool with `{}` as in v1.0; tools needing args produce isError=True and TEST-08 fails. The failure is the signal — Phase 08 (call_arguments) is the user-facing fix. | ✓ |
| Auto-skip output-conformance tests if required args | When inputSchema.required is non-empty, mark TEST-08/09/10 as pytest.skip with a deferred-to-Phase-08 reason. Schema and judge tests still run. | |
| Auto-skip + warn | Same as auto-skip, but additionally print a warning at session start. | |

**User's choice:** Fail visibly (Recommended).
**Notes:** MVP discipline — don't paper over real failures the next phase resolves. No skip-logic in Phase 07 that overlaps with Phase 08's TOOLCFG-07.

---

## Runtime envelope / blast radius

| Option | Description | Selected |
|--------|-------------|----------|
| Accept slow runtime (Recommended) | Document expected runtime in README/EXTENDING (Phase 10) and leave it. Users curate via Phase 08 skip-list. v1.2 brings parallelism. | ✓ |
| Print up-front estimate at collection | After tool discovery, print "Discovered N tools → ~M minutes estimated …" to terminal. Small lift; sets expectations on first run. | |
| Soft cap with explicit override | Abort at collection if discovered tools > threshold; require target.tool_name OR new target.allow_all_tools=true opt-in. Introduces a Phase-08-overlapping config field. | |

**User's choice:** Accept slow runtime (Recommended).
**Notes:** A cap is a de-facto skip mechanism — Phase 08 territory. Adding it in Phase 07 inverts phase ordering. Per PROJECT.md: per-worker isolation (v1.1) → parallelism (v1.2) is the planned sequence.

---

## Claude's Discretion

These are technical seam decisions captured in CONTEXT.md (CD-01..CD-06) but not raised as gray areas because they don't have user-facing implications:

- Discovery cache mechanism (module-level dict vs `pytest.StashKey` vs `pytest.Config.cache`)
- Whether `_preflight` and the discovery hook share `list_tools()` results
- Exact placement of the `pytest.mark.parametrize` invocation (module pytestmark vs per-test decorator vs `pytest_generate_tests` hook)
- New name for the renamed test file (`test_mcp_tool_contract.py` is suggested but not locked)
- Whether the discovery hook short-circuits when target.tool_name is set, or always spawns
- Plan-cut order (researcher / planner picks)

## Deferred Ideas

Captured in CONTEXT.md `<deferred>` for future-phase consumption:

- Starter-config generator (Phase 08, lands on TOOLCFG-01 schema)
- Up-front runtime estimate at collection time (post-v1.2 if user feedback warrants)
- Soft cap on tool count with `target.allow_all_tools=true` (Phase 08 overlap; not shipped)
- Auto-skip output-conformance tests when inputSchema.required is non-empty (Phase 08 territory)
- Process-parallel execution / xdist (v1.2; SEED-002)
- Warm-up / cold-start amortization (v1.2)
- Sharing `list_tools()` between `_preflight` and discovery hook (Claude's discretion / single optimization point)
