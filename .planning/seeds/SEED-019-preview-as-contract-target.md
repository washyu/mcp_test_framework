---
id: SEED-019
status: superseded
planted: 2026-05-12
superseded: 2026-05-12
superseded_by: Architectural principle — "framework provides primitives; SDET owns safety calls" (see SEED-022)
planted_during: Phase 17 planning (post v1.3 milestone open, after second homelab-mcp run feedback)
trigger_when: N/A — superseded
scope: Small
related_seeds: [SEED-018 (example-args manifest — sibling), SEED-020 (effect taxonomy — sibling), SEED-004 (stateful testing — adjacent)]
---

# SEED-019: `_preview`-as-contract-target convention  *[SUPERSEDED 2026-05-12]*

## Why This Was Superseded

Planted earlier the same day and retired within hours after the user
challenged the homelab-mcp coupling: "i am wondering if we are starting to
model this tool around testing the homelab_mcp rather then keeping it
generic. i am not sure if mcp generally have a preview feature for there
tools."

The `_preview` convention is a homelab-mcp idiom, not an MCP protocol
feature. Designing a framework feature around it would over-fit the
framework to one server's idiosyncrasy.

The user then made the deeper architectural call that obsoletes this
seed entirely:

> "we can drop the is this a safe tool assumption and just let the
> sdet/QAE decide that when they are creating tests with this framework."

Under that principle, the framework does no safety reasoning at all —
SDETs decide what to call, with what args, and write their own assertions.
Preview-redirect was framework-side safety reasoning, so it goes.

Preserved here (rather than deleted) so the rationale survives in the
seed corpus for future readers asking "did we consider preview redirect?"
Answer: yes, briefly, then chose a cleaner architectural line.

---

# Original content (preserved for history):

# SEED-019: `_preview`-as-contract-target convention

## Why This Matters

homelab-mcp ships ~14 tools paired with `_preview` siblings:
`decommission_device` / `decommission_device_preview`, `purge_devices` /
`purge_devices_preview`, `remove_vm` / `remove_vm_preview`,
`destroy_terraform_service` / `destroy_terraform_service_preview`, etc.

This is effectively a self-declared dry-run protocol baked into the server's
tool surface — the operator can ask "what would happen if I called the
destructive version" without committing. The framework currently treats both
sides identically: `delete_proxmox_vm` and `delete_proxmox_vm_preview` are
both contract-tested with the same parametrize loop, and either both pass
(if both have example_args) or both fail (if neither does).

**This wastes the gift the server is giving us.** A 50-line framework feature
turns the convention into a safe-by-default policy:

> If a tool `foo` has a sibling tool `foo_preview` (or `foo_dry_run`,
> configurable suffix list), the contract suite's call test for `foo`
> invokes `foo_preview` instead of `foo`. The real `foo` can still be
> called from SDET-authored tests inside an explicitly opted-in scenario,
> but the cheap, every-commit contract pass never touches it.

That single rule unlocks contract testing for the entire destructive
surface without any sandbox infrastructure.

## When to Surface

**Trigger:** Phase 18 (SDET surface), Phase 19 (stateful primitives, where
"safe destructive call" semantics get codified), OR any user conversation
mentioning "I don't have a test environment" or "I can't fuzz the destructive
tools."

Surface during `/gsd-new-milestone` when the milestone touches: SDET safety,
sandbox alternatives, dry-run support, destructive-tool coverage, or "test
environment problem."

## Scope Estimate

**Small** — under a day. Three pieces:

### 1. Suffix detection in tool discovery

Augment `_discover_tools_for_run` (or its callee) with:

```python
PREVIEW_SUFFIXES = ("_preview", "_dry_run")  # configurable

def find_preview(tool_name: str, all_tools: set[str]) -> str | None:
    for suffix in PREVIEW_SUFFIXES:
        candidate = f"{tool_name}{suffix}"
        if candidate in all_tools:
            return candidate
    return None
```

### 2. Contract-suite redirect

In the contract test that does the wire call, replace:
```python
result = await mcp.call_tool(tool_name, args)
```
with:
```python
target = config.preview_redirect.get(tool_name) or find_preview(tool_name, all_tools) or tool_name
if target != tool_name:
    log.info(f"redirecting contract call: {tool_name} -> {target} (preview convention)")
result = await mcp.call_tool(target, args)
```

### 3. Operator opt-out + opt-in surface

Config knob:
```yaml
contract:
  preview_redirect:
    enabled: true        # default true; set false to test foo for real
    suffixes: [_preview, _dry_run]
    overrides:
      delete_proxmox_vm: delete_proxmox_vm_dry_run  # explicit pin
      backup_database:   null  # explicit "no, run the real thing in contract"
```

Three states per tool:
- Default (auto-detect): use `find_preview` result if any.
- Explicit override: use the named alias.
- Explicit `null`: never redirect (operator wants the real thing).

## Open Design Questions

- Does the redirected contract case render as `delete_proxmox_vm` or
  `delete_proxmox_vm_preview` in the domain UI? Recommended: render as
  `delete_proxmox_vm` with a `(preview)` annotation. The operator's mental
  model is "I tested delete_proxmox_vm safely," not "I tested the preview
  tool."
- What about the description-quality judges? They run on the *original*
  tool's description (the operator wants to know if `delete_proxmox_vm`
  has a good description, not whether `delete_proxmox_vm_preview` does).
  So judges run against the original; the wire call uses the preview.
  Two different tool identities for the two test classes.
- Should the convention also cover `_simulate`, `_test`, `_dry`, etc.?
  Suffixes are configurable; ship with `_preview` + `_dry_run` and let
  the homelab-mcp pattern speak. Other servers can add their own.

## Breadcrumbs

Related code (verified present 2026-05-12):
- `src/mcp_test_framework/cli.py::_discover_tools_for_run` — where the
  tool list is materialized; suffix detection wires in here.
- `tests/contract/` — where the per-tool call test lives (the redirect
  applies inside the call test, after schema validation but before the
  wire send).
- The 14 `_preview` tools observed in the 2026-05-12 run:
  `decommission_device_preview`, `delete_proxmox_vm_preview`,
  `destroy_terraform_service_preview`, `purge_devices_preview`,
  `remove_device_preview`, `remove_vm_preview`,
  `rollback_infrastructure_changes_preview`,
  `update_device_fingerprint_preview`. Server pattern is stable.

Related decisions:
- Phase 13 SAFE-03 lineage — "fail loud on dangerous defaults"; the
  inverse here is "succeed safe on dangerous defaults." Same
  philosophy applied to the test surface.
- v1.2 black-box rule — the framework can't read homelab-mcp source to
  *learn* what's destructive. The `_preview` convention is the server's
  way of telling us at the protocol level. Honoring it preserves the
  black-box rule.

Related seeds:
- **SEED-018** (example-args manifest) — sibling. Together they let the
  contract suite cover destructive tools using example args sent to the
  preview sibling.
- **SEED-020** (tool effect taxonomy) — sibling. Taxonomy could
  promote the implicit `_preview` convention into an explicit
  `effect: destructive, dry_run_alias: foo_preview` declaration.
- **SEED-004** (stateful testing) — adjacent. SEED-019 is the
  zero-state, zero-sandbox alternative; SEED-004 is the full
  setup/teardown answer for cases the preview convention can't cover.

## Notes

Captured 2026-05-12 after observing the homelab-mcp `_preview` pattern
in the v2 run. The user described their environment situation:

> "i was going to start work on the a stateful SDET type of tests
> capability so we can do some of the paramer tests a little mroe
> safily since some of the homelab mcp calls are destructive and i
> don't really have a decent test enviroment setup."

SEED-019 is the cheaper of two answers to that pain. Stateful sandboxing
(SEED-004) is the expensive answer. Both are valid; SEED-019 should land
first because it's a 50-line framework feature that closes a large
fraction of the destructive surface without any infrastructure work.
