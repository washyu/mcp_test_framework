# Phase 4: Fixtures & Test Cases - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the framework's session-scoped pytest-asyncio fixtures together and ship the spec's 10 test cases against `homelab-mcp` / `list_registered_servers`, so `uv run pytest tests/` produces a green run end-to-end (schema → call → judge).

**In scope:**
1. `src/mcp_test_framework/fixtures.py` — defines all framework fixtures (`config`, `mcp_client`, `judge`, `target_tool`, `_preflight`, `rubric_clarity`, `rubric_disambiguation`, `rubric_parameters`). All session-scoped; `mcp_client` and `judge` own their I/O lifecycle via `contextlib.AsyncExitStack`. `judge` is type-annotated as `Judge` Protocol (Phase 3 D-06), instantiates `OllamaJudge` internally.
2. `src/mcp_test_framework/rubrics.py` — `Rubric(BaseModel)` base class containing the shared hardening preamble (anti-verbosity clause + delimited-subject reinforcement + 1–5 score-anchor template). Three concrete subclasses (`ClarityRubric`, `DisambiguationRubric`, `ParametersRubric`) each fill in dimension-specific criteria. `__str__` composes the final prompt. Users extend by subclassing.
3. `tests/conftest.py` — adds `pytest_plugins = ["mcp_test_framework.fixtures"]` so the framework fixtures auto-load. The existing Phase 1 `pytest_configure` black-box guard stays untouched.
4. `tests/test_homelab_list_registered_servers.py` — all 10 spec'd tests, **unmarked**:
   - Category 1 (deterministic): TEST-01 (target tool exists), TEST-02 (`validate_tool_schema` returns no errors), TEST-03 (description ≥20 chars), TEST-04 (every input parameter has description + type).
   - Category 2 (LLM-judged, `score >= 4`): TEST-05 clarity, TEST-06 disambiguation, TEST-07 parameters-self-explanatory.
   - Category 3 (deterministic): TEST-08 (`{}` call returns non-error), TEST-09 (`CallToolResult` has ≥1 content block OR non-null `structuredContent`), TEST-10 (≥1 TextContent block parses as JSON; if `structuredContent` and `outputSchema` both present, validate via `Draft202012Validator`).
5. `_preflight` fixture (FIX-02) — three checks before any test starts:
   - Ollama: `GET /api/tags` returns 200 within ~10s AND configured model is in `models[].name`.
   - MCP: `shutil.which(mcp_server.command)` returns non-None AND a brief `McpTestClient` session opens, `list_tools()` succeeds, then closes (single subprocess spawn for verification).
   - Target tool: configured `target.tool_name` is in the returned tool list.
   On any failure → `pytest.exit(precise_diagnostic, returncode=2)`. The `mcp_client` fixture afterward respawns its own long-lived session.
6. `target_tool` fixture (FIX-03) — calls `mcp_client.get_tool(cfg.target.tool_name)`, raises `ToolNotFoundError` (Phase 2) if missing. Defense in depth alongside preflight's check.

**Not in scope (other phases):**
- Typer CLI (`run`, `list-tools`, `version`) — Phase 5 CLI-01/02/03.
- KeyboardInterrupt cleanup at the CLI surface — Phase 5 OPS-03.
- README — Phase 5 DOCS-01.
- Best-of-N judge consensus, rubric calibration, or position-randomization — explicit out of scope per REQUIREMENTS.md.
- Warmup judge call inside `_preflight` — deferred (see Deferred Ideas).
- Any new env vars — none added this phase; all configuration already shipped Phase 1.
- LLM-generated test inputs (SEED-001/v2 GEN-01) — out of MVP.

</domain>

<decisions>
## Implementation Decisions

### Test markers + default-skip

- **D-markers-1:** Phase 4's 10 tests carry **NO markers**. The framework requires both MCP and Ollama to function — they aren't optional. `_preflight` is the gate that detects missing dependencies before any test runs. `tests/smoke/test_smoke_homelab_mcp.py` and `tests/smoke/test_smoke_ollama_judge.py` keep their existing `live_homelab` / `live_ollama` markers (they're the per-component canaries; Phase 4 is the integration suite). Rationale: SC#5 says "`pytest tests/` ... discovers and runs all 10" — unmarked tests + preflight matches this verbatim. Marker-gating would force the user to remember `-m ''` and risks a default-skip green run that proves nothing.
- **D-markers-2:** Preflight failure is `pytest.exit(reason, returncode=2)` with a single-line precise diagnostic (e.g., `"Ollama at http://127.0.0.1:11434 not reachable: ConnectError"` / `"model 'qwen3.6:latest' not in /api/tags (available: [...])"` / `"MCP command 'homelab-mcp' not found on PATH"`). Returncode 2 distinguishes preflight-abort from pytest's regular pass/fail (0/1) so a future CI can branch on it. No ERROR cascade across 10 tests (Pitfall 3 mitigation).
- **D-markers-3:** Phase 5 CLI's `mcp-test-framework run` invokes `pytest.main([test_dir, *user_flags])` with **no extra `-m` flag**. The default `addopts = "-m 'not live_homelab and not live_ollama'"` from `pyproject.toml` stays in effect, which keeps the smoke tests opt-in. Phase 4's unmarked tests run by default. Anyone running `uv run pytest tests/` directly gets the same behavior — symmetric.

### Rubrics + judge call shape

- **D-rubrics-1:** Three session-scoped pytest fixtures (`rubric_clarity`, `rubric_disambiguation`, `rubric_parameters`) defined in `src/mcp_test_framework/fixtures.py`. Tests `async def test_description_clarity(judge, target_tool, rubric_clarity): ...`. Users override individual rubrics by defining same-name fixtures in their own conftest (pytest's nearest-conftest wins); add new rubric-based tests by adding new rubric fixtures + test functions; remove rubric tests by skipping them at the test level — the framework rubric module stays untouched.
- **D-rubrics-2:** `Rubric(BaseModel)` base class in `src/mcp_test_framework/rubrics.py` with shared hardening (anti-verbosity clause per Pitfall 6 + delimited-subject reinforcement + 1–5 score-anchor template). `ClarityRubric`, `DisambiguationRubric`, `ParametersRubric` subclass it and provide `dimension_criteria` / dimension-specific score anchors. `Rubric.__str__` composes the final prompt (hardening + dimension criteria + anchors). Fixtures yield instances; tests pass `str(rubric_clarity)` to `judge.judge(...)`. Rationale: hardening defined once; new rubric = subclass + override; testable (assert hardening clause present in `str()`).
- **D-rubrics-3:** Per-rubric subject choice. TEST-05 (clarity) and TEST-06 (disambiguation) call `judge.judge(str(rubric), subject=target_tool.description, context={"tool_name": target_tool.name, "inputSchema": target_tool.inputSchema})`. TEST-07 (parameters-self-explanatory) calls `judge.judge(str(rubric_parameters), subject=json.dumps(target_tool.inputSchema, indent=2), context={"tool_name": target_tool.name, "description": target_tool.description})`. Rationale: the SUBJECT block (Phase 3 D-07 delimited fences) holds exactly what's being judged — keeps the prompt-injection mitigation focused, matches spec wording ("with the tool's name, description, and input schema as context").

### `_preflight` fixture shape

- **D-preflight-1:** Three basic checks. (1) Ollama: `GET {ollama.base_url}/api/tags` returns 200 within ~10s AND configured `ollama.model` is in `response["models"][].name`. (2) MCP: `shutil.which(mcp_server.command)` is not None AND a brief `McpTestClient(...).__aenter__` + `list_tools()` succeeds + `__aexit__` closes (single verification spawn). (3) Target tool: configured `target.tool_name` is in the returned tool list. **No LLM warmup call** — cold-start cost is paid by TEST-05 (the first rubric test) under the locked 120s `httpx.Timeout`. Acceptable: failure mode is "first description-quality test takes ≤60s" not "whole suite hangs". Warmup deferred (see Deferred Ideas).
- **D-preflight-2:** Preflight closes its MCP session after validation; the `mcp_client` session-scoped fixture respawns its own long-lived session. Two subprocess spawns per run (~0.5s each on warm OS). Rationale: clean independent ownership — preflight failure aborts the run cleanly without needing to plumb the open handle through `mcp_client`. Keeps each fixture's `AsyncExitStack` chain self-contained.
- **D-preflight-3:** FIX-03 (`target_tool` fixture) keeps its own `mcp_client.get_tool(cfg.target.tool_name)` membership check (which raises `ToolNotFoundError` from Phase 2 with the candidate-tool list in the message). Defense in depth alongside preflight. Cost: one `list_tools()` round-trip the fixture would have made anyway. If preflight ever loosens (e.g., post-MVP warmup-only mode), FIX-03 still fails fast.
- **D-preflight-4:** Preflight failure messages are **structured** — each check produces a one-line diagnostic that names the failed precondition and the configured value (e.g., `"Ollama at {base_url} not reachable: {exc.__class__.__name__}: {exc}"`). The diagnostic goes to `pytest.exit(msg, returncode=2)`. No ERROR cascade.

### Layout: `fixtures.py` + `pytest_plugins`

- **D-layout-1:** All eight fixtures (`config`, `mcp_client`, `judge`, `target_tool`, `_preflight`, `rubric_clarity`, `rubric_disambiguation`, `rubric_parameters`) live in `src/mcp_test_framework/fixtures.py`. `tests/conftest.py` registers them with `pytest_plugins = ["mcp_test_framework.fixtures"]` (added alongside the existing Phase 1 `pytest_configure` black-box guard). Matches the spec's module layout. Post-MVP framework users adopt by adding the same `pytest_plugins` line to their own conftest.
- **D-layout-2:** The `judge` fixture is type-annotated against the `Judge` Protocol from `mcp_test_framework.judge_protocol`, NOT the concrete `OllamaJudge`. Tests use `async def test_x(judge: Judge, ...)`. The fixture body instantiates `OllamaJudge(cfg.ollama.base_url, cfg.ollama.model, cfg.ollama.timeout_seconds)` and yields it inside an `AsyncExitStack`. Phase 3 D-06 / SEED-001 enabler — swapping the concrete backend later is a one-fixture-body change.

### TEST-10 `is JSON` heuristic

- **D-test10-1:** TEST-10 contract: for each `TextContent` block in `result.content`, attempt `json.loads(block.text)`; **at least one block must parse**. If `result.structuredContent is not None` AND `target_tool.outputSchema` is present, validate `structuredContent` against the schema via `jsonschema.Draft202012Validator(schema).validate(structuredContent)`. The test PASSES if (parseable text exists) AND (no structured-content schema violation). Black-box-safe: zero assertions on specific keys or homelab-mcp internals.
- **D-test10-2:** Unparseable text content is a legitimate test failure. The diagnostic surfaces the raw text (`pytest.fail(f"No TextContent block parsed as JSON. content[0].text={...!r}")`). Rationale: machine-actionable MCP tools are expected to return parseable content; if `list_registered_servers` doesn't, that's a real signal worth surfacing — not a test bug to soften with warnings. The verifier's UAT confirms actual tool behavior; if SC#4 doesn't pass deterministically against live `homelab-mcp`, that's a discovery, not a workaround target.

### Claude's Discretion

The user passed on these — planner/executor has flexibility within the constraints below:

- **`config` fixture body:** trivially returns `Config()` (loads env + YAML per Phase 1 precedence). No special handling needed; cached session-scope.
- **Pydantic shape of `Rubric`:** `BaseModel` with `model_config = ConfigDict(frozen=True)` (parallels `JudgeResult` and `OllamaConfig` patterns). Dimension criteria and score anchors as fields, the hardening preamble as a class attribute or `@property` on the base. Final composition order is the planner's call as long as `__str__` produces a single coherent prompt with hardening preceding dimension criteria.
- **Score anchors wording:** Each subclass picks its own 1–5 anchors. Anti-verbosity language goes in the BASE preamble (single source). Score-of-5 caution (Pitfall 6) lives in the base score-anchor template ("5 = exceptional and rare; default to 4 for clearly-good descriptions").
- **`_preflight` failure ordering:** which check runs first is the planner's call. Recommended order: `which()` → Ollama `/api/tags` → MCP handshake → target-tool membership (cheapest first; abort early on the first failure with that check's diagnostic).
- **TEST-10 multi-block iteration:** if `result.content` has multiple TextContent blocks, the planner picks how to phrase the diagnostic when none parse (e.g., show the first block's text up to N chars, or list all attempts). Just don't truncate so aggressively that the failure is undiagnosable.
- **Rubric's `__str__` shape:** the planner picks the exact section ordering and joining whitespace as long as the final string contains (in order) the hardening preamble, the dimension criteria, and the score anchors. Use double-newline section separators.
- **Test parameterization vs flat:** TEST-05/06/07 stay as three distinct named test functions (matches REQUIREMENTS naming). The shared boilerplate (`assert result.score >= 4, f"...{result.raw_response}..."`) can move into a small helper in the test file or stay inline — planner's call.
- **`list_tools()` cache for FIX-03:** `target_tool` fixture is allowed to call `list_tools()` separately or use a session-scoped cached list — the round-trip cost is negligible at session scope. Don't mock the client.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents (researcher, planner) MUST read these before planning Phase 4.**

### Phase 4 source-of-truth specs
- `docs/mcp_test_framework_mvp_spec.md` §`fixtures.py and conftest.py` (lines ~207–215) — Public fixture surface (`mcp_client`, `judge`, `target_tool`, `config` all session-scoped; `target_tool` fails the run early if absent). Phase 4 also adds `_preflight` (REQUIREMENTS FIX-02) and three rubric fixtures (D-rubrics-1).
- `docs/mcp_test_framework_mvp_spec.md` §Test Cases (lines ~230–256) — All 10 test cases, the `score >= 4` threshold, and the rubric shape ("rubric + tool name/description/inputSchema as context").
- `docs/mcp_test_framework_mvp_spec.md` §Implementation Notes for Claude Code — pytest-asyncio strict mode, `asyncio.timeout` invariants, `stream:false` / `format:json` for Ollama. All inherited from Phases 1–3; restated here for completeness.
- `.planning/REQUIREMENTS.md` §Pytest Fixtures FIX-01/02/03, §Test Cases TEST-01..10 — falsifiable acceptance for every Phase 4 deliverable.
- `.planning/ROADMAP.md` §Phase 4 — Goal statement and the 5 success criteria the verifier will check (`pytest tests/` discovers + runs all 10; `_preflight` fail-fast; FIX-03 early-fail; deterministic Cat 1 + Cat 3; rubric Cat 2 score ≥4; green run zero ERRORs no leftover homelab-mcp.exe).

### Project-wide constraints
- `.planning/PROJECT.md` §Constraints, §Key Decisions, §Out of Scope — Black-box principle (no `import homelab_mcp` anywhere — Phase 1's two-layer guard catches violations mechanically), `score >= 4` MVP threshold, single-shot judge calls, single-tool target.
- `.planning/STATE.md` §Accumulated Context > Decisions — Pytest-asyncio strict + `asyncio_default_fixture_loop_scope=session` (Phase 1 lock), `_BareNameNestedEnvSource` config-source pattern, `AliasChoices`+`populate_by_name` convention. Phase 4 introduces no new env vars.
- `CLAUDE.md` §Tooling, §Architecture Notes, §Module Layout — restated invariants. Phase 4's `fixtures.py` location matches the layout map verbatim.

### Phase 1 prior decisions Phase 4 inherits
- `.planning/phases/01-foundation-pure-data-core/01-CONTEXT.md` — `Config()` shape (frozen sub-models, `OllamaConfig` / `McpServerConfig` / `TargetConfig`); `validate_tool_schema()` for TEST-02; `tests/_fixtures/` convention (not used directly by Phase 4 but established).
- `.planning/phases/01-foundation-pure-data-core/01-LEARNINGS.md` — silent-default-fallback discipline. Phase 4 adds no env vars; the lesson is informational.

### Phase 2 prior decisions Phase 4 mirrors
- `.planning/phases/02-mcp-client-wrapper/02-CONTEXT.md` D-04..D-08 — `McpTestClient(command, args, timeout_seconds)` constructor signature (Phase 4's `mcp_client` fixture wires it via `Config.mcp_server` fields). `ToolNotFoundError` from `mcp_client.py` (D-discretion) is what `target_tool` fixture catches.
- `.planning/phases/02-mcp-client-wrapper/02-CONTEXT.md` D-01..D-03 — `live_homelab` marker pattern + `addopts` skip. Phase 4 deviates: integration tests are unmarked (D-markers-1) because they ARE the framework's reason for existing. Smoke tests retain markers.
- `tests/smoke/test_smoke_homelab_mcp.py` — Reference shape for `tests/test_homelab_list_registered_servers.py` test bodies (config loading, async fixture wiring, `pytest.mark.asyncio(loop_scope="session")` per Pitfall 1).

### Phase 3 prior decisions Phase 4 inherits / extends
- `.planning/phases/03-ollama-judge/03-CONTEXT.md` D-05..D-10 — `OllamaJudge(base_url, model, timeout_seconds)` constructor; `Judge` Protocol seam in `judge_protocol.py`; locked request body (`stream:false`, `format:json`, `think:false`, `temperature:0`, `num_predict:256`, `keep_alive:"30m"`); 120s `httpx.Timeout`; defensive parser fallback to `passed=False` `JudgeResult` with raw_response preserved; transport-level errors propagate.
- `.planning/phases/03-ollama-judge/03-CONTEXT.md` D-08 — "No warmup logic in `OllamaJudge`. Phase 4's session-scoped `_preflight` fixture either calls a no-op `judge()` or skips warmup." → Phase 4 D-preflight-1 picks "skip warmup, defer to post-MVP" (recorded in Deferred Ideas).
- `src/mcp_test_framework/judge_protocol.py` — Phase 4 fixtures and tests type-annotate against `Judge`, not `OllamaJudge` (D-layout-2).
- `tests/smoke/test_smoke_ollama_judge.py` — Reference shape for the rubric-based test calls. Phase 4's three description-quality tests parallel its `OllamaJudge` instantiation pattern but run against the real `target_tool.description` rather than a canned synthetic subject.

### Pitfalls research (mandatory pre-implementation read)
- `.planning/research/PITFALLS.md` Pitfall 1 — anyio cancel-scope teardown. Drives `loop_scope="session"` on every async test + `AsyncExitStack` ownership inside `mcp_client` and `judge` fixtures. Already locked Phase 1; Phase 4 must apply consistently to the new fixture bodies.
- `.planning/research/PITFALLS.md` Pitfall 3 — Session-fixture cascade. Drives `_preflight` fixture (FIX-02) + `pytest.exit(returncode=2)` on failure (D-markers-2 + D-preflight-4); preflight checks ordering + structured single-line diagnostics.
- `.planning/research/PITFALLS.md` Pitfall 4 — Windows ProactorEventLoop subprocess cleanup. Session-scoped event loop already locked Phase 1; Phase 4 verifies no zombie `homelab-mcp.exe` after the green run (SC#1 zero-leftover-processes acceptance).
- `.planning/research/PITFALLS.md` Pitfall 5 — Undetected stdio termination. `asyncio.timeout()` already wraps every SDK call inside `McpTestClient` (Phase 2). Phase 4 inherits.
- `.planning/research/PITFALLS.md` Pitfall 6 — LLM-as-judge biases (verbosity, prompt injection). Drives `Rubric` base class hardening (D-rubrics-2): anti-verbosity clause + delimited-subject reinforcement + score-of-5 caution in score anchors.
- `.planning/research/PITFALLS.md` Pitfall 7 — Cold-start timeout. Phase 4 D-preflight-1 deliberately does NOT warmup (deferred); cold-start cost falls on TEST-05 within the locked 120s `httpx.Timeout`. Warmup is the first post-MVP add if first-test latency becomes a UX issue.
- `.planning/research/PITFALLS.md` Pitfall 8 — Black-box coupling via the backdoor. TEST-10 D-test10-1 is explicitly black-box-safe (try-parse only, no key assertions, optional schema validation only when `outputSchema` is declared).

### Stack research
- `.planning/research/STACK.md` — `pytest 9.0+`, `pytest-asyncio 1.3+` strict, `httpx 0.28+`, `pydantic 2.x`, `jsonschema 4.26+` `Draft202012Validator`. All locked Phase 1 / used by earlier phases.

### Seeds (informational, not Phase 4 deliverables)
- `.planning/seeds/SEED-001-agentic-tool-use-judge.md` — Trigger fired Phase 3 (dormant). Phase 4 keeps the `Judge` Protocol seam load-bearing by typing `judge` fixture against `Judge` (D-layout-2).
- `.planning/seeds/SEED-002-tool-level-parallelism-xdist.md` — Phase 4 fixture review: `mcp_client` is session-scoped (single subprocess per session). xdist parallelism would multiply subprocess count linearly and is incompatible with the current shape; revisit only if/when seed germinates.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/mcp_test_framework/config.py` `Config()` — already loads env + YAML with locked precedence; Phase 4 `config` fixture trivially returns `Config()`.
- `src/mcp_test_framework/models.py` — `OllamaConfig`, `McpServerConfig`, `TargetConfig` already shipped (Phase 1 + 2). Phase 4 reads from them; adds nothing.
- `src/mcp_test_framework/mcp_client.py` `McpTestClient` — `__init__(command, args, timeout_seconds)`, `__aenter__`/`__aexit__`, `list_tools` / `get_tool` / `call_tool`. `ToolNotFoundError(tool_name, available)` raised by `get_tool`. Phase 4 fixtures wire it; `_preflight` uses it briefly; FIX-03 catches `ToolNotFoundError`.
- `src/mcp_test_framework/ollama_judge.py` `OllamaJudge` — `__init__(base_url, model, timeout_seconds)`, `__aenter__`/`__aexit__`, `judge(rubric, subject, context=None)`. Returns `JudgeResult{passed, score, reasoning, raw_response}`. Phase 4 `judge` fixture instantiates it; tests assert `result.score >= 4` with `result.raw_response` in the failure diagnostic.
- `src/mcp_test_framework/judge_protocol.py` `Judge` Protocol — `@runtime_checkable`. Phase 4 fixture + test annotations import this; concrete `OllamaJudge` is never imported by tests.
- `src/mcp_test_framework/schema_validator.py` `validate_tool_schema(tool) -> list[ValidationIssue]` — Phase 4 TEST-02 calls it directly and asserts `len(issues) == 0` (or asserts no `severity="error"`).
- `tests/conftest.py` — Existing Phase 1 `pytest_configure` black-box guard stays. Phase 4 ADDS `pytest_plugins = ["mcp_test_framework.fixtures"]` (D-layout-1). No fixture bodies in this file.
- `tests/smoke/test_smoke_homelab_mcp.py` — Reference for async test shape (`pytestmark = [pytest.mark.asyncio(loop_scope="session")]`, `Config()` loading, `AsyncExitStack` ownership). Phase 4 tests follow the same pytestmark pattern but drop the live_homelab marker.
- `tests/smoke/test_smoke_ollama_judge.py` — Reference for `OllamaJudge` instantiation + `judge.judge()` call shape. Phase 4 tests inherit the `loop_scope="session"` pattern but call against real `target_tool` fields, not a canned synthetic.
- `pyproject.toml` `[tool.pytest.ini_options]` — Existing `markers` table (`live_homelab`, `live_ollama`) and `addopts = "-m 'not live_homelab and not live_ollama'"` stay. Phase 4 adds NO new markers (D-markers-1).

### Established Patterns (from Phases 1–3)
- Pydantic v2 `BaseModel` with `ConfigDict(frozen=True, populate_by_name=True)` for cross-cutting models — applies to the new `Rubric` base + subclasses.
- Domain-local types live in their owning module (`Rubric` and subclasses live in `rubrics.py` not `models.py`, paralleling `JudgeResult` in `ollama_judge.py` and `ToolNotFoundError` in `mcp_client.py`).
- Session-scoped fixtures with `loop_scope="session"`; long-lived I/O components (`McpTestClient`, `OllamaJudge`) own their lifecycle via `AsyncExitStack`.
- Permanent live tests under `tests/smoke/` carry `live_<thing>` markers and are default-skipped via `addopts`. Phase 4 tests are the exception — they're the integration suite, not smoke; they're unmarked and gated by `_preflight` instead (D-markers-1).
- `pytest_plugins = ["..."]` registration in `tests/conftest.py` is the chosen plugin-discovery seam (D-layout-1) — keeps fixtures importable as a Python module rather than locked inside the test directory.
- All public APIs that touch I/O are async; Phase 4 fixtures (`mcp_client`, `judge`, `_preflight`) are async generator fixtures using `@pytest_asyncio.fixture(loop_scope="session")`.

### Integration Points
- Phase 5 CLI `run` command (CLI-01) wraps `pytest.main([test_dir, *user_flags])` — Phase 4's unmarked tests run under whatever default `addopts` are configured; D-markers-3 is the contract.
- Phase 5 CLI `list-tools` command (CLI-02) needs MCP-only access (no judge, no pytest). Phase 4's `mcp_client` fixture is session-scoped and pytest-bound; CLI-02 will instantiate `McpTestClient` directly. The `Config` shape and `McpTestClient` constructor are the shared seams.
- The `target_tool` fixture's `Tool` object is consumed by every test (Cat 1, 2, 3) — its `name`, `description`, `inputSchema`, and `outputSchema` (if declared) feed every assertion.
- Phase 4's three rubric fixtures + `Rubric` base in `rubrics.py` are the user-extensibility seam: dropping in a new `BiasCheckRubric(Rubric)` + `bias_check` fixture + `test_description_bias_check` body lets adopters extend coverage without touching framework code.
- Post-MVP SEED-001 (agentic judge): the `Judge` Protocol seam used by Phase 4's `judge` fixture (D-layout-2) makes swapping in `AgenticJudge` a one-fixture-body change. Phase 4 must NOT import `OllamaJudge` from test modules — only from `fixtures.py`.

</code_context>

<specifics>
## Specific Ideas

- **"The framework requires MCP and Ollama; tests shouldn't be filtered out by markers — preflight should fail fast if deps are missing"** was the user's framing for the marker discussion. Drives D-markers-1 / D-markers-2 / D-preflight-1.
- **"Use a base fixture class with the hardening, derive the three rubric classes from it"** was the user's call for the rubric shape. Drives D-rubrics-2 (base `Rubric(BaseModel)` + three subclasses) — keeps hardening defined once and lets adopters subclass for new rubrics.
- **"Add to tests as fixtures, defined in a Python file, so someone can extend the framework with other tool-quality fixtures or remove them from tests if needed"** was the user's framing for rubric placement. Drives D-rubrics-1 (rubrics-as-fixtures in `src/mcp_test_framework/fixtures.py`) + D-layout-1 (`pytest_plugins` registration).
- **"Do basic checks; revisit warmup as a post-MVP add — don't lose it"** drives D-preflight-1 + the explicit Deferred Ideas entry preserving the warmup design intent with a clear trigger condition.
- The `pytest.exit(returncode=2)` choice for preflight failure aligns with pytest's own semantics (0=pass, 1=fail, 2=usage error / collection error / interrupted) — CI tooling can branch on returncode without parsing stderr.

</specifics>

<deferred>
## Deferred Ideas

- **Warmup judge call in `_preflight`** — User explicitly flagged this as post-MVP. Add `await judge.judge("warmup", "ok")` (or a dedicated `warmup()` method on `OllamaJudge`) after the `/api/tags` reachability check so cold-start cost is paid in the named preflight fixture rather than leaking into TEST-05's wall-clock time. Trigger: when first-test cold-start latency surfaces as a CLI UX issue ("first run takes 60s, subsequent runs are fast"). Phase 3 D-08 already noted the deferred shape; this re-records it explicitly so post-MVP work doesn't lose the design intent.
- **`OllamaJudge.warmup()` explicit method** — Phase 3 deferred this. Re-deferred here. If Phase 4's preflight ends up calling `judge.judge("warmup", "ok")` and the planner finds the trivial-args pattern noisy, add `OllamaJudge.warmup()` as a public method then. Cheap retrofit.
- **xdist tool-level parallelism (SEED-002)** — `mcp_client` is session-scoped (single subprocess per session). Parallelizing tests across xdist workers would multiply subprocess count and require either per-worker MCP servers or a shared MCP server with appropriate concurrency. Not blocked by Phase 4; revisit in a future "scale" phase.
- **Best-of-N judge consensus / score-of-5 anti-bias** — Out of scope per REQUIREMENTS.md. Single-shot is locked. The `Rubric` base class score-anchor template warns against score-of-5 (Pitfall 6 mitigation), but the test still passes at 5 — the warning surfaces in `result.reasoning` for human review.
- **Calibration / golden-set for the judge** — Out of scope per REQUIREMENTS.md "Out of Scope". Mentioned only to record that Phase 4 deliberately ships no labeled-data threshold derivation.
- **`mcp-test-framework list-tools` reusing `_preflight`** — Phase 5 territory. The CLI command will need its own MCP reachability check; reusing the preflight body is a Phase 5 plan-time decision. Recorded so Phase 5 doesn't reinvent the diagnostic.
- **Output-schema-aware test parameterization for TEST-10** — If a future tool has a strict `outputSchema`, tests could parameterize per-schema-variant. Not needed for `list_registered_servers`; Phase 4's TEST-10 is single-shape per spec.
- **Rubric tests for non-text tools** — Tools that return ImageContent or ResourceContent have no description text to judge. The current rubric set (clarity / disambiguation / parameters) targets text-content tools. Future "tool quality" rubrics for binary-output tools belong in their own phase or as new rubric subclasses.

### Reviewed Todos (not folded)

None — the Pending Todos accumulator (STATE.md §Accumulated Context > Pending Todos) was empty at the time of this discussion.

</deferred>

---

*Phase: 04-fixtures-test-cases*
*Context gathered: 2026-05-05*
