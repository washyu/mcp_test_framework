# Phase 18: SDET test surface + typed errors - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-12
**Phase:** 18-sdet-test-surface-typed-errors
**Areas discussed:** mcp_session vs mcp_client, --sdet scope semantics, ToolCallError extraction policy, ToolCallError → renderer surface

---

## mcp_session vs mcp_client

### Q1: How should `mcp_session` relate to the existing `mcp_client` fixture?

| Option | Description | Selected |
|--------|-------------|----------|
| Alias / re-export | `mcp_session = mcp_client` (thin re-export). One MCP connection, one anyio-owner-task; preserves Phase 04.1 cancel-scope invariant. | ✓ |
| Fresh session fixture | Separate session-scoped fixture with its own `stdio_client` / `ClientSession` / owner task. Doubles the handshake; duplicates 90 LOC of plumbing. | |
| Conditional reuse | Reuse `mcp_client` when both surfaces active; fresh session under `--sdet`-only. Complicates wiring for small upside. | |

**User's choice:** Alias / re-export (Recommended).
**Notes:** D-01 in CONTEXT.md. `mcp_session` is exported from `src/mcp_test_framework/sdet/__init__.py` as an alias of the existing `mcp_client` fixture. Phase 04.1 cancel-scope-invariant anyio-owner-task plumbing is preserved verbatim.

### Q2: Where should the generated `_REGISTRY` get activated?

| Option | Description | Selected |
|--------|-------------|----------|
| Inside mcp_session fixture | Fixture body imports the generated module, sets `_ACTIVE_SLUG`, yields, restores on teardown. Matches the docstring already in `_tool_factory.py`. | ✓ |
| Separate autouse fixture | Independent of mcp_session being requested. Risk of leaking active slug into framework self-tests. | |
| Lazy in tool() factory | First `tool(name)` call triggers activation. No defined teardown; violates module-level-state warning. | |

**User's choice:** Inside mcp_session fixture (Recommended).
**Notes:** D-02. Single seam at the fixture boundary; the only place that mutates `_ACTIVE_SLUG` in test code.

### Q3: If `--sdet` is set but no generated module exists for the live serverInfo.name slug, what should happen?

| Option | Description | Selected |
|--------|-------------|----------|
| Fail loud at session start | Preflight `importlib.import_module`; `pytest.exit` with operator-tone message naming the missing slug + `gen-sdet-classes` next step. | ✓ |
| Skip all sdet tests with reason | Emit a session-start skip across `tests/sdet/`. Silently hides operator misconfiguration. | |
| Best-effort empty registry | Activate `_REGISTRIES[slug] = {}`; every `tool()` lookup then raises `KeyError`. Misleading errors per-test. | |

**User's choice:** Fail loud at session start (Recommended).
**Notes:** D-03. Mirrors Phase 13 SAFE-03 fail-loud semantics via `_pytest_exit_operator_tone` helper at `fixtures.py:57-81`.

---

## --sdet scope semantics

### Q1: Does `--sdet` ADD `tests/sdet/` on top of contract, or REPLACE contract with SDET-only?

| Option | Description | Selected |
|--------|-------------|----------|
| SDET-only | `--sdet` swaps the operator-surface scope from contract to sdet. Operators wanting both run twice. | ✓ |
| Additive on top of contract | `--sdet` adds sdet to contract; renderer interleaves two domains. | |
| Opt-out via separate flag | Default contract; `--sdet` = contract+sdet; `--sdet-only` = sdet. Doubles the flag surface. | |

**User's choice:** SDET-only (Recommended).
**Notes:** D-04. Matches SDET-persona mental model; avoids interleaving two domains in one summary line.

### Q2: How should `--sdet --with-framework` behave?

| Option | Description | Selected |
|--------|-------------|----------|
| Collect sdet + framework | Each flag's job stays the same; `--sdet --with-framework` = `tests/sdet/ + tests/framework/`. | ✓ |
| Mutually exclusive | Error when both set. Forces operators to pick one; adds a flag-combination rule. | |
| --with-framework wins | Silently drops `--sdet`. Surprising, discoverable only via help text. | |

**User's choice:** Collect sdet + framework (Recommended).
**Notes:** D-05. Clean composition: `--sdet` picks the operator-surface scope; `--with-framework` always adds framework on top.

### Q3: How should the pre-run digest render under `--sdet`?

| Option | Description | Selected |
|--------|-------------|----------|
| Scenario-aware digest | Reuse Running/Skipping bucketing, keyed on scenario MODULE names; `--explain` expands identically. | ✓ |
| Tool-keyed digest | Aggregate scenarios by target tool. Risks misleading rows when a module touches multiple tools. | |
| Minimal banner only | `Mode: SDET — N scenarios collected`. Loses pre-run visibility. | |

**User's choice:** Scenario-aware digest (Recommended).
**Notes:** D-06. Same operator-domain idiom from Phase 16, keyed on module names instead of tool names.

---

## ToolCallError extraction policy

### Q1: How should the call wrapper populate `ToolCallError.code` and `.message`?

| Option | Description | Selected |
|--------|-------------|----------|
| Heuristic chain | `structuredContent` → JSON-parse first TextContent → concat text fallback. Mirrors `ToolResponse.data` chain. | ✓ |
| Structured-only | Only populate from `structuredContent`. Prose-error tools get empty typed surface. | |
| Message=text always | `.message = concat text`; `.code = None` always. Downgrades UI-02 promise. | |

**User's choice:** Heuristic chain (Recommended).
**Notes:** D-08. Strict `code`/`message` key recognition; no synonyms; non-string `code` coerced via `str(...)`.

### Q2: Should the heuristic recognize other key names besides `code` / `message`?

| Option | Description | Selected |
|--------|-------------|----------|
| code/message only | Strict; predictable; documented narrowly. | ✓ |
| code/message + error/detail/reason synonyms | Wider real-world coverage; bigger doc story; false-match risk. | |
| Walk arbitrary depth | Most lenient; least predictable; performance + false-match risk. | |

**User's choice:** code/message only (Recommended).
**Notes:** D-08 strict-key-set clause. Synonym recognition deferred to v1.4 if real homelab-mcp responses force the conversation.

### Q3: Should `ToolCallError` be a Pydantic model or a plain `Exception` subclass?

| Option | Description | Selected |
|--------|-------------|----------|
| Plain Exception subclass | Standard Python idiom; clean pytest traceback integration; minimal runtime overhead. | ✓ |
| Pydantic BaseModel exception | Validation + serialization for free; heavier; non-idiomatic. | |
| Frozen dataclass + Exception | Lightweight typed surface; less aligned with the codebase's everything-is-Pydantic convention. | |

**User's choice:** Plain Exception subclass (Recommended).
**Notes:** D-07. `class ToolCallError(Exception)` with keyword-only `__init__`; re-exported from `mcp_test_framework.sdet`.

---

## ToolCallError → renderer surface

### Q1: How should `.code` / `.message` reach Phase 16's em-dash FAIL row?

| Option | Description | Selected |
|--------|-------------|----------|
| pytest_exception_interact hook | conftest hook attaches `[code, message]` as JUnit `<property>` entries; XML parser reads them. | ✓ |
| Structured `__str__` prefix | `ToolCallError.__str__` emits `[code=foo] message`; parser strips bracket prefix. Relies on string-format stability. | |
| Pattern-match XML message attr | Parse `<failure message=...>` looking for `ToolCallError:` prefixes. Brittle across pytest versions. | |

**User's choice:** pytest_exception_interact hook (Recommended).
**Notes:** D-09. Hook lives in `tests/sdet/conftest.py`; JUnit `user_properties` keys `mcptf_error_code` / `mcptf_error_message`. Clean seam, no string-parsing brittleness.

### Q2: What goes in the em-dash FAIL row when both `.code` and `.message` are populated?

| Option | Description | Selected |
|--------|-------------|----------|
| [code] message | Code-first in brackets; operators scan column of codes; message gives context. | ✓ |
| message (code suffix) | Natural-language-first; code as parenthetical; risk of code truncation. | |
| message only | Code visible only under `--debug`. Cleanest default; loses scannability. | |

**User's choice:** [code] message (Recommended).
**Notes:** D-10. Renders as `  ✗ {scenario_tag} — [VM_NAME_TAKEN] name already in use`. Falls back to bare message when `.code is None`.

### Q3: Under `--debug`, what `ToolCallError` info should the appendix carry?

| Option | Description | Selected |
|--------|-------------|----------|
| Full CallToolResult dump | Structured block with tool/code/message/raw JSON before pytest's raw output. | ✓ |
| Pytest traceback only | Keep current `--debug` behavior; rely on exception repr. | |
| Both — traceback + structured block | Most information; risks duplication. | |

**User's choice:** Full CallToolResult dump (Recommended).
**Notes:** D-11. Structured block leads `--- ToolCallError dump ---`; emits BEFORE pytest's raw stdout so operators get a grep-able summary first.

---

## Claude's Discretion

The following implementation mechanics were left to the planner / researcher (not surfaced in discussion):

- Exact `mcp_session` exposure shape (bare re-export vs thin façade — default: bare).
- `params.model_dump(mode=...)` mode (suggest `mode="json"` for wire-safe serialization).
- JUnit property name keys (suggest `mcptf_error_code` / `mcptf_error_message`).
- Where the scenario-aware digest builder lives (suggest new function in `_runner.py` near `_compose_pre_run_skip_reasons`).
- Whether to ship a minimum-viable `tests/sdet/test_basic_call.py` in this phase (suggest yes, against the synthetic fixture server from Phase 17).
- `--sdet --raw` composition (suggest: `--raw` bypasses domain UI; `--sdet` still controls discovery scope; pin a test).
- `--sdet` + `-q` digest gating (no special case; existing Phase 16 D-08 gate applies).
- Whether `_preflight` gates Ollama checks under `--sdet` (suggest split: leaner `_sdet_preflight` that does MCP + the D-03 generated-module check; SDET runs no judges, so Ollama check is unnecessary).
- `tool(name).call(params)` keeps `params: BaseModel` typing (no `Awaitable` overload).

## Deferred Ideas

- Stateful yield-fixture cleanup contract + VM-lifecycle dogfood scenario — Phase 19.
- `requires_homelab(...)` marker factory + reachability preflight — Phase 20.
- Authoring walkthrough + README scenario parity — Phase 21.
- Attribute-access `Tool.create_vm.call(...)` ergonomic — v1.4 if SDETs ask.
- `pytest_exception_interact` enrichment for ALL framework exceptions — out of scope for v1.3.
- JSON-key synonyms for `ToolCallError` extraction (`error`, `detail`, `errorCode`) — strict-only for v1.3; revisit if real responses force it.
- Multi-server SDET runs — anti-vision per PROJECT.md.
- `--sdet --with-contract` additive surface — revisit in v1.4 if operators request.
- Per-judge breakdown under `--debug` — Phase 16 D-11; v1.5 cohort with SEED-003.
- Custom pytest plugin packaging (SEED-015) — v1.4.
