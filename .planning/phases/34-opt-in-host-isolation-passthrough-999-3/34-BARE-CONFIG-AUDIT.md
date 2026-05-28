# Phase 34 ISOL-05 — Bare `Config()` Caller Audit

**Audited:** 2026-05-26 (Phase 34 plan-time research)
**Source of truth:** `34-RESEARCH.md` Finding 4 + Bare `Config()` Inventory section.

## Phase 34-09 correction

Bare `Config()` RAISES `pydantic.ValidationError` because `Config.test_code` is a REQUIRED
field with no default (Phase 21.1). The earlier audit classification (that bare `Config()`
would simply use the host_isolation strict default) was false — ValidationError fires before
any default is evaluated. All four fallback/scenario sites now use explicit
`Config(test_code=TestCodeConfig(generated_root='tests/test_code/_generated'))` construction.

## Summary

This audit IS the ISOL-05 deliverable. `34-CONTEXT.md` Claude's Discretion locks the shape:
"inventory is the deliverable, NOT a per-site refactor." The audit documents every bare
`Config()` call site in `src/` and `tests/`, distinguishes actionable call sites from
incidental references inside docstrings or comments, and points at the four landing plans
where the remediations land (or are intentionally NOT applied).

Two corrections versus the CONTEXT.md initial framing land here:

1. **`src/` actionable count is 2, not 3.** CONTEXT.md cited `cli.py:15`, `fixtures.py:111`,
   and `test_code/session.py:mcp_session`. `cli.py:15` is a docstring reference inside
   `_load_config`'s docstring — not a call site. The two real call sites in `src/` are
   `fixtures.py:111` (stash-miss fallback) and `test_code/session.py:mcp_session`
   (HIGH RISK — runs after stash population during fixture resolution and bypasses the
   resolved operator YAML under passthrough).

2. **`tests/` audit produces a categorized inventory, not a sweep refactor.** Of the dozens
   of bare-Config references across `tests/framework/...` and `tests/test_code/...`, only
   one ships an actionable add (the `host_isolation` default pin from Plan 34-01), two ship
   inline-comment annotations (the operator-authored Proxmox scenario via Plan 34-06
   Task 3), and one is explicitly NOT updated (`tests/framework/unit/test_sdet_fixtures.py`
   keeps its monkeypatch shim load-bearing because Plan 34-06 Task 2 preserves the
   bare-Config fallback at `test_code/session.py:mcp_session`).

Landing plans referenced by this audit:

- `.planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-01-PLAN.md` — Config field
  + the `test_host_isolation_default_is_strict` defaults pin (Phase 35 SHIM-09 capstone).
- `.planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-04-PLAN.md` — Task 1
  audit comment at `fixtures.py:111`.
- `.planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-06-PLAN.md` — Task 2
  stash-routing remediation at `test_code/session.py:mcp_session`; Task 3 inline comments at
  `tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py` (`module:_load_generated_homelab_mcp`, `module:proxmox_vm_lifecycle_readme`).
- `.planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-07-PLAN.md` — scaffold
  emission of the `host_isolation: strict` line in `config-init` output; smoke check the
  round-trip through `tests/framework/test_config_init_cli.py`.

## `src/` Inventory

| file:line | Category | Recommended Remediation | Landing Plan |
|-----------|----------|-------------------------|--------------|
| `src/mcp_test_framework/fixtures.py:111` | Stash-miss fallback — bare Config() RAISES ValidationError (test_code REQUIRED since Phase 21.1); now uses explicit Config(test_code=TestCodeConfig(generated_root=...)) | Explicit construction (Phase 34-09) | Plan 34-04 Task 1 + 34-09 |
| `src/mcp_test_framework/test_code/session.py:mcp_session` | **HIGH RISK** — runs after stash population during fixture resolution; bypasses operator YAML under passthrough; bare Config() RAISES ValidationError (test_code REQUIRED); now uses explicit Config(test_code=TestCodeConfig(generated_root=...)) | Explicit construction (Phase 34-09) | Plan 34-06 Task 2 + 34-09 |
| `src/mcp_test_framework/cli.py:15` (docstring) | Not a call site — docstring reference inside `_load_config`'s docstring | No remediation | n/a |
| `src/mcp_test_framework/cli.py:471` (docstring) | Not a call site | No remediation | n/a |
| `src/mcp_test_framework/cli.py:551` (comment) | Not a call site | No remediation | n/a |
| `src/mcp_test_framework/fixtures.py:100, 208` (docstrings) | Not call sites | No remediation | n/a |

Net `src/` actionable count: **2** (CONTEXT.md initially flagged 3; cli.py:15 is doc text, not a call site).

## `tests/` Inventory

| file:line | Category | Recommended Remediation | Landing Plan |
|-----------|----------|-------------------------|--------------|
| `tests/framework/smoke/test_smoke_homelab_mcp.py:40` (comment) | Not a call site | No remediation | n/a |
| `tests/framework/test_config_init_cli.py:104, 133` (comments / inline kwargs) | Tests mode directly via config-init scaffold round-trip | After plan 34-07 scaffold edit, verify the round-trip still passes | Plan 34-07 smoke check |
| `tests/framework/test_tool_config.py:36, 299` | Mode-agnostic; constructs `Config(test_code=stub)` for ToolConfig table tests | No remediation (strict default preserves behavior) | n/a |
| `tests/framework/unit/test_config.py:280, 287, 300, 314, 358, 365` | Mode-agnostic; pure Config-defaults validation | Add `test_host_isolation_default_is_strict` (Phase 35 SHIM-09 capstone pin) | Plan 34-01 Task 2 |
| `tests/framework/unit/test_mcp_config_fixture.py:11, 76, 100` (test bodies + comments) | Tests mode directly — Tier 1 stash hit, Tier 2 bare fallback | No remediation | n/a |
| `tests/framework/unit/test_runner_migration.py:101, 105, 118, 150, 166, 209` | Mode-agnostic; verifies env-var fallback removal (Phase 31 SHIM-05) | No remediation | n/a |
| `tests/framework/unit/test_sdet_fixtures.py:122, 147` | Tests `test_code/session.py:mcp_session`'s bare Config() via `_install_session_config` monkeypatch shim | CONDITIONAL — NOT updated because plan 34-06 Task 2 preserves bare-Config fallback at `test_code/session.py:mcp_session` (Open Question 3 recommendation (b)); Phase 34-09 replaces the fallback with explicit construction, so the monkeypatch shim now installs an explicit Config | n/a |
| `tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py` (`module:_load_generated_homelab_mcp`, `module:proxmox_vm_lifecycle_readme`) | Operator-authored test-code scenario; bare Config() raised ValidationError -- module-level demoted to wrong-reason skip, fixture-body raised on live_homelab | Explicit Config(test_code=TestCodeConfig(generated_root=...)) at both sites (Phase 34-09); bare Config() raised ValidationError — module-level demoted to wrong-reason skip, fixture-body raised on live_homelab | Plan 34-06 Task 3 + 34-09 |
| `tests/framework/unit/test_config_init.py:100` (comment) | Not a call site | No remediation | n/a |

Net `tests/` actionable count: **1 add** (defaults pin — Plan 34-01) + **2 inline comments** (Plan 34-06 Task 3) + **0 conditional updates** (test_sdet_fixtures preserved by fallback-alive recommendation (b)).

## Anti-goals

The audit deliberately does NOT propose any of the following directions. Each is locked
off-table by a memory entry that future planners should cite if a fixer or research
proposal drifts in this direction:

- **no keyring faking** — locked by memory `project_isolation_blocks_live_uat.md`
  (2026-05-19 Phase 30 UAT-1). A test-only keyring backend or credential-mock layer
  trades the real-world reachability the operator opted into for a synthetic surface
  the framework would then have to reason about. Operator opted into reachability;
  the framework does not virtualize it.
- **no per-env-var allowlist** — locked by memory
  `project_framework_primitives_sdet_safety_principle.md` (SEED-022). The framework
  does no SUT-safety reasoning, so it has no business deciding which environment
  variables are "dangerous" under passthrough. The binary `strict | passthrough`
  surface keeps the framework primitive caller-passes-data.
- **no per-tool isolation mode** — locked by the same SEED-022 memory. Per-tool mode
  re-introduces the safety-classification problem and inflates the test matrix.
- **no SUT-aware safety reasoning** — same lock. Even under passthrough, the
  framework's stance is "the operator decides what to call." No prompt-before-destructive
  banners, no auto-detection of dangerous tools.
- **no audit-only deferral phase** — locked by memory `feedback_phase_scope_intent.md`.
  The phase title names the audit (ISOL-05); the audit lands in Phase 34, not a
  separate cross-cutting cleanup phase.

## Cross-references

- `.planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-CONTEXT.md` —
  Claude's Discretion ISOL-05 ("inventory is the deliverable; NOT a per-site refactor").
- `.planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-RESEARCH.md` —
  Finding 2 (stash timing safety) + Finding 4 (full inventory tables) + Open Question 3
  (recommendation (b): keep bare-Config fallback alive).
- `.planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-PATTERNS.md` —
  stash-lookup-with-fallback pattern (`fixtures.py:108-111`) reused at
  `test_code/session.py:mcp_session`.
- `.planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-01-PLAN.md` —
  Config field + defaults pin.
- `.planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-04-PLAN.md` —
  `fixtures.py:111` annotation.
- `.planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-06-PLAN.md` —
  `test_code/session.py:mcp_session` stash routing + Proxmox scenario annotations.
- `.planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-07-PLAN.md` —
  scaffold emission of the `host_isolation:` line.
