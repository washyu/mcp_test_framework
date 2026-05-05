# Phase 4: Fixtures & Test Cases - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-05
**Phase:** 04-fixtures-test-cases
**Areas discussed:** Test markers + default-skip, Rubrics + judge call shape, _preflight fixture shape, fixtures.py vs conftest.py + TEST-10 heuristic

---

## Test markers + default-skip

### Q1: How should the 10 Phase 4 tests be gated by markers?

User reframed the question — the framework REQUIRES MCP + Ollama; deps shouldn't be gated by markers, preflight should fail loudly when missing.

| Option | Description | Selected |
|--------|-------------|----------|
| Unmarked; _preflight gates | Phase 4 tests carry no markers; _preflight checks deps; smoke retains live_* | ✓ |
| Unmarked + drop live_* entirely | Convert smoke tests to unmarked too — too aggressive; loses opt-in smoke affordance | |
| Unmarked + extended preflight (warmup) | Same as #1 plus warmup judge call | (split — warmup deferred) |

**User's choice:** Unmarked; _preflight gates.
**Notes:** "We would expect to have those dependencies so filtering out tests because they don't have access should just fail to execute since we should be checking for those dependencies before we execute the tests."

### Q2: On preflight failure, what's the user-facing failure mode?

| Option | Description | Selected |
|--------|-------------|----------|
| pytest.exit(reason, returncode=2) | Single-line diagnostic, exit code 2 (usage error), no ERROR cascade | ✓ |
| Raise in fixture (10 ERRORs cascade) | Pitfall 3 antipattern — fixture errors hide under ERROR-level reports | |
| Skip the suite | Wrong — green skipped run is worst CI signal | |
| Custom error class + summary line | More work for same end behavior | |

**User's choice:** pytest.exit(reason, returncode=2).
**Notes:** Aligns with "fail to execute" framing from Q1.

### Q3: Phase 5 CLI's `run` command — what `-m` flag does it pass?

| Option | Description | Selected |
|--------|-------------|----------|
| Nothing (default skip applies) | CLI defers to pyproject addopts; smoke stays opt-in; Phase 4 unmarked tests run | ✓ |
| CLI overrides `-m ''` to run everything | Wider but redundant with smoke tests | |
| CLI excludes `tests/smoke/` explicitly | Belt-and-suspenders | |

**User's choice:** Nothing (default skip rule applies).
**Notes:** Symmetric with `uv run pytest tests/`.

---

## Rubrics + judge call shape

### Q1: Where should the three rubric strings live?

User reframed — propose rubrics-as-fixtures so they're extensible / overridable / removable.

| Option | Description | Selected |
|--------|-------------|----------|
| src/.../rubrics.py constants | Module constants imported by tests | (replaced by fixtures path) |
| Inline in test file | Tightest coupling; bloats test file | |
| tests/rubrics/*.txt files | Filesystem corpus | |
| src/.../rubrics/*.md via importlib.resources | Heaviest abstraction | |

**User's framing:** "What if we add them to tests as fixtures? They should be defined in a Python file — it will allow someone to extend the framework if they want with other tool-quality fixtures or remove them from tests if needed."

### Q2: What shape do the rubric fixtures take?

| Option | Description | Selected |
|--------|-------------|----------|
| Three separate fixtures named per rubric | `rubric_clarity`, `rubric_disambiguation`, `rubric_parameters` in fixtures.py via pytest_plugins | ✓ |
| One `rubrics` dict fixture | Less idiomatic pytest; harder to override one rubric | |
| Parametrized fixture with ids | Collapses TEST-05/06/07 into one parametrized test | |
| RubricSet object fixture | Heaviest; better for 8+ rubrics | |

**User's choice:** Three separate fixtures, named per rubric.

### Q3: How heavily do we encode Pitfall 6 hardening in the rubric strings?

User pivoted: "use a base fixture class that has the hardening in it then derive the three fixture classes from that."

### Q4: Base class shape — what does it look like and what do fixtures yield?

| Option | Description | Selected |
|--------|-------------|----------|
| Pydantic Rubric base; fixtures yield instances | BaseModel base + three subclasses; __str__ renders prompt; fixtures yield instances | ✓ |
| ABC base; fixtures yield rendered strings | Less inspectable | |
| HardenedRubric mixin + per-dimension class | Composition-flavored; lower readability for MVP | |
| Function composition: shared HARDENING constant + three fixtures | No class hierarchy; less extensible per user's framing | |

**User's choice:** Pydantic Rubric base; fixtures yield instances.
**Notes:** Hardening defined once in base class; new rubrics subclass and override.

### Q5: Subject vs context split for the three description-quality tests?

| Option | Description | Selected |
|--------|-------------|----------|
| Subject = description; context = {name, inputSchema} | Per-rubric subject choice; matches spec wording | ✓ |
| Subject = full tool blob; rubrics differ only in wording | Larger SUBJECT block surface for injection | |
| Subject = name + description for all three; context varies | Mixed injection model | |
| Subject from rubric.subject_for(tool) method | Heaviest abstraction | |

**User's choice:** Subject = description; context = {name, inputSchema}. TEST-07 uses inputSchema as subject.

---

## _preflight fixture shape

### Q1: What does _preflight check, and does it warmup?

User reframed: "Let's do the basic checks — is Ollama, is MCP, is tests. But I do want to revisit the preflight to add the warmup and don't want that to get lost — it will be a post-MVP add."

### Q2: Confirming the three basic checks — which version?

| Option | Description | Selected |
|--------|-------------|----------|
| Ollama reachable + MCP runnable + target tool present | Three is X checks: ollama / mcp / tests | ✓ |
| Cheaper: which() only, target check lazy | Skip MCP handshake during preflight | |
| Combine handshake + target-tool: preflight owns MCP session | Hands open session to mcp_client | |

**User's choice:** Ollama reachable + MCP runnable + target tool present.
**Notes:** Warmup deferred to post-MVP, preserved in Deferred Ideas.

### Q3: Reuse open MCP session or close + respawn?

| Option | Description | Selected |
|--------|-------------|----------|
| Close after preflight; mcp_client respawns own | Two spawns; clean independent ownership | ✓ |
| Hand off session to mcp_client | One spawn; couples lifecycles | |
| Merge preflight into mcp_client | Drops _preflight fixture; violates FIX-02 | |

**User's choice:** Close after preflight; mcp_client respawns its own.

### Q4: Does FIX-03 keep its own membership check?

| Option | Description | Selected |
|--------|-------------|----------|
| Both check; FIX-03 raises ToolNotFoundError | Defense in depth; one extra round-trip | ✓ |
| FIX-03 trusts preflight; returns cached Tool | Reintroduces coupling rejected in Q3 | |
| Drop FIX-03 entirely | Loses named seam | |

**User's choice:** Both check; FIX-03 raises ToolNotFoundError on its own.

---

## fixtures.py vs conftest.py + TEST-10 heuristic

### Q1: Where do all eight fixtures live?

| Option | Description | Selected |
|--------|-------------|----------|
| src/.../fixtures.py + pytest_plugins | Spec-aligned; importable by future test packages | ✓ |
| Everything in tests/conftest.py | Idiomatic pytest; loses module-importability | |
| Split: state-bearing in src/, glue in conftest | Fuzzy rule | |
| src/.../fixtures.py + thin conftest re-export | Same effect; less idiomatic than pytest_plugins | |

**User's choice:** src/.../fixtures.py + pytest_plugins.

### Q2: judge fixture type annotation — Protocol or concrete?

| Option | Description | Selected |
|--------|-------------|----------|
| Protocol Judge from judge_protocol.py | SEED-001 enabler; Phase 3 D-06 enforced | ✓ |
| Concrete OllamaJudge | Violates Phase 3 D-06 | |

**User's choice:** Protocol Judge.

### Q3: TEST-10 'is JSON' heuristic — what's the contract?

| Option | Description | Selected |
|--------|-------------|----------|
| Try-parse every text block; assert ≥1 parses | Black-box-safe; optional schema validation when outputSchema present | ✓ |
| Heuristic: text starts with { or [ | Could mask broken-JSON-without-leading-brace | |
| Use mimeType field if present | Shape-coupling on union variants | |
| Pass if EITHER content OR structuredContent valid | Less strict; closer to MCP spec flexibility | |

**User's choice:** Try-parse every text block; assert at least one parses.

### Q4: Unparseable text content — failure or soft-skip?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — unparseable = test failure | Real signal; informative diagnostic | ✓ |
| Skip 'parseable' check, log warning | Weakens contract | |
| Inspect outputSchema first; skip text parsing if absent | Could mask undeclared-schema cases | |

**User's choice:** Yes — unparseable = test failure.

---

## Claude's Discretion

The user passed on these — the planner/executor has flexibility:

- `config` fixture body shape (trivial `Config()` return).
- Pydantic shape of `Rubric` base — `BaseModel` with `frozen=True` (parallels `JudgeResult` and config sub-models).
- Score anchors wording per rubric subclass — anti-verbosity in BASE preamble; score-of-5 caution in base score-anchor template.
- `_preflight` failure ordering — recommended cheapest-first (which → Ollama → MCP handshake → tool membership).
- TEST-10 multi-block diagnostic phrasing.
- `Rubric.__str__` exact section ordering as long as hardening precedes dimension criteria.
- Test parameterization vs flat — flat (matches REQUIREMENTS naming).
- `list_tools()` cache for FIX-03 — no mocking; planner picks cache shape.

## Deferred Ideas

- Warmup judge call in `_preflight` — explicitly user-flagged for post-MVP. Trigger: first-test cold-start latency surfacing as CLI UX issue.
- `OllamaJudge.warmup()` explicit method — re-deferred from Phase 3.
- xdist tool-level parallelism (SEED-002) — incompatible with current session-scope shape.
- Best-of-N judge consensus / score-of-5 anti-bias — out of scope per REQUIREMENTS.
- Calibration / golden-set for the judge — out of scope per REQUIREMENTS.
- Phase 5 list-tools CLI reusing `_preflight` body — Phase 5 plan-time decision.
- Output-schema-aware TEST-10 parameterization — not needed for `list_registered_servers`.
- Rubric tests for non-text tools (Image/Resource content) — future rubric subclasses.
