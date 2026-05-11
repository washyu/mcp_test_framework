---
id: SEED-012
status: dormant
planted: 2026-05-10
planted_during: v1.2 / Phase 13 close (config-safety-opt-in-tool-selection complete)
trigger_when: AFTER SEED-003 (dynamic judging protocol / rubrics-as-data) lands. Surface during any milestone scoping that touches judges, rubrics, judge backends, or cost-control. Earliest natural surface is v1.3 (SEED-003's target milestone) or whichever later milestone first ships dynamic judges. Do NOT surface before SEED-003 — there's only one judge type today (static rubrics) and the per-judge override is meaningless without a second, cost-asymmetric judge type to differentiate.
scope: Small-Medium
depends_on: [SEED-003, SEED-005]
target_milestone: v1.3+ (cohort with SEED-003 / SEED-005)
---

# SEED-012: Per-judge model config — let dynamic judges use a paid backend while static rubric judges stay local

Today every judge in `src/mcp_test_framework/rubrics.py` shares one `ollama.model`
and `ollama.base_url` from top-level `Config`. That's fine for v1.x because the
only judges are static rubrics (`description_clarity`,
`description_disambiguation`, `parameters_self_explanatory`) — all the same
cost profile, all the same shape of judgment.

Once SEED-003's dynamic-judging-protocol lands, the cost profile fractures.
A dynamic judge that has to read tool docs, run an exploratory tool-call loop,
and produce structured reasoning is a real candidate for a stronger paid model
(Claude, GPT-4-class). A static "is this description clear?" rubric still runs
fine on a 7B local model in milliseconds.

Forcing both onto the same backend means either:
- run everything on the paid model (expensive, slow, defeats local-first)
- run everything on the local model (dynamic judge quality drops below the
  threshold that makes it useful as a test signal)

Neither is good. The fix is a **per-judge model override** so the operator
declares the backend on the judge, not on the framework.

## Why This Matters

- **Cost control.** Static rubrics fire on every contract test, every CI run,
  on every tool the operator opts in. At homelab-mcp's ~70-tool scale that's
  hundreds of judge calls per run. Paid inference there is wasteful; local
  Ollama is right-sized.
- **Quality where it matters.** A dynamic judge running an agentic loop
  benefits substantially from a frontier model; a static rubric does not.
- **Local-first stays local-first.** SEED-005 establishes the long-term cost
  model (local-first by default, hosted opt-in via `base_url`). This seed
  pushes that override down one level — from "the whole framework" to "this
  one judge" — so the operator can mix.
- **Operator-first design (v1.2 milestone theme).** A vibe-coded MCP user who
  wants to try the dynamic judge against Claude shouldn't have to globally
  flip the framework's backend and break their existing static-rubric runs.

## When to Surface

**Trigger:** After SEED-003 (dynamic judging protocol) is implemented.
Earlier than that, this seed is solving a problem that doesn't exist yet —
all judges have the same cost profile, so a per-judge override is overkill.

Specific surface conditions:
- Any `/gsd-new-milestone` that has SEED-003 in its cohort.
- Any milestone scoping that mentions "judge backend", "model override",
  "cost control", "paid inference", or "agentic judge".
- Post-SEED-005 if the OpenAI-compat unifier lands first — this seed
  composes cleanly with it (one extra optional field per judge).

## Scope Estimate

**Small-Medium** — pending the shape SEED-003 lands in. Two plausible
shapes, both modest:

1. **Per-judge config block.** Add an optional `judges:` top-level mapping
   to `Config`, keyed by judge ID. Each entry holds optional `base_url`
   and `model` overrides that fall through to the existing `ollama.*`
   defaults when unset. The existing `tools.<name>.judges: [...]` list
   continues to reference judges by ID; the new `judges:<id>:` block is
   where the backend override lives.

   ```yaml
   judges:
     description_clarity:           # uses ollama.* defaults — no override
     dynamic_tool_use:
       base_url: https://api.anthropic.com/v1   # paid backend
       model: claude-opus-4-7
   ```

2. **Judge-class-level default + per-judge override.** If SEED-003 ships
   judge "classes" (static-rubric vs dynamic-agent-loop), let the class
   carry a default backend and let each judge instance override. More
   structure, more flexibility.

Either way the change is bounded: a new Pydantic sub-model, a fall-through
lookup in `OllamaJudge`-equivalent constructors, regression tests pinning
the override semantics. No major refactor.

## Breadcrumbs

Related code and decisions in the current codebase:

- `src/mcp_test_framework/models.py` — `OllamaConfig.base_url` / `OllamaConfig.model`
  (the single global today; per-judge would compose against this as fallback).
- `src/mcp_test_framework/ollama_judge.py` — the only judge implementation.
  Currently reads `config.ollama.*` directly; would need to accept a
  resolved (base_url, model) tuple from a per-judge lookup instead.
- `src/mcp_test_framework/rubrics.py` — the three static rubrics. After
  SEED-003 lands, dynamic judges live alongside these; the per-judge model
  override applies to the union.
- `src/mcp_test_framework/judge_protocol.py` — the `Judge` Protocol the
  framework already routes through (D-layout-2 / SEED-001 enabler). A
  per-judge backend override fits naturally inside the Judge instance.
- `.planning/seeds/SEED-003-dynamic-judging-protocol.md` — the precondition.
  SEED-003 is the seed that creates the cost asymmetry this seed solves.
- `.planning/seeds/SEED-005-pluggable-judge-backends.md` — the unifying
  interface. SEED-005 makes "switching backends" a `base_url` override
  rather than a backend swap; SEED-012 says the override is per-judge.
- `.planning/seeds/SEED-001-agentic-tool-use-judge.md` — full agent
  tool-use loop. Another judge type whose cost asymmetry this seed
  serves.

## Notes

- Composes with SEED-005's OpenAI-compat unifier: each per-judge entry
  just sets a different `base_url`. No new backend code needed if SEED-005
  ships first.
- Composes with SEED-003's rubrics-as-data: if rubrics are declared in
  config, the model override is one more optional field on the same row.
- Composes with v1.2's operator-first theme: operator declares which
  judges cost what — no global flag, no surprise paid inference.
- **Not** about authentication / secrets — that's an orthogonal concern
  (`.env` is dead-letter for config values per Phase 13 D-05/D-07, but
  CI-secret passthrough for paid-API keys still works as a process-env
  convention). Per-judge `base_url` references a process-env-resolved
  endpoint or hardcoded URL; the API key is handled by whatever HTTP
  client the judge uses, the same way `httpx.AsyncClient` works today.
- Order to ship: SEED-003 first (creates the cost asymmetry), then
  SEED-005 (collapses N backends to 1 OpenAI-compat interface), then
  SEED-012 (per-judge override on that unified interface). Trying to
  ship 012 before 003 is solving a non-problem.
