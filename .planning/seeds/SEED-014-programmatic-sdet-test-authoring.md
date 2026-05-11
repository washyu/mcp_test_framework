---
id: SEED-014
status: dormant
planted: 2026-05-11
planted_during: v1.2 / post Phase 14 UAT, before Phase 15 planning
trigger_when: When current contract/operator mode stabilizes and users start asking "I want to test a specific scenario, not the random parameter space." Most likely a v2.x milestone reframing the product as an SDET-grade framework, not a contract-only validator. Surface during /gsd-new-milestone if the next milestone mentions: "SDET", "programmatic tests", "user-authored tests", "parameter classes", "tester DX", "test scenario library", "stateful testing", or anything coupling the framework to a real test environment that users want surgical control over.
scope: Large
target_milestone: v2.0+ (pairs naturally with SEED-004 stateful-testing — the two should likely ship together)
---

# SEED-014: Programmatic SDET test authoring — generated parameter classes + tester-authored test cases

Extend the framework beyond auto-generated contract tests into a true SDET-grade authoring surface. Auto-generate typed Python classes from each MCP tool's `inputSchema`, expose them via a stable testing API, and let testers write their own pytest test files that drive specific, named scenarios — not just random/auto-generated parameter sweeps.

The motivating use case (user's words, 2026-05-11):

> "I would like to test create_vm but I don't want to generate random VMs in my test environment for an extensive parameter pass — so allowing the tester to generate specific tests for more complex tools is a must."

The current v1.x framework auto-parametrizes every selected tool through a fixed rubric (schema validation → call → judge). That's the right shape for an **operator** validating a contract. It's the wrong shape for a **tester** who wants to assert that `create_vm(name="test-vm-prod-prefix", cpu=1, memory=512, disk_gb=10)` specifically returns `{vm_id: <non-empty>, status: "pending"}` and nothing else.

## Why This Matters

**The framework currently has one mode and one persona — the operator.** Phase 14's domain UI and Phase 13's safety semantics are explicitly operator-shaped. But the user's homelab-mcp surface is ~70 tools, many of them mutating / destructive / state-bearing (`create_vm`, `destroy_terraform_service`, `decommission_device`, `register_server`). The contract-test approach (run the tool with reasonable inputs, score the response) is fine for read-only tools but actively dangerous or meaningless for the rest:

- **Destructive tools cannot be exercised by random parameter packs.** Calling `delete_proxmox_vm` with a random `vm_id` either does nothing (id doesn't exist) or destroys infrastructure (id exists). Neither is useful contract evidence.
- **Mutating tools need precise pre-state.** `update_device_config` needs a known device fingerprint before the call to validate the diff.
- **Composite scenarios cannot be expressed.** "register_server → list_registered_servers → confirm it appears → deregister" is one logical test, not three.
- **Domain assertions are richer than rubric scores.** A tester wants to assert `result.vm_id matches /^vm-\d+$/`, not "the judge gave the response a 4/5 for clarity."

This is the **SDET persona** that the framework doesn't currently serve. They're not random sweepers, not contract validators, not operators verifying their config — they're test engineers writing intentional scenarios against the tool surface.

Phase 14's UAT exposed a hint of this gap: pytest parametrize-ids like `path0`, `NOTSET`, `-1`, `None` leaked into the domain UI because *the framework* parametrized over those values without anyone naming the scenarios. If the same coverage came from tester-authored tests, the IDs would be `test_create_vm_with_minimum_resources`, `test_create_vm_rejects_negative_cpu`, etc. — meaningful in the operator UI for free.

## When to Surface

**Trigger:** When current contract/operator mode stabilizes (post-v1.4) and users start asking for surgical scenario control over the tool surface. Specifically surface during `/gsd-new-milestone` if the next milestone mentions:

- "SDET" / "test engineer" / "programmatic tests" / "user-authored tests"
- "Parameter classes" / "typed test inputs"
- "Test scenario library" / "scenario catalogue"
- "Stateful testing" (auto-pairs with SEED-004)
- Any framing of "test environment with surgical control"

Sister seeds — likely ship in the same milestone or as paired milestones:

- **SEED-004 (stateful-tool-testing)** — programmatic test authoring without setup/teardown semantics is half a product. SEED-014 *consumes* SEED-004's primitives (`setup:` / `teardown:` hooks become `@pytest.fixture` building blocks for tester-authored tests). The pair = "the framework you can test stateful tools with."
- **SEED-005 (pluggable-judge-backends)** — programmatic tests likely don't need a judge at all (assertions ARE the judge), but if they do, plug in whichever.
- **SEED-001 (agentic-tool-use-judge)** — orthogonal but complementary. Agentic = "rate this tool by trying to use it." SDET = "I'm telling you exactly how to use it."
- **SEED-010 (operator-vs-framework-test-surface)** — established that operator ≠ framework dev. SEED-014 adds **SDET** as a third persona. The CLI surface needs to split: `mcp-test-framework run` for operators (current), `mcp-test-framework test` for SDET-authored scenarios, framework's own tests stay in tests/framework/.

## Scope Estimate

**Large** — milestone-sized, possibly multi-milestone. The pieces:

1. **Schema → class codegen (medium plan).** For each tool in the connected MCP server, generate a Pydantic model (or dataclass) from `inputSchema`. Output to a user-editable location (`tests/sdet/generated/` or installable as `mcp_test_framework.tools`). JSON Schema → Python types is mechanical and well-tooled (datamodel-code-generator, etc.) — pick a library, wire it to the discovery output. Output must be regeneratable without losing user customization (separate file for generated stubs vs user-extended subclasses).

2. **Testing API (medium plan).** A stable seam testers import:
   ```python
   from mcp_test_framework.sdet import tool, mcp_session

   @pytest.mark.asyncio
   async def test_create_vm_minimal(mcp_session):
       result = await tool("create_vm").call(
           name="sdet-test-vm",
           cpu=1, memory=512, disk_gb=10,
       )
       assert result.vm_id.startswith("vm-")
       assert result.status == "pending"
   ```
   The `tool(...)` and `mcp_session` fixture build on the existing `McpTestClient` from `src/mcp_test_framework/mcp_client.py` but expose a friendlier surface with type completion.

3. **Test discovery split (small plan).** A new pytest discovery path for `tests/sdet/` (or wherever user tests live) that's distinct from the contract suite. Operator's `mcp-test-framework run` keeps doing the contract pass. SDET runs via either a new subcommand (`mcp-test-framework test`) or the user invokes pytest directly with the SDET fixtures available. The split should mesh with SEED-010's operator vs framework folder split.

4. **Test scenario library convention (small plan).** Recommended layout for user repos: `tests/sdet/<tool_name>/test_<scenario>.py` so the framework can report "Test 14 of 23 SDET scenarios passed" in domain language. Optional shared fixtures library (`tests/sdet/conftest.py` with framework-provided base fixtures).

5. **Domain UI integration (small plan).** When the SDET surface runs, the existing `_render_per_tool_rows` should aggregate by tool from real test names (`test_create_vm_minimal` → tool: `create_vm`, scenario: `minimal`). This collapses naturally if the test file convention matches the folder structure. Solves Phase 14's parametrize-id-leak gap as a side effect.

6. **Documentation + tester-persona docs (medium plan).** A new top-level doc for the SDET persona, distinct from operator docs. "Here's how you write a test against your MCP server." Plus the regeneration workflow ("you added a tool to your server → run `mcp-test-framework gen-sdet-classes` → rebase your tests").

Could realistically span two milestones: v2.0 = "framework supports SDET mode" (pieces 1-3); v2.1 = "SDET ergonomics + integration" (pieces 4-6).

## Breadcrumbs

Related code (current v1.x — what the SDET layer would build on):
- `src/mcp_test_framework/schema_validator.py` — already validates `inputSchema` via `jsonschema`'s `Draft202012Validator`. The SDET codegen taps the same schemas.
- `src/mcp_test_framework/mcp_client.py::McpTestClient` — the existing async stdio client. SDET's `mcp_session` fixture wraps this with a tester-friendly façade (likely just rename + re-export).
- `src/mcp_test_framework/fixtures.py` — session-scoped `mcp_client` / `target_tool` / `config` fixtures. The SDET surface keeps `mcp_client` and `config`, drops `target_tool` (replaced by `tool("name")` builder).
- `tests/conftest.py::_resolve_tool_names` — discovery cache. SDET codegen reads this cache (or a fresh discovery call) to enumerate tools to generate.
- `src/mcp_test_framework/_runner.py::ParsedRun` / `ToolVerdict` — the domain model from Phase 14. SDET test results need to map cleanly into the same model so the operator UI renders both contract + SDET runs identically.

Related decisions / constraints (must honor):
- **Black-box rule (CLAUDE.md):** "Never import, read, or vendor `homelab-mcp` source." SEED-014 does NOT violate this. The generated parameter classes are derived from the MCP `inputSchema` protocol output — same source the framework already uses for validation. Testers write tests against the MCP wire protocol via the generated classes, never against SUT internals. Memory item: project_vibe_coded_persona reinforces this.
- **Operator-first design (v1.2 milestone theme):** SDET mode is additive, not subtractive. The operator surface (`mcp-test-framework run` → domain UI) does not change. The SDET surface is opt-in (separate CLI subcommand or direct pytest invocation).
- **MCP transport contract:** stdio-only via `stdio_client` context manager. SDET fixtures must reuse the same context-manager dance — no raw `subprocess.Popen`.
- **Async discipline (CLAUDE.md):** SDET tests are async (it's an async MCP client); use `@pytest.mark.asyncio` markers in strict mode, just like the contract suite. `asyncio.timeout` wraps any MCP/HTTP operation.

Related seeds + planning artifacts:
- SEED-004 (stateful-tool-testing) — required dependency for SDET to handle `create_vm`-class tools properly. Setup/teardown semantics provide the fixture primitives.
- SEED-010 (operator-vs-framework-test-surface) — established three-persona split; SEED-014 formalizes the third persona (SDET) and its surface.
- SEED-008 (reporter-ux-overhaul) — the per-tool aggregation work there should anticipate SDET output too.
- SEED-011 (hybrid-runner-domain-ui) — Phase 14 work. SDET output flows through the same rendering pipeline.
- `docs/mcp_test_framework_mvp_spec.md` — explicit "Out of Scope" lists "Stateful or destructive tool testing" + "Custom user-authored test cases (read-only contract validation only)". SEED-014 captures the deliberate v1 deferral.
- Memory item: project_output_ergonomics_at_scale — homelab-mcp ≈ 70 tools; SDET mode where each tool may have 5-20 named scenarios → 350+ tests. UI design must hold up.

## Notes

**Why this is a seed, not a Phase 15+ plan:** Three reasons.

1. **v1.x is operator-shaped.** The current milestone (v1.2) is about operator UX. v1.3 / v1.4 are likely about polishing that further (SEED-008 reporter overhaul, SEED-001 agentic judge). Bolting SDET on now muddies the persona work.

2. **Stateful primitives must land first.** SDET test authoring without setup/teardown fixtures is half a product — testers would have to manually create-and-destroy VMs in their own fixtures, defeating the framework's value. SEED-004 should ship first or simultaneously.

3. **The codegen library choice is a 2-day spike.** Best done when the schema→class layer is the focus, not when other persona work is in flight.

**Open design questions to revisit when this germinates:**

- Codegen output: separate package (`mcp_test_framework_tools_<server_name>`), in-tree generated module, or both? Implications for distribution and IDE completion.
- Generated class style: Pydantic models (validation parity with the rest of the framework) vs plain dataclasses (lighter, no Pydantic 2.x churn). Probably Pydantic for consistency.
- Regeneration semantics: how do user-extended subclasses survive `gen` runs? Either separate file (`generated_*.py` vs `tool_*.py`) or marker comments. The OpenAPI-codegen world has solved this; lift the convention.
- CLI surface: `mcp-test-framework test`? `mcp-test-framework sdet`? Just expose pytest plugin and tell users to run pytest directly? Operator vs SDET CLI parity matters — both should feel like first-class modes.
- Scenario reporting: how does the domain UI distinguish a contract test (auto-generated rubric) from an SDET scenario (named assertion)? Different glyph? Different section? Phase 16 (SEED-008) territory.
- Test data hygiene: if a tester writes `test_create_vm` and the test creates a real VM, who tears it down on failure? SEED-004's teardown contract must guarantee cleanup even on assertion failure — pytest fixtures with `yield` patterns handle this naturally.

If a user starts asking for this surface before SEED-004 lands, the right answer is "let's plan stateful testing first" — but the seed surfacing here will give the right framing for that conversation.
