---
id: SEED-002
status: dormant
planted: 2026-05-04
revised: 2026-05-07
planted_during: v1.0 / Phase 01 (foundation-pure-data-core, just completed)
revised_during: v1.0 / `/gsd-explore` Long-term Vision pass
trigger_when: REVISED — v1.2 milestone. v1.1 (multi-tool + per-worker isolation) is now the **hard prerequisite** because process-parallel xdist workers stomp on each other's homelab-mcp state without per-worker tempdir isolation. Surface during /gsd-new-milestone for v1.2 ("performance + portability"), cohort with SEED-005 and warm-up stage.
scope: Medium
target_milestone: v1.2 (cohort with SEED-005 + warm-up stage)
---

# SEED-002: Tool-level parallelism via pytest-xdist with read/write resource markers

Run non-conflicting MCP tool tests concurrently using `pytest-xdist`, with each
test annotated by **resource markers** that declare which server-side resources
it touches and in which **mode** (read vs. write). The xdist scheduler — or a
small custom scheduler on top — uses these markers to interleave tests that
don't share writable resources, while serializing any pair that shares a
write-mode resource.

This is **out of scope for the MVP**, but the architectural prep work — *not
hardcoding single-tool execution into fixtures, config, or test layout* — needs
to start now in v1.0 so we don't have to retrofit it later.

## Why This Matters

**CI throughput at scale.**

Per-tool work in this framework is dominated by slow operations:

- Ollama judge calls (cold-start + reflection prompt per tool): seconds-to-tens-of-seconds
- MCP `call_tool` round-trips over stdio: tens-to-hundreds of milliseconds, but cumulative
- Schema validation × N tools, output conformance × N tools

With one tool today, serial is fine. With even 5–10 tools — let alone the full
surface of a real homelab MCP server, or multiple servers — serial CI runs
balloon past acceptable thresholds. Tool-level parallelism is the only way to
keep the test suite fast enough to gate every PR.

The read/write marker design is what makes this *safe*: many MCP tools are
read-only queries (list, describe, get, search) and freely parallelizable;
the few that mutate state (create, delete, restart) need exclusive access to
their resource. Markers let the scheduler exploit the read/write asymmetry
instead of falling back to "serialize everything that might conflict."

## When to Surface

**Trigger:** Out of MVP scope, but **must** influence v1.0 architecture so we
don't lock in single-tool assumptions. Surface eagerly during:

- `/gsd-discuss-phase` for any phase that touches fixture design or test
  layout (Phase 04 fixtures, Phase 05 CI smoke)
- `/gsd-new-milestone` whenever the milestone scope mentions: multi-tool,
  multi-server, parallelism, xdist, throughput, generalization
- Any audit of `TargetConfig` / `target.tool_name` (see Breadcrumbs)

The user explicitly flagged this with a hybrid trigger: "we are planning on
it, it is just out of scope for the MVP, but don't want to hardcode
single-tool execution from the beginning." Treat as a *prep-now, build-later*
seed — surface during current planning to inform decisions, then again when
the actual implementation phase opens.

## Scope Estimate

**Medium** — a phase or two when actually built. Concretely:

1. **Add `pytest-xdist` to dev deps** and configure the worker count via
   config (`workflow.xdist_workers` or env var).

2. **Design the resource-marker DSL.** Two-level shape:
   - `@pytest.mark.mcp_resource("servers", mode="read")`
   - `@pytest.mark.mcp_resource("servers/<id>", mode="write")`
   The path identifies the resource; `mode` is `read` or `write`. Multiple
   markers per test allowed (a test that lists then deletes touches
   `servers` read AND `servers/<id>` write).

3. **xdist-safe fixtures.** The current `mcp_client`, `judge`, and
   `target_tool` fixtures are session-scoped (per CLAUDE.md). Under xdist,
   "session" is per-worker — each worker spawns its own MCP subprocess and
   its own Ollama HTTP client. Audit Phase 4 fixtures to confirm they
   don't share mutable state across workers (file paths, ports, the
   stdio subprocess itself).

4. **Scheduler.** Either:
   - **Simple:** xdist's default `loadgroup` distribution + `xdist_group`
     markers derived from resources (groups serialize within a worker).
     Cheap, leaves write-write conflicts on the table.
   - **Custom:** small dispatcher that reads markers and assigns tests to
     workers with a resource-conflict check. More work, but exploits
     read-read parallelism fully.
   - Recommend starting with the simple scheme and upgrading only if
     needed.

5. **Documentation.** A test author needs to know: how to mark a new tool's
   tests, what counts as a "resource," what happens when markers are
   missing (default to write — i.e. fully serialized — for safety).

What this seed is **not**: distributing across machines, parallelizing within
a single tool's tests (intra-tool concurrency is a different concern), or
parallelizing the Ollama judge (Ollama is the bottleneck and the homelab box
serializes it anyway).

## Breadcrumbs

Today's code already has single-tool assumptions that this seed needs to push
back against during v1.0 planning. Flag these during reviews of the affected
phases:

- **`src/mcp_test_framework/models.py:60–68`** — `TargetConfig.tool_name`
  is a single string. By the time SEED-002 fires this likely needs to become
  `tool_names: list[str]` or a wildcard, with the MVP keeping a single-name
  shorthand. Don't bake "exactly one tool" into the **test discovery path**
  (CLAUDE.md mentions a `target_tool` fixture that fails the run if the
  configured tool is absent — that contract has to generalize).
- **`.planning/PROJECT.md` Core Value** — "exercises one MCP tool
  end-to-end." This wording hardcodes "one" into the MVP scope. The seed
  doesn't ask to change MVP scope — only to keep the door open in
  fixture/config shape.
- **`.planning/REQUIREMENTS.md` and `.planning/ROADMAP.md`** — Phases 04/05
  scaffold fixtures and CI. Their plans should describe `target_tool`
  fixtures in a way that is *list-amenable* even if the MVP only asks for
  one element.
- **`.planning/research/PITFALLS.md`** — Documents Windows
  `ProactorEventLoop` subprocess cleanup races. Under xdist this multiplies
  — each worker spawns its own subprocess on Windows. The cleanup contract
  (revisited during Phase 4 plan) needs to be xdist-safe from the start.
- **`pyproject.toml`** — `asyncio_default_fixture_loop_scope = "session"`
  (locked Phase 1, 01-02-CONTEXT). Under xdist this becomes
  per-worker-session, which is the right semantics — but document it
  explicitly when xdist lands so debugging "why does each worker get its
  own loop?" doesn't take an hour.

## Notes

- User context (2026-05-04): "Tool-level parallelism via pytest-xdist with
  resource markers (read/write modes) so non-conflicting tools run
  concurrently. … this is something we are planning on, it is just out of
  scope for the MVP but don't want to hardcode single tool execution from
  the beginning."
- The read/write marker idea generalizes well beyond MCP — it's a standard
  test-isolation pattern (e.g., `pytest-rerunfailures` + database fixtures
  use a similar shape). When this seed fires, search prior art before
  inventing a bespoke DSL.
- Adjacent seed: SEED-001 (agentic tool-use judge). The agentic judge
  multiplies the per-tool cost further, which makes parallelism even more
  attractive — but it also means the *judge* call is the new bottleneck,
  and Ollama on a single homelab box still serializes those. Plan
  parallelism around tool-call concurrency, not judge concurrency.
- Default-to-safe principle: tests without markers should be treated as
  full-write (fully serialized) rather than full-read (fully parallel).
  Better to be slow than to flake.

## Vision-Pass Addendum (2026-05-07)

The `/gsd-explore` long-term-vision pass (PROJECT.md "Long-term Vision" section) added two load-bearing constraints that lock this seed's milestone target and shape its scope:

**1. Threading constraint identified as load-bearing project fact.** "homelab-mcp is not thread-safe" was confirmed as a current limitation of the test target. Per PROJECT.md "Performance constraints": **the framework parallelizes at the process level only.** This rules out any thread-pool variant of parallelism inside a single MCP subprocess — the only path is xdist + multiple subprocesses. That's exactly what this seed proposes; the architectural alignment is now explicit and locked.

**2. Per-worker isolation is a HARD prerequisite.** v1.1's isolation work (HOME/USERPROFILE override + tempdir-per-session) was originally framed as a bug fix for `homelab-mcp` state-bleed-through. The vision pass clarified it's also the *prerequisite* for parallelism — without per-worker isolation, two xdist workers would write to the same `~/.homelab_mcp/credential_registry.json` and corrupt each other's runs. **v1.2 cannot ship parallelism until v1.1 ships isolation.**

**3. Cohort-shipped with SEED-005 + warm-up stage in v1.2.** The vision pass committed v1.2 as "performance + portability" — three concerns that ship together because they share architectural muscles:

- **SEED-002 (this seed):** xdist parallelism with per-worker isolated subprocess
- **SEED-005:** OpenAI-compat backend (parallel workers each need a judge client; pooling/rate-limiting must be per-worker or globally negotiated)
- **Warm-up stage:** a session-scoped fixture that issues a dummy judge call to amortize cold-start across the run. Without this, the project's wall-clock-budget target (~5 min/run) is unreachable on local Ollama.

**4. Wall-clock target locked at ~5 min per run.** PROJECT.md's "Performance constraints" section codifies this. Without xdist parallelism + warm-up, the budget is unreachable for any reasonable multi-tool surface. This seed's cost/value justification is now anchored to a concrete number, not a hand-wave.

**Net:** this seed is now scoped, sequenced, and architecturally pinned. v1.1 must enable it (isolation); v1.2 ships it. Don't delay the v1.1 isolation work because its real downstream consumer is here.
