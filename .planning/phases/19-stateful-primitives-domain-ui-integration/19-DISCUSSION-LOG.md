# Phase 19 Discussion Log

**Phase:** 19 — Stateful primitives + domain UI integration
**Date:** 2026-05-13
**Mode:** default (interactive, 1–2 questions per area)
**Audience:** Human reference (audits, retrospectives). NOT consumed by downstream agents.

---

## Gray areas selected

| Area | Selected | Notes |
|------|----------|-------|
| Dogfood scenario design | ✓ | Live Proxmox, real VM, CPU bump, VMID isolation. |
| Tool-group key for the renderer | ✓ | Module filename → group; function name → row label. |
| STATE-02 cleanup-on-failure self-test | ✓ | Direct fixture + finalizer counter; no MCP, no subprocess. |
| State object & module-scope passing pattern | ✓ | Per-scenario `ScenarioState` dataclass with typed response fields. |

---

## Area 1: Dogfood scenario design

### Q1: Live Proxmox vs preview/dry-run/mock?

**Options presented:** Live (real VM) [Recommended] / Live with isolated VMID range / Preview tools / Mock MCP server.

**User selection:** Live Proxmox — real VM.

**Notes captured:**
- Authentic dogfood, matches v1.3 thesis ("stateful testing is observably real").
- Acceptable trade-off that the test fails loud if Proxmox unreachable until Phase 20 ships `requires_homelab`.
- Mock MCP would violate the black-box principle (Phase 04.1 invariant).
- D-01 locked.

### Q2: What does `modify_vm` change?

**Options presented:** CPU core bump (1→2) / Memory bump (1024→2048) / Tags/notes/description / You decide.

**User selection:** CPU core count bump (1→2).

**Notes captured:**
- ROADMAP wording matches (`modify_accepts_cpu_increase`).
- Re-read assertion via `get_proxmox_vm_status.data.cpus == 2`.
- D-02 locked.

### Q3: VMID isolation?

**Options presented:** Reserved range + name prefix [Recommended] / Random VMID from Proxmox allocator / Manual via config / You decide.

**User selection:** Reserved VMID range + name prefix.

**Notes captured:**
- VMID range 9990–9999, name prefix `mcptf-dogfood-{timestamp}`.
- Teardown sweeps stranded prior-crash VMs.
- Made configurable via `homelab.proxmox.dogfood_vmid_range` block (Claude's extension to lock structural isolation without forcing operators with conflicting ranges to fork).
- D-03 locked.

---

## Area 2: Tool-group key for the renderer

### Q1: How is a scenario "group" identified?

**Options presented:** Module filename [Recommended] / Explicit pytest marker / Module-scope fixture name / Pytest class wrapping each scenario.

**User selection:** Module filename.

**Notes captured:**
- Zero SDET-facing API surface — the file you write IS the scenario name.
- JUnit `classname` carries it; renderer reads it when `nodeid.startswith("tests/sdet/")`.
- Convention: one scenario per file.
- D-04 (CONTEXT.md D-08) locked.

### Q2: How are individual rows rendered?

**Options presented:** Function name verbatim [Recommended] / Docstring first line / Nodeid suffix / You decide.

**User selection:** Function name verbatim (with `test_` stripped).

**Notes captured:**
- Matches ROADMAP examples (`create_returns_pending_vm`, `modify_accepts_cpu_increase`).
- Operator reads rows as narrative.
- Same PASS/✗/SKIP glyphs + em-dash failure-detail as contract.
- D-05 (CONTEXT.md D-09) locked.

---

## Area 3: STATE-02 cleanup-on-failure self-test

### Q1: What is the shape of the self-test?

**Options presented:** Direct fixture w/ finalizer counter [Recommended] / Subprocess pytest + JUnit XML / Both shapes / Skip.

**User selection:** Direct fixture w/ finalizer counter.

**Notes captured:**
- Lives at `tests/framework/unit/test_state_cleanup_on_failure.py`.
- Module-scope counter, `xfail(strict=True)` on deliberate-failure consumer, second test asserts counter == 1.
- No MCP, no subprocess, <100 ms.
- "Both shapes" rejected — STATE-02 is fully pinned by D-06's counter; subprocess JUnit-XML would 50× the cost for the same proof.
- D-06 + D-07 locked.

---

## Area 4: State object & module-scope passing pattern

### Q1: What does the module-scope fixture yield?

**Options presented:** ScenarioState dataclass [Recommended] / Mutate generated Response instance / Plain dict or SimpleNamespace / Tuple unpacking.

**User selection:** ScenarioState dataclass.

**Notes captured:**
- Per-scenario dataclass with typed fields (`created: CreateProxmoxVmResponse; modified: ManageProxmoxVmResponse | None`).
- Pattern, not a base class — each scenario owns its state shape; framework ships no abstract `ScenarioState` superclass.
- Untyped containers (dict, SimpleNamespace, tuple) rejected: STATE-03 says "typed via the response class".
- Mutating generated Response instances rejected: "do not hand-edit" header.
- D-04 (state) + D-05 (rejections) locked → CONTEXT.md D-04 + D-05.

### Q2: `pytest-order` adoption for STATE-04?

**Options presented:** Recipe only — no dev-dep [Recommended] / Add as dev-dep, dogfood it / Add as dev-dep, no dogfood / You decide.

**User selection:** Recipe only — no dev-dep.

**Notes captured:**
- Dogfood is single-file by D-04, so framework itself never needs cross-file ordering.
- Recipe lands in Phase 21's `docs/SDET-AUTHORING.md`.
- Phase 19 plans MUST NOT add `pytest-order` to `pyproject.toml`.
- D-11 locked (CONTEXT.md D-11).

---

## Scope creep redirected

None this session. The user stayed inside the phase domain across all four areas; no out-of-scope ideas surfaced.

## Claude's discretion

- The `homelab.proxmox.dogfood_vmid_range` config block (D-03) was a Claude extension to the "Reserved VMID range + name prefix" choice. The user picked the range-based isolation; Claude added the config-knob so the default range doesn't force operators with conflicting VMID conventions to fork.
- Open items in CONTEXT.md's "Open / inferred" section deliberately left for the planner: `parse_junit_xml` extension shape, scenario fixture wiring detail (`mcp_session` vs `_ACTIVE_CLIENT`), sweep failure handling.

## Canonical refs added during discussion

- `.planning/phases/18-sdet-test-surface-typed-errors/18-CONTEXT.md`, `18-06-SUMMARY.md`, `18-07-SUMMARY.md` — Phase 18 surfaces Phase 19 builds on.
- `src/mcp_test_framework/_runner.py`, `sdet/session.py`, `sdet/generated/homelab_mcp/`, `tests/sdet/conftest.py`, `tests/sdet/test_basic_call.py` — code-level integration points.
- Memory: `SEED-022 / framework primitives + SDET safety principle` — cited to justify rejecting "framework auto-detects destructive tools" suggestions if they surface during planning.
