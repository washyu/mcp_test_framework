# Phase 20: Preflight + conditional skip - Context

**Gathered:** 2026-05-13
**Status:** Ready for planning

> **Phase reframed during discuss-phase.** The original ROADMAP wording — "An SDET decorating a scenario module with `requires_homelab(proxmox=True, ollama=False, ...)` gets a fast graceful SKIP" — was rejected during discussion as a violation of the framework's generic-MCP-test-framework identity. `requires_homelab(proxmox=True)` bakes SUT-specific knowledge into the framework's API surface; the framework must stay agnostic to which subsystems any given MCP server depends on. Phase 20 pivots to closing the loose ends that surfaced from this reframe.

<domain>
## Phase Boundary

Phase 20 retroactively realigns v1.3 with the principle that **the framework wraps tool calls (params/body/results) and nothing else** — external-dependency reachability is the SDET's responsibility, expressed via stock `@pytest.mark.skipif(not my_probe(), reason="...")` in their own test code. Three deliverables, **zero `src/` framework changes**:

1. **Remove the SUT-specific dogfood** — delete `tests/sdet/test_proxmox_vm_lifecycle.py`. The Phase 19 dogfood was a Proxmox-hardcoded scenario that (a) cannot run in CI without operator-specific Proxmox credentials and (b) made the framework's own test suite SUT-aware in violation of the generic-framework principle. The scenario is preserved as an operator-UAT recipe (lands in Phase 21 docs); the project's shipped test suite stays SUT-agnostic.

2. **Drop PREFLIGHT-01/02 from REQUIREMENTS.md** — both requirements as written presume the framework owns subsystem-specific reachability checks (`requires_homelab(proxmox=...)`). They're replaced with a deferred-items entry: "hello-world MCP server for CI-runnable tool-wrapping coverage" — a future phase that ships a tiny in-tree MCP fixture so end-to-end "all tools wrapped" coverage is achievable in CI without operator infrastructure. v1.3 REQ count drops from 21 to 19.

3. **Add mock-fixture-driven codegen unit tests** — feed the codegen pipeline a hardcoded synthetic tool list (with hand-crafted inputSchema + outputSchema) and assert the generated wrappers are correctly shaped. Pure-data, no live MCP, CI-safe. Catches future codegen drift without depending on any specific SUT being reachable.

**In scope:** Test-suite removal, REQUIREMENTS.md edits, ROADMAP.md edits, new mock-driven codegen unit test(s) under `tests/framework/unit/`. Capturing the v1.3 deferred items in STATE.md / RETROSPECTIVE.md as appropriate.

**Out of scope (deliberate):**
- **Any framework `src/` changes** — Phase 20 ships zero new framework code. The principle: if the framework had to grow new code to satisfy `requires_homelab`, the requirement was wrong, not the implementation.
- **Hello-world MCP server fixture** — captured as a deferred item; that's its own future phase. The work would include: a tiny in-tree MCP server with known-shape tools, used by an end-to-end "every discovered tool gets wrapped" test that runs in CI. Not Phase 20.
- **Operator-UAT Proxmox dogfood docs** — the Phase 19 dogfood pattern is preserved as an operator UAT recipe; the prose lands in Phase 21 (`docs/SDET-AUTHORING.md` already on Phase 21's slate).
- **`requires_homelab` decorator (any flavor)** — the API itself is rejected. SDETs use stock `@pytest.mark.skipif(not their_probe_callable(), reason="...")` for SUT-specific reachability. No framework helper, no decorator factory, no timeout wrapper.
- **Generic `@requires(probe_fn, reason=...)` framework primitive** — also rejected. `pytest.mark.skipif` is sufficient; mcptf adds no value-add wrapper around it.
- **Phase 19 D-02 substitution (CPU bump → lifecycle action / different tool)** — moot now. The dogfood file is being deleted, not fixed.
- **`tests/sdet/test_basic_call.py` disposition** — flagged for planner attention but not pre-decided. It's read-only (`list_registered_servers`) and not Proxmox-touching, but still requires a live homelab-mcp subprocess and currently `pytest.exit`s on a CI host with no MCP. Planner decides: keep as-is (operators run locally), soften with `@pytest.mark.skipif` recipe, or remove entirely.
- **Live-MCP coverage check ("did every discovered tool get wrapped")** — needs a live SUT; that's the hello-world MCP work, deferred.

**Hard dependencies (LOCKED — implement against):**
- **SEED-022 architectural principle** ("Framework primitives; SDET owns safety / SUT specifics") — locks the whole reframe. The framework provides primitives (param/response classes, tool wrapper, session fixture) and renders test outcomes; the SDET decides what tools to call and what reachability to gate on. PREFLIGHT-01/02 as originally written violate this principle; their removal restores alignment.
- **Vibe-coded MCP user persona (v1.2)** — operator may not know SUT internals. The framework must be runnable against any MCP without prior knowledge of that MCP's external dependencies. A `requires_homelab` decorator presumes the framework knows about "homelab" subsystems, which presumes a specific SUT.
- **Phase 18 SDET surface** (`mcp_session`, `tool()`, `ToolCallError`, `tests/sdet/` discovery scope, `--sdet` flag, `_render_per_tool_rows`) — unchanged. The codegen + wrapper + renderer surface is what the framework owns; reachability is not.
- **Existing session-wide `_preflight` autouse** (`fixtures.py:104-298`) — unchanged. It gates `tests/contract/` + `tests/sdet/` for the framework's OWN dependencies (Ollama judge, MCP server binary), `pytest.exit(returncode=2)` on missing prerequisites. That's a framework concern (the framework can't run tests without its own runtime deps); SUT-internal subsystems are NOT a framework concern.
- **Phase 17 codegen surface** (`_codegen.py`, `_slugs.py`, generated `<ToolName>Params` / `<ToolName>Response` classes) — the new mock-fixture unit tests exercise this surface. The walker / emitter functions stay unchanged; new tests add coverage at the integration boundary (synthetic tool list → generated module artifacts).
- **Existing codegen unit tests** (`tests/framework/unit/test_codegen_walker.py`, `test_codegen_emitter.py`, `test_codegen_typecheck.py`, `test_gen_sdet_classes_cli.py`) — locked patterns to extend. The new mock-fixture tests sit alongside these and follow the same pure-data style (no live MCP, no subprocess).
- **Phase 15 test-surface split** — new tests live under `tests/framework/unit/`, preserving the operator-vs-framework separation.
- **Black-box rule** — unchanged. Mock-fixture tests do NOT import or vendor `homelab-mcp`; the synthetic tool list is hand-crafted in the test file or a fixture module under `tests/framework/_fixtures/` (existing convention).

</domain>

<decisions>
## Implementation Decisions

### The reframe (architectural — the most important decisions in this phase)

- **D-01: The framework wraps tool calls and nothing else.** "Tool calls" = params (typed input via Pydantic), body (the wire call), results (typed response via ToolResponse). Anything outside that boundary — reachability checks, environment probes, infrastructure assumptions — belongs to the SDET's test code, not the framework. This is a restatement of SEED-022 with sharper edges; cite this decision when future proposals ask the framework to grow domain-aware features.

- **D-02: `requires_homelab(...)` and any spiritual successor are rejected.** Including all the variants surfaced during discussion: keyword-arg flavor (`requires_homelab(proxmox=True)`), generic-registry flavor (`@requires_subsystems(...)` + SDET-registered probes), single-callable flavor (`@requires(probe_fn, reason)`), and even a thin timeout helper (`probe_with_timeout`). All add API surface the framework doesn't need; pytest's stock `@pytest.mark.skipif(not _probe(), reason=...)` is sufficient. SDETs write the probe inline (or factor it into their own conftest helpers); the framework adds nothing.

- **D-03: Framework's runtime deps stay framework's problem (no scope change).** The existing autouse `_preflight` (Ollama judge + MCP server binary) is correct as-is — those are framework's own dependencies for running ANY test that uses `mcp_session` / `judge`. `pytest.exit(returncode=2)` semantics stay; CI distinguishes "framework can't run" from "tests failed". Phase 20 makes no `_preflight` changes.

### Test-suite cleanup

- **D-04: Delete `tests/sdet/test_proxmox_vm_lifecycle.py` outright.** No archive, no comment-out, no `@pytest.mark.skip`. The file is removed from the working tree. Phase 19's dogfood demonstrated stateful primitives end-to-end against a live cluster; that work is preserved in Phase 19's CONTEXT/SUMMARY artifacts (the architectural patterns are documented). The test code itself does not belong in the project's test suite.

- **D-05: Phase 19's deferred D-02 (CPU-bump-impossible) is closed by D-04, not by substitution.** No replacement step is chosen because no replacement file exists. Update STATE.md "Deferred Items" table to mark D-02 as resolved-by-deletion.

- **D-06: `tests/sdet/test_basic_call.py` disposition deferred to planner.** The file is read-only (`list_registered_servers`) and not SUT-specific in the same way the Proxmox dogfood was, but it still requires a live homelab-mcp subprocess to run. Three options the planner can choose from based on what's cleanest after D-04:
  - (a) Leave as-is — it runs behind `_preflight` for operators with a live MCP; CI without an MCP exits at preflight (acceptable since the test surface CI exercises is `tests/framework/`).
  - (b) Add `@pytest.mark.skipif` recipe inline so it skips cleanly when no MCP is configured (demonstrates the SDET-side recipe pattern in-repo).
  - (c) Remove — by the same logic as D-04, it's exercising a specific MCP server. Defers the "hello-world MCP" work to surface this kind of sanity check in CI.
  
  Planner picks based on what produces the cleanest `tests/sdet/` directory (likely empty or near-empty) after D-04 lands.

### Mock-driven codegen coverage (replaces the killed PREFLIGHT-01/02 work)

- **D-07: New tests live under `tests/framework/unit/`** (alongside existing `test_codegen_*`), follow the pure-data style, and use a hand-crafted synthetic tool list. Naming convention: `test_codegen_integration_mock.py` (or planner's choice — single-file integration test vs split per scenario is a planner decision).

- **D-08: The synthetic input is a small fixture in-test** (or under `tests/framework/_fixtures/` — existing pattern from `_fixtures/`). Hardcoded shape: a list of `Tool`-like records with `name`, `description`, `inputSchema` (one with required scalars, one with optional defaults, one with arrays — covers the codegen branches), `outputSchema` (one declared, one omitted to exercise the degraded-stub path). The fixture is committed test data; not auto-generated, not derived from a live MCP.

- **D-09: Assertions verify the codegen contract end-to-end.** For each synthetic tool, after running the codegen pipeline, assert: (a) a `<ToolName>Params` Pydantic class exists with the expected field names, types, defaults, and required-vs-optional flags; (b) a `<ToolName>Response` class exists, inherits `ToolResponse`, exposes `.raw` / `.data` / `.text` / `.is_error`; (c) the generated `__init__.py`'s `_REGISTRY` has the expected `(ParamsClass, ResponseClass)` tuple keyed by tool name; (d) module imports without errors. Implementation idiom: codegen into a temp dir, dynamically import via `importlib`, introspect via `model_fields` / `__bases__`. Locks the public codegen contract against silent regressions.

- **D-10: New tests do NOT touch `src/mcp_test_framework/sdet/generated/homelab_mcp/`.** The committed homelab_mcp generated artifacts stay as-is (they're regenerated via `mcp-test-framework gen-sdet-classes` against a live homelab-mcp). The new tests use synthetic input only; they validate the codegen pipeline shape, not any specific SUT's wrappers.

### REQUIREMENTS.md / ROADMAP.md edits

- **D-11: Drop PREFLIGHT-01 and PREFLIGHT-02 from REQUIREMENTS.md.** Both are removed from the requirements table; v1.3 REQ count drops from 21 to 19. Phase 20's REQUIREMENTS row is replaced with a small, accurate set (see D-12). The "Phase coverage summary" table updates accordingly.

- **D-12: Add new REQUIREMENTS for Phase 20's actual deliverables.** Likely shape (planner finalizes wording):
  - `CLEANUP-DOGFOOD-01`: SUT-specific dogfood test files removed from `tests/sdet/`; project test suite stays SUT-agnostic.
  - `CODEGEN-COVERAGE-01`: Mock-fixture-driven unit tests verify the codegen pipeline produces correctly-shaped Params / Response / registry artifacts for synthetic tool input.
  - `REQ-SCRUB-01`: PREFLIGHT-01/02 removed from REQUIREMENTS.md; "hello-world MCP for CI" captured as a deferred item.

- **D-13: Update ROADMAP.md Phase 20 entry.** Goal rewrites to reflect the new scope. Success criteria rewrite to: dogfood file deleted; PREFLIGHT-01/02 removed from REQUIREMENTS.md; mock-fixture codegen unit tests added under `tests/framework/unit/`; ROADMAP/STATE both reflect the v1.3 REQ count drop.

### Claude's Discretion

- **Mock-fixture file location and naming** — D-07/D-08 leave room for the planner to pick `tests/framework/unit/test_codegen_integration_mock.py` vs splitting across multiple files. Existing convention (one file per area) suggests one new file is enough.
- **Synthetic tool count** — D-08 says "small" (covers required/optional/array branches + outputSchema-present/absent). Planner picks 3–5 tools or whatever covers the codegen branches with the fewest fixtures.
- **REQUIREMENTS.md ID naming** (D-12) — `CLEANUP-DOGFOOD-01` / `CODEGEN-COVERAGE-01` / `REQ-SCRUB-01` are placeholder names. Planner finalizes consistent with existing ID conventions in REQUIREMENTS.md.
- **`tests/sdet/test_basic_call.py` disposition** (D-06) — three options spelled out; planner picks based on what looks cleanest after D-04 lands.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope + reframe rationale
- `.planning/ROADMAP.md` — Phase 20 entry (will be edited by this phase to reflect new scope)
- `.planning/REQUIREMENTS.md` — PREFLIGHT-01 / PREFLIGHT-02 (to be removed); requirements coverage table (to be updated)
- `.planning/PROJECT.md` — project boundaries; Key Decisions table; framework-primitives principle
- `.planning/STATE.md` — Phase 19 closure context; deferred items table (D-02 to be marked resolved-by-deletion)
- Memory: `feedback_phase_scope_intent.md` — phase title is the contract; if the title's framing is wrong, fix the framing rather than expand the implementation
- Memory: `project_framework_primitives_sdet_safety_principle.md` (SEED-022) — the locked architectural principle this phase enforces
- Memory: `project_vibe_coded_persona.md` (v1.2) — operator may not know SUT internals; framework must be SUT-agnostic
- Memory: `feedback_uat_must_be_user_driven.md` — UAT verifies user intent; in-tree project tests verify framework contract; do not conflate

### Phase 19 carry-forward
- `.planning/phases/19-stateful-primitives-domain-ui-integration/19-CONTEXT.md` — locks D-01..D-11 for Phase 19 (module-scope yield fixture, ScenarioState dataclass, dogfood scenario file layout, renderer key derivation)
- `.planning/phases/19-stateful-primitives-domain-ui-integration/19-VERIFICATION.md` — Phase 19 PASS-WITH-DEFERRALS notes; D-02 deferral entry that this phase resolves
- `.planning/phases/19-stateful-primitives-domain-ui-integration/19-04-SUMMARY.md` — Plan 19-04 (the dogfood scenario itself)

### Codegen integration target (for new mock-fixture tests)
- `src/mcp_test_framework/_codegen.py` — codegen pipeline entry; the function under test
- `src/mcp_test_framework/sdet/_slugs.py` — slug derivation (single source of truth used by codegen + session)
- `src/mcp_test_framework/sdet/response.py` — `ToolResponse` base class; assertions check `__bases__` against this
- `src/mcp_test_framework/sdet/generated/homelab_mcp/__init__.py` — reference shape for `_REGISTRY` (read-only; do not modify)
- `tests/framework/unit/test_codegen_walker.py`, `test_codegen_emitter.py`, `test_codegen_typecheck.py` — existing codegen unit tests; locked style/idiom
- `tests/framework/unit/test_gen_sdet_classes_cli.py` — existing CLI-level codegen test; reference for end-to-end pipeline assertions
- `tests/framework/_fixtures/` — existing fixture-data convention

### Files this phase deletes / edits
- `tests/sdet/test_proxmox_vm_lifecycle.py` — DELETE (D-04)
- `.planning/REQUIREMENTS.md` — EDIT (D-11, D-12)
- `.planning/ROADMAP.md` — EDIT (D-13: Phase 20 entry rewrite; v1.3 REQ count update)
- `.planning/STATE.md` — EDIT (mark Phase 19 D-02 resolved-by-deletion; record reframe in Decisions)

### Files this phase intentionally does NOT touch
- Anything under `src/mcp_test_framework/` (D-01: zero src/ changes)
- `tests/sdet/test_basic_call.py` — disposition deferred to planner (D-06)
- `src/mcp_test_framework/sdet/generated/homelab_mcp/*` — committed artifacts stay (D-10)
- The session-wide `_preflight` autouse — correct as-is (D-03)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/framework/unit/test_codegen_*.py` — pure-data unit tests on the walker/emitter; locked style (no live MCP, no subprocess) for the new mock-fixture tests to follow.
- `tests/framework/_fixtures/` — existing fixture-data directory convention; new synthetic tool list could live here if planner prefers separation from the test file itself.
- `src/mcp_test_framework/_codegen.py` + `_slugs.py` + `sdet/response.py` — the codegen pipeline + the `ToolResponse` contract; everything the new tests assert against.

### Established Patterns
- **Tests under `tests/framework/` are framework self-tests; `tests/sdet/` is for SDET-authored scenarios.** Phase 15's split is the locked partition; the new mock-fixture tests are framework self-tests, hence `tests/framework/unit/`.
- **No live MCP in framework self-tests.** Existing codegen tests follow this; new tests do too.
- **Codegen happens to a temp dir, then importlib loads the result.** Existing `test_gen_sdet_classes_cli.py` shows the pattern: invoke codegen, point at a tmp output dir, dynamically import + introspect. Reuse verbatim.

### Integration Points
- **Mock fixture → codegen pipeline → temp output dir → importlib.import_module → introspect generated classes** — the integration boundary the new tests cover.
- **No new integration with `tests/sdet/`** beyond the deletion of one file.
- **No new integration with `src/`** at all.

</code_context>

<specifics>
## Specific Ideas

**The reframe lineage** (paraphrased from discussion):
1. "the framework shouldn't be focused on a proxmox server since this is supposed to be a generic mcp test framework we are just using it to test the homelab mcp"
2. "no proxmox hardcoded tests in this framework"
3. "the framework should only be concerned about wrapping the tool calls and any parameter/body calls and return values"
4. "if we were to run this in a github action it would fail since it wouldn't have access to my proxmox system, so we should just have tests that validate that the code was generated. did all the tools in the SUT get wrapped, did the parameters/body/results classes get generated. and leave the do they work for the uat for now"
5. "we might have to add a quick hello world type of mcp in the project for ci/cd check ... but it is out of scope for now"
6. "we can just add mock unit tests for this — pass a hardcoded tool list and parameter response and body thingies and see if we generate the correct wrappers"

These statements together drive D-01 through D-13. Quote them in any future proposal that resurrects "the framework should auto-detect / probe / skip-on / warn-about subsystem X."

**Synthetic tool fixture sketch** (illustrative — planner finalizes):

```python
# tests/framework/_fixtures/synthetic_tools.py (or inline in the test)

SYNTHETIC_TOOLS = [
    {
        "name": "echo_message",
        "description": "Echo a string back unchanged.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
            },
            "required": ["message"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "echoed": {"type": "string"},
            },
        },
    },
    {
        "name": "add_numbers",
        "description": "Sum a list of numbers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "numbers": {"type": "array", "items": {"type": "number"}},
                "label": {"type": "string", "default": "sum"},
            },
            "required": ["numbers"],
        },
        # outputSchema deliberately omitted — exercises degraded-stub path
    },
    {
        "name": "ping_with_timeout",
        "description": "Pretend to ping with optional timeout.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "host": {"type": "string"},
                "timeout_ms": {"type": "integer", "default": 1000},
            },
            "required": ["host"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "elapsed_ms": {"type": "integer"},
            },
        },
    },
]
```

This shape covers: required scalar string, optional scalar with default, array-of-scalar, integer-with-default, boolean output, outputSchema-declared and outputSchema-omitted. Three tools is enough; planner can add more if a codegen branch isn't covered.

**Expected assertions per synthetic tool** (sketch):

```python
def test_echo_message_params_class_shape():
    Params = _import_generated_class("echo_message", "Params")
    assert "message" in Params.model_fields
    assert Params.model_fields["message"].annotation is str
    assert Params.model_fields["message"].is_required()

def test_echo_message_response_class_shape():
    Response = _import_generated_class("echo_message", "Response")
    assert ToolResponse in Response.__mro__
    assert hasattr(Response, "raw")  # via ToolResponse base
    # ... etc.

def test_add_numbers_response_degrades_to_stub():
    # outputSchema omitted upstream; codegen emits a stub Response that
    # still inherits ToolResponse but has no extra fields.
    Response = _import_generated_class("add_numbers", "Response")
    assert ToolResponse in Response.__mro__
    # field assertions match the degraded-stub contract
```

**REQUIREMENTS.md edit shape** (illustrative):

Before:
```
| PREFLIGHT-01 | `requires_homelab(...)` marker factory exported from ... |
| PREFLIGHT-02 | Reachability checks are fast (sub-second) and degrade ... |
```

After:
```
| CLEANUP-DOGFOOD-01    | SUT-specific dogfood test files removed from `tests/sdet/`; the project test suite stays SUT-agnostic. |
| CODEGEN-COVERAGE-01   | Mock-fixture-driven unit tests verify the codegen pipeline produces correctly-shaped Params/Response/registry artifacts for synthetic tool input. |
| REQ-SCRUB-01          | PREFLIGHT-01/02 removed from REQUIREMENTS.md; "hello-world MCP for CI" recorded in deferred items. |
```

(Planner finalizes ID naming + table-row prose to match existing REQUIREMENTS.md style.)

</specifics>

<deferred>
## Deferred Ideas

### Hello-world MCP server for CI/CD coverage (future phase, NOT v1.3)

A tiny in-tree MCP server with hand-crafted, deterministic tools. Lets the framework run a real end-to-end "every discovered tool gets wrapped, every wire call returns the expected typed response" pass in CI, without depending on any operator-specific infrastructure (Proxmox, Ansible, Ollama-judged content, etc.). User explicitly said "out of scope for now" but flagged the need.

Likely scope when activated:
- Tiny in-tree MCP server (Python, stdio, ships under `tests/_fixtures/` or `tests/framework/_helpers/mcp_server_hello_world/`)
- A tool surface large enough to exercise: required + optional params, scalars + arrays, declared + omitted outputSchema
- A `tests/framework/integration/` directory (new) that runs the full discovery → codegen → wire-call → typed-response loop against this fixture MCP
- Documents the in-tree MCP as the canonical CI sanity surface; `tests/sdet/` stays for operator-authored SUT-specific scenarios

Activation trigger: when the v1.3 close retrospective surfaces "we have no end-to-end CI coverage of the SDET surface."

### Operator-UAT-only Proxmox dogfood recipe (Phase 21 docs)

The Phase 19 dogfood scenario (`create_proxmox_vm` → modify → delete) is preserved as an operator UAT recipe in `docs/SDET-AUTHORING.md` (Phase 21's slate already includes this doc). The recipe covers:
- Module-scope yield fixture pattern (Phase 19 D-04 ScenarioState dataclass)
- Cleanup-on-failure contract (Phase 19 D-06 self-test still ships in `tests/framework/unit/`)
- VMID isolation strategy (Phase 19 D-03 reserved range + timestamped name)
- The SDET-side `@pytest.mark.skipif(not _proxmox_reachable(), reason=...)` pattern as the canonical example

Phase 21 already owns this; Phase 20 just needs to ensure the deletion in D-04 doesn't lose the prose intent (Phase 19's CONTEXT.md preserves the architectural patterns for Phase 21 to lift into docs).

### `tests/sdet/test_basic_call.py` disposition

Captured as Claude's Discretion above (D-06). Three options spelled out for the planner. If planner picks "remove," that strengthens the "framework self-tests don't touch SUT" boundary; if planner picks "soften with skipif," that demonstrates the SDET-side recipe in-repo. Either is consistent with the reframe.

### Phase 19 D-02 substitution — RESOLVED, not deferred

For completeness: Phase 19's deferred D-02 ("CPU-cores bump impossible via manage_proxmox_vm — defer to Phase 20 substitution decision") is resolved by D-04 (delete the file). No substitution chosen because no file remains to host it. STATE.md entry updates from Open → Resolved-by-deletion (Phase 20).

### Upstream homelab-mcp inputSchema bug — UNCHANGED status

Phase 19's other deferral (homelab-mcp inputSchema declares optional fields as `type: "string"` without `"null"` but defaults them to null) remains Open as an upstream-fix item. Phase 20 doesn't touch it; it's an upstream bug, not a framework concern. Captured in STATE.md "Deferred Items" table; future homelab-mcp release tracks it.

</deferred>

---

*Phase: 20-preflight-conditional-skip*
*Context gathered: 2026-05-13*
