---
id: SEED-005
status: dormant
planted: 2026-05-06
planted_during: v1.0 / post-shipping conversation about v1.1 scoping
trigger_when: When the team needs to run judges against a backend other than local Ollama — OpenAI-compatible endpoints, Anthropic Claude, hosted inference, or in CI environments where running Ollama locally is impractical. Also surface when a milestone mentions "judge backend", "OpenAI", "Anthropic", "hosted inference", or "CI integration".
scope: Medium
---

# SEED-005: Pluggable judge backends

The MVP locks the judge backend to local Ollama (`127.0.0.1:11434` running
`qwen3.6:latest`). The `Judge` Protocol seam in
`src/mcp_test_framework/judge_protocol.py` was deliberately built to permit
alternative backends without an architectural rewrite. This seed captures
the deliberate post-MVP work to add at least one alternative backend
(OpenAI-compatible endpoint is the obvious first target) so the framework
is portable to environments that can't or won't run Ollama locally.

## Why This Matters

**Three concrete forces:**

1. **CI portability.** Most CI runners don't have a GPU; running Ollama on
   CPU is slow enough to push test runs over the budget. A hosted backend
   (OpenAI, Anthropic, an internal LLM gateway) keeps test latency
   bounded and predictable.

2. **Reproducibility / determinism.** Local Ollama with a model file users
   pull manually means "did the test fail because the tool changed or
   because someone updated their qwen3 weights?" A hosted backend pinned
   to a specific model version (`gpt-4o-2024-11-20`) gives every team
   member and every CI run the same scoring substrate.

3. **Cost-quality tradeoff control.** Different teams want different
   knobs. Some want free-but-slow local. Some want fast-but-paid hosted.
   Some want both — local for dev iteration, hosted for the canonical
   nightly run. Pluggable backends make those choices configurable,
   not architectural.

**The seam already exists.** PROJECT.md Key Decision:
"Judge Protocol seam (judge_protocol.py) ships in MVP — zero-cost post-MVP
backend-swap enabler." This seed is the deliberate cash-in on that
investment.

## When to Surface

**Trigger:** When any of these signals appear:
- A user requests a backend other than Ollama
- CI integration becomes a priority and local Ollama is the bottleneck
- A milestone is opened mentioning: judge backend, OpenAI, Anthropic,
  hosted inference, model gateway, BYOM (bring your own model)
- The dynamic-judging milestone (SEED-003) is being scoped — backends and
  rubrics-as-data are orthogonal but commonly conflated; surfacing this
  seed alongside SEED-003 keeps the discussion clean

This seed should be presented during:
- `/gsd-new-milestone` when scope mentions: backend, hosted, OpenAI,
  Anthropic, CI, portability, gateway
- `/gsd-discuss-phase` for any phase that touches `OllamaJudge`,
  `judge_protocol.py`, or judge configuration
- After v1.1 ships, if v1.2 candidates are being weighed (this seed is a
  strong candidate for v1.2 specifically because it's *small enough* to
  ship alongside other work, unlike SEED-003 and SEED-004)

## Scope Estimate

**Medium** — a phase or two. The Protocol seam keeps it bounded:

1. **Backend abstraction extraction.** Audit `OllamaJudge` for
   Ollama-specific assumptions that leak through the Protocol (e.g.,
   `format: "json"` is Ollama syntax; OpenAI uses
   `response_format: { type: "json_object" }`). Lift the leaks into the
   backend, not the protocol.

2. **OpenAI-compatible backend.** First alternative implementation. Many
   inference endpoints (vLLM, LM Studio, LiteLLM, real OpenAI) speak
   OpenAI-compatible API, so one backend covers many providers. Use the
   `openai` Python SDK or raw `httpx` against `/v1/chat/completions`.

3. **Backend selection in config.** Config gains a `judge.backend:
   ollama|openai|...` discriminator with backend-specific config nested
   under it. Pydantic discriminated unions handle this cleanly.

4. **Auth handling.** API keys via env vars (`OPENAI_API_KEY`), never
   committed to config files. Document the precedence rules.

5. **Smoke test harness.** A `tests/smoke/test_smoke_<backend>_judge.py`
   per backend, gated on env var presence so CI only runs the backends
   it has credentials for.

Optional (defer to follow-up if time pressed):
- Anthropic Claude backend (different SDK, different JSON-output mode)
- Cost/latency reporting per run

## Breadcrumbs

Related code and decisions in the current codebase:

- **`src/mcp_test_framework/judge_protocol.py`** — the Protocol seam.
  This is the file that permits this seed to germinate without a
  refactor. Verify its abstractions are backend-neutral when this seed is
  picked up; tighten if needed.
- **`src/mcp_test_framework/ollama_judge.py`** — the current concrete
  implementation. Audit for Ollama-isms (`format: "json"`,
  `/api/chat` URL shape, response envelope structure) that need to be
  contained, not leaked.
- **`src/mcp_test_framework/config.py`** — gains a backend discriminator.
  Use Pydantic `Discriminated Unions` (already on Pydantic 2.x).
- **`src/mcp_test_framework/models.py`** — `JudgeResult` should remain
  backend-agnostic. If a backend has unique data (e.g., usage tokens),
  carry it in `raw_response` rather than promoting it to the model.
- **`tests/smoke/test_smoke_ollama_judge.py`** — pattern for what a
  per-backend smoke test looks like; clone for new backends.
- **`docs/mcp_test_framework_mvp_spec.md` Future Work** — "Pluggable
  judge backends (OpenAI-compatible endpoints, not just Ollama)" is
  listed verbatim. This seed is the deliberate follow-through.
- **`PROJECT.md` "Out of Scope"** — "Pluggable judge backends —
  Ollama-only for MVP." Same deferral codified at project level.

## Notes

- **Anti-coupling note:** Don't conflate this seed with SEED-003 (dynamic
  rubrics). They're orthogonal. Backends = *how* the judge runs.
  Rubrics = *what* the judge evaluates. They can ship independently and
  in either order, though shipping backends first probably makes
  rubric-versioning testing easier (you can compare the same rubric across
  two backends).
- **Anti-coupling note 2:** Don't conflate this seed with SEED-001
  (agentic judge). Agentic judge is a *new judge style* implemented as a
  new backend conceptually but really a new `Judge` Protocol implementor
  with its own loop semantics. SEED-005's scope is *swapping the
  underlying LLM call*, not changing what the judge does with it.
- **Cost note:** Hosted backends introduce monetary cost per test run.
  Surface this clearly in docs when this seed germinates; don't let
  someone accidentally rack up a bill via CI.
- **Determinism note:** Even hosted backends with `temperature: 0` are
  not perfectly deterministic across model versions. Pin model strings
  and document the regression-test implications.
- **Why MEDIUM not LARGE:** the Protocol exists, the patterns are
  well-understood, and shipping one alternative backend (OpenAI-compatible)
  proves the seam without committing to many. Subsequent backends are
  copy-pattern work.
