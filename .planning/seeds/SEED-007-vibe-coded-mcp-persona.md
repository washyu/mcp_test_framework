---
id: SEED-007
status: dormant
planted: 2026-05-08
planted_during: v1.1 milestone complete (between-milestones)
trigger_when: v1.2 milestone framing — should shape positioning before any phase planning
scope: Small
---

# SEED-007: Vibe-coded MCP user persona reframe

## Why This Matters

The "black-box" rule in v1.0/v1.1 was originally about **test discipline** (do not import or vendor the SUT). User flagged on 2026-05-08 that the rule has a second, unstated meaning that should become explicit in v1.2: the **operator** may also not know the SUT internals — e.g. when testing a vibe-coded MCP server they did not write themselves.

This reframes several v1.1 artifacts:
- `config-init`'s minimal scaffold is wrong if the operator can't read the source to know what `call_arguments` to set per tool
- The judge rubrics (clarity / disambiguation / parameters_self_explanatory) are *exactly* the right product for this persona — they evaluate whether an LLM agent could use the tool blindly, which is the same question the operator is asking
- "Black box" stops being a constraint and becomes a feature: "test any MCP server, even one you didn't build"

## When to Surface

**Trigger:** v1.2 milestone framing — should shape positioning before any phase planning

This seed should be presented when the new milestone scope mentions any of:
- Vibe-coded / generic / unknown MCP servers
- User experience / persona / positioning
- README / docs / examples (because docs need to reflect the persona)
- Black-box / black box / test discipline

## Scope Estimate

**Small** — A few hours of positioning work plus knock-on effects in copy across other phases. This is more "framing decision" than "implementation phase." It influences naming, README, scaffold defaults, and the shape of error messages, but doesn't ship its own artifacts.

## What Falls Out of It

- Scaffold should include each tool's `inputSchema` (already discoverable via `Tool` record) so the operator can read parameter shapes without opening source — but at scale (homelab-mcp ≈ 70 tools) this needs verbosity controls (see SEED-008)
- Consider a `call_arguments_template` generator that builds a valid example from the schema (deeper move, but matches the persona)
- README / EXTENDING positioning may want a "testing an MCP you didn't write" section
- SEED-001 (full agent tool-use loop) is most valuable through this lens — an agent figuring out the tool blindly IS the test

## Sequencing Within v1.2

Surface this **first** during milestone framing — before the bigger semantic redesigns (SEED-006) or the reporter work (SEED-008) — so the persona shapes copy + naming + error-message tone across all of them. Cheap to land but expensive to retrofit.

## Breadcrumbs

- `.planning/PROJECT.md` — original "black box" framing
- `docs/mcp_test_framework_mvp_spec.md` — authoritative design spec
- `README.md` — currently uses homelab-mcp / list_keyring_credentials as the worked example
- `docs/EXTENDING.md` — "Add a new MCP tool target" walkthrough; closest current proxy for the persona

## Related Memories

- project_vibe_coded_persona.md
- project_genericize_example_config.md (this persona is what makes the homelab-saturated example config a positioning problem)
