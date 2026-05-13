---
id: SEED-018
status: dormant
planted: 2026-05-12
planted_during: Phase 17 planning (post v1.3 milestone open, after second homelab-mcp run feedback)
trigger_when: Phase 18 (SDET test surface + typed errors) scoping, OR any conversation about closing the contract-suite "required property" noise floor, OR a v1.3 milestone audit notices that 23 of 55 failures in the v2 homelab run are missing-required-param errors
scope: Small
related_seeds: [SEED-014 (programmatic SDET authoring — parent), SEED-020 (tool effect taxonomy — sibling)]
---

# SEED-018: Per-tool example-args manifest for contract tests

## Why This Matters

In the 2026-05-12 second homelab-mcp run (580 contract cases against 58 tools),
**23 of 55 failures were "Input validation error: 'X' is a required property"
failures** — the framework correctly invoked each tool, but the parametrize-derived
payload had nothing to put in `node`, `device_id`, `hostname`, `service_name`,
`filter_type`, `query`, `backup_id`. These aren't framework bugs; they're missing
operator-supplied test fixtures.

This is noise that drowns out the real signal (the ~31 description-quality
failures the judge correctly identified). Every contract run against a real
server with non-trivial schemas will have this problem until the framework
gives the operator a way to declare example values per tool.

**This is orthogonal to Phase 18's SDET surface.** SDET-authored tests carry
their own params (the operator imports `CreateProxmoxVmParams` and fills them
in). The manifest is specifically for the contract suite — the cheap-to-run
"call every tool, assert it doesn't error" pass that should stay automated.

## When to Surface

**Trigger:** Phase 18 scoping (most natural fit), OR a v1.3 audit that asks
"why is the contract suite still 23/55 noisy after we shipped codegen", OR any
user file asking for a way to give the contract suite example data.

Surface during `/gsd-new-milestone` when the milestone touches: contract suite
ergonomics, false-positive reduction, operator fixture data, or "give the
framework a way to know what arguments each tool wants."

## Scope Estimate

**Small** — ~1 day. Three pieces:

### 1. Config schema extension

Add `tools.<name>.example_args` to `config.yaml`:

```yaml
tools:
  create_proxmox_vm:
    example_args:
      node: "pve1"
      vmid: 999
      name: "framework-test-vm"
      memory: 512
  decommission_device:
    example_args:
      device_id: "test-device-do-not-use"
  list_registered_servers:
    # no required params, no entry needed
```

Pydantic-validated against the tool's generated `Params` class once Phase 17
ships (codegen surface). Until then, validated against `inputSchema` via
existing `Draft202012Validator`.

### 2. Contract-suite fixture wiring

Conftest fixture `example_args(tool_name) -> dict | None`:
- Returns the configured args if present.
- Returns `None` if no entry AND `inputSchema.required` is empty (tool needs no args).
- Returns `None` AND emits a skip-with-reason if `inputSchema.required` is
  non-empty AND no entry is configured. The skip reason names the missing
  required keys so the operator sees exactly what to add.

### 3. Skip-with-reason rendering

`tools that need fixtures` becomes a domain-UI section, distinct from
`failures` and `passing`. Reads:
```
needs example_args:
  create_proxmox_vm        (required: node, vmid, name)
  decommission_device      (required: device_id)
  …
```
This turns the 23 false-failures from this run into 23 actionable
"add these to your config.yaml" items.

## Open Design Questions

- Should example_args be allowed to reference shell environment vars / 
  `$NODE` interpolation? (Yes for v1, probably — matches the existing
  config.example.yaml convention.)
- What about tools where "running the example" *is* destructive? Answer:
  pair with SEED-019 (_preview convention) and SEED-020 (effect taxonomy) —
  if a tool is tagged destructive AND has a `_preview` sibling, the contract
  suite invokes the preview using `example_args`. SDET tests retain the
  ability to run the real thing explicitly.
- Should the manifest live in config.yaml or a sibling
  `example_args.yaml`? Sibling is cleaner for tools-with-70-entries
  (homelab-mcp scale memory note); config.yaml is simpler for small SUTs.
  Recommended: support both, with `tools.*.example_args` taking precedence
  over `example_args.yaml` for fine overrides.

## Breadcrumbs

Related code (verified present 2026-05-12):
- `src/mcp_test_framework/config.py` / `models.py` — where ToolConfig lives;
  add `example_args: dict[str, Any] | None = None`.
- `tests/contract/` (current generic contract suite location) — where the
  `example_args` fixture would wire in.
- Phase 17 generated `Params` classes — manifest can validate against
  `Params(**example_args)` once codegen ships.

Related decisions:
- v1.2 SAFE-* config-safety lineage — manifest follows the same "fail loud
  if config is missing something needed" posture; never silently default
  missing required args to `None`.
- Phase 09 OUTPUT-01 contract — manifest does not change JUnit XML shape;
  skipped tests render as `<skipped>` with the reason, matching existing
  contract.

Related seeds:
- **SEED-014** (programmatic SDET authoring) — parent. SEED-018 is the
  contract-suite-shaped narrower piece SEED-014 doesn't explicitly cover.
- **SEED-019** (_preview-as-contract-target) — sibling. Example args + 
  preview redirect together close the destructive-tool gap.
- **SEED-020** (tool effect taxonomy) — sibling. Taxonomy tells the
  framework *what* a tool is; example_args tells it *what to send*.

## Notes

Captured during Phase 17 planning on 2026-05-12 after the user ran the
framework against homelab-mcp's full 58-tool surface and observed the
23-false-failure pattern. The user explicitly said they should have
surfaced this before opening v1.3 — strong signal this belongs *in* v1.3,
ideally as a small phase between 17 and 18, or folded into Phase 18's
"SDET test surface" prerequisites.

If v1.3 closes without this, Phase 18's SDET tests will work, but the
contract suite that's supposed to give the operator "running coverage
across all 58 tools" will keep producing noisy output until v1.4.
