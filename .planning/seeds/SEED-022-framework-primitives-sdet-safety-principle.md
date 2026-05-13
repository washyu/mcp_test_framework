---
id: SEED-022
status: locked-principle
planted: 2026-05-12
planted_during: Phase 17 planning (post v1.3 milestone open, mid-conversation after second homelab-mcp run feedback)
trigger_when: Any /gsd-new-milestone, /gsd-explore, or /gsd-discuss-phase invocation where the question "should the framework decide / detect / gate something about tool safety" surfaces. This seed is a load-bearing architectural principle and should be cited by name in CONTEXT.md when any phase makes a decision that depends on it.
scope: Principle (not a feature) — durable architectural decision
related_seeds: [SEED-018 (operates within this principle), SEED-019 (superseded by this), SEED-020 (superseded by this), SEED-021 (documents this), SEED-014 (parent SDET vision), SEED-004 (stateful testing — also operates within this)]
---

# SEED-022: Architectural principle — framework provides primitives; SDET owns safety

## The Principle

**The framework does no safety reasoning about MCP tools. The SDET decides
what is safe to call, with what arguments, and what to assert. The
framework provides the primitives (transport, codegen, judges, scenario
runner, reporters) and gets out of the way.**

Locked 2026-05-12 by the user, verbatim:

> "we can drop the is this a safe tool assumption and just let the
> sdet/QAE decide that when they are creating tests with this framework."

Following the user's earlier observation that homelab-mcp-shaped
heuristics (the `_preview` convention) were leaking into generic
framework design:

> "i am wondering if we are starting to model this tool around testing
> the homelab_mcp rather then keeping it generic. i am not sure if mcp
> generally have a preview feature for there tools."

## What This Principle Rules Out

The framework does NOT:

- Classify tools as `read` / `mutating` / `destructive` based on names or
  schemas. (SEED-020 retired for this reason.)
- Detect server-specific dry-run conventions and redirect destructive
  calls through them. (SEED-019 retired for this reason.)
- Maintain a "known dangerous" list of tool name patterns.
- Auto-skip tools the framework guesses might be destructive.
- Refuse to invoke a tool the SDET has opted in.
- Warn at runtime that the SDET "may be about to do something
  destructive" based on framework-side inference.

## What This Principle Rules In

The framework DOES:

- Provide a tool list, schemas, and (via Phase 17) typed `Params` /
  `Response` classes.
- Expose a stable `tool("name").call(params)` seam (Phase 18) the SDET
  drives with whatever args they decide.
- Run description-quality judges that never touch the SUT — these are
  safe for every tool by construction, including ones the SDET would
  never wire-call.
- Run output-conformance tests only for tools the SDET has explicitly
  opted in AND provided `example_args` for (SEED-018). The operator's
  act of providing args is the safety judgment.
- Document clearly which test classes wire-call vs which are
  pure-analysis (SEED-021) so the SDET can make the opt-in decision
  with full information.
- Support stateful scenarios with explicit setup/teardown (Phase 19,
  SEED-004) where the SDET owns the safety semantics inside the
  scenario.

## What This Principle Implies for v1.3 and Beyond

### Existing v1.3 phases (no replan needed)

- **Phase 17 (codegen):** Already principle-compatible. Generating
  typed `Params` classes makes it easier for SDETs to drive tools
  themselves; codegen makes no claims about safety.
- **Phase 18 (SDET surface + typed errors):** Already principle-
  compatible. The `tool("name").call(params)` seam is exactly the
  "framework provides primitives" half of the principle.
- **Phase 19 (stateful primitives):** Already principle-compatible.
  Setup/teardown semantics are SDET-authored — framework provides the
  hook, SDET decides what goes in it.
- **Phase 20 (preflight + conditional skip):** Already principle-
  compatible. `requires_homelab(proxmox=True, ...)` is the SDET
  declaring environmental requirements, not the framework guessing.
- **Phase 21 (SDET authoring docs):** This is where SEED-021 lands —
  documenting the principle so SDETs can act on it.

### Existing v1.x contract suite

The legacy "call every tool, assert isError=False" contract behavior
exists in v1.2 code. It predates this principle. Under the new
principle, that auto-call behavior should be either:
1. Removed entirely (cleanest), OR
2. Reduced to running only on tools opted in with `example_args` via
   SEED-018 (preserves the ergonomic, drops the assumption).

Treat the legacy auto-call as **vestigial** — it doesn't get extended,
it doesn't get new safety features bolted on. Its eventual fate (drop
or narrow) is a v1.4 / v2.0 decision, not a v1.3 one. v1.3 ships with
it intact but the architectural direction is clear.

### Why this principle is more important than the seeds it replaces

A taxonomy enum, a preview-redirect feature, an effect-aware contract
suite — these are all defensible local optimizations against a single
example server. None of them survive contact with **the next server an
SDET wants to test**. A user reporting on the framework against
filesystem-mcp wouldn't have `_preview` siblings; against a database
server they wouldn't have homelab-shaped verbs. Each new server
would require new framework-side heuristics.

The principle scales to any MCP server: the framework asks the SDET,
the SDET answers, the framework runs what was asked. Adding a new
SUT requires zero framework changes.

## When This Principle Should Be Cited

In CONTEXT.md (or DISCUSSION-LOG.md) of any future phase where a
design question contains "should the framework decide..." about tool
calls. Specific phrases to watch for:

- "should the framework auto-detect..."
- "should the framework default to skipping..."
- "should the framework redirect..."
- "should the framework warn that this might be unsafe..."
- "should the framework infer effect / kind / class from..."

All of these have the same answer under SEED-022: **no — the SDET
decides; the framework provides the primitive they need to express
their decision.**

## Breadcrumbs

Related code (verified present 2026-05-12):
- v1.2 opt-in `tools:` allowlist design (config.example.yaml,
  models.py::ToolConfig) — the principle is already implemented in
  the v1.2 architecture; SEED-022 makes it explicit and durable.
- v1.3 Phase 18 SDET surface design — explicitly hands the call
  decision to the SDET via the `tool("name").call(params)` seam.

Related decisions:
- **SEED-021** documents this principle for SDETs in the README.
- **SEED-018** operates within this principle (example_args as SDET-
  authored opt-in, not framework-side fixture).
- **SEED-019, SEED-020** were retired by this principle on the day they
  were planted — useful exhibits of the kind of work this principle
  prevents.

## Notes

This is a `locked-principle` seed rather than a `dormant` feature seed.
It does not get "implemented" — it gets *cited*. When a future phase's
design question bumps into it, the answer is already written here.

Memory note for future-Claude (and future-self): if you find yourself
about to propose a framework feature that classifies tools by safety,
detects server-specific safety conventions, or makes any "is this safe
to call" decision on behalf of the operator — stop and re-read this
seed. The principle was load-bearing enough that it retired two seeds
on the day they were planted; it'll retire any successors with the
same shape.
