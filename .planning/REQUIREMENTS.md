# Requirements — mcp_test_framework v1.3 Homelab Scenario Testing

**Milestone:** v1.3
**Scoped:** 2026-05-12
**Status:** Active (planning phase — pending roadmap approval)

## Milestone Goal

Replace manual Claude-client verification of homelab-mcp with automated end-to-end coverage. Every tool gets graded by the existing static contract pass (schema + description rubrics); stateful tools additionally get authored SDET scenarios for functional verification (e.g. VM lifecycle: create → modify → delete with cleanup-on-failure).

**Persona shift:** v1.0–v1.2 served the operator persona. v1.3 adds the SDET persona as a second first-class user. Both personas share the same CLI surface; SDET adds a new test-discovery scope and an authoring API.

**Carry-forward debt closure:** v1.3 SDET runs against live homelab-mcp naturally exercise the surfaces that Phase 13 + 14's live-stack UATs were waiting on. Those UATs close opportunistically during v1.3 rather than requiring separate verification.

## Requirement Groups

### SDET — Test Surface and Fixtures

| ID       | Description                                                                                                                                                                                              |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SDET-01  | `tests/sdet/` directory exists as a recognized test discovery scope. The CLI's default contract pass does NOT collect it; SDET scenarios run only when explicitly opted in.                              |
| SDET-02  | `mcp-test-framework run --sdet` opts SDET scope into the run. Composable with existing flags (`-q`, `--explain`, `--debug`, `--raw`). Default run remains contract-only — no behavior change.            |
| SDET-03  | `mcp_test_framework.sdet` module exports `mcp_session` (session-scoped fixture wrapping `McpTestClient`) and `tool(name)` (returns a typed call wrapper for the named tool).                             |
| SDET-04  | Async-only by contract: SDET fixtures and call wrappers require `@pytest.mark.asyncio` markers; pytest-asyncio strict mode is enforced for the SDET scope just as it is for `tests/contract/`.            |

### CODEGEN — Schema-driven class generation

| ID         | Description                                                                                                                                                                                                                                                |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CODEGEN-01 | `mcp-test-framework gen-sdet-classes` command introspects the configured MCP server via `list_tools` and writes generated artifacts to `src/mcp_test_framework/sdet/generated/<server_slug>/`. Idempotent — rerunning overwrites generated files only.        |
| CODEGEN-02 | Parameter classes generated as Pydantic models from each tool's `inputSchema`. Field types, required/optional, defaults, and validators (where expressible) all derive from the schema. Class name: `<PascalCaseToolName>Params`.                            |
| CODEGEN-03 | Response classes generated for every tool. When `outputSchema` is declared, the class is a Pydantic model with typed attribute access. When undeclared, the class inherits only from `ToolResponse` base (no typed fields). Class name: `<PascalCaseToolName>Response`. |
| CODEGEN-04 | `ToolResponse` base class provides uniform surface for all tools regardless of `outputSchema` declaration: `.raw` (the `CallToolResult`), `.data` (best-effort dict view — `structuredContent` first, then JSON-parse of first `TextContent`, then `{"text": ...}` fallback), `.text` (concatenated text content), `.is_error` (mirror of `result.isError`). |
| CODEGEN-05 | Typed call wrapper: `tool("create_vm").call(params: CreateVmParams) -> CreateVmResponse`. Validates params against `inputSchema` before the wire call (Pydantic does this for free); parses the response into the typed class on the way back.              |
| CODEGEN-06 | Regeneration safety: generated files contain a leading comment marker so an operator extending them in-place gets a clear warning. The recommended pattern is to import generated classes and subclass for extensions — generated files are never hand-edited. |

### STATE — Stateful test primitives (SEED-004 cohort)

| ID       | Description                                                                                                                                                                                                                                  |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| STATE-01 | pytest yield-fixture pattern documented and dogfooded for create/cleanup chains. The framework's own SDET self-tests demonstrate the canonical idiom (create resource → yield → teardown).                                                  |
| STATE-02 | Cleanup-on-failure contract: when a test consuming a stateful fixture raises (including assertion failures), the fixture's teardown still executes. This is pytest-native behavior; the framework verifies the dogfood path enforces it.   |
| STATE-03 | Module-scope state passing pattern documented: tests within a single scenario module share a `scope="module"` fixture, run in file order, and all see the same created state (typed via the response class).                              |
| STATE-04 | Cross-file ordering supported via pytest-order (or equivalent) when scenarios genuinely span files. Documented as a recipe; framework doesn't ship a custom ordering mechanism.                                                              |

### CLEANUP — v1.3 retroactive scope correction (Phase 20)

| ID                  | Description                                                                                                                                                                                                                       |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CLEANUP-DOGFOOD-01  | SUT-specific dogfood test files removed from `tests/sdet/`; the project's shipped test suite stays SUT-agnostic so CI can run without operator-specific infrastructure (Proxmox, Ansible, etc.).                                  |
| CODEGEN-COVERAGE-01 | Mock-fixture-driven unit tests verify the codegen pipeline produces correctly-shaped `<ToolName>Params` / `<ToolName>Response` / `_REGISTRY` artifacts for a synthetic tool list (no live MCP, CI-safe).                          |
| REQ-SCRUB-01        | The two prior Phase 20 preflight requirements (`requires_homelab(...)` marker factory + reachability checks) are removed from REQUIREMENTS.md; "hello-world MCP server for CI-runnable end-to-end coverage" is recorded as a deferred item for a future v1.x phase. |

### RELOC — SDET generated output relocation (Phase 21.1, INSERTED 2026-05-14)

| ID        | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| RELOC-01  | The output root for generated SDET classes is read from `config.yaml` (`sdet.generated_root`). The field is **required** on the v2 schema — no default, no env-var override, no CLI flag override. Missing or empty value triggers a SAFE-03-style operator-tone error via the existing `_emit_operator_error_for_validation` mapper (Pydantic "missing required field" branch). `config.example.yaml` and `examples/homelab-mcp.yaml` include the new key.                                                            |
| RELOC-02  | The `gen-sdet-classes` CLI command writes to `cfg.sdet.generated_root / <slug>/` (3 sites: `out_root` derivation at cli.py:995, docstring at cli.py:932, error detail at cli.py:981, success echo at cli.py:1018). The `mcp_session` pytest fixture loads the generated `__init__.py` via `importlib.util.spec_from_file_location` with `submodule_search_locations` against `cfg.sdet.generated_root / <slug> / __init__.py` — no `sys.path` mutation, no `importlib.import_module` against a package path. The `_tool_factory.py:21` docstring no longer references the old hardcoded module path. |
| RELOC-03  | Tests that previously imported `mcp_test_framework.sdet.generated.homelab_mcp` are reworked off that path. `tests/framework/unit/test_sdet_fixtures.py` uses a synthetic-mock fixture pattern lifted from `test_codegen_integration_mock.py` (writes a slug dir into `tmp_path`, drives `mcp_session` with a fake client). `tests/framework/unit/test_gen_sdet_classes_cli.py` extends its `_write_config` helper to set `sdet.generated_root` to a `tmp_path` location. `tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py` switches to live regen against the configured `sdet.generated_root` (gated `@pytest.mark.live_homelab`). `tests/framework/unit/test_codegen_integration_mock.py` is unaffected (D-10). |
| RELOC-04  | `src/mcp_test_framework/sdet/generated/` is deleted from the working tree (56 `homelab_mcp/*.py` files + `homelab_mcp/__init__.py` + the top-level `generated/__init__.py` namespace marker). `pyproject.toml` `[tool.pyright]` `include` and `strict` lists drop the now-extinct subtree. `docs/SDET-AUTHORING.md` (7 hardcoded `sdet/generated` path references) and `README.md:293` (SDET sample import) are rewritten to reference the new config-driven path and recommend the on-disk convention `tests/sdet/_generated/`. |

### UI — Domain rendering for SDET runs

| ID    | Description                                                                                                                                                                                                                                                                                                       |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UI-01 | SDET scenarios render through Phase 14's `_render_per_tool_rows`. The per-tool group header carries the scenario module name (e.g. `proxmox_vm_lifecycle`); nested rows show individual test results with their function names (`create_returns_pending_vm`, `modify_accepts_cpu_increase`, etc.).                |
| UI-02 | `ToolCallError` typed exception class with `.tool` / `.code` / `.message` / `.raw` fields. Raised when `result.isError` is True. On `--debug`, the raw `CallToolResult` is dumped to the appendix. Default-mode FAIL rows surface `.code`/`.message` via the existing em-dash failure-detail pattern from Phase 16. |

### DOC — Authoring documentation

| ID            | Description                                                                                                                                                                                                                                                                  |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DOC-SDET-01   | "Authoring a scenario test for your MCP server" walkthrough in `docs/SDET-AUTHORING.md` (or appended to `docs/EXTENDING.md`). Uses the VM lifecycle scenario as the worked example. Covers fixture patterns, ordering, preflight markers, response typing degradation.    |
| DOC-SDET-02   | Codegen regeneration workflow documented: when to regen (`gen-sdet-classes` after homelab-mcp schema changes), what gets overwritten, the import surface as the stable contract, mypy/pyright as the change-detection mechanism.                                          |
| DOC-SDET-03   | README sample section showing one scenario file and its operator-side output. Char-for-char parity with the renderer (per the Phase 16 doc-mirroring pattern from the SEED-008 closure — README samples MUST match what the runner emits).                              |

## Success Criteria (milestone-level)

The milestone is **shippable** when ALL of these are true:

1. An SDET writes a `tests/sdet/test_<name>.py` file in this repo, imports `tool`, `mcp_session`, `requires_homelab`, and the generated param/response classes for their target tools, then runs `mcp-test-framework run --sdet` — and the result distinguishes pass / fail / skip in the same operator domain language Phase 14 + 16 established.

2. The VM lifecycle scenario (`create → modify → delete`) ships as the dogfood scenario in this repo. Running it against live homelab-mcp + Proxmox produces a clean green run; running it without Proxmox produces a clean skip with the unreachable target named.

3. `mcp-test-framework gen-sdet-classes` exists and idempotently produces the generated module from the configured MCP server. The generated files compile under mypy/pyright with no errors.

4. The `ToolResponse` base class works uniformly across `outputSchema`-declared and `outputSchema`-undeclared tools — test code calling `.data["..."]`, `.text`, `.raw`, `.is_error` does NOT need to branch on whether the response is typed.

5. Cleanup-on-failure verified by a deliberately-failing dogfood scenario — the framework's own SDET self-test suite includes a test that asserts a stateful fixture's teardown still ran after an intervening test raised.

6. Phase 13 + 14 carry-forward live-stack UATs close as part of normal v1.3 verification — either by being directly subsumed (the SDET run IS the live homelab-mcp exercise) or by being formally re-verified once the live stack is being driven by `--sdet`.

7. Docs updated: `docs/SDET-AUTHORING.md` exists; README has a scenario sample section; CLAUDE.md notes the dual operator+SDET persona.

8. **Phase 21.1 added 2026-05-14:** generated SDET classes no longer live under `src/mcp_test_framework/sdet/generated/`. Output path is operator-controlled via `sdet.generated_root` in `config.yaml`; the framework reads from the configured path and never writes inside its own `src/` tree. SEED-022 (framework primitives only; no SUT code in `src/`) is enforced structurally.

## Out of Scope (explicit, not silent)

- **Library mode / pytest plugin delivery** (SEED-015) — deferred to v1.4. The SDET surface stabilizes on the CLI model first.
- **Pluggable judge backends / OpenAI-compat** (SEED-005) — v1.4 or v1.5.
- **Dynamic judging protocol / rubrics-as-data + agent-realism input fuzz** (SEED-003) — v1.5.
- **pytest-xdist parallelism** (SEED-002) — v1.4 (cohort with SEED-015).
- **Phase 16 D-11 `--debug` per-judge breakdown** — v1.5 cohort with SEED-003.
- **`judges_only: true` per-tool config flag** — flagged as a useful Phase-17-area discussion topic but not committed. May land if a clean implementation surfaces during planning; otherwise carries to v1.4.
- **Multi-server SDET scenarios** — one MCP server per run remains the contract. Multi-server is post-v2.
- **Random / adversarial parameter fuzzing** — anti-vision per PROJECT.md. Agent-realistic-mistake fuzz lives in SEED-003 (v1.5).
- **SEED-023 SDET→test-code rename** — deferred to v1.4. Phase 21.1 keeps the `sdet` namespace name; only the `generated/` subtree relocates.
- **CLI `--out` override and `MCPTF_GENERATED_ROOT` env var for `sdet.generated_root`** — explicitly rejected at Phase 21.1 D-02. One source of truth.

## Open Design Questions for Phase Planning

These are explicitly NOT requirements — they're decisions to make during `/gsd-plan-phase` for the relevant phase. Captured here so they don't get lost.

- **CLI surface for `gen-sdet-classes`:** subcommand or `mcp-test-framework codegen sdet`? Decide during the codegen phase.
- **Generated file location:** `src/mcp_test_framework/sdet/generated/<server_slug>/` (in-tree, importable) vs `tests/sdet/generated/` (test-tree, gitignored). Probably in-tree because it's importable; revisit.
  - **Resolved Phase 21.1 (RELOC-01..04):** location is operator-controlled via `sdet.generated_root` config; framework recommends `tests/sdet/_generated/` in docs but does not enforce.
- **Server-slug derivation:** server name from config? hostname? a config-set slug? Needs to be stable across regens.
- **`requires_homelab` location:** module-level export vs `mcp_test_framework.sdet.markers.requires_homelab`? Decide during preflight phase.
- **`tool("name")` builder vs `Tool.create_vm.call(...)` attribute access:** ergonomics call. Stringly-typed access is simpler; attribute access gives IDE completion on tool names. Probably ship both, but lock the recommended idiom.
- **Generated `<Tool>Response` for `outputSchema`-undeclared tools:** stub class (`class FooResponse(ToolResponse): pass`) or alias (`FooResponse = ToolResponse`)? Stub gives a stable import name even though the surface is identical; aliasing saves a class but breaks `from ... import FooResponse` for tools that later gain typed schemas. Probably stub.

## Traceability Table

| Requirement ID | Phase    | Status   |
| -------------- | -------- | -------- |
| SDET-01        | Phase 18 | Complete |
| SDET-02        | Phase 18 | Complete |
| SDET-03        | Phase 18 | Complete |
| SDET-04        | Phase 18 | Complete |
| CODEGEN-01     | Phase 17 | Pending  |
| CODEGEN-02     | Phase 17 | Pending  |
| CODEGEN-03     | Phase 17 | Pending  |
| CODEGEN-04     | Phase 17 | Pending  |
| CODEGEN-05     | Phase 17 | Pending  |
| CODEGEN-06     | Phase 17 | Pending  |
| STATE-01       | Phase 19 | Pending  |
| STATE-02       | Phase 19 | Pending  |
| STATE-03       | Phase 19 | Pending  |
| STATE-04       | Phase 19 | Pending  |
| CLEANUP-DOGFOOD-01  | Phase 20 | Pending  |
| CODEGEN-COVERAGE-01 | Phase 20 | Pending  |
| REQ-SCRUB-01        | Phase 20 | Pending  |
| RELOC-01       | Phase 21.1 | Complete |
| RELOC-02       | Phase 21.1 | Pending  |
| RELOC-03       | Phase 21.1 | Pending  |
| RELOC-04       | Phase 21.1 | Pending  |
| UI-01          | Phase 19 | Pending  |
| UI-02          | Phase 18 | Complete |
| DOC-SDET-01    | Phase 21 | Complete |
| DOC-SDET-02    | Phase 21 | Complete |
| DOC-SDET-03    | Phase 21 | Pending  |

**Total: 26 requirements mapped across 6 phases (17–21.1). Coverage: 26/26 (100%).**

### Phase coverage summary

| Phase | Requirements                                                                | Count |
| ----- | --------------------------------------------------------------------------- | ----- |
| 17    | CODEGEN-01, CODEGEN-02, CODEGEN-03, CODEGEN-04, CODEGEN-05, CODEGEN-06      | 6     |
| 18    | SDET-01, SDET-02, SDET-03, SDET-04, UI-02                                   | 5     |
| 19    | STATE-01, STATE-02, STATE-03, STATE-04, UI-01                               | 5     |
| 20    | CLEANUP-DOGFOOD-01, CODEGEN-COVERAGE-01, REQ-SCRUB-01                       | 3     |
| 21    | DOC-SDET-01, DOC-SDET-02, DOC-SDET-03                                       | 3     |
| 21.1  | RELOC-01, RELOC-02, RELOC-03, RELOC-04                                      | 4     |
