# Phase 3: Ollama Judge - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-05
**Phase:** 03-ollama-judge
**Areas discussed:** SEED-001 disposition, Live smoke shape, Judge.judge context shape, Cold-start warmup, Prompt parameterization

---

## SEED-001 Disposition (rubric vs agentic judge)

| Option | Description | Selected |
|--------|-------------|----------|
| Rubric only, defer agentic | Ship Phase 3 exactly as ROADMAP / REQUIREMENTS spec it: `OllamaJudge` implements `Judge` with rubric-style `/api/chat` scoring. SEED-001 stays dormant; surfaces as a future phase or post-MVP milestone. Matches "phase scope = phase title" rule — title is "Ollama Judge" (rubric). | ✓ |
| Rubric now, plan agentic as Phase 3.1 | Phase 3 ships rubric as planned; insert Phase 3.1 (analogous to 02.1) for the agentic backend reusing the `Judge` Protocol. Both backends coexist; Phase 4 picks rubric for MVP. Adds work but locks the seed in flight. | |
| Pivot Phase 3 to agentic-only | Replace rubric-style with `AgenticJudge` in Phase 3 itself. Significantly changes scope: ROADMAP SC#1–5, REQUIREMENTS CORE-04, spec, and Phase 4 rubric tests all need re-derivation. Single backend, but invalidates locked criteria. | |

**User's choice:** Rubric only, defer agentic
**Notes:** Seed was explicitly planted with trigger "before any judge-architecture decisions are locked for Phase 3" — surfacing it was correct, but the locked success criteria + 'phase scope = phase title' rule make rubric-only the right call. The `Judge` Protocol seam ships in Phase 3 anyway, so a future agentic backend is a 1-file addition, not a rewrite.

---

## Live Smoke Shape (smoke test structure + subject)

### Sub-question 1: structure

| Option | Description | Selected |
|--------|-------------|----------|
| Permanent live_ollama pytest test | Match Phase 2 D-01: `tests/smoke/test_smoke_ollama_judge.py` with `@pytest.mark.live_ollama`. Update `pyproject.toml` `addopts` to skip both live markers. ROADMAP "throwaway script" wording overridden the same way Phase 2 D-01 overrode it. | ✓ |
| Throwaway script under scripts/ | Literal ROADMAP wording — one-time-use script under `scripts/` for cold-start verification, then deleted. Matches spec verbatim; loses ongoing CI value; inconsistent with Phase 2 pattern. | |
| Both — throwaway + permanent | Throwaway script for cold-start AND permanent `live_ollama` pytest smoke for ongoing runs. Matches both the literal ROADMAP wording and the Phase 2 D-01 reusability pattern. | |

### Sub-question 2: subject

| Option | Description | Selected |
|--------|-------------|----------|
| Canned synthetic subject | Hard-coded fake tool description embedded in the smoke test. Zero coupling to homelab-mcp; smoke is hermetic; markers stay orthogonal. | ✓ |
| Real homelab-mcp tool description | Smoke pulls `list_registered_servers` description from live homelab-mcp via `McpTestClient`, then judges it. More end-to-end; depends on BOTH `live_homelab` AND `live_ollama` — markers get muddy. | |
| Trivial 1-token plumbing check | Just verifies httpx + Ollama plumbing with a 5-word description. Cheapest; doesn't validate rubric shape against realistic input. | |

**User's choice:** Permanent `live_ollama` pytest test + canned synthetic subject
**Notes:** Marker orthogonality (`live_ollama` ⊥ `live_homelab`) was the load-bearing reason for the canned subject — one failing should not be ambiguous about the other.

---

## Judge.judge `context` Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Free-form `dict \| None` (spec-verbatim) | `context: dict \| None = None`. Each Phase 4 test passes whatever fields its rubric mentions. Zero coupling to a specific schema, leaves room for SEED-001 reflection traces, smallest Phase 3 surface. No compile-time check that rubric and context fields agree — enforced by the rubric prompt itself. | ✓ |
| Typed `JudgeContext` model | Pydantic model with optional fields like `tool_name`, `tool_description`, `input_schema`, `sibling_tools`. Type checker catches missing fields; over-fits to current 3 rubrics; brittle for SEED-001 later. | |
| No context — fold into subject | Drop the `context` parameter; callers pre-format everything into `subject`. Diverges from ROADMAP SC#1. | |

**User's choice:** Free-form `dict | None` (spec-verbatim)
**Notes:** Matches ROADMAP SC#1 and canonical spec exactly; keeps the door open for SEED-001 reflection traces without a Phase 3 model migration.

---

## Cold-Start Warmup

| Option | Description | Selected |
|--------|-------------|----------|
| Defer to Phase 4 _preflight | `OllamaJudge` has no warmup behavior. Phase 4's `_preflight` fixture (FIX-02) issues a no-op 1-token call before any rubric tests run. Phase 3 stays minimal: `judge()` is `judge()`. The 120s `httpx.Timeout` covers cold-start if a rubric call happens to be first. Phase 3 smoke verifies cold-start works because the smoke IS the first call. | ✓ |
| Bake into OllamaJudge — lazy on first call | Internal `_warmed` flag; first `judge()` call internally issues a 1-token warmup, then proceeds. Encapsulated; reused by anyone instantiating; hidden side effect inside what should be a pure I/O method. | |
| Explicit OllamaJudge.warmup() method | Public `async def warmup(self) -> None` that callers invoke explicitly. Compromise — warmup logic lives WITH the judge but isn't hidden inside `judge()`. | |
| No warmup — rely on keep_alive + 120s timeout | Skip warmup entirely. `keep_alive: "30m"` keeps the model hot between calls; 120s timeout absorbs a cold-start. First test of the day is the canary; failure presents as 'judge timeout' rather than 'cold start in progress'. | |

**User's choice:** Defer to Phase 4 _preflight
**Notes:** Keeps `OllamaJudge` a clean I/O wrapper. Cold-start handling split across the smoke test (which IS the first call) and Phase 4's _preflight fixture.

---

## Prompt Parameterization (rubric placement)

| Option | Description | Selected |
|--------|-------------|----------|
| Rubric in user content, system prompt is fixed | System prompt is a constant template (strict-evaluator + `/no_think` + JSON-only + delimited subject contract). Rubric and subject + context are injected into the `user` message. One stable system prompt = better Ollama prompt caching, easier to test, matches typical chat-API patterns. | ✓ |
| Rubric in system prompt, subject in user content | Each call rebuilds a system prompt that interpolates the rubric. Rubric framed as 'evaluator's instructions'; defeats prompt caching, makes system prompt non-constant per-call. | |

**User's choice:** Rubric in user content, system prompt is fixed
**Notes:** Pinned explicitly so the planner doesn't need to re-ask — sub-question of D-05/D-07.

---

## Claude's Discretion

The user passed on these areas — captured in CONTEXT.md `<decisions>` "Claude's Discretion" section:

- `httpx.AsyncClient` lifecycle — one client per `OllamaJudge`, owned via `AsyncExitStack`
- `OllamaJudge.__init__` signature — `(base_url, model, timeout_seconds)` mirroring Phase 2 D-08
- System prompt template literal text — planner picks within D-07 constraints, starting from spec template
- Phase 3 unit-test scope — parser slices (`<think>` strip, malformed JSON, brace-recovery, score-out-of-range, missing field) + request-body shape helper
- Where the body-shape helper lives — module-level function vs method (planner's call)
- `<think>` regex pattern — `re.compile(r"<think>.*?</think>", re.DOTALL)` suggested
- Logging policy — named logger at DEBUG only; full content gated on `--log-cli-level=DEBUG`

## Deferred Ideas

Captured in CONTEXT.md `<deferred>` section:

- Agentic tool-use judge (SEED-001) — stays dormant for MVP
- Typed `JudgeContext` model — rejected per D-05; reconsider only if Phase 4 shows brittleness
- `OllamaJudge.from_config(cfg: OllamaConfig)` classmethod — add only if Phase 4 fixture finds positional wiring painful
- `OllamaJudge.warmup()` explicit method — rejected per D-08; cheap to retrofit if _preflight wants it
- JSON Schema as `format` value — rejected for Phase 3 (ROADMAP locks `format: json` literally)
- Best-of-N judge consensus / re-prompt-on-malformed — out of scope per PROJECT.md
- Calibration / golden-set for the judge — out of scope per REQUIREMENTS.md
- `JUDGE_FIRST_CALL_TIMEOUT_SECONDS` separate env var — rejected (single 120s ceiling locked)
- Richer `<think>`-style filtering — extend regex if/when other reasoning markup appears
