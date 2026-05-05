# Phase 3: Ollama Judge - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Ship a working `OllamaJudge` that returns a validated `JudgeResult` from the live Ollama at `127.0.0.1:11434`, defends against qwen3 thinking quirks and cold-start, and exposes the `Judge` Protocol seam so post-MVP backends (including SEED-001's agentic backend) can slot in without rewrites.

**In scope:**
1. `src/mcp_test_framework/judge_protocol.py` — defines `Judge` Protocol with one async method `judge(rubric: str, subject: str, context: dict | None = None) -> JudgeResult`. Phase 4 fixtures and tests type-annotate against `Judge`, not the concrete class.
2. `src/mcp_test_framework/ollama_judge.py` — concrete `OllamaJudge` implementing the Protocol via `httpx.AsyncClient` POSTing to Ollama `/api/chat`. Locked request body: `stream:false`, `format:json`, `think:false`, `temperature:0`, `num_predict:256`, `keep_alive:"30m"`. Locked timeout: `httpx.Timeout(120, connect=10)`.
3. `JudgeResult` Pydantic model in `ollama_judge.py` (domain-local, paralleling `ValidationIssue` in `schema_validator.py` and `ToolNotFoundError` in `mcp_client.py`): `passed: bool`, `score: int (1..5)`, `reasoning: str`, `raw_response: str`. `1 <= score <= 5` enforced via `Field(ge=1, le=5)`.
4. Defensive response parser: strips `<think>...</think>` blocks before JSON parse, validates the three required fields, falls back to a `passed=False` `JudgeResult` with the raw response preserved when parse or shape validation fails.
5. Constant system prompt template (strict-evaluator + `/no_think` + JSON-only contract + delimited subject block); rubric, subject, and context fields injected as user-message content (D-05).
6. Permanent live smoke test at `tests/smoke/test_smoke_ollama_judge.py` gated behind a new `live_ollama` marker that satisfies success criteria #1 (Protocol defined) and #2 (cold-start path returns valid JudgeResult). Canned synthetic subject — no coupling to homelab-mcp.
7. `pyproject.toml` updates: register the `live_ollama` marker; expand `addopts` to skip both live markers (`addopts = "-m 'not live_homelab and not live_ollama'"`).

**Not in scope (other phases):**
- Pytest fixtures consuming `OllamaJudge` — Phase 4 FIX-01 (session-scoped `judge` fixture).
- The `_preflight` fixture and its warmup call — Phase 4 FIX-02. Phase 3 deliberately ships no warmup logic in `OllamaJudge` (D-04).
- Any test rubric (TEST-05/06/07) — Phase 4. The smoke test exercises a canned synthetic subject only; the three real description-quality rubrics are Phase 4 territory.
- KeyboardInterrupt cleanup at the CLI surface — Phase 5 OPS-03.
- README documenting the cold-start behavior — Phase 5 DOCS-01.
- Any agentic-judge work — SEED-001 stays dormant (D-01).

</domain>

<decisions>
## Implementation Decisions

### SEED-001 disposition (rubric vs agentic)

- **D-01:** Phase 3 ships rubric-only as scoped in ROADMAP / REQUIREMENTS / spec. SEED-001 (replace rubric with agentic tool-use loop) stays dormant for the MVP. Rationale: phase title is "Ollama Judge" and the locked success criteria all describe the rubric-style judge; pivoting now would invalidate ROADMAP SC#1–5, REQUIREMENTS CORE-04, the canonical spec, and Phase 4's three rubric tests. The `Judge` Protocol seam (CORE-04, SEED-001 trigger note) is the architectural enabler that makes a future agentic backend a 1-file addition rather than a rewrite — it ships in Phase 3 exactly as planned. SEED-001 should re-surface in a future phase or post-MVP milestone (e.g., `/gsd-new-milestone` for "pluggable judge backends" or "tool-use evaluation").

### Live smoke test shape

- **D-02:** The Phase 3 cold-start smoke is a **permanent pytest test** at `tests/smoke/test_smoke_ollama_judge.py` — NOT a throwaway script under `scripts/`. The ROADMAP wording ("throwaway smoke script") is overridden the same way Phase 2 D-01 overrode it. Rationale: live smoke tests have ongoing value (cold-start regression coverage, post-Ollama-upgrade verification, pluggable-backend cross-checks), and the framework already has the marker pattern from Phase 2.
- **D-03:** Marker convention: `@pytest.mark.live_ollama`. Any test with this marker requires reachable Ollama at the configured `OLLAMA_BASE_URL` and the configured model in `/api/tags`; missing → test fails fast inside the test body (consistent with Phase 2 D-02). Register in `pyproject.toml`:
  ```toml
  markers = [
    "live_homelab: requires homelab-mcp runnable via uvx (or on PATH)",
    "live_ollama: requires reachable Ollama at OLLAMA_BASE_URL with the configured model",
  ]
  addopts = "-m 'not live_homelab and not live_ollama'"
  ```
  Default `uv run pytest` skips both live markers; `uv run pytest -m live_ollama` runs Ollama smoke only; `uv run pytest -m ''` runs everything.
- **D-04:** Smoke test subject is a **canned synthetic** description hard-coded in the test (e.g., a plausible MCP tool with a 1-paragraph description and a parameter or two). Rationale: keeps Phase 3 smoke independent of `homelab-mcp` plumbing — `live_ollama` and `live_homelab` are orthogonal markers, and one failing should not be ambiguous about the other. The smoke test must cover BOTH ROADMAP success criteria #1 and #2:
  - SC#1 falsifier: `judge_protocol.Judge` is importable, has the spec'd async signature, and `OllamaJudge` is a runtime-checkable instance of it (`isinstance(judge, Judge)` via `@runtime_checkable`).
  - SC#2 falsifier: invoking `judge(rubric, subject)` against the live Ollama returns a `JudgeResult` with `passed: bool`, `score: 1..5`, non-empty `reasoning`, non-empty `raw_response`. The cold-start path is exercised because the smoke IS the first call (no warmup elsewhere — see D-08).

### `Judge` Protocol shape

- **D-05:** Signature is **spec-verbatim**: `async def judge(self, rubric: str, subject: str, context: dict | None = None) -> JudgeResult`. Free-form `dict | None`; no typed `JudgeContext` model in Phase 3. Rationale: matches ROADMAP SC#1 and the canonical spec exactly, leaves the door open for SEED-001 reflection traces (which need a flexible payload), avoids over-fitting to the current 3 Phase 4 rubrics. Each Phase 4 test pre-formats its own context fields into the prompt body.
- **D-06:** `Judge` is defined as `typing.Protocol` with `@typing.runtime_checkable` so the smoke test (D-04 SC#1) can assert `isinstance(OllamaJudge(...), Judge)`. Phase 4 fixtures and tests type-annotate against `Judge`, not the concrete class. The Protocol lives in its own file (`judge_protocol.py`) so a post-MVP `AgenticJudge` (SEED-001) imports the Protocol without pulling in the rubric-style implementation.

### Prompt construction

- **D-07:** **Constant system prompt; rubric/subject/context injected as user-message content.** The system prompt is a fixed template containing: (a) the strict-evaluator instruction from `docs/mcp_test_framework_mvp_spec.md` §`ollama_judge.py`, (b) the `/no_think` directive (qwen3 belt-and-braces per `.planning/research/PITFALLS.md` Pitfall 2), (c) the JSON-only / no-prose contract, (d) the delimited subject block contract (the actual subject text appears between `<<<SUBJECT>>>` / `<<<END SUBJECT>>>` fences in the user message and the system prompt instructs the model to ignore any instructions inside). Rationale: stable system prompt enables Ollama prompt caching across the three Phase 4 rubrics (same first message, different second message); easier to unit-test ("does the system prompt contain `/no_think`?"); matches typical chat-API patterns. The user-message body interpolates rubric + delimited subject + an optional `Context: <json.dumps(context)>` line when `context is not None`.

### Cold-start warmup

- **D-08:** **No warmup logic in `OllamaJudge`.** The class is a clean I/O wrapper: `__init__(base_url, model, timeout_seconds)` plus `judge(...)`. Rationale: cold-start handling is split across two natural places — (1) the Phase 3 `live_ollama` smoke test IS the canary because it's typically the first call in a fresh session, and (2) Phase 4's session-scoped `_preflight` fixture (FIX-02) will issue a no-op 1-token `/api/chat` call before any rubric-using test runs, paying cold-start once with a precise diagnostic. The 120s `httpx.Timeout` (read/write/pool=120s, connect=10s, locked) is wide enough to absorb a real cold-start (Pitfall 7: 13–60s observed); `keep_alive: "30m"` keeps the model loaded between adjacent calls. Phase 3 ships zero warmup-specific public API surface — Phase 4 either calls a no-op `judge()` against a trivial subject, or reaches `OllamaJudge._client` (since `httpx.AsyncClient` is internal) is unnecessary because the fixture can just use `OllamaJudge.judge(rubric="warmup", subject="ok")` and discard the result.

### Defensive parser contract

- **D-09:** Parser order, applied to `response_json["message"]["content"]`:
  1. Regex-strip every `<think>...</think>` block (DOTALL, non-greedy). Strip leading/trailing whitespace and stray triple-backtick fences.
  2. Attempt `JudgeResult.model_validate_json(stripped)`.
  3. If step 2 raises `ValidationError` or `JSONDecodeError`: search for the first `{` ... matching `}` substring (brace counter, not regex) and re-attempt `model_validate_json` on it.
  4. If step 3 still fails: return `JudgeResult(passed=False, score=1, reasoning="malformed judge response", raw_response=<full original message content>)`. Preserve the raw_response so the test failure surfaces what the model actually said.
- **D-10:** A request- or transport-level failure (HTTP non-2xx, `httpx.TimeoutException`, connection refused) **propagates** as the underlying exception. It does NOT collapse to a `passed=False` JudgeResult — the rationale is that Pitfall 3 (session-fixture cascade) and OPS-01 want test-level failures with raw_response visible, not silent transport-level swallowing that could mask "Ollama is down" as "this rubric failed." Phase 4's per-test `pytest.fail(...)` formatting decides how the exception surfaces in the diagnostic. (OPS-01 fulfillment is split: malformed-JSON path = D-09 fallback path; timeout/HTTP path = bubbles up, Phase 4 surfaces.)

### Claude's Discretion

The user passed on these areas — planner/executor has flexibility within the constraints below:

- **`httpx.AsyncClient` lifecycle:** One client per `OllamaJudge` instance (per Pitfalls "Re-creating httpx.AsyncClient per call"). Owned via `contextlib.AsyncExitStack` inside `OllamaJudge.__aenter__` / `__aexit__` so the judge can be used as an async context manager and the client is disposed deterministically. Phase 4's session-scoped `judge` fixture wires the lifecycle.
- **`OllamaJudge.__init__` signature:** `(base_url: str, model: str, timeout_seconds: int)` — mirrors `McpTestClient(command, args, timeout_seconds)` from Phase 2 D-08. Phase 4 fixture wires `OllamaJudge(cfg.ollama.base_url, cfg.ollama.model, cfg.ollama.timeout_seconds)`. A `from_config(cfg: OllamaConfig)` classmethod can be added later if a fixture wants it (parallel to the Phase 2 deferred idea); not added preemptively.
- **System prompt template literal text:** The planner picks the exact wording within the constraints in D-07 (must include `/no_think`, JSON-only contract, strict-evaluator framing, delimited-subject contract). Use the spec's template (§`ollama_judge.py`) as the starting point.
- **Phase 3 unit-test scope:** `tests/unit/test_ollama_judge.py` covers parser slices that are mock-friendly: `<think>`-strip happy path, malformed-JSON fallback, brace-extraction recovery, score-out-of-range fallback, missing-field fallback. Live HTTP behavior is covered by `tests/smoke/test_smoke_ollama_judge.py` — no `httpx.AsyncClient` mocking for "the request body had `stream: false`"; instead, a unit test on a pure helper that builds the request body asserts the body shape (decoupled from the HTTP layer).
- **Where the body-shape helper lives:** Inside `ollama_judge.py` as a module-level `_build_request_body(model, system_prompt, user_content)` function (or method on `OllamaJudge`). The unit-test can import it directly. This is the planner's call — both shapes are fine.
- **`<think>` regex pattern:** `re.compile(r"<think>.*?</think>", re.DOTALL)` is the suggested form. If qwen3 emits unbalanced or self-closing think tags, the brace-recovery in D-09 step 3 catches the rest.
- **Logging policy:** Per Pitfalls "Logging full Ollama responses verbosely by default" — the judge does NOT log the full Ollama response by default. A `logging.getLogger("mcp_test_framework.ollama_judge")` named logger emits a `DEBUG`-level record with the request body shape (model, message length, options) and a `DEBUG` record with the response shape (length, parser path taken). Full content only at `DEBUG`. Pytest's `--log-cli-level=DEBUG` surfaces them when needed.
- **No `homelab_mcp` import anywhere in this phase's deliverables:** Phase 1's two-layer guard (ruff TID251 + `tests/conftest.py` `sys.modules` scan) catches violations mechanically. No additional measures needed.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents (researcher, planner) MUST read these before planning Phase 3.**

### Phase 3 source-of-truth specs
- `docs/mcp_test_framework_mvp_spec.md` §`ollama_judge.py` (lines ~139–183) — `OllamaJudge` public interface, `JudgeResult` Pydantic model, system prompt template. Locked. The only deviation from spec wording is D-09 (brace-recovery + missing-field fallback specifics).
- `docs/mcp_test_framework_mvp_spec.md` §Implementation Notes for Claude Code — `stream: false`, `format: json`, `--verbose` / `LOG_LEVEL=DEBUG` gating for response logging.
- `.planning/REQUIREMENTS.md` §Core Modules CORE-04 — `Judge` Protocol + `OllamaJudge` falsifiable acceptance. §Operational OPS-01, OPS-02. §Documentation DOCS-03.
- `.planning/ROADMAP.md` §Phase 3 — Goal statement and the 5 success criteria the verifier will check. The locked request-body parameters (`stream:false`, `format:json`, `think:false`, `temperature:0`, `num_predict:256`, `keep_alive:"30m"`) and `httpx.Timeout(120, connect=10)` come from this section.

### Project-wide constraints
- `.planning/PROJECT.md` §Constraints, §Key Decisions, §Out of Scope — Black-box principle (no `import homelab_mcp` anywhere), Ollama at `127.0.0.1:11434` with `qwen3.6:latest`, `Judge` Protocol seam ships in MVP for post-MVP backend swap, pluggable judge backends out of scope for MVP.
- `.planning/STATE.md` §Accumulated Context > Decisions — Config precedence, `_BareNameNestedEnvSource` pattern, `AliasChoices`+`populate_by_name`. Phase 3 does not introduce new env vars (Ollama config already covered by Phase 1's `OllamaConfig`).
- `CLAUDE.md` §Tooling, §Architecture Notes, §Module Layout — restated invariants.

### Phase 1 prior decisions Phase 3 inherits
- `.planning/phases/01-foundation-pure-data-core/01-CONTEXT.md` — `OllamaConfig` already shipped (`base_url`, `model`, `timeout_seconds`); Phase 3 consumes it, does NOT extend it. Frozen sub-model + `populate_by_name=True` + `AliasChoices` pattern is the inherited convention.
- `.planning/phases/01-foundation-pure-data-core/01-LEARNINGS.md` — Lesson on silent-default-fallback for new env vars; not directly relevant since Phase 3 adds none, but the discipline (any new env var needs a precedence test) applies if a deviation surfaces during planning.

### Phase 2 prior decisions Phase 3 mirrors
- `.planning/phases/02-mcp-client-wrapper/02-CONTEXT.md` D-01..D-04 — Live integration tests as committed pytest tests under `tests/smoke/` with marker + `addopts` skip. **Phase 3's `live_ollama` is the direct analog to Phase 2's `live_homelab`; the marker registration and `addopts` line MUST be updated in lockstep (D-03).**
- `.planning/phases/02-mcp-client-wrapper/02-CONTEXT.md` Claude's Discretion — Constructor signature pattern (`McpTestClient(command, args, timeout_seconds)`); `OllamaJudge(base_url, model, timeout_seconds)` mirrors it. `AsyncExitStack`-owned client lifecycle pattern; same here.

### Pitfalls research (mandatory pre-implementation read)
- `.planning/research/PITFALLS.md` Pitfall 2 — qwen3 thinking tokens corrupting `format: json`. Drives D-07 (`/no_think` in system prompt) and D-09 (`<think>` strip + brace-recovery). `temperature: 0` and `num_predict: 256` are part of this mitigation; both are locked in ROADMAP SC#2.
- `.planning/research/PITFALLS.md` Pitfall 3 — Session-fixture cascade. Drives D-10 (transport-level errors propagate; do NOT collapse to JudgeResult).
- `.planning/research/PITFALLS.md` Pitfall 5 (judge as ground truth) — Threshold ≥4 reasonable for MVP; flag score-of-5 in test diagnostics. Phase 4 territory but informs the Phase 3 raw_response preservation policy.
- `.planning/research/PITFALLS.md` Pitfall 7 — Cold-start timeout. Drives D-08 (no warmup in OllamaJudge; rely on the locked 120s timeout + `keep_alive: "30m"`; cold-start exercised by the smoke test itself).
- `.planning/research/PITFALLS.md` `/api/chat` streaming default — Drives the `stream: false` lock and the suggested unit-test for the request-body helper.

### Stack research
- `.planning/research/STACK.md` — `httpx 0.28+` async client (already locked Phase 1); `pydantic 2.x` `model_validate_json` for JudgeResult; pinned versions in `uv.lock`.

### Seeds (informational, not Phase 3 deliverables)
- `.planning/seeds/SEED-001-agentic-tool-use-judge.md` — **Trigger fired this phase.** Per D-01, the seed stays dormant for the MVP and surfaces again post-Phase-3 / post-MVP. The `Judge` Protocol seam in `judge_protocol.py` is the architectural enabler that makes germinating this a 1-file addition. No Phase 3 work changes because of it.
- `.planning/seeds/SEED-002-tool-level-parallelism-xdist.md` — Out of Phase 3 scope; Phase 4 fixture review checks compatibility.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/mcp_test_framework/models.py` `OllamaConfig` (`base_url`, `model`, `timeout_seconds: int = 120`) — already shipped Phase 1. Phase 3 consumes it via `OllamaJudge(cfg.ollama.base_url, cfg.ollama.model, cfg.ollama.timeout_seconds)`. No edits to `models.py` this phase.
- `src/mcp_test_framework/config.py` `_BareNameNestedEnvSource` — Phase 3 adds no new env vars, so no change needed. `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS` already route correctly.
- `tests/conftest.py` — `pytest_configure` hook scans `sys.modules` for `homelab_mcp` at session start (Phase 1 01-04). Catches accidental imports from `ollama_judge.py` mechanically; no additional guard.
- `pyproject.toml` `[tool.pytest.ini_options]` `markers = […]` and `addopts` lines — Phase 3 only adds the `live_ollama` marker registration and expands the `addopts` filter expression (D-03).
- `tests/smoke/test_smoke_homelab_mcp.py` (Phase 2 deliverable) — Reference shape for the new `tests/smoke/test_smoke_ollama_judge.py`. Same marker pattern, fail-fast diagnostic on missing live dependency, falsifies both phase-level success criteria.
- `tests/_fixtures/` (Phase 1 convention) — established location for malformed-input fixtures if Phase 3's parser unit tests want a `.txt` corpus of qwen3-style malformed JSON samples (planner's call).

### Established Patterns (from Phases 1 and 2)
- Pydantic v2 `BaseModel` with `ConfigDict(frozen=True, populate_by_name=True)` for cross-cutting models — `JudgeResult` is domain-local so frozen is optional but recommended (immutable result records). Use `Field(ge=1, le=5)` for the score bound.
- Domain-local exceptions and result types live in their owning module (`ToolNotFoundError` / `JudgeResult` pattern). `JudgeResult` lives in `ollama_judge.py`; the `Judge` Protocol lives in its own `judge_protocol.py` (per CORE-04 wording and the SEED-001 separation point).
- All public APIs that touch I/O are async — `OllamaJudge.judge` is async, mirrors `McpTestClient.list_tools/call_tool` shape.
- Permanent live smoke tests under `tests/smoke/` with `live_<thing>` markers + `addopts` skip — Phase 2 D-01/D-02/D-03; Phase 3 follows this verbatim.
- One `httpx.AsyncClient` per long-lived component, lifecycle via `AsyncExitStack` — Phase 2 `McpTestClient` ownership pattern; `OllamaJudge` mirrors.
- Spec-verbatim bare env var names (no `MCPTF_` prefix) — Phase 3 adds none.

### Integration Points
- `OllamaJudge` is consumed by Phase 4 fixture FIX-01 (`judge` session-scoped). Phase 3 ships the constructor that takes `(base_url, model, timeout_seconds)` — Phase 4 wires it.
- Phase 4 FIX-02 (`_preflight` fixture) issues the no-op warmup call against `OllamaJudge.judge(...)` to pay cold-start once per session. Phase 3 ships no warmup-specific API; the fixture can either call `judge` with a trivial subject or check `/api/tags` separately and skip a warmup call entirely.
- Phase 4 TEST-05/06/07 (description-quality rubrics) each call `judge(rubric, subject, context)` with a different rubric and pass `score >= 4`. The constant system prompt (D-07) is shared; rubric and per-test context fields are user-message content.
- `tests/smoke/test_smoke_ollama_judge.py` provides the Phase 3 cold-start canary; running it after `ollama stop qwen3.6:latest` is the Phase 3 verifier's manual UAT analog (parallel to the Phase 2 02.1-style human-UAT pattern, if the verifier elects to capture cold-start output).
- `live_ollama` marker semantics extend naturally to any future test that hits live Ollama. Phase 4's three rubric tests all carry the marker; same `addopts` skip behavior.

</code_context>

<specifics>
## Specific Ideas

- "Permanent live smoke under `tests/smoke/` with marker — not throwaway" was the user's pick, mirroring the Phase 2 D-01 decision. ROADMAP SC#2 wording ("throwaway smoke script") is overridden the same way Phase 2 overrode it — the override is a project-wide pattern by this point.
- "Canned synthetic subject in the smoke test" was the user's pick — orthogonality of `live_ollama` and `live_homelab` markers is the load-bearing reason; one failing should not be ambiguous about the other.
- "Free-form `dict | None` context, spec-verbatim" was the user's pick over a typed `JudgeContext` model. The flexibility intentionally keeps SEED-001's reflection-trace payload doable without a Phase 3 model migration.
- "No warmup in OllamaJudge, defer to Phase 4 _preflight" was the user's pick over baking warmup into the judge. Keeps `OllamaJudge` a clean I/O wrapper.
- "Constant system prompt; rubric in user content" was the user's pick over per-call system-prompt rebuilding. Prompt caching + testability + consistent shape across the three Phase 4 rubrics drive the choice.
- The 120s `httpx.Timeout` is a CEILING, not a target — successful judge calls return in seconds; 120s is the "Ollama is loading from cold or hung" bound (parallel to Phase 2's "30s ceiling" framing on `mcp_server.timeout_seconds`). Update Phase 5 README to say so.

</specifics>

<deferred>
## Deferred Ideas

- **Agentic tool-use judge (SEED-001)** — Per D-01, stays dormant for the MVP. Re-surfaces after Phase 3 lands or in a future "pluggable judge backends" / "tool-use evaluation" milestone. The `Judge` Protocol seam (`judge_protocol.py`) is the architectural enabler that ships in Phase 3 specifically so this is a 1-file addition, not a rewrite.
- **Typed `JudgeContext` model** — Rejected per D-05 (free-form `dict | None` is spec-verbatim and SEED-001-friendly). Reconsider only if Phase 4 reveals concrete brittleness — e.g., three rubrics duplicating the same `tool_name` / `tool_description` packing logic, where a typed wrapper would dedupe.
- **`OllamaJudge.from_config(cfg: OllamaConfig)` classmethod** — Constructor signature is positional `(base_url, model, timeout_seconds)` per D-claude-discretion. If Phase 4's `judge` fixture finds the three positional args painful to wire, add the classmethod then — paralleling the Phase 2 deferred idea on `McpTestClient.from_config`.
- **`OllamaJudge.warmup()` explicit method** — Rejected per D-08 (no warmup logic in the judge). If Phase 4's `_preflight` fixture turns out to want a clearer explicit call site than `judge(rubric="warmup", subject="ok")`, add `warmup()` as a public method then. Cheap to retrofit.
- **JSON Schema as `format` value** (instead of `format: "json"`) — Ollama supports passing a JSON Schema as `format` to constrain the response shape, not just "valid JSON". Rejected for Phase 3 because: (a) ROADMAP SC#2 locks `format: json` literally, (b) qwen3 has known issues even with JSON Schema constrained output (Pitfall 2), (c) the Pydantic-validate fallback chain (D-09) handles shape drift defensively. Plant Seed if a future eval shows the defensive parser is materially flaky on real rubrics.
- **Best-of-N judge consensus / re-prompt-on-malformed** — Out of scope per PROJECT.md / REQUIREMENTS.md. Single-shot only for MVP. The malformed-response path (D-09 step 4) returns a failed `JudgeResult` rather than retrying; Phase 4 tests fail loudly with `raw_response` visible. Revisit only if single-shot proves materially flaky on real rubrics.
- **Calibration / golden-set for the judge** — Out of scope per REQUIREMENTS.md "Out of Scope". Mentioned only to record that Phase 3 deliberately does not derive thresholds from labeled data.
- **`JUDGE_FIRST_CALL_TIMEOUT_SECONDS` separate env var** — Pitfall 7 mentions distinguishing first-call from steady-state timeouts. Rejected for Phase 3 (single 120s ceiling is locked in ROADMAP SC#4). If users observe persistent first-call failures even with `keep_alive: "30m"`, add the second knob then; would mirror the Phase 2 "per-call timeout knobs" deferred idea.
- **Richer `<think>`-style filtering** — D-09 strips `<think>...</think>` plus brace-recovery. If qwen3 (or a future model) emits other reasoning markup (e.g., `<reasoning>`, `<plan>`), extend the strip regex then. Don't over-engineer Phase 3 for hypothetical markup.

</deferred>

---

*Phase: 03-ollama-judge*
*Context gathered: 2026-05-05*
