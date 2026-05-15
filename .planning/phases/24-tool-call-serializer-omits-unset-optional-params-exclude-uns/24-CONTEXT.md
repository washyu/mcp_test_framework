# Phase 24: Tool call serializer omits unset optional params (exclude_unset) - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 24 switches the SDET `tool().call()` serializer from `model_dump(mode="json")` to `model_dump(mode="json", exclude_unset=True)` at `src/mcp_test_framework/sdet/_tool_factory.py:99` so optional Pydantic fields the SDET never set stay off the MCP wire. The change preserves SEED-022 — `model_dump(exclude_unset=True)` distinguishes user-omitted from user-explicitly-set, so a scenario that needs to test the server's null-handling path can still pass `field=None` in the params constructor and have `null` flow on the wire.

Four downstream artifacts ripple from the one-line serializer fix:

1. **`tests/framework/unit/test_tool_factory.py`** — three new payload-asserting tests that lock the user-visible contract (unset → omitted; explicit `None` → on wire; explicit value → on wire); the existing kwargs-spy test (`test_call_serializes_params_with_mode_json`, L169) gets a one-line update to also assert `exclude_unset=True`.
2. **`docs/SDET-AUTHORING.md` `## The inputSchema workaround` section** — soften framing now that the `_CpuBumpManageVmParams(extra="allow")` pattern is needed only for explicit null-payload testing rather than every Proxmox call. SEED-022 teaching moment preserved (Phase 21 D-06 lock-in).
3. **`README.md` `## SDET scenarios` section** — re-capture the sample as PASS output (currently embeds FAIL output per Plan 21-02 D-14 re-scope) and rewrite the surrounding paragraph that frames the `✗` rows as "the framework doing its job."
4. **`.planning/STATE.md` Deferred Items table** — split the existing `homelab-mcp inputSchema` row (L155) into two rows: one `resolved` for the framework-default-behavior half, one `open` (narrower scope) for the upstream bug that explicit-null-testing still hits.

**In scope:** the four ripples above. **Out of scope:** changes to codegen output, `gen-sdet-classes`, the SEED-022 principle itself, or any homelab-mcp source.

</domain>

<decisions>
## Implementation Decisions

### Serializer change (pre-locked by memory + roadmap)
- **D-01:** `_tool_factory.py:99` becomes `arguments = params.model_dump(mode="json", exclude_unset=True)`. Single-line change. Locked before discussion by memory `project_serializer_exclude_unset_phase_24.md`, the Phase 24 roadmap entry, and the STATE.md 2026-05-14 Roadmap-Evolution entry. This is **not** a SEED-022 violation: `exclude_unset` filters on user-intent (did the SDET set this attribute?), not on value (`is None`). An SDET writing `CreateProxmoxVmParams(host=h, name=n, ..., cdrom=None)` still puts `cdrom: null` on the wire.

### Test coverage for exclude_unset semantics
- **D-02:** Payload-asserting tests only. Add three new tests to `tests/framework/unit/test_tool_factory.py` that inspect `_StubClient.calls[0][1]` (the actual `arguments` dict the wrapper passes to `McpTestClient.call_tool`). One test per behavior: (a) optional field unset → key absent from `arguments`; (b) optional field set to `None` explicitly → `arguments[k] is None`; (c) optional field set to a value → `arguments[k] == value`. The new tests carry the contract weight — a future refactor that breaks the user-visible behavior produces three named failing tests, not one cryptic spy failure.
- **D-03:** The existing kwargs-spy test (`test_call_serializes_params_with_mode_json`, L169) gets one line added: `assert captured_kwargs.get("exclude_unset") is True`. Locks the chosen implementation alongside the existing `mode='json'` assertion. Rename the test to `test_call_serializes_params_with_mode_json_and_exclude_unset` so its purpose stays self-documenting after the change.
- **D-04:** Fixture model is a **hand-rolled Pydantic class in the test file** — e.g. `_FakeParamsWithOptional(BaseModel)` with one required field and one `cdrom: str | None = None`. Matches the existing `_FakeParams` / `_SpyParams` pattern at the top of `test_tool_factory.py`. Self-contained: framework unit tests must not depend on the codegen-generated tree (`tests/sdet/_generated/homelab_mcp/`) existing at collection time, and the test asserts a generic Pydantic-serialization contract, not a homelab-mcp-shaped one.

### STATE.md Deferred Items rescope
- **D-05:** Split the existing row (L155) into two rows so the audit trail records that Phase 24 resolved part of the deferred concern without erasing the upstream bug that still exists.
- **D-06:** Row A (replaces existing row's framework-side framing) — **status: `resolved`**, **deferred-at: `Phase 19 close (2026-05-13)` → `resolved Phase 24 (2026-05-15)`**, **item text:** "Framework default behavior contribution to homelab-mcp inputSchema null trigger — `_tool_factory.py:99` `model_dump(mode='json')` emitted `null` for unset optional Pydantic fields, conflicting with upstream `type: 'string'` declarations." Resolution note: "`exclude_unset=True` shipped in Phase 24; SDET-omitted optionals stay off the wire. SDETs explicitly passing `field=None` to test null-handling still trigger the upstream bug — that is SEED-022-by-design (Row B)."
- **D-07:** Row B (narrower scope of the original concern) — **status: `open`**, **deferred-at: `Phase 19 close (2026-05-13)`** (preserves the original surfacing date so the deferred-items timeline reads correctly), **item text:** "Upstream homelab-mcp inputSchema bug — Proxmox tools (and likely others) declare optional fields as `type: 'string'` (no `'null'`) but default them to `null`. SDETs explicitly testing null-handling hit `Input validation error: None is not of type 'string'` (e.g. via `_CpuBumpManageVmParams(extra='allow')` pattern in `docs/SDET-AUTHORING.md`). Server should declare `type: ['string','null']` or strip null-valued keys before its own jsonschema check." Category: `upstream-fix`.
- **D-08:** Row ordering: Row A appears immediately above Row B in the table (related concerns stay adjacent), both inserted at L155's current position so existing line references downstream stay stable for nearby rows.

### Claude's Discretion (deferred to planner)
- **README sample re-capture mechanism** — planner picks between (a) temporarily resurrecting `tests/sdet/test_proxmox_vm_lifecycle_readme_sample.py` per Plan 21-02 D-14 manual-snapshot precedent, (b) a one-shot script outside `tests/sdet/`, or (c) manual run + paste. The Phase 21 D-14 precedent is the strong default. The rewrite of the framing paragraph (currently `the two ✗ rows above are the framework doing its job`, L420–L427) is also planner-discretion within these constraints: it must still teach that the framework surfaces upstream contract violations as test failures (SEED-022), but the example shifts from "the default path triggers it" to "an SDET who explicitly tests null-handling triggers it."
- **`docs/SDET-AUTHORING.md` `## The inputSchema workaround` section depth** — Phase 21 D-06 locked the section as a load-bearing SEED-022 teaching moment **including** the `_CpuBumpManageVmParams(extra="allow")` pattern. Phase 24 softens framing only: the pattern's necessity narrows from "always needed for Proxmox tools" to "needed only when you want to test null-handling explicitly." Planner picks the rewrite shape (soften in-place, demote to "Advanced", or reframe as an intentional-null-payload-testing example) — Phase 21 D-06's "extra='allow' stays in the doc" lock is respected; only the framing around it changes.
- Exact paragraph wording, code-block formatting, and section-anchor stability are planner-discretion (the README cross-link to `docs/SDET-AUTHORING.md`'s workaround section at README L426 must not break — if the planner renames the H2 anchor, update the cross-link in the same plan).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 24 source artifacts
- `src/mcp_test_framework/sdet/_tool_factory.py` — the file changed; the single-line edit lives at L99 inside `ToolWrapper.call`.
- `tests/framework/unit/test_tool_factory.py` — host file for the three new payload tests + the one-line kwargs-spy update. Existing `_FakeParams`, `_SpyParams`, `_FakeResponse` patterns to mirror at top of file.
- `docs/SDET-AUTHORING.md` §`## The inputSchema workaround` (L252–L305) — section to soften; pattern stays per Phase 21 D-06.
- `README.md` §`## SDET scenarios` (sample block L288–L427, FAIL output at L413–L417, framing paragraph at L420–L427, cross-link to SDET-AUTHORING anchor at L426).
- `.planning/STATE.md` Deferred Items table L155 — the row to split into D-06 Row A + D-07 Row B.
- `.planning/STATE.md` L35 (`Next:`) and L130 (Roadmap Evolution Phase 24 entry) — auto-managed by execute-phase / state.record-session; planner should not duplicate.

### Cross-phase principle anchors
- Memory `project_framework_primitives_sdet_safety_principle.md` (SEED-022) — framework owns no tool-safety reasoning; the discriminator for `exclude_unset=True` vs `exclude_none=True` lives here. Load-bearing for both the test naming and the docs framing.
- Memory `project_serializer_exclude_unset_phase_24.md` — the pre-locked serializer decision; documents why `exclude_unset` is SEED-022-compatible whereas `exclude_none` is not.

### Precedent / pattern reuse
- `.planning/phases/21-sdet-authoring-docs-readme-parity/21-CONTEXT.md` §`D-06` — locks the `_CpuBumpManageVmParams(extra="allow")` pattern in the doc as a SEED-022 teaching moment; Phase 24 narrows its framing but does not delete it.
- `.planning/phases/21-sdet-authoring-docs-readme-parity/21-CONTEXT.md` §`D-14` — manual-snapshot mechanism for README parity. Phase 24's README re-capture inherits this precedent verbatim.
- `.planning/phases/19-stateful-primitives-domain-ui-integration/19-04-SUMMARY.md` — original surfacing of the inputSchema bug on `create_proxmox_vm`; cite when explaining why the framework-side fix exists (live UAT evidence).
- `.planning/STATE.md` L179 — existing precedent for `resolved-by-deletion` status value (rows can be marked resolved with explanatory note); D-06 row A's `resolved` status follows the same precedent.

### Requirements + roadmap
- `.planning/ROADMAP.md` §`### Phase 24` (L199–L211) — phase goal, anticipated scope, background. Requirements row is `TBD` (per ROADMAP); planner finalizes 1 framework requirement + 1 doc-update requirement at `/gsd-plan-phase 24`.
- `.planning/REQUIREMENTS.md` — append new rows at planning time (no existing rows to read for Phase 24).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_FakeParams`, `_SpyParams`, `_FakeResponse` at the top of `tests/framework/unit/test_tool_factory.py` — established hand-rolled-Pydantic fixture pattern; the new `_FakeParamsWithOptional` follows the same shape (top-of-file module-level class, `BaseModel`-derived, no codegen coupling).
- The `_StubClient` pattern with `self.calls: list[tuple[str, dict]]` in the existing `test_call_success_path_returns_response_cls` (L106–L134) — the new payload tests reuse this exact spy structure; they just assert against `stub.calls[0][1]` (the `arguments` dict) instead of asserting against the `ToolResponse` return value.
- `tf._ACTIVE_SLUG = "homelab_mcp"; tf._REGISTRIES["homelab_mcp"] = {"create_vm": (_FakeParams, _FakeResponse)}` setup pattern repeated in every existing test in the file — autouse reset fixture (referenced at L209) handles teardown.

### Established Patterns
- **Single-line wire-format serializer call** — the entire `ToolWrapper.call` body is intentionally minimal (line 99 is the only serialization concern); Phase 24's change is a kwargs append, not a refactor. SEED-022 protected — the framework does not transform payloads, it only marshals them.
- **Framework unit tests are codegen-tree-independent** — every test in `tests/framework/unit/` uses hand-rolled Pydantic models. The `tests/sdet/_generated/` tree is SDET-side; framework tests do not import from it. D-04 honors this invariant.
- **Phase 21 D-14 manual-snapshot precedent** — README sample blocks are paste-once-with-comment-pointer, no regen script, no regression test (`# mirrors _runner.py output — re-run the framework when output format changes`). Re-snapshot manually when the framework changes the output.

### Integration Points
- `_tool_factory.py:99` is the only `model_dump` call in the SDET `tool().call()` path. Schema validation at construction time (`CreateVmParams(...)`) still uses Pydantic's default behavior; only the wire-marshalling step changes.
- `tests/framework/unit/test_tool_factory.py` is the only framework unit test file that exercises the serializer kwargs. No other test under `tests/framework/` asserts on `model_dump` shape.
- README §`## SDET scenarios` cross-links to `docs/SDET-AUTHORING.md` at L426 with the literal anchor `_CpuBumpManageVmParams(extra='allow') workaround` — if SDET-AUTHORING.md's H2 anchor changes during the soften pass, the README cross-link must update in the same plan.

</code_context>

<specifics>
## Specific Ideas

- The three new tests should be named `test_call_omits_unset_optional_field_from_wire_arguments`, `test_call_serializes_explicit_none_to_wire_null`, `test_call_serializes_explicit_value_unchanged` — each name reads as a Phase 24 contract assertion.
- The kwargs-spy rename in D-03 (to `..._and_exclude_unset`) is a one-test rename plus its docstring; do not also rename the test class or move the test.
- The STATE.md split (D-05..D-08) should be a contiguous patch — Row A directly above Row B at the current L155 position. Subsequent rows shift by one; this is acceptable churn (no line-anchor cross-references exist to rows below L155).
- The `Resolution note` in D-06 Row A must explicitly cite SEED-022 by name and link memory `project_framework_primitives_sdet_safety_principle.md` so the audit trail records *why* explicit-null-testing remains SDET-owned.
- The doc-side rewrite (Claude's discretion) must not break the README L426 cross-link. If the H2 anchor `the-inputschema-workaround-and-why-the-framework-does-not-mask-it` changes, update the cross-link.
- v1.3 close push (per memory `project_v1_3_close_push_and_scrub.md`) follows Phase 24 — keep Phase 24 scope tight so that close push remains a clean separate event.

</specifics>

<deferred>
## Deferred Ideas

- **JSON-Schema-validated wire-format contract test** — surfaced implicitly during test-shape discussion (a test that validates the actual `arguments` dict against the tool's declared `inputSchema`). Out of scope for Phase 24 — would require runtime access to the MCP server's `list_tools` output, which framework unit tests deliberately avoid. Revisit if a future phase introduces a hello-world MCP CI fixture (already on the deferred-items log).
- **Codegen-side test that round-trips a generated Params class through the serializer** — out of scope; codegen tree must remain independent from framework unit tests (D-04 invariant). If this is ever wanted, it belongs under `tests/sdet/` against a hello-world MCP fixture, not under `tests/framework/`.
- **README sample regen script (`scripts/regen-readme-sample.py`)** — already Phase 21 deferred (Phase 21 §Deferred Ideas); Phase 24's re-capture inherits the manual-snapshot precedent. Do not re-promote.
- **Auditing `_runner.py` for similar `model_dump(mode='json')` call sites** — Phase 24 scope is `_tool_factory.py:99` only. A repo-wide sweep is not part of this phase; if other serialization sites exist that warrant the same fix, surface them in a separate phase (no evidence today that they do).

</deferred>

---

*Phase: 24-tool-call-serializer-omits-unset-optional-params-exclude-uns*
*Context gathered: 2026-05-14*
