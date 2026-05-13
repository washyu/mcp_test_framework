---
phase: 17
slug: schema-driven-codegen-surface
status: verified
threats_open: 0
asvs_level: 1
created: 2026-05-12
---

# Phase 17 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Phase 17 ships the codegen surface (walker, emitter, factory seam, CLI) that
> walks JSON Schema produced by an **untrusted** MCP server and emits Python
> source later imported by the test runner. Source-injection threats dominate
> the register (HIGH severity because the import path is the privileged test
> process).

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| MCP server (subprocess) → walker (`_codegen.translate_tool`) | Server-controlled `serverInfo.name`, `serverInfo.version`, `tool.name`, `tool.inputSchema`, `tool.outputSchema` flow over stdio into the codegen pipeline. The framework treats `homelab-mcp` as a black-box subprocess under test; "Vibe-coded MCP persona" project memory notes the operator may not vet SUT internals. | strings (name/version), JSON Schema dicts, JSON-Schema property names |
| Walker output → filesystem (`generate()`) | `shutil.rmtree(out_root / slug)` where `slug` derives from server-controlled `serverInfo.name`. `out_root` is package-relative (`Path(__file__).parent / "sdet" / "generated"`), not operator-controlled. | path-segment string |
| Generated Python source → Python import system | Phase 18's `mcp_session` fixture will `import mcp_test_framework.sdet.generated.<slug>` — anything that survives the emitter executes in the test runner's privileged process. | Python source text |
| MCP server text payload → `ToolResponse.data` (`json.loads`) | Server-controlled `TextContent.text` passed to `json.loads` inside the response accessor. | bytes / str |
| CLI subcommand `gen-sdet-classes` → MCP subprocess spawn | `cfg.mcp_server.command` + args spawned via `stdio_client`. Operator-controlled config; same trust contract as `run` / `list-tools` (Phase 5 baseline). | argv |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Evidence (file:line / test) | Status |
|-----------|----------|-----------|-------------|------------|------------------------------|--------|
| T-17.01-01 | Tampering | `ToolResponse.data` JSON-parse of server-controlled text | mitigate | `try/except (json.JSONDecodeError, ValueError)` wraps `json.loads`; falls back to `{"text": <concat>}`. | `src/mcp_test_framework/sdet/response.py:90-94`; test `tests/framework/unit/test_tool_response.py::test_data_falls_back_to_text_dict_when_json_parse_fails` | closed |
| T-17.01-02 | Denial of Service | `json.loads` against arbitrarily large server-controlled text | accept | Bounded at the `call_tool` layer by `asyncio.timeout(timeout_seconds)` (Phase 2 LOCKED `mcp_client.py:209`). No new codegen-time vector. | See Accepted Risks AR-1. | closed |
| T-17.01-03 | Information Disclosure | `.data` does not branch on `is_error`; error payloads surface via `.data["..."]` | accept | Locked CODEGEN-04 spec; documented in `data` docstring. Phase 18's typed `ToolCallError` is the error path. | `src/mcp_test_framework/sdet/response.py:82-86`; test `tests/framework/unit/test_tool_response.py::test_data_does_not_check_is_error_pitfall_8`. See Accepted Risks AR-2. | closed |
| T-17.01-04 | Tampering | Non-`TextContent` blocks (Image/Audio) crash `.text` accumulator | mitigate | `isinstance(block, TextContent)` filter inside `.text` generator. | `src/mcp_test_framework/sdet/response.py:66-69`; test `test_text_skips_non_text_blocks_pitfall_7` | closed |
| T-17.01-05 | Spoofing | `arbitrary_types_allowed=True` could let a caller pass non-`CallToolResult` as `raw` | accept | Pydantic field-type validation still runs (`raw: CallToolResult` rejects mismatched types with `ValidationError`); the opt-in is for type identity only. | `src/mcp_test_framework/sdet/response.py:47-49`. See Accepted Risks AR-3. | closed |
| T-17.02-01 | Tampering | Server-controlled `inputSchema` exploiting walker to emit arbitrary Python (source injection) | mitigate | Walker never `eval`/`exec` server input. Property names routed through `_safe_field_ident` (CR-03 fix) — non-ident chars → `_`, keywords suffixed, leading-digit prefixed `f_`. Tool/server names routed through `pascal_case` / `module_name` / `server_slug` for filesystem + class identifiers. | `src/mcp_test_framework/sdet/_codegen.py:276-319` (`_safe_field_ident`), `src/mcp_test_framework/sdet/_slugs.py` (`pascal_case`/`module_name`/`server_slug`); tests `tests/framework/unit/test_codegen_walker.py::TestPascalCase::test_keyword_guard`, `::test_leading_digit_guard`, `TestModuleName::*` | closed |
| T-17.02-02 | Tampering | Server name with path-traversal characters reaching `shutil.rmtree` | mitigate | `server_slug` strips `[^a-zA-Z0-9_]+`, collapses underscores, strips leading/trailing — `"../etc/passwd"` → `"etc_passwd"`. Empty-after-normalization raises `ValueError` BEFORE any filesystem touch. `out_root` is package-relative (CLI-controlled, not server-controlled). | `src/mcp_test_framework/sdet/_slugs.py:26-49`; test `TestServerSlug::test_collapses_runs_and_strips`, `::test_empty_raises`, `tests/framework/unit/test_codegen_emitter.py::test_emitter_loud_fail_on_empty_server_name` | closed |
| T-17.02-03 | Tampering | Malformed JSON Schema crashing walker mid-emit leaving partial files | mitigate | `_check_schema_structural` pre-flight rejects `required: not-a-list` / `properties: not-a-dict` with `SchemaValidityError` BEFORE any write (now runs unconditionally on dict inputs per WR-06 fix). CLI maps to operator-tone error + exit 2. | `src/mcp_test_framework/sdet/_codegen.py:124-157` and `:495` (unconditional invocation); test `test_invalid_schema_raises_loud` | closed |
| T-17.02-04 | Denial of Service | Pathologically large / deeply-nested inputSchema | accept | Walker is O(properties); D-02 explicitly degrades nested objects to `dict[str, typing.Any]` — no recursion. `asyncio.timeout` bounds wall time at the SDK layer. | See Accepted Risks AR-4. | closed |
| T-17.02-05 | Information Disclosure | Server-controlled `description` strings in `Field(description=...)` | accept | `description=<repr>` quotes via `repr()` which escapes embedded quotes/backslashes — text is inert at parse time. No f-string interpolation of raw server input into source. | `src/mcp_test_framework/sdet/_codegen.py:184-185`. See Accepted Risks AR-5. | closed |
| T-17.02-06 | Tampering | Wipe-and-write race with editor/pyright daemon (Pitfall 5) | mitigate | `__init__.py` is written LAST; partial states fail clean with `ModuleNotFoundError`. | `src/mcp_test_framework/sdet/_codegen.py:670-676`; test `test_emitter_writes_init_py_last` (mtime assertion) | closed |
| T-17.02-07 | Tampering | `repr()` of a non-JSON default emitting non-literal Python | accept | JSON Schema `default` is JSON-typed (scalar/list/object/null). `repr()` of any JSON-typed value is a valid Python literal. | See Accepted Risks AR-6. | closed |
| T-17.03-01 | Tampering | Phase 18 fixture failing to clean up `_ACTIVE_SLUG` after a session leaves stale registry consulted next session | mitigate | Phase 18 owns the save-restore (out of Phase 17 scope). Phase 17's `_reset_module_state` autouse fixture demonstrates the contract Phase 18 must follow. | `src/mcp_test_framework/sdet/_tool_factory.py:38-39` (module slots); test `test_state_resets_between_tests_part_a/b` | closed |
| T-17.03-02 | Information Disclosure | `KeyError` on unknown tool name echoes full tool list | accept | Tool list comes from the operator's own configured MCP server; no multi-tenant scenario. | See Accepted Risks AR-7. | closed |
| T-17.03-03 | Denial of Service | `ToolWrapper.call(...)` leaking a coroutine | accept | `.call()` raises `NotImplementedError` synchronously when awaited — coroutine consumed normally. | `src/mcp_test_framework/sdet/_tool_factory.py:70-82`. See Accepted Risks AR-8. | closed |
| T-17.03-04 | Spoofing | In-repo test code directly mutating `_REGISTRIES["other_slug"]` to inject a fake wrapper | accept | Test code IS the testing surface; module-level slots are intentionally write-accessible so Phase 18's fixture can populate them. | See Accepted Risks AR-9. | closed |
| T-17.04-01 | Tampering | Server-controlled `serverInfo.name` with path-traversal reaching `rmtree(generated/<slug>/)` | mitigate | `server_slug()` strips non-`[a-z0-9_]` chars; `out_root` is package-relative. Empty-slug raises `ValueError` pre-filesystem. | `src/mcp_test_framework/sdet/_slugs.py:26-49`, `src/mcp_test_framework/sdet/_codegen.py:648-653`; test `TestServerSlug::test_collapses_runs_and_strips`, `test_emitter_loud_fail_on_empty_server_name` | closed |
| T-17.04-02 | Elevation of Privilege | `cfg.mcp_server.command` arbitrary-binary execution | accept | Pre-existing framework contract (Phase 5); operator-authored config; not a Phase 17 regression. | See Accepted Risks AR-10. | closed |
| T-17.04-03 | Information Disclosure | `_emit_operator_error` echoes `cfg.mcp_server.command` + args | accept | Config came from the operator; echo-back is informational, not disclosure. | See Accepted Risks AR-11. | closed |
| T-17.04-04 | Denial of Service | Malicious MCP server returning a 10,000-tool `list_tools` response → 10,000 files | accept | Wipe-and-write D-03 bounds disk impact; `asyncio.timeout(cfg.mcp_server.timeout_seconds)` bounds wall time. | See Accepted Risks AR-12. | closed |
| T-17.04-05 | Tampering | SDK private attribute `_initialize_result` renamed in mcp 2.x silently produces wrong serverInfo | mitigate | Implementation pivoted to class-level monkey-patch of `ClientSession.initialize` after planner discovered SDK doesn't store `_initialize_result` (mcp 1.27); a missing capture raises explicit `RuntimeError` ("SDK contract changed"). WR-01 added `_codegen_handshake_lock` to serialize concurrent patches. | `src/mcp_test_framework/cli.py:1036-1069` (patch + lock); `:1060-1064` (loud-fail on missing capture) | closed |
| T-17.04-06 | Spoofing | Malicious MCP server lies about `serverInfo.name` to collide with another server's slug | accept | D-05 documents this as operator-error; collision is visible because `generated/<slug>/` already exists at wipe-step (wipe is the resolution). | See Accepted Risks AR-13. | closed |
| T-17.04-07 | Repudiation | Generated files lose operator hand-edits silently (D-03 wipe) | mitigate | CODEGEN-06 header ("DO NOT HAND-EDIT", "Extend by subclassing in tests/sdet/") on every emitted file. | `src/mcp_test_framework/sdet/_codegen.py:50-55` (HEADER_TEMPLATE); test `test_emitter_header_marker_on_every_file` | closed |
| T-17.05-01 | Tampering | Regression in `translate_tool` emits type-broken source that the gate fails to catch | mitigate | Negative-coverage test `test_pyright_rejects_deliberately_broken_generated_file` deliberately injects a type error and asserts pyright fails — anti-no-op insurance. | `tests/framework/unit/test_codegen_typecheck.py::test_pyright_rejects_deliberately_broken_generated_file` | closed |
| T-17.05-02 | Denial of Service | Pyright takes >120s on a pathological tree | mitigate | `subprocess.run(..., timeout=120)` raises `TimeoutExpired` → test failure with clear message. Synthetic fixture bounded at 6 tools. | `tests/framework/unit/test_codegen_typecheck.py` `_run_pyright` (timeout=120) | closed |
| T-17.05-03 | Information Disclosure | Pyright output may include absolute `tmp_path` paths on failure | accept | Test-time only; `tmp_path` under operator's home dir. | See Accepted Risks AR-14. | closed |
| T-17.05-04 | Tampering | Pyright version drift surfaces new errors on previously-passing code | accept | Trade-off: `>=1.1.409` lower bound + `uv.lock` for deterministic reproducibility; CI catches drift. | See Accepted Risks AR-15. | closed |

### Post-Plan code-review mitigations (CR-01..04)

The Phase 17 code review (`17-REVIEW.md`, dated 2026-05-12) surfaced four
**critical** source-injection / data-integrity defects that the original plan
threat models had not enumerated. All four landed before this audit (commits
`f32bb48` … `b6ed194`); each maps onto T-17.02-01 / T-17.04-01 as a deeper
mitigation than the plan originally specified.

| Review ID | Category | Component | Disposition | Mitigation | Evidence | Status |
|-----------|----------|-----------|-------------|------------|----------|--------|
| CR-01 | Tampering (source injection) | `HEADER_TEMPLATE` — server-controlled `serverInfo.name` / `version` interpolated into Python comment | mitigate | New `_render_header(...)` helper feeds both fields through `json.dumps(...)` before template format — embedded `"` / `\n` / unicode are stringified into harmless escape sequences. Safe inputs render byte-identically. | `src/mcp_test_framework/sdet/_codegen.py:50-75` (`HEADER_TEMPLATE` + `_render_header`); commit `f32bb48`. **GAP:** no regression test added — verified by hand-execution per `17-REVIEW-FIX.md`. | closed (warning) |
| CR-02 | Tampering (source injection) | `_render_init` — server-controlled `tool.name` interpolated into `_REGISTRY` dict literal | mitigate | `f"    {json.dumps(tool_name)}: (...)"` — `json.dumps` produces a safely-escaped string literal. Spec-compliant names render byte-identically (`test_emitter_init_py_carries_registry` pin still matches). | `src/mcp_test_framework/sdet/_codegen.py:596-598`; commit `7e196ad`. **GAP:** no adversarial-name regression test — verified by hand. | closed (warning) |
| CR-03 | Tampering (SyntaxError → import failure) | `_format_field_line` — JSON-Schema property names with keywords / leading-digit / hyphens / whitespace interpolated verbatim into field LHS | mitigate | New `_safe_field_ident(name) -> (ident, alias_or_None)` + `_inject_alias(default_expr, alias)`. Non-ident chars → `_`; keywords suffixed `_`; leading-digit / collapsed-empty prefixed `f_` (NOT `_` — Pydantic v2 raises `NameError` on leading-underscore field names); rename injects `Field(alias=<original>, ...)` so wire field still validates. | `src/mcp_test_framework/sdet/_codegen.py:276-354` (`_safe_field_ident` + `_inject_alias`); called from `_format_field_line:382-385`; commit `62a74a8`. **GAP:** no regression tests for keyword / leading-digit / hyphen / space / unicode field-name shapes — verified by hand. | closed (warning) |
| CR-04 | Tampering (gate bypass) | Substring scan `"typing." in body_text` / `"Field(" in body_text` false-positives on field descriptions containing those literals → resurrects orphaned-import bug Plan 17-06 was meant to close | mitigate | `_BodyEmission` dataclass threads `uses_typing_any` / `has_fields` as structured signals computed at field-emission time over the typed `FieldSpec.py_type` (annotation only, not the rendered Field() call). `translate_tool` consults the flags directly. | `src/mcp_test_framework/sdet/_codegen.py:393-461` (`_BodyEmission` + `_emit_params_body` flag computation), `:533-534` (consumption); commit `b6ed194`. **GAP:** no regression test for description-with-`"typing."`-substring shape — verified by hand. | closed (warning) |

### Code-review warning mitigations (WR-01..06)

| Review ID | Category | Mitigation | Evidence | Status |
|-----------|----------|------------|----------|--------|
| WR-01 | Tampering (race) | `_codegen_handshake_lock = asyncio.Lock()` serializes class-level `ClientSession.initialize` patches. | `src/mcp_test_framework/cli.py:989-995, 1036`; commit `cc10a41` | closed |
| WR-02 | Type fidelity | `_REGISTRY` typed `dict[str, tuple[type[BaseModel], type[ToolResponse]]]`; `BaseModel` import added to generated `__init__.py`. | `src/mcp_test_framework/sdet/_codegen.py:608-619`; commit `46d70ed` | closed |
| WR-03..05 | Code quality | Dropped unused `name` parameter; hoisted mid-file imports; removed dead `_ = (...)` keep-alive. | Commits `783084a`, `d45a41e`, `722aeea` | closed |
| WR-06 | Tampering (silent accept) | `_check_schema_structural` now runs unconditionally on dict inputs — `{"required": "not-a-list"}` no longer slips through. | `src/mcp_test_framework/sdet/_codegen.py:495` (no `if input_schema:` guard); commit `673232f` | closed |

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-1 | T-17.01-02 | `json.loads` has no length cap; an MCP server returning a 100MB JSON blob would consume memory. Acceptable for v1.3: framework bounds via `asyncio.timeout` at the `call_tool` layer (`mcp_client.py:209`); codegen-time concern out of scope. | Phase 17 planner | 2026-05-12 |
| AR-2 | T-17.01-03 | `.data` returning error payloads is the locked CODEGEN-04 spec (Pitfall 8). Phase 18's `ToolCallError` is the typed-error path. Pinned by `test_data_does_not_check_is_error_pitfall_8`. | Phase 17 planner | 2026-05-12 |
| AR-3 | T-17.01-05 | `arbitrary_types_allowed=True` is required because `CallToolResult` is an external Pydantic model; Pydantic still validates field type at construction. | Phase 17 planner | 2026-05-12 |
| AR-4 | T-17.02-04 | Walker is O(properties); D-02 degrades nested objects to `dict[str, Any]` (no recursion). Worst case (millions of properties in one tool) not realistic for MCP. | Phase 17 planner | 2026-05-12 |
| AR-5 | T-17.02-05 | `Field(description=<repr>)` quoting via `repr()` makes descriptions inert at parse time; safer than f-string interpolation. | Phase 17 planner | 2026-05-12 |
| AR-6 | T-17.02-07 | JSON Schema `default` is JSON-typed; `repr()` of JSON-typed values is always a valid Python literal. | Phase 17 planner | 2026-05-12 |
| AR-7 | T-17.03-02 | Tool list comes from the operator's own configured MCP server; no multi-tenant disclosure surface. | Phase 17 planner | 2026-05-12 |
| AR-8 | T-17.03-03 | `.call()` raises `NotImplementedError` synchronously when awaited; coroutine consumed normally. | Phase 17 planner | 2026-05-12 |
| AR-9 | T-17.03-04 | Phase 17 has no defense against in-repo test code — test code IS the testing surface; module slots are intentionally write-accessible. | Phase 17 planner | 2026-05-12 |
| AR-10 | T-17.04-02 | Pre-existing framework contract (Phase 5); operator-authored config; same threat surface as `run` / `list-tools`. | Phase 17 planner | 2026-05-12 |
| AR-11 | T-17.04-03 | Config came from the operator; echoing back to the operator is informational. | Phase 17 planner | 2026-05-12 |
| AR-12 | T-17.04-04 | Wipe-and-write D-03 bounds disk impact (next run wipes); `asyncio.timeout(cfg.mcp_server.timeout_seconds)` bounds wall time. | Phase 17 planner | 2026-05-12 |
| AR-13 | T-17.04-06 | Slug collision is visible at wipe-step (existing `generated/<slug>/`); D-05 documents this as operator-error. | Phase 17 planner | 2026-05-12 |
| AR-14 | T-17.05-03 | Test-time only; `tmp_path` under operator's home dir; not a real disclosure concern. | Phase 17 planner | 2026-05-12 |
| AR-15 | T-17.05-04 | Pinning pyright too tightly misses real fixes; too loosely lets drift in. `>=1.1.409` + `uv.lock` is the chosen balance. | Phase 17 planner | 2026-05-12 |

---

## Unregistered Flags

None. No `## Threat Flags` sections in any 17-XX-SUMMARY.md surfaced new attack
surface beyond the threats already enumerated in the per-plan
`<threat_model>` blocks. The four CR-XX critical findings from the code review
ARE new attack surface that did not appear in any plan threat model, but are
now reified in this register (above) with file:line evidence — not unregistered.

---

## Verification Notes (auditor observations)

**Audit method:** for each declared mitigation, grep for the mitigation pattern in
the cited implementation file at the cited path; for `accept` dispositions,
confirm an entry exists in the Accepted Risks Log; for `transfer` — N/A
(no `transfer` dispositions in Phase 17).

**CR-01..04 mitigation pattern check (the four critical source-injection threats
the orchestrator highlighted as load-bearing):**

- CR-01: `grep -c "json.dumps" src/mcp_test_framework/sdet/_codegen.py` → 5+ matches; `_render_header` at `_codegen.py:58-75` calls `json.dumps(server_name)` + `json.dumps(server_version)` exactly as the review prescribed. **Present.**
- CR-02: `_render_init` at `_codegen.py:596-598` emits `f"    {json.dumps(tool_name)}: (...)"` exactly as the review prescribed. **Present.**
- CR-03: `_safe_field_ident` at `_codegen.py:276-319` + `_inject_alias` at `:322-354` exist; `_format_field_line` at `:382-385` calls both. Sanitization strategy matches review prescription exactly, with the documented Pydantic-v2 leading-underscore divergence (`f_` prefix). **Present.**
- CR-04: `_BodyEmission` dataclass at `_codegen.py:393-424` with `uses_typing_any` + `has_fields` flags; computation at `_emit_params_body:451-452` operates on `spec.py_type` (the typed annotation), NOT the rendered Field() string. `translate_tool` at `:533-534` consults `.uses_typing_any` / `.has_fields` directly. The substring scan over `body_text` is GONE. **Present.**

**Audit gap (recorded as warning, not blocker):** the four CR critical fixes
landed WITHOUT accompanying regression tests despite the review explicitly
recommending tests for each ("Add a regression test for..."). `17-REVIEW-FIX.md`
states they were "verified by hand-execution"; no test pins the adversarial
inputs (`evil"\nimport os; ...`, `x", __import__(...), "y`, `class` / `2fa_code`
/ `vm-id` field names, description containing `"typing.Any"`). A future
regression could silently bypass these mitigations and pass CI. **Recommend:
file a Phase-18 or v1.4 follow-up to add adversarial regression tests for
CR-01..04 in `tests/framework/unit/test_codegen_*.py`.**

This audit does NOT block Phase 17 ship on the missing tests — the code-level
mitigations are present, correct, and provably the patterns the review
prescribed. The test-coverage gap is a separate finding and is logged here for
visibility.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-05-12 | 27 (22 plan threats + 5 critical review findings consolidated as deeper mitigations + 6 warning review findings, deduped) | 27 | 0 | Claude (gsd-secure-phase) |

Counted: 5 (Plan 01) + 7 (Plan 02) + 4 (Plan 03) + 7 (Plan 04) + 4 (Plan 05) = 27 threats from plan registers. CR-01..04 + WR-01..06 represent deeper mitigations / additional concrete fixes for threats already in the plan registers (primarily T-17.02-01 and T-17.04-01 / T-17.04-05); they are recorded above as their own rows for traceability without inflating the total count.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log (AR-1..AR-15)
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-05-12 (Claude / gsd-secure-phase). One follow-up
recommendation logged: add adversarial regression tests for CR-01..04 to
prevent silent bypass in future work. Not blocking.
