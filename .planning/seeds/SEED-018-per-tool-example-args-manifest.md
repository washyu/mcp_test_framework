---
id: SEED-018
status: dormant
planted: 2026-05-12
rewritten: 2026-05-12
planted_during: Phase 17 planning (post v1.3 milestone open)
trigger_when: Phase 18 (SDET test surface + typed errors) scoping, OR any conversation about giving SDETs an ergonomic shortcut for the common "call this tool with these args, assert no error" test pattern
scope: Small
related_seeds: [SEED-014 (programmatic SDET authoring — parent), SEED-022 (architectural principle — sets the safety frame)]
---

# SEED-018: Per-tool `example_args` as SDET output-conformance shortcut

## Why This Matters

Under the architectural principle locked 2026-05-12 (see SEED-022), the
framework does no safety reasoning about tool calls — the SDET decides
which tools to opt into which test classes and what arguments to invoke
them with.

That makes the per-tool `example_args` manifest **not** a framework-side
fixture (the earlier framing) but an **ergonomic shortcut for SDETs**.

The common case: an SDET opts a tool into output-conformance testing
("call this tool, assert `isError == False`, assert response shape
matches `outputSchema`"). Today the SDET has to hand-write a one-line
test file for every such tool:

```python
async def test_create_proxmox_vm_conformance(mcp_session):
    result = await tool("create_proxmox_vm").call(
        CreateProxmoxVmParams(node="pve1", vmid=999, name="test-vm")
    )
    assert not result.is_error
```

With `example_args` declared in config, the framework can synthesize that
test for any tool the SDET has opted in. Same test, no boilerplate:

```yaml
tools:
  create_proxmox_vm:
    enabled: true
    judges: [output_conformance]
    example_args:
      node: "pve1"
      vmid: 999
      name: "test-vm"
```

The operator's act of providing `example_args` *is* the safety judgment —
they're saying "yes, calling this tool with these args is fine in my
environment, run it." No framework-side `effect: destructive` reasoning;
the operator's decision is sufficient.

## When to Surface

**Trigger:** Phase 18 (SDET test surface) scoping, OR any conversation
about SDET authoring boilerplate, OR "I want to skip writing the same
two-line conformance test for 30 tools."

Surface during `/gsd-new-milestone` when the milestone touches: SDET
authoring ergonomics, test boilerplate reduction, or config-driven
output-conformance.

## Scope Estimate

**Small** — ~1 day. Three pieces:

### 1. Config schema extension

Add `tools.<name>.example_args` to `config.yaml` (or sibling
`example_args.yaml` for large tool surfaces — see Open Questions):

```yaml
tools:
  create_proxmox_vm:
    enabled: true
    judges: [output_conformance]
    example_args:
      node: "pve1"
      vmid: 999
      name: "test-vm"
  list_registered_servers:
    enabled: true
    judges: [output_conformance]
    # no required params, no example_args needed
  delete_proxmox_vm:
    enabled: false   # SDET decided this needs a real test, not the shortcut
```

Once Phase 17 ships, validate `example_args` against the tool's generated
`Params` class. Until then, validate against `inputSchema` via existing
`Draft202012Validator`.

### 2. Output-conformance test generation

When a tool is opted into the `output_conformance` judge AND has
`example_args` declared, the framework synthesizes the conformance test at
collection time. No SDET boilerplate required.

If a tool is opted in but has no `example_args` AND `inputSchema.required`
is non-empty: skip-with-reason naming the missing keys. The skip reason
tells the SDET exactly what to add:
```
skipped: create_proxmox_vm — output_conformance requires example_args (missing: node, vmid)
```

If `inputSchema.required` is empty (no required params), call with `{}`.

### 3. Renders cleanly in the domain UI

Conformance-from-`example_args` results render the same as hand-written
SDET tests — no separate section, no "fixture vs test" distinction. From
the operator's view, output-conformance is one test class; whether it
came from a config entry or a hand-written file is implementation detail.

## What This Seed Is NOT

- **Not** a framework-side safety mechanism. The framework does no
  classification of tools as safe/unsafe. The SDET decides what to opt
  in via `enabled: true` + `judges: [...]`.
- **Not** an auto-running contract suite. Without explicit
  `output_conformance` opt-in per tool, no wire call happens.
- **Not** a replacement for hand-written SDET tests. Complex flows,
  stateful scenarios, custom assertions, and parameter-space sweeps all
  still belong in SDET-authored test files. `example_args` is for the
  common "call once, assert shape" case only.

## Open Design Questions

- Should `example_args` allow env-var interpolation (e.g.,
  `node: "${PROXMOX_TEST_NODE}"`)? Yes for v1 — matches the existing
  `config.example.yaml` interpolation convention.
- Single-file `config.yaml` entry vs sibling `example_args.yaml`?
  Sibling is cleaner at 70-tool scale (homelab-mcp memory note);
  config.yaml is simpler for small SUTs. Recommended: support both,
  with `tools.*.example_args` taking precedence.
- Multiple example-arg sets per tool (e.g., minimal vs full vs edge-case)?
  Probably yes — `example_args` becomes a list, each entry generates a
  separate conformance case. Defer to a separate seed if it gets too
  large.

## Breadcrumbs

Related code (verified present 2026-05-12):
- `src/mcp_test_framework/models.py::ToolConfig` — add
  `example_args: dict[str, Any] | None = None`.
- Phase 17 generated `Params` classes (in progress) — `example_args` can
  validate via `Params(**example_args)` once codegen ships.
- Existing output-conformance test path (wherever `assert not isError`
  lives in the current contract suite) — replace its blind-call logic
  with the `example_args`-driven flow.

Related decisions:
- v1.2 opt-in design: `tools:` is an allowlist (unlisted tools auto-skip).
  `example_args` extends that same opt-in shape rather than introducing
  a new opt-in surface.
- Architectural principle (SEED-022): framework provides primitives; SDET
  owns safety. `example_args` is the operator's act of opting in to a
  wire call — no framework-side reasoning required.

Related seeds:
- **SEED-014** (programmatic SDET authoring) — parent. SEED-018 is the
  ergonomic-shortcut subset that lets opt-in conformance tests be
  config-driven instead of hand-written.
- **SEED-022** (architectural principle) — sets the safety frame this
  seed operates within.

## Notes

Originally planted 2026-05-12 as a "framework fixture to close the 23
required-property false-failures in the v2 homelab-mcp run." The user
challenged the framing later the same day with the architectural call
that the framework should make no safety assumptions about tools. This
seed was rewritten to fit the new principle: it is no longer a contract-
suite fixture but an SDET-authoring shortcut. The 23 v2-run failures
remain real but are now an SDET-side concern, not a framework concern —
they'll close when an SDET opts those tools in with `example_args`.
