---
id: SEED-001
status: dormant
planted: 2026-05-04
planted_during: v1.0 / Phase 01 (foundation-pure-data-core, just completed)
trigger_when: After Phase 02 (mcp-stdio-client) lands — re-evaluate the judge architecture before building Phase 03's rubric-style OllamaJudge, or surface during planning of any milestone that revisits judge design.
scope: Medium
---

# SEED-001: Replace rubric-style judge with full agent tool-use loop

Replace the static 1–5 description-quality rubric judge (planned for Phase 03) with
an **agentic judge**: the local Ollama model is given the MCP tool's schema and
description, asked to plan and execute a real `call_tool` against the live MCP
server, observe the result, and then reflect on the experience. The reflection
becomes the eval signal — pass/fail, score, and reasoning grounded in actual
tool-use rather than prose-grading.

## Why This Matters

**Both — failures + fidelity:**

1. **The current rubric misses real failures.** A 1–5 score on description clarity
   can rate a tool "5/5" even when its parameter docs are wrong, its required
   fields are mislabeled, or its output is unparseable. Only an agent actually
   *invoking* the tool surfaces those usability bugs. The rubric judge is a
   proxy for usability; the agentic judge measures usability directly.

2. **It produces higher-fidelity eval data.** MCP tools are designed to be called
   by LLM agents in a loop, not graded as prose. An agentic judge's pass/fail
   signal reflects how the tool will actually be used in production — closer
   to the test framework's stated goal of "exercising one MCP tool end-to-end."
   The rubric score is one step removed from real behavior; the agentic loop
   *is* real behavior.

Combined, this lifts the framework from "does the tool look documented?" to
"can a model actually use this tool successfully?" — which is the question the
MVP is implicitly asking anyway.

## When to Surface

**Trigger:** After Phase 02 (mcp-stdio-client) is complete and before Phase 03
(Ollama Judge) detailed planning begins. The user explicitly flagged this as
"something to look at after phase 2."

This seed should be presented during:
- `/gsd-discuss-phase 3` — before any judge-architecture decisions are locked
- `/gsd-new-milestone` if a future milestone scopes "pluggable judge backends"
  (already noted in PROJECT.md "Out of Scope" / future work) or "tool-use
  evaluation"

Surface conditions:
- Milestone or phase mentions: judge, rubric, ollama, evaluation, tool-use
- Phase 03 is being planned, replanned, or audited
- A "v2.0" or "judge backends" milestone is opened

## Scope Estimate

**Medium** — a phase or two. Concretely involves:

1. **New judge backend variant.** `AgenticJudge` implements the same `Judge`
   Protocol (already locked in for Phase 03 — see PROJECT.md Key Decision
   "`Judge` Protocol seam (judge_protocol.py) ships in MVP — zero-cost post-MVP
   backend-swap enabler"). The Protocol seam means rubric and agentic judges
   coexist without an architectural rewrite.

2. **Tool-use loop harness.** Wire Ollama tool-calling (function-calling) so the
   model can emit `call_tool` invocations the harness routes through the
   existing `McpTestClient`. Bound the loop (max N steps, timeout) to keep test
   runs deterministic.

3. **Reflection rubric.** After the loop terminates, ask the judge a structured
   reflection question (`format: json` again, same Pydantic envelope) that
   produces the final `JudgeResult`. The "raw_response" field carries the
   call-trace.

4. **Eval dataset.** A small set of tool-use traces — at least one happy-path
   success, one description-misled failure, one schema-mismatch failure — to
   regression-test the agentic judge itself.

Not large because the Protocol seam already exists, the MCP client wrapper is
the deliverable of Phase 02, and Ollama already supports tool calls in
`/api/chat`. The work is mostly in reflection prompting and loop bounding.

## Breadcrumbs

Related code and decisions in the current codebase:

- **`PROJECT.md` line 9** — Core value statement ("schema → call → judge"). The
  agentic judge collapses "call → judge" into one experience, which is closer
  to the stated value than the current rubric path.
- **`PROJECT.md` Key Decisions** — "Phase 3: `Judge` Protocol seam
  (judge_protocol.py) ships in MVP — user confirmed; zero-cost post-MVP
  backend-swap enabler." The Protocol exists *specifically* so this seed can
  germinate without breaking changes.
- **`PROJECT.md` Out of Scope** — "Pluggable judge backends (OpenAI-compatible,
  etc.) — Ollama-only for MVP." The agentic judge is a *new backend*, not a
  rewrite of the Ollama backend; it slots in alongside.
- **`.planning/ROADMAP.md` Phase 3** — Defines `OllamaJudge` rubric scoring as
  the MVP shape. This seed proposes that Phase 3 ships rubric-only AS PLANNED,
  and the agentic judge becomes a post-Phase-3 (or post-MVP) addition that
  reuses the same `Judge` Protocol.
- **`.planning/research/PITFALLS.md`** — Surfaces qwen3 thinking quirks,
  cold-start timeouts, `<think>` blocks. The agentic judge inherits all of
  these and adds a new failure mode: tool-call schema generation drift. The
  reflection loop must defend against the model emitting malformed
  `tool_calls` payloads.
- **`docs/mcp_test_framework_mvp_spec.md`** — The authoritative MVP spec is
  rubric-based. Any agentic-judge work must update or supplement the spec.

## Notes

- User context (2026-05-04, just after Phase 1 completion): "Replace
  rubric-style judge with full agent tool-use loop where the local model
  executes the tool and reflects on the experience."
- The agentic judge does NOT replace deterministic schema validation
  (Phase 1's `schema_validator.py`) or output-conformance checks (Phase 4).
  Those remain as fast, cheap, deterministic checks. The agentic judge only
  replaces the *description-quality* rubric.
- Open question for surfacing time: should the agentic judge run in addition
  to the rubric (two signals, compare) or fully replace it (one signal,
  simpler)? The Protocol seam supports either configuration via the existing
  judge backend selector.
- Cost note: the agentic loop is N× more Ollama calls per tool than the
  single-shot rubric. With Ollama running locally at 127.0.0.1 this is
  free-but-slow; bound the loop carefully so CI runs stay under the spec's
  implied budget.
