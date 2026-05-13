---
id: SEED-020
status: superseded
planted: 2026-05-12
superseded: 2026-05-12
superseded_by: Architectural principle — "framework provides primitives; SDET owns safety calls" (see SEED-022)
planted_during: Phase 17 planning (post v1.3 milestone open, after second homelab-mcp run feedback)
trigger_when: N/A — superseded
scope: Medium
related_seeds: [SEED-018 (example-args manifest), SEED-019 (preview-as-contract-target — also superseded), SEED-004 (stateful testing — depends on this), SEED-014 (programmatic SDET — depends on this)]
---

# SEED-020: First-class tool effect taxonomy  *[SUPERSEDED 2026-05-12]*

## Why This Was Superseded

Planted earlier the same day and retired within hours. The user made the
architectural call that obsoletes this seed:

> "we can drop the is this a safe tool assumption and just let the
> sdet/QAE decide that when they are creating tests with this framework."

The taxonomy's value was gating framework behavior (auto-skip destructive
in contract suite, redirect to preview, etc.). Under the new principle the
framework does no gating — the SDET reads the tool's description, decides
what's safe to test how, and writes assertions accordingly.

Without framework-side gating, the taxonomy becomes informational metadata
the SDET could optionally consume — and at that point it's just docstrings
on test files, not a framework feature. Not seed-worthy.

A weaker version of this idea survives in SEED-021 (judge documentation):
the README should explain *which test classes are safe-by-construction*
(description judges = no wire call) vs *operator-judged* (output
conformance = wire call). That's the taxonomy that actually matters under
the new principle, and it lives in docs, not code.

Preserved here (rather than deleted) so the rationale survives for future
readers asking "did we consider an effect enum?" Answer: yes, then chose
a cleaner principle that doesn't need one.

---

# Original content (preserved for history):

# SEED-020: First-class tool effect taxonomy (`read` / `preview` / `mutating` / `destructive` / `stateful`)

## Why This Matters

The framework currently treats every MCP tool identically — `list_vms` (pure
read, no side effects, safe to call 1000 times), `get_proxmox_node_status`
(pure read but needs a node connection), `create_proxmox_vm` (creates state
that must be reaped), and `delete_proxmox_vm` (destroys real infrastructure)
all flow through the same parametrize loop and the same pass/fail rubric.

That's the root cause of the "I have no test environment" pain captured in
the user's 2026-05-12 conversation:

> "some of the homelab mcp calls are destructive and i don't really have a
> decent test enviroment setup."

You can't write a one-size-fits-all contract test against a tool surface
when half the tools are destructive and the framework can't tell which.
**Effect taxonomy is the missing primitive that lets every other safety
feature work.**

This is a foundation seed. SEED-018 (example-args), SEED-019 (preview
redirect), SEED-004 (stateful setup/teardown), and SEED-014 (SDET
authoring) all become much sharper when the framework knows whether a
tool is `read` or `destructive`.

## When to Surface

**Trigger:** Phase 18 (SDET surface) scoping if siblings 18 + 19 are also
being addressed (the three are a coherent set); OR Phase 19 (stateful
primitives) where effect-awareness is a hard prerequisite; OR a v2.0
reframing.

Surface during `/gsd-new-milestone` when the milestone touches: SDET
safety, stateful semantics, sandbox/preview policy, "what kind of tool is
this," or "first-class tool metadata."

## Scope Estimate

**Medium** — 2–3 days. The taxonomy itself is small (an enum + a config
schema); the value is in the framework features that consume it.

### 1. The taxonomy

```python
class ToolEffect(str, Enum):
    READ = "read"               # no side effects; safe to call repeatedly
    PREVIEW = "preview"         # explicit dry-run; safe by design
    MUTATING = "mutating"       # creates/modifies state but reversible
    DESTRUCTIVE = "destructive" # irreversible without a backup
    STATEFUL = "stateful"       # requires prior state to make sense
```

A tool can have ONE primary effect plus modifiers (e.g., `MUTATING +
STATEFUL`: needs prior state and modifies it).

### 2. Three sources of truth (precedence top-to-bottom)

1. **Operator config** (`tools.<name>.effect: destructive`). Operator's
   word is final.
2. **Server-declared annotation.** If the MCP spec ever ships an
   `annotations.effect` or `annotations.readOnly` field on `Tool`,
   honor it. Worth pushing this conversation upstream.
3. **Heuristic inference.** Last resort. Tool name starts with `get_` /
   `list_` / `search_` → READ. Ends with `_preview` / `_dry_run` →
   PREVIEW. Starts with `delete_` / `destroy_` / `remove_` / `purge_` /
   `decommission_` → DESTRUCTIVE. Everything else → MUTATING with a
   warning.

The heuristic is a starting line, not the answer. The framework should
emit a "I guessed these effects from tool names — review and pin in
config" report on first run against a new server.

### 3. Framework features that consume the taxonomy

- **Contract suite default policy** (per effect):
  - READ: call freely, full rubric.
  - PREVIEW: call freely, full rubric.
  - MUTATING: call only if `example_args` configured AND
    `contract.allow_mutating: true`; else skip-with-reason.
  - DESTRUCTIVE: never call directly in contract suite. If a `_preview`
    sibling exists (SEED-019), redirect; else skip-with-reason.
  - STATEFUL: skip-in-contract-suite by default (these are SDET-test
    territory).
- **Domain UI grouping.** Render contract results grouped by effect so
  the operator sees "5 READ pass, 3 READ fail, 12 DESTRUCTIVE skipped
  (preview-redirected), 8 STATEFUL skipped (SDET-only)." This makes
  coverage gaps visible.
- **SDET test policy enforcement** (Phase 18+ surface). A scenario
  that calls a DESTRUCTIVE tool must declare it explicitly:
  `with allow_destructive("real teardown of test-vm-01"):` — gives
  the framework a chance to warn loudly and lets future audit tools
  find every destructive call site.

## Open Design Questions

- Are `MUTATING` and `STATEFUL` orthogonal flags or part of a single
  enum? Recommended: orthogonal. A tool can be MUTATING (creates state)
  without being STATEFUL (requiring prior state) — `register_server`
  is MUTATING+not-STATEFUL; `update_device_config` is MUTATING+STATEFUL.
- Should the heuristic-inferred report block on first-run-with-new-server
  or just warn? Warn — blocking is hostile to the "just point me at a
  server" use case. The report is part of the domain UI; operator sees
  it and acts when they're ready.
- Should the framework ship a curated effect manifest for known servers
  (e.g., `effects/homelab-mcp.yaml` shipped in the repo)? Probably yes
  for the dogfood server; that doubles as documentation of what
  effect-classification looks like in practice.

## Breadcrumbs

Related code (verified present 2026-05-12):
- `src/mcp_test_framework/models.py::ToolConfig` — add `effect`
  field here.
- `src/mcp_test_framework/cli.py::_discover_tools_for_run` — where the
  inference runs after tool list is fetched.
- `tests/contract/` — where the effect-driven skip / call policy
  enforces.

Server-side observations from the 2026-05-12 run that motivate the
taxonomy:

| Tool name pattern | Inferred effect | Risk if mis-tested |
|-------------------|-----------------|---------------------|
| `list_*`, `get_*`, `search_*`, `scan_*` | READ | None — these are the 3 currently passing |
| `*_preview`, `*_dry_run` | PREVIEW | None |
| `register_*`, `update_*`, `install_*`, `deploy_*`, `create_*` | MUTATING | Creates undeclared state |
| `delete_*`, `destroy_*`, `remove_*`, `purge_*`, `decommission_*`, `rollback_*` | DESTRUCTIVE | Real infra loss |
| `manage_*`, `control_*`, `run_*` | MUTATING with side effects unclear | Operator must classify |

Related decisions:
- v1.2 black-box rule — the framework cannot read homelab-mcp source to
  *infer* effect; it must rely on (operator config) → (server annotations
  if MCP ever adds them) → (name heuristic). All three respect black-box.
- Phase 13 SAFE-* lineage — taxonomy is the explicit version of "what
  defaults are dangerous"; SAFE asked the question per-config-key, taxonomy
  asks it per-tool.

Related seeds:
- **SEED-018** (example-args manifest) — consumes taxonomy: only
  MUTATING/DESTRUCTIVE tools need example_args to be safely callable.
- **SEED-019** (preview-as-contract-target) — consumes taxonomy: 
  preview redirect is the policy DESTRUCTIVE tools opt into.
- **SEED-004** (stateful testing) — consumes taxonomy: STATEFUL is
  the effect that triggers setup/teardown infrastructure.
- **SEED-014** (programmatic SDET) — consumes taxonomy: SDET tests
  for DESTRUCTIVE tools require explicit opt-in.

Sibling group: 018 + 019 + 020 ship together cleanly. 020 is the
foundation; 018 and 019 are the immediate consumers. SEED-004 and
SEED-014 are the larger downstream consumers that benefit when 020 lands.

## Notes

Captured 2026-05-12 during Phase 17 planning. The user observed the
~14 `_preview` siblings in homelab-mcp and asked how the framework
should think about them. Taxonomy is the answer to "how the framework
should think about *any* tool's safety profile" — `_preview` is just
one effect class among five.

If only one of {018, 019, 020} ships in v1.3, this one (020) has the
highest leverage because everything else depends on it. If all three
ship, they form a coherent "the framework knows what each tool is and
treats it accordingly" upgrade that closes most of the
no-test-environment pain without any sandbox work.
