# Phase 24: Tool call serializer omits unset optional params - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-14
**Phase:** 24-tool-call-serializer-omits-unset-optional-params-exclude-uns
**Areas discussed:** Test coverage shape for exclude_unset semantics, STATE.md Deferred Items entry rescope

---

## Area selection

| Option | Description | Selected |
|--------|-------------|----------|
| README sample re-capture mechanism | Choose between resurrecting deleted test, one-shot script, or manual paste; also rewrite "✗ rows are the framework doing its job" framing paragraph | |
| SDET-AUTHORING.md inputSchema-workaround section depth | Soften in-place, demote to Advanced subsection, or restructure as intentional-null-testing example (Phase 21 D-06 lock-in respected) | |
| Test coverage shape for exclude_unset semantics | Lock the three behaviors (unset omitted / explicit None on wire / explicit value on wire) via payload tests, spy update, or both | ✓ |
| STATE.md Deferred Items entry rescope | Resolve the existing row with audit note, keep open with narrowed scope, or split into two rows (framework-side resolved + upstream still open) | ✓ |

**User's choice:** discuss the two technical areas; defer README + SDET-AUTHORING ripple to planner discretion under existing Phase 21 precedents (D-14 manual snapshot, D-06 SEED-022 teaching lock).

---

## Test coverage shape for exclude_unset semantics

### Q1: Test mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Payload-asserting tests only | 3 new tests inspecting `_StubClient.calls[0][1]`; existing kwargs-spy test gets one-line update to also assert `exclude_unset=True` so 'how' is locked alongside the new contract tests | ✓ |
| Extend existing kwargs-spy only | Add `assert captured_kwargs.get('exclude_unset') is True` to existing test. Smallest diff. Still proves HOW not WHAT — risks false-positive failures under serializer refactor | |
| Both: payload tests + spy update | Defense in depth; payload tests prove the user-visible contract, spy documents the implementation choice. ~4 tests total | |

**User's choice:** Payload-asserting tests only.
**Notes:** Existing kwargs-spy still picks up the `exclude_unset=True` assertion per the option's wording — three new tests carry the contract weight, one-line addition to existing spy locks the implementation choice.

### Q2: Test fixture model

| Option | Description | Selected |
|--------|-------------|----------|
| Hand-rolled Pydantic model in test file | `_FakeParamsWithOptional(BaseModel)` with one required + one `Optional[str] = None` field. Matches existing `_FakeParams` / `_SpyParams` pattern. No codegen-tree dependency at test-collection time | ✓ |
| Import real codegen-generated Params class | `from tests.sdet._generated.homelab_mcp import CreateProxmoxVmParams`. Higher realism but couples framework unit test to SDET-side generated artifact | |

**User's choice:** Hand-rolled Pydantic model in test file.
**Notes:** Honors the existing invariant — `tests/framework/unit/` is codegen-tree-independent; the test asserts a generic Pydantic-serialization contract, not a homelab-mcp-shaped one.

---

## STATE.md Deferred Items entry rescope

### Q1: Rescope shape

| Option | Description | Selected |
|--------|-------------|----------|
| Split into two rows | Row A resolved (framework-side default behavior; Phase 24 close), Row B open with narrowed scope (upstream bug; explicit-null-testing still hits). Cleanest audit trail; costs one extra row | ✓ |
| Keep one row, rewrite as Open-with-narrowed-scope | In-place rewrite; drop "framework deliberately does NOT mask" framing; add "Phase 24 reframe" alongside original deferred-at note. One less row but loses milestone signal that Phase 24 resolved part of the concern | |
| Mark Resolved-with-residue, add audit note | Single row, new `resolved-with-residue` status (precedent: `Resolved-by-deletion` at L179). Combined cell text documenting both halves | |

**User's choice:** Split into two rows.
**Notes:** Clean audit trail — Phase 24 close records the framework-side resolution as a distinct row; upstream bug preserved as a separate open row so the deferred-items timeline still shows the open upstream concern.

---

## Claude's Discretion

- **README sample re-capture mechanism** — planner picks between Phase 21 D-14 manual-snapshot precedent (default), one-shot script, or manual paste. Constraint: the framing paragraph at README L420–L427 must change with the output (PASS rows no longer demonstrate "framework doing its job" the same way FAIL rows did).
- **`docs/SDET-AUTHORING.md` `## The inputSchema workaround` section depth** — Phase 21 D-06 lock respected (`_CpuBumpManageVmParams(extra="allow")` pattern stays as SEED-022 teaching moment). Planner picks rewrite shape; framing narrows from "always needed for Proxmox tools" to "needed only when testing null-handling explicitly." If H2 anchor changes, README L426 cross-link must update in the same plan.
- Exact wording of test names beyond the suggested `test_call_omits_unset_optional_field_from_wire_arguments` / `test_call_serializes_explicit_none_to_wire_null` / `test_call_serializes_explicit_value_unchanged` triple is planner-discretion.
- STATE.md row positioning within the Deferred Items table (Row A above Row B at current L155 position) is the recommended layout; planner may adjust if categorically-grouped insertion serves the table better, provided the deferred-at timeline column reads chronologically.

## Deferred Ideas

- **JSON-Schema-validated wire-format contract test** — out of scope; would require runtime MCP `list_tools` access (framework unit tests deliberately avoid). Revisit when hello-world MCP CI fixture lands (already on deferred-items log).
- **Codegen-side round-trip test** — would belong under `tests/sdet/` against a future hello-world MCP fixture, not `tests/framework/`. Out of scope for Phase 24 per the framework-unit-tests-codegen-independent invariant.
- **README sample regen script** — already Phase 21 deferred; manual-snapshot precedent holds. Not re-promoted.
- **Repo-wide audit of other `model_dump(mode='json')` call sites** — Phase 24 is `_tool_factory.py:99` only. No evidence today other sites warrant the same fix; surface as a separate phase if one emerges.
