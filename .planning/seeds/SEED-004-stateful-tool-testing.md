---
id: SEED-004
status: dormant
planted: 2026-05-06
revised: 2026-05-07
planted_during: v1.0 / post-shipping conversation about v1.1 scoping
revised_during: v1.0 / `/gsd-explore` Long-term Vision pass
trigger_when: REVISED — Later than v1.4 (i.e., after SEED-001 / agentic judge ships). The vision pass kept this seed at the back of the queue because (a) v1.1's per-tool config schema reservation makes future stateful-config additive, not breaking; (b) stateful testing pairs naturally with the agentic judge (agents in production are stateful); (c) v1.2/v1.3/v1.4 all ship without needing stateful semantics. Surface during /gsd-new-milestone after v1.4 lands, or earlier if a user files a request to test a stateful tool.
scope: Large
target_milestone: v1.5+ (post-SEED-001)
---

# SEED-004: Stateful tool testing with resource setup/teardown

Extend the framework beyond read-only stateless tool calls to support tools
that require **prior state** to exercise meaningfully. This includes
per-tool setup (create a fake server entry before testing `update_server`),
inter-tool dependencies (call `register_server` before `list_registered_servers`
to validate the listed entry), authenticated flows, and isolated teardown so
runs don't leak state.

The MVP spec explicitly lists this as out-of-scope future work
(`docs/mcp_test_framework_mvp_spec.md` Out of Scope: "Stateful or destructive
tool testing (read-only tools only)"). This seed captures the deliberate
deferral and the design constraints that should shape it when it eventually
germinates.

## Why This Matters

**The MCP tool surface is mostly stateful in the real world.** Read-only
tools (`list_*`, `get_*`, `describe_*`) are the easy minority.
`homelab-mcp` alone exposes `register_server`, `create_proxmox_vm`,
`deploy_infrastructure`, `decommission_device` — every one of these requires
the framework to either:

1. Create a sandbox state to operate against, OR
2. Use real state and clean up afterward, OR
3. Mock/fake at a layer the framework currently doesn't have

Without stateful support, the framework can only validate ~20% of any real
MCP server's surface. v1.1's "test the whole server" narrative quietly
plateaus at "test the read-only subset of the whole server" — useful, but
not the long-term win.

**It's also the line where the framework stops being purely declarative.**
Stateful testing introduces ordering, dependencies, isolation, and
cleanup-on-failure semantics. That's a different design problem than v1.1's
parameterize-over-tool-list shape. Treating it as a separate milestone is
the only honest scoping.

## When to Surface

**Trigger:** After v1.1 ships, when one or more of these signals appear:
- A user files an issue/request to test a stateful tool
- The framework's tool coverage on a given server stalls because remaining
  tools all require setup
- A milestone is opened that mentions: setup, teardown, fixtures (in the
  MCP-tool sense, not the pytest sense), dependencies, ordering,
  destructive testing, sandbox state, mocking

This seed should be presented during:
- `/gsd-new-milestone` when scope mentions: stateful, setup, teardown,
  resource, dependency, destructive
- `/gsd-discuss-phase` for any phase that proposes calling tools beyond
  the read-only category
- Any planning that touches per-tool config beyond `skip` and
  `call_arguments` (the v1.1 schema reserves space here — see SEED-003 and
  v1.1 design notes)

## Scope Estimate

**Large** — full milestone, possibly two. Concretely the design space:

1. **Setup/teardown contract per tool.**
   - Declarative (config-defined: "before this tool, run that tool with these
     args") vs imperative (Python hook functions). Declarative is simpler,
     scales better, but can't express conditional setup.
   - Lifecycle: per-tool setup, per-run setup (one-shot), per-session setup.

2. **Inter-tool dependencies and ordering.**
   - DAG of tool calls? Topological execution order?
   - How does a setup tool's output flow into the dependent tool's input?
     (Templating? JSONPath references? Python lambdas?)
   - Failure semantics: does setup-failure skip the dependent tool, or fail
     the run?

3. **Isolation.**
   - Each test gets a fresh sandbox? Each session?
   - For servers that don't *have* sandbox semantics (homelab-mcp talks to
     real Proxmox boxes), do we provide a "dry-run mode" hook in the
     framework, or punt to per-server config?

4. **Teardown reliability.**
   - Cleanup on test failure (try/finally semantics).
   - Cleanup on framework crash (best-effort registries that resume on next
     run? skip and accept leakage?).
   - The hardest part of any stateful test framework — easy to get
     superficially right, hard to get correct.

5. **Destructive-tool gating.**
   - Some tools (`delete_proxmox_vm`, `decommission_device`) cannot be
     undone. Need explicit allowlist, dry-run mode, or hard-block.
   - Pairs with safety guardrails — should not be enabled by default.

Likely shape: a "v1.x: Stateful Testing — Read+Create" milestone first
(setup, teardown, simple deps), then a later "v1.y: Destructive Testing
+ Isolation Guarantees" milestone for the dangerous parts. Don't try to
ship both at once.

## Breadcrumbs

Related code and decisions in the current codebase:

- **`docs/mcp_test_framework_mvp_spec.md`** — Out of Scope: "Stateful or
  destructive tool testing (read-only tools only)". Future Work: "Stateful
  tool testing with setup and teardown." This seed is the deliberate
  follow-through on those deferrals.
- **`PROJECT.md` Out of Scope** — same constraint codified at project level.
- **`src/mcp_test_framework/fixtures.py`** — current fixtures are
  session-scoped and stateless (mcp_client, judge, target_tool, config).
  Stateful testing introduces test-scoped or per-tool-scoped fixtures with
  setup/teardown lifecycle.
- **`src/mcp_test_framework/mcp_client.py`** — stateful testing reuses the
  existing `call_tool` method to execute setup steps; no new transport
  needed.
- **v1.1 per-tool config schema (in design)** — this seed depends on v1.1
  reserving space in the per-tool block for future fields like `setup:`
  and `depends_on:`. **Action item for v1.1:** explicitly reserve those
  field names in the Pydantic model (Optional, unused) so v1.x can light
  them up additively. Without this reservation, v1.x becomes a config
  migration; with it, v1.x is purely additive.

## Notes

- **User intent (2026-05-06):** "for this tool we need these parameters or
  this resource setup first." The user is already thinking about resource
  setup — this seed captures it explicitly so v1.1 doesn't quietly absorb
  "just a little setup support."
- **Anti-pattern to avoid:** Don't fold setup support into v1.1 incrementally.
  Once setup exists in any form, users will rely on it, and the partial
  implementation becomes a contract that constrains the eventual proper
  design. Either commit to the full milestone or reserve the schema slot
  and decline.
- **Open question for germination time:** does the framework provide its
  own "fake state" sandbox (e.g., MCP server stub), or rely on each MCP
  server to provide a test-mode flag? Probably the latter — keeps the
  framework neutral — but worth deciding deliberately.
- **Pairs naturally with:** SEED-001 (agentic judge — agentic loops are
  inherently stateful) and SEED-003 (dynamic rubrics — stateful tools
  often need rubrics about state-mutation correctness, not just description
  quality). All three may converge in a later milestone.

## Vision-Pass Addendum (2026-05-07)

The `/gsd-explore` long-term-vision pass (PROJECT.md "Long-term Vision" section) confirmed this seed's framing without architectural changes, but **clarified its sequencing in the milestone shape:**

| Milestone | Includes | This seed |
|-----------|----------|-----------|
| v1.1 | Multi-tool + isolation + JUnit | not yet — but reserves config schema |
| v1.2 | xdist parallelism + warm-up + OpenAI-compat backend | not yet |
| v1.3 | Dynamic rubrics + agent-realism fuzz | not yet |
| v1.4+ | Agentic tool-use judge | not yet |
| **v1.5+** | **Stateful tool testing** | **this seed germinates** |

**Why so late:** stateful testing has the largest design-space of any seed (setup/teardown contracts, inter-tool dependencies, isolation, destructive-tool gating). Each prior milestone makes the eventual stateful-testing implementation cleaner:

- **v1.1 isolation** gives stateful tests a clean per-test-or-per-session sandbox. Without per-worker tempdir isolation, stateful tests would inherit the same bleed-through bug v1.1 fixes.
- **v1.2 OpenAI-compat backend** is irrelevant to stateful semantics directly, but keeps the framework's backend story clean before adding another axis of complexity.
- **v1.3 dynamic rubrics** lets stateful tests express their stateful-correctness criteria as rubric data ("after calling `register_server`, `list_registered_servers` should include the new entry"). Without rubrics-as-data, every stateful assertion is hardcoded Python.
- **v1.4 agentic judge** is the natural consumer of stateful testing. Agents in production maintain state across tool calls; the agentic judge's call-and-reflect loop becomes much richer once stateful tools are testable.

**Critical preservation requirement reaffirmed:** v1.1 MUST reserve `setup:` and `depends_on:` as Optional/unused fields in the per-tool Pydantic config model. The original seed already flagged this; the vision pass preserves it as a hard requirement. Without those reserved field names, this seed becomes a config migration; with them, it's purely additive.

**Net:** no scope change, no design change. Position in the milestone queue is now explicit (v1.5+, post-SEED-001). Don't try to pull this earlier — the architectural prerequisites genuinely aren't ready until then.
