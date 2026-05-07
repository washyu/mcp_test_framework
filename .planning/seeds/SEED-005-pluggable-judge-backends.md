---
id: SEED-005
status: dormant
planted: 2026-05-06
revised: 2026-05-07
planted_during: v1.0 / post-shipping conversation about v1.1 scoping
revised_during: v1.0 / `/gsd-explore` Long-term Vision pass
trigger_when: v1.2 milestone — promoted from "deferred backend swap" to "strategic pillar of the project's local-first cost model" after the 2026-05-07 vision pass. Surface during /gsd-new-milestone v1.2 scoping; also surface if a milestone mentions "judge backend", "OpenAI-compatible", "hosted inference", "CI portability", or "local-first".
scope: Medium-Large (revised up from Medium)
target_milestone: v1.2 (cohort with SEED-002 + warm-up stage)
---

# SEED-005: OpenAI-compatible judge backend as the unifier (local-first / hosted-opt-in)

The framework's long-term cost model is **local-first by default, hosted opt-in via base_url override.** OpenAI-compatible API is the unifying interface: one backend implementation covers Ollama (OpenAI-compat mode), llama.cpp servers, vLLM, LM Studio, LiteLLM proxy, real OpenAI, and hosted Anthropic via a LiteLLM gateway. Switching from local to hosted is a single config value (`base_url`) — not a backend swap.

**Revision note (2026-05-07):** This seed was originally planted as a generic "post-MVP backend pluggability" deferral. The vision pass elevated it to a strategic pillar. Test data must stay in the user's network by default (a real value prop for security-conscious CI), with hosted compute as an opt-in escape hatch for teams that want speed/determinism over locality. The unifying-interface approach (OpenAI-compat) collapses N backends into 1.

## Why This Matters

**Three forces, all CI-engineer-facing per the v1.0 vision pass:**

1. **Data locality.** CI engineers in regulated environments cannot send tool descriptions, parameter docs, or test traces to third-party hosted LLMs. **Local-first by default = "your test data never leaves your network."** That's a sentence a security review will accept; "we send everything to OpenAI" is not.

2. **Cost portability.** The same framework needs to run on (a) a developer laptop with `ollama serve`, (b) a CI runner with a vLLM endpoint on a shared GPU box, (c) a cloud CI runner with a LiteLLM proxy fronting whatever LLM the org has procurement for, (d) a fully-hosted production-grade run against real OpenAI/Anthropic. **One backend, one interface, configured per environment.**

3. **Determinism / model-version pinning.** Local Ollama models drift when users upgrade weights. Hosted endpoints can pin model strings (`gpt-4o-2024-11-20`). Teams that want reproducibility get it via the hosted path; teams that want privacy get it via local. The framework supports both with the same code.

The Judge Protocol seam in `src/mcp_test_framework/judge_protocol.py` already exists. PROJECT.md Key Decision: "zero-cost post-MVP backend-swap enabler." This seed is the deliberate cash-in.

## When to Surface

**Trigger:** v1.2 milestone planning. The 2026-05-07 vision pass committed v1.2 as the cohort milestone for SEED-002 + SEED-005 + warm-up stage ("performance + portability"). All three share architectural concerns and ship together.

Surface during:
- `/gsd-new-milestone` for v1.2 scoping (definitive trigger)
- `/gsd-discuss-phase` for any phase touching `judge_protocol.py`, `ollama_judge.py`, or judge configuration
- Any planning that proposes adding hosted-compute support to v1.1 — push back: v1.1 is local-only, v1.2 is the cohort milestone for backend portability

## Scope Estimate

**Medium-Large** — revised up from "Medium" because the unifier-architecture decision adds rigor to the seam-tightening work. Concretely:

1. **Tighten the Judge Protocol seam.** Audit `OllamaJudge` for Ollama-isms that leak through `Judge` (e.g., `format: "json"` is Ollama syntax; OpenAI-compat uses `response_format: { type: "json_object" }`). Lift the leaks into the backend, not the protocol. The protocol post-tightening must work for *any* OpenAI-compatible endpoint without backend-specific branching in the caller.

2. **`OpenAICompatJudge` backend.** Single new implementation. Use the `openai` Python SDK or raw `httpx` against `/v1/chat/completions`. Configurable: `base_url`, `api_key`, `model`, `temperature`, `max_tokens`, `response_format`. **Defaults targeted at local Ollama-in-OpenAI-compat-mode** (`base_url=http://127.0.0.1:11434/v1`, `api_key="ollama"`, model from existing config) so the migration from `OllamaJudge` to `OpenAICompatJudge` is invisible to existing users in the default-local path.

3. **Backend selection in config.** Pydantic discriminated union under `judge`:
   - `judge.backend: ollama | openai_compat | ...`
   - `judge.openai_compat: { base_url, api_key, model, ... }`
   - The `ollama` discriminator stays for back-compat for at least one minor version, then the recommendation moves to `openai_compat` with Ollama's `/v1` prefix as the default `base_url`.

4. **Auth handling.** API keys via env vars only (`OPENAI_API_KEY`, `MCP_TEST_JUDGE_API_KEY`). Never persisted in config files. Documented precedence rules.

5. **Smoke test harness.** Per-backend smoke tests in `tests/smoke/test_smoke_<backend>_judge.py`, gated on env var presence so CI runs only the backends it has credentials for. Pattern from `tests/smoke/test_smoke_ollama_judge.py` (already exists).

6. **Migration path documentation.** A "moving from local Ollama to hosted compute" section in `docs/EXTENDING.md` or a new `docs/BACKENDS.md`. Should include: cost-per-run estimates for typical model strings, latency expectations, the data-locality story, how to point at LiteLLM as a multi-provider gateway.

7. **(Stretch, possibly v1.3)** Anthropic-direct backend. The `anthropic` SDK has a different shape (Messages API, system prompts as a separate parameter, JSON output via tool use rather than `response_format`). Keep a stretch goal — most users can route through LiteLLM and stay on the OpenAI-compat path, so this is value-add not blocker.

## Cohort with SEED-002 and warm-up stage (v1.2 architecture)

v1.2 ships three concerns together because they share architectural muscles:

- **SEED-002 (xdist parallelism):** depends on v1.1 isolation; multiplies the per-test cost AND the per-test concurrent judge load. The OpenAI-compat backend needs to support concurrent calls (an `httpx.AsyncClient` + connection pool, with sane defaults).
- **SEED-005 (this seed):** the backend abstraction. Per-worker isolation means each xdist worker has its own judge client; pooling/rate-limiting must be per-worker or globally negotiated.
- **Warm-up stage:** a session-scoped fixture that issues a single dummy judge call before any test runs, to amortize cold-start across the run. For Ollama this preloads the model; for hosted OpenAI this is a no-op but documents the seam for future per-backend warm-up logic. Without warm-up, the wall-clock-budget target of ~5 min/run is unreachable on local.

The three together make the framework match the vision's "CI-friendly, ~5 min/run, local-first, portable" spec.

## Breadcrumbs

Related code and decisions:

- **`src/mcp_test_framework/judge_protocol.py`** — the seam this seed builds on. Audit for Ollama-isms that leaked.
- **`src/mcp_test_framework/ollama_judge.py`** — current concrete impl. The Ollama-specific belt-and-braces (think:false, `<think>` strip, brace-recovery, keep_alive:30m) are qwen3-specific tactics — they should NOT migrate verbatim to `OpenAICompatJudge` because hosted models don't have the same failure modes. The OpenAI-compat backend is simpler.
- **`src/mcp_test_framework/config.py`** — gains a `judge.backend` discriminator. Pydantic `Discriminator` (Pydantic 2.x).
- **`src/mcp_test_framework/models.py`** — `JudgeResult` stays backend-agnostic. Backend-specific extras (e.g., usage tokens, hosted billing metadata) carry in `raw_response` rather than promoting to the model.
- **`tests/smoke/test_smoke_ollama_judge.py`** — pattern to clone for new backends.
- **`docs/mcp_test_framework_mvp_spec.md` Future Work** — "Pluggable judge backends (OpenAI-compatible endpoints, not just Ollama)." This seed is the deliberate follow-through; the 2026-05-07 vision pass elevated it to a strategic pillar.
- **`PROJECT.md` Long-term Vision (added 2026-05-07)** — codifies the local-first / hosted-opt-in cost model and the OpenAI-compat-as-unifier interface design. This seed is the implementation; PROJECT.md is the strategic frame.
- **SEED-002 (xdist)** — cohort dependency; ship together in v1.2.
- **SEED-001 (agentic judge)** — orthogonal but co-evolving. Agentic loops also benefit from the OpenAI-compat backend (tool-calling support is more uniform across hosted endpoints than across local). When SEED-001 germinates (v1.4+), it builds *on top of* this seed's backend abstraction.

## Notes

- **Anti-coupling note:** Don't conflate this seed with SEED-003 (dynamic rubrics). They're orthogonal. Backends = *how* the judge runs (this seed). Rubrics = *what* the judge evaluates (SEED-003). Both ship independently and can be implemented in either order, though shipping the backend first (v1.2) before the rubric-data-system (v1.3) probably makes rubric-versioning testing easier (compare same rubric across two backends).
- **Anti-coupling note 2:** Don't conflate with SEED-001 (agentic judge). Agentic judge is a *new judge style* that uses Ollama tool-calling or OpenAI-compat tool-use — it implements `Judge` Protocol with its own loop semantics. SEED-005's scope is *swapping the underlying LLM call*, not changing what the judge does with it.
- **Cost note:** Hosted backends introduce monetary cost per run. Documentation must be loud about this (default-local, hosted-opt-in is the architectural answer; clear docs is the UX answer). Don't let someone accidentally rack up a bill via CI by pointing `base_url` at production OpenAI without realizing.
- **Determinism note:** Even hosted backends with `temperature: 0` are not perfectly deterministic across model versions. Pin model strings; document the regression-test implications.
- **Why scope went from Medium to Medium-Large:** the unifier-architecture decision (one backend covering N providers via OpenAI-compat) is right, but it adds rigor to the seam-tightening work. The original Medium estimate assumed "ship one alternative backend"; the Medium-Large estimate covers "make the protocol seam genuinely backend-neutral, ship the OpenAI-compat backend, document the migration path, smoke-test multiple endpoints."
- **User intent (2026-05-07):** "We are currently using ollama but we should focus on openapi support [interpreted: OpenAI-compatible API]. But yes we should focus on using local models suggesting they can use smaller models to test the tools. So data and test runs stay secure and llm expense can be as cheap as a in house server with a graphics card. But if they wanted they could use cloud compute if they want." Captured verbatim because this IS the cost model.
