# ADR-001: Judge Backend Abstraction — Generalizing Beyond Ollama

**Status:** Proposed
**Date:** 2026-05-28
**Deciders:** Project owner (sole maintainer); to be ratified during v1.6 `/gsd-new-milestone` scoping
**Seed:** SEED-005 (planted v1.0, revised 2026-05-07 vision pass) • **Supersedes nothing** • **Builds on** the v1.0 `Judge` Protocol seam  <!-- noqa: sdet-rename-shim -->

## Context

The framework currently has exactly one judge backend: `OllamaJudge`, an async wrapper over Ollama's **native** `/api/chat` endpoint. It is deliberately hardened for `qwen3` quirks — `think: false` + `/no_think` directive + `<think>…</think>` stripping, `format: "json"` (Ollama-native JSON mode), `keep_alive: "30m"`, `temperature: 0`, a four-step defensive parser with brace-recovery, and a prompt-injection-resistant delimited-subject contract.

The v1.0 vision pass elevated SEED-005 from "post-MVP backend pluggability" to a **strategic pillar**: the cost model is **local-first by default, hosted opt-in**. Test data (tool descriptions, parameter docs, traces) must stay on the user's network by default — a sentence a security review will accept — with hosted compute as an opt-in escape hatch for teams that prioritize speed/determinism over locality.  <!-- noqa: sdet-rename-shim -->

The architectural enablers are already in place, so this is genuinely a *small-surface* change with *large strategic* weight:

- `src/mcp_test_framework/judge_protocol.py` — `@runtime_checkable` `Judge` Protocol with `async judge(rubric, subject, context=None) -> JudgeResult`. Backend-neutral by design.
- `src/mcp_test_framework/fixtures.py:511` — `mcp_judge` fixture; the backend instantiation is isolated to **one fixture body**. Tests annotate `judge: Judge`, never the concrete class. Swap point is a single edit.
- `JudgeResult` is backend-agnostic; backend extras (token usage, billing metadata) ride in `raw_response` rather than promoting to the model.

**Forces at play:**

1. **Data locality** — default path must never leave the network.
2. **Cost portability** — same framework on laptop (Ollama), CI runner (vLLM on shared GPU), cloud CI (LiteLLM proxy), or fully-hosted (OpenAI/Anthropic). One interface, configured per environment.
3. **Determinism** — local weights drift on upgrade; hosted endpoints pin model strings (`gpt-4o-2024-11-20`).
4. **Don't regress what works** — `OllamaJudge`'s qwen3 hardening is hard-won. The seed itself warns these tactics should **not** migrate verbatim to a generic backend, because hosted models don't share qwen3's failure modes.
5. **Accidental-bill safety** — nothing should let a CI run silently bill production OpenAI because someone set `base_url`.

**Constraint:** No new *required* dependency on the default-local path. A hosted SDK, if added, must be optional/extra so privacy-first users install nothing new.

## Decision

**Adopt Option C — a two-backend discriminated union: retain `OllamaJudge` (native `/api/chat`) as the default-local backend, and add a single `OpenAICompatJudge` that covers every other endpoint (vLLM, LM Studio, LiteLLM proxy, hosted OpenAI, and Anthropic-via-LiteLLM) through one OpenAI-compatible `/v1/chat/completions` interface.**

Backend selection is a Pydantic discriminated union under `judge.backend`, defaulting to `ollama`. API keys come from env vars only, never config files. This keeps the proven qwen3 path untouched for the privacy-first default while delivering the full local→hosted portability story through exactly one new implementation.

## Options Considered

### Option A: OpenAI-compat as the sole unifier (the seed's literal proposal)

Replace `OllamaJudge` with a single `OpenAICompatJudge` against `/v1/chat/completions`; default-local points at Ollama's OpenAI-compat endpoint (`http://127.0.0.1:11434/v1`, `api_key="ollama"`). One backend covers all providers; switching is a single `base_url` value.

| Dimension | Assessment |
|-----------|------------|
| Complexity | **Low** (one backend class, long-term) but **High migration risk** (must re-validate the default-local path) |
| Cost | Free local; hosted opt-in |
| Scalability | Excellent — N providers collapse to 1 interface |
| Team familiarity | High (sole maintainer authored the seam) |

**Pros:** Architecturally cleanest — one backend, zero per-provider branching. Smallest long-term surface to maintain. Matches the "one interface" vision verbatim.

**Cons:** Moves the **default** path onto Ollama's `/v1` compat shim, abandoning native `/api/chat`. Ollama's OpenAI-compat mode uses `response_format: {type: "json_object"}` and does **not** expose `think`/`keep_alive`/native `format` the same way — the qwen3 belt-and-braces hardening (the thing that made the judge reliable) would be silently dropped from the path 95% of users run. Highest blast radius for the lowest-tolerance path.

### Option B: Per-provider concrete backends

Keep `OllamaJudge`; add discrete `OpenAIJudge`, `AnthropicJudge`, `VLLMJudge`, etc. — each a concrete `Judge` impl, selected by discriminator.

| Dimension | Assessment |
|-----------|------------|
| Complexity | **High** — N backends to write, test, and maintain |
| Cost | Free local; hosted opt-in |
| Scalability | Poor — every new provider is a new class + smoke test |
| Team familiarity | High |

**Pros:** Each backend tuned to its provider's exact quirks. No reliance on compatibility shims.

**Cons:** Defeats the unifier insight entirely — OpenAI-compat already collapses vLLM/LM Studio/LiteLLM/OpenAI into one shape, so writing them separately is redundant work. Maintenance burden scales linearly with providers. Anthropic's genuinely different shape (Messages API, JSON-via-tool-use) is the *only* real justification for a second class, and LiteLLM absorbs even that.

### Option C: Two-backend hybrid — Ollama-native default + OpenAI-compat for the rest ✅ (CHOSEN)

Retain `OllamaJudge` (native `/api/chat`, all qwen3 hardening intact) as `judge.backend: ollama` (default). Add one `OpenAICompatJudge` (`judge.backend: openai_compat`) covering every OpenAI-compatible endpoint. Anthropic routes through a LiteLLM proxy on the OpenAI-compat path — no separate class.

| Dimension | Assessment |
|-----------|------------|
| Complexity | **Low–Medium** — one new backend + a 2-variant discriminator |
| Cost | Free local (unchanged); hosted opt-in |
| Scalability | Excellent — OpenAI-compat covers all current + future providers |
| Team familiarity | High |

**Pros:** Default path is **byte-for-byte unchanged** — zero regression risk to the proven qwen3 flow, no re-validation of the thing that already works. Full portability/hosted story delivered by one new class. Honors the seed's own warning that qwen3 tactics shouldn't migrate verbatim. Discriminator has exactly two arms, so the config surface stays legible.

**Cons:** Two backends instead of one (slightly more than the platonic ideal). Two JSON-mode code paths (`format: "json"` vs `response_format`). A user who wants Ollama *in OpenAI-compat mode* specifically can do so via `openai_compat` + `base_url=…/v1`, which is a mild redundancy with the native path.

### Option D: Embed LiteLLM as a library dependency

One `LiteLLMJudge`; route all providers through the `litellm` Python library (not a proxy).

| Dimension | Assessment |
|-----------|------------|
| Complexity | Low (one backend) but heavy dependency |
| Cost | Free local; hosted opt-in |
| Scalability | Excellent (LiteLLM supports 100+ providers) |
| Team familiarity | Medium |

**Pros:** Maximum provider coverage out of the box, including Anthropic-direct, with no per-provider code.

**Cons:** `litellm` is a large, fast-moving dependency with its own transitive tree — at odds with the "no new required dep on the default path" constraint and the project's lean `uv`-locked posture. Pulls provider-routing logic *into* the framework rather than leaving it at the deployment boundary (where LiteLLM-as-a-proxy belongs). Option C already reaches LiteLLM **as a proxy** over plain OpenAI-compat HTTP — same coverage, zero dependency.

## Trade-off Analysis

The real decision is **A vs C** — B and D are dominated (B by the unifier insight, D by the dependency cost that C avoids by treating LiteLLM as a proxy rather than a library).

A and C deliver an *identical* portability story to the user: set `base_url` (and an env-var API key) and you're on hosted compute. They differ in exactly one place — **what runs by default**:

- **A** bets that Ollama's OpenAI-compat `/v1` shim is as reliable as native `/api/chat` for qwen3. That bet is unproven and, per the seed's own breadcrumbs, *probably wrong* — the `<think>`-stripping, `think:false`, and `keep_alive` hardening exist because qwen3 misbehaves without them, and the `/v1` shim doesn't expose those knobs. A's reward is removing one already-written, already-passing class.
- **C** keeps that bet off the table. The default path doesn't change at all; the new code is purely additive and only runs when a user opts into a non-Ollama endpoint, where the qwen3 tactics were never relevant anyway.

The cost of C over A is one extra backend class and a second JSON-mode branch — a small, *bounded* maintenance cost. The cost of A over C is a regression risk on the **lowest-tolerance, highest-traffic path**, paid to save a class that already exists and works. For a framework whose entire value proposition is *reliable* judging, protecting the proven path dominates shaving one class.

C is also strictly more future-proof for SEED-001 (agentic judge): when that germinates, it implements `Judge` with its own loop and can target whichever backend (native or compat) suits its tool-calling needs — C leaves both available; A leaves only the compat path.  <!-- noqa: sdet-rename-shim -->

## Consequences

**What becomes easier**

- Local→hosted migration is a single config value + env-var key — exactly the vision's promise.
- Adding any future OpenAI-compatible provider (new vLLM build, a new gateway) needs **zero** new code.
- A "data never leaves your network" claim is defensible by default, because the default backend is unchanged and local.
- SEED-001's agentic judge inherits a backend menu rather than a single forced path.  <!-- noqa: sdet-rename-shim -->

**What becomes harder**

- Two JSON-mode code paths to keep correct (`format:"json"` for native, `response_format` for compat). Mitigated by per-backend smoke tests gated on env-var presence (clone `tests/smoke/test_smoke_ollama_judge.py`).
- Config surface grows a discriminator; docs must make the accidental-bill risk *loud* (default-local, hosted-opt-in, API keys env-only).
- Two backends to smoke-test in CI, each gated on whether credentials exist.

**What we'll need to revisit**

- **Anthropic-direct** (Messages API, JSON-via-tool-use) stays a stretch/deferred item; reassess only if LiteLLM-proxy routing proves insufficient.
- **Concurrency** — when SEED-002 (xdist) lands, `OpenAICompatJudge` must hold a pooled `httpx.AsyncClient` per worker; revisit pooling/rate-limiting then (the seed flags this cohort coupling).  <!-- noqa: sdet-rename-shim -->
- **Determinism caveat** — even hosted `temperature:0` isn't reproducible across model versions; docs must tell users to pin model strings.
- **Protocol-leak audit** — confirm no Ollama-ism (`format:"json"`) leaked *through* `Judge` into callers; lift any into the backend.

## Action Items

1. [ ] **Ratify** this ADR during v1.6 `/gsd-new-milestone` scoping; confirm SEED-005 lands in v1.6 (cohort with SEED-002 per the seed) or stands alone.  <!-- noqa: sdet-rename-shim -->
2. [ ] **Audit the seam** — grep callers for Ollama-isms reaching through `Judge`; lift leaks into `OllamaJudge`. Make the `isinstance(x, Judge)` + signature smoke load-bearing for the new backend too.
3. [ ] **Add `judge.backend` discriminated union** to `config.py` (`ollama` | `openai_compat`), default `ollama`; nest `judge.openai_compat: {base_url, model, temperature, max_tokens, response_format}`. API key via `MCP_TEST_JUDGE_API_KEY` / `OPENAI_API_KEY` env only.
4. [ ] **Implement `OpenAICompatJudge`** (raw `httpx` against `/v1/chat/completions`; `openai` SDK only if it earns its keep) — simpler parser than `OllamaJudge` (no `<think>` stripping); `JudgeResult` unchanged; usage metadata into `raw_response`.
5. [ ] **Update the `mcp_judge` fixture** (`fixtures.py:511`) to select backend by discriminator — still a one-fixture-body change.
6. [ ] **Smoke harness** — `tests/smoke/test_smoke_openai_compat_judge.py`, gated on env-var presence.
7. [ ] **`docs/BACKENDS.md`** — local→hosted migration, per-model cost/latency estimates, the data-locality story, LiteLLM-as-gateway recipe, and a **loud** accidental-bill warning.

## Open Questions (decide before ratification)

- **A vs C is the only real fork.** C is chosen to protect the qwen3 hardening on the default path. If re-validating the default path on Ollama's `/v1` shim is acceptable and single-backend cleanliness is preferred, **A** becomes defensible and this ADR flips.
- **Sequencing.** SEED-005's breadcrumbs cohort it with SEED-002 (xdist) because concurrent judging stresses backend connection pooling. Decide whether v1.6 takes both together or SEED-005 alone.  <!-- noqa: sdet-rename-shim -->
