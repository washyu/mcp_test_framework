---
phase: 34-opt-in-host-isolation-passthrough-999-3
plan: 06
subsystem: bare-config-audit
tags: [audit, stash-routing, test-code-fixture, isol-05, seed-022]
requires:
  - Config.host_isolation field (plan 34-01)
  - _mcp_contracts_config stash population (Phase 27 / Phase 31 seam)
provides:
  - "34-BARE-CONFIG-AUDIT.md deliverable (ISOL-05 inventory)"
  - "mcp_session(request, mcp_client) stash-routed fixture signature"
  - "ISOL-05 audit annotations on the Proxmox scenario test"
affects:
  - .planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-BARE-CONFIG-AUDIT.md (new)
  - src/mcp_test_framework/test_code/session.py
  - tests/framework/unit/test_mcp_session_host_isolation_stash.py (new)
  - tests/framework/unit/test_sdet_fixtures.py
  - tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py
tech-stack:
  added: []
  patterns:
    - "Stash-lookup-with-fallback (canonical Phase 27 / Phase 31 seam at fixtures.py:108-111) reused at test_code/session.py"
    - "Bare-Config fallback preserved for framework self-tests + monkeypatch shims (Open Question 3 recommendation (b))"
    - "Inventory-as-deliverable (CONTEXT.md Claude's Discretion ISOL-05 -- audit ships an inventory, NOT a per-site refactor)"
    - "TDD RED/GREEN gate sequence for the stash-routing task"
key-files:
  created:
    - .planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-BARE-CONFIG-AUDIT.md
    - tests/framework/unit/test_mcp_session_host_isolation_stash.py
  modified:
    - src/mcp_test_framework/test_code/session.py
    - tests/framework/unit/test_sdet_fixtures.py
    - tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py
decisions:
  - "ISOL-05 deliverable shape: inventory document, not a per-site refactor (CONTEXT.md Claude's Discretion lock honored)"
  - "Open Question 3 recommendation (b) implemented: bare-Config fallback preserved at session.py so _install_session_config monkeypatch shim stays load-bearing"
  - "Test infrastructure (_run_fixture helper + missing-module test) updated to construct a fake request whose stash is empty; preserves the shim's pre-Phase-34 contract"
  - "src/ actionable count documented as 2 (NOT 3 -- cli.py:15 is docstring text, not a call site)"
metrics:
  duration: ~20 minutes
  tasks_completed: 3
  files_created: 2
  files_modified: 3
  tests_added: 3
  framework_tests_passing: 781
completed: 2026-05-27
---

# Phase 34 Plan 06: Bare `Config()` Audit + `mcp_session` Stash Routing Summary

**One-liner:** Shipped the ISOL-05 audit deliverable (`34-BARE-CONFIG-AUDIT.md`), routed the highest-risk bare-`Config()` call site (`test_code/session.py:67`) through the plugin's `_mcp_contracts_config` stash with the framework-self-test fallback preserved, and annotated the operator-authored Proxmox scenario file's two bare-`Config()` sites with inline ISOL-05 audit comments.

## Outcome

Wave 2 ships the audit half of ISOL-05:

- **Inventory document** at `.planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-BARE-CONFIG-AUDIT.md` — 15 rows total (6 `src/` + 9 `tests/`), categorized by remediation type, cross-referenced to the four landing plans, and explicit about the "2 actionable `src/` sites" finding that corrects CONTEXT.md's initial count of 3.
- **`test_code/session.py:67` remediation** — the HIGH-RISK site flagged in RESEARCH Finding 2. The `mcp_session` fixture now takes `request: pytest.FixtureRequest` as its first parameter and routes through `request.session.config._mcp_contracts_config` with a bare-`Config()` fallback. Operator-driven runs (CLI or library) reach the resolved YAML's `host_isolation`; framework self-tests that bypass the plugin keep their pre-Phase-34 fallback intact.
- **Proxmox scenario annotations** — two 2-line `ISOL-05 audit, Phase 34:` inline comments at the bare-`Config()` sites in `tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py`. Documents the implicit `strict` default + the field-non-consumption clause; pure documentation, no behavior change.

The operator-real path under `passthrough` now consumes the YAML-resolved `host_isolation` value at every spawn site AND at the test-code-author session-activation site. The framework-primitive contract (SEED-022) holds: `_isolation.py` still takes `mode: Literal[str]`, not a `Config`; `mcp_session` consumes a Config-shaped object via the stash but does not import config plumbing.

## Final `mcp_session` Fixture Signature (verbatim)

```python
@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def mcp_session(
    request: pytest.FixtureRequest,
    mcp_client: McpTestClient,
):
    """Live ClientSession driver + active test-code registry."""
    ...
```

## Final Stash-Lookup-with-Fallback Block (verbatim)

```python
    # Step 3: load the generated package from cfg.test_code.generated_root/<slug>/.
    # Audit: route through the plugin stash so the operator's resolved Config
    # (and its host_isolation setting) reaches the fixture. Bare-Config fallback
    # preserved for framework self-tests + the test_sdet_fixtures
    # `_install_session_config` monkeypatch shim. Mirrors fixtures.py:108-111.
    cfg = getattr(request.session.config, "_mcp_contracts_config", None)
    if cfg is None:
        cfg = Config()  # framework-self-test fallback; mirrors fixtures.py:108-111
    generated_root = cfg.test_code.generated_root
```

Both branches present: stash-hit (operator-real path) AND bare-`Config()` fallback (framework-self-test path). The fallback line preserves the `_install_session_config` monkeypatch shim's contract verbatim.

## Audit Deliverable

- **Path:** `.planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-BARE-CONFIG-AUDIT.md`
- **Total inventory rows:** 15 (6 `src/` rows + 9 `tests/` rows)
- **Actionable `src/` sites:** 2 (was reported as 3 in CONTEXT.md; `cli.py:15` is docstring text, not a call site — correction documented in the audit's Summary section)
- **Actionable `tests/` sites:** 1 add (defaults pin via Plan 34-01) + 2 inline comments (this plan's Task 3) + 0 conditional updates (test_sdet_fixtures preserved by recommendation (b))
- **Anti-goals section:** four locked off-table directions (no keyring faking, no per-env-var allowlist, no per-tool isolation mode, no SUT-aware safety reasoning) each citing the memory entry that locks them
- **Cross-references:** four landing plans (34-01, 34-04, 34-06, 34-07) + CONTEXT.md + RESEARCH.md + PATTERNS.md

## Proxmox Scenario Annotations

- **File:** `tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py`
- **Sites annotated:** 2 (L67 in `_load_generated_homelab_mcp`, L196 in `proxmox_vm_lifecycle_readme` fixture)
- **Annotation template** (per RESEARCH PATTERNS.md):
  ```python
  # NOTE (ISOL-05 audit, Phase 34): bare Config() in operator-authored scenario.
  # Inherits host_isolation='strict' default; scenario does not consume the field.
  cfg = Config()
  ```
- **Behavior change:** none (pure annotation).
- **File still collects cleanly** under `pytest --co` (skipped at module level via `pytest.skip(allow_module_level=True)` because the homelab-mcp generated classes are not available without a live `gen-test-classes` run — this is the pre-existing live-only guard, not a Phase-34 regression).

## Acceptance Criteria

All plan-level `<verification>` and `<success_criteria>` checks pass:

| Check                                                                          | Result |
| ------------------------------------------------------------------------------ | ------ |
| `.planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-BARE-CONFIG-AUDIT.md` exists | yes (115 lines) |
| Audit document references all four landing plans (34-01, 34-04, 34-06, 34-07) | 9 references found |
| Audit document references anti-goals + memory locks                            | 5 lock-related phrases including "no keyring faking" |
| Bare `Config()` sites in `src/mcp_test_framework/test_code/session.py`         | 1 (only the fallback inside the `if cfg is None:` branch) |
| `request: pytest.FixtureRequest` in `mcp_session` signature                    | present (L57) |
| Stash-lookup line + fallback line in `session.py`                              | both present (L74, L76) |
| `ISOL-05 audit, Phase 34` occurrences in Proxmox scenario file                 | 2 (matches the 2 bare-`Config()` sites) |
| `uv run pytest tests/framework/unit/test_sdet_fixtures.py -x`                  | 12 passed (monkeypatch shim still works -- recommendation (b) verified) |
| `uv run pytest tests/framework/ -x`                                            | 781 passed, 2 skipped, 18 deselected, 1 xfailed |
| `tests/framework/unit/test_no_planning_ids_in_src.py` planning-ID gate         | passes |

## Tasks Completed

| Task | Name                                                                       | RED Commit | GREEN Commit | Files                                                                          |
| ---- | -------------------------------------------------------------------------- | ---------- | ------------ | ------------------------------------------------------------------------------ |
| 1    | Create the `34-BARE-CONFIG-AUDIT.md` deliverable                           | n/a        | 1a39f45      | `.planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-BARE-CONFIG-AUDIT.md` |
| 2    | Route `mcp_session` fixture through plugin stash with bare-Config fallback | 7bbe7ec    | 38908fd      | `src/mcp_test_framework/test_code/session.py` + 2 test files                   |
| 3    | Add 2-line ISOL-05 audit comments to operator-authored Proxmox scenario    | n/a        | 602f3ae      | `tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py`                   |

## Commits (chronological)

| Hash       | Type | Message                                                                                              |
| ---------- | ---- | ---------------------------------------------------------------------------------------------------- |
| `1a39f45`  | docs | add ISOL-05 bare `Config()` caller audit deliverable                                                 |
| `7bbe7ec`  | test | add failing pins for `mcp_session` stash routing (RED)                                               |
| `38908fd`  | feat | route `mcp_session` through plugin stash with bare-Config fallback (GREEN)                           |
| `602f3ae`  | docs | annotate bare `Config()` sites in Proxmox scenario with ISOL-05 audit comments                       |

## TDD Gate Compliance

Per-task discipline observed for Task 2 (the only `tdd="true"` task in the plan):

- Task 2: `test(...)` 7bbe7ec → `feat(...)` 38908fd (RED → GREEN). RED gate verified by running the new pin file and observing the signature-mismatch failure at `test_mcp_session_signature_takes_request_as_first_param`.

REFACTOR gate skipped for Task 2 -- code landed in its final shape; no cleanup pass needed.

Tasks 1 and 3 are documentation tasks (no `tdd="true"` flag) and land as single commits.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reworded `session.py` audit comment to avoid the planning-ID leak gate**

- **Found during:** Task 2 GREEN authoring
- **Issue:** The plan's verbatim audit comment block leads with `# ISOL-05 (Phase 34): route through plugin stash …`. The repo's planning-ID leak gate at `tests/framework/unit/test_no_planning_ids_in_src.py` uses the locked regex `(CLI|PERSONA|CODEGEN|SAFE|RUNNER|UX|ISOL|JUNIT|SURFACE|TEST|CLEAN|DOC|UI|SDET|STATE|PREFLIGHT|SCRUB|RELOC)-\d+|\bD-\d+\b`. Writing the literal string `ISOL-05` inside `src/` would have tripped the gate. The plan's `acceptance_criteria` for Task 2 included `grep -nE "ISOL-05" src/mcp_test_framework/test_code/session.py` exits 0 — this expectation is incompatible with the leak gate.
- **Fix:** Reworded the comment to lead with `# Audit:` (planning-ID-free) — same idiom Plan 34-04 Task 1 used for `fixtures.py:111`. The narrative content (stash-routing reason, fallback rationale, mirror reference to `fixtures.py:108-111`) is preserved verbatim. The planning ID lives in PLAN.md, this SUMMARY, and the commit messages — the operator's source remains plain operator-tone language.
- **Files modified:** `src/mcp_test_framework/test_code/session.py` (the comment immediately above the stash-lookup line).
- **Commit:** Folded into `38908fd` (Task 2 GREEN); the rewording lands before the GREEN commit, so the planning-ID gate stays green throughout.
- **Why Rule 1 not Rule 4:** Identical pattern to Plan 34-04's deviation and Plan 34-03's deviation. The leak gate (D-04 hard zero, no allowlist) is unambiguous and the operator-source idiom for "this is an audit note pointing at the inventory document" is already established. No architectural decision needed.

**2. [Rule 3 - Blocker] Updated `_run_fixture` helper + missing-module test to pass a fake request**

- **Found during:** Task 2 GREEN — running the existing `tests/framework/unit/test_sdet_fixtures.py` after the signature change
- **Issue:** `test_sdet_fixtures.py:_run_fixture` (helper) and `test_mcp_session_fail_loud_on_missing_generated_module` (test body) both called the unwrapped fixture via `func(client)` — a single positional argument. After adding `request: pytest.FixtureRequest` as the first parameter to `mcp_session`, `client` would land in `request` and the call would fail at fixture entry. Without updating the test driver, the plan's `<acceptance_criteria>` requirement "`uv run pytest tests/framework/unit/test_sdet_fixtures.py -x` exits 0" would not hold.
- **Fix:** Both call sites now construct a `SimpleNamespace`-based fake request whose `session.config._mcp_contracts_config = None` so the bare-Config fallback fires — which is the exact path `_install_session_config` monkeypatch shim depends on. The shim itself (L142-163) is untouched; only the test driver that invokes the fixture got the signature update. Open Question 3 recommendation (b) is honored verbatim: the shim's pre-Phase-34 contract is preserved by the bare-Config fallback, not by reverting the signature change.
- **Files modified:** `tests/framework/unit/test_sdet_fixtures.py` (the `_run_fixture` helper docstring + body, and the missing-module test's direct `func(client)` invocation).
- **Commit:** Folded into `38908fd` (Task 2 GREEN) alongside the production-code change so the test suite stays green at every commit.
- **Why Rule 3 not Rule 4:** Signature-change ripples in the test driver are mechanical wiring updates, not an architectural decision. The plan acceptance criteria themselves (preserve the monkeypatch shim's contract + run the framework tests green) name the constraint; updating the test driver is the smallest valid implementation.

## Authentication Gates

None.

## Threat Flags

None. The four threat-register entries (T-34-06-01..04) are all mitigated as planned:

- T-34-06-01 (passthrough bypass at `test_code/session.py:67`): mitigated by the stash-lookup remediation in Task 2.
- T-34-06-02 (monkeypatch shim breaks if fallback removed): mitigated by recommendation (b) — bare-Config fallback preserved at the `if cfg is None:` branch.
- T-34-06-03 (scenario silently misses passthrough opt-in): annotated, not refactored, per CONTEXT.md "audit is a deliverable, not a refactor."
- T-34-06-04 (future bare-Config drift): cross-milestone enforcement is Phase 35 SHIM-09's job; Phase 34 ships the v1.5 inventory snapshot.

## Known Stubs

None. The inventory document, the stash routing, and the scenario annotations are each complete deliverables; no follow-up plan needs to re-touch this surface within Phase 34.

## Verification Results

- `uv run pytest tests/framework/` → 781 passed, 2 skipped, 18 deselected, 1 xfailed (no regressions; 3 new tests added in `test_mcp_session_host_isolation_stash.py`).
- `uv run pytest tests/framework/unit/test_sdet_fixtures.py -x` → 12 passed (monkeypatch shim still works — recommendation (b) verified).
- `uv run pytest tests/framework/unit/test_no_planning_ids_in_src.py -x` → 1 passed (planning-ID gate green).
- `uv run pytest tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py --co` → file collects cleanly (skipped at module level via the pre-existing live-only guard; no syntax error introduced).
- `grep -cE "= Config\(\)" src/mcp_test_framework/test_code/session.py` → 1 (only the fallback remains; the original bare site is gone).
- `grep -cE "ISOL-05 audit" tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py` → 2 (one per bare-`Config()` site).

## Self-Check: PASSED

- Created files exist:
  - `.planning/phases/34-opt-in-host-isolation-passthrough-999-3/34-BARE-CONFIG-AUDIT.md` -- FOUND
  - `tests/framework/unit/test_mcp_session_host_isolation_stash.py` -- FOUND
- Modified files exist:
  - `src/mcp_test_framework/test_code/session.py` -- FOUND
  - `tests/framework/unit/test_sdet_fixtures.py` -- FOUND
  - `tests/test_code/test_proxmox_vm_lifecycle_readme_sample.py` -- FOUND
- Commits exist (`git log --oneline`):
  - `1a39f45` -- FOUND
  - `7bbe7ec` -- FOUND
  - `38908fd` -- FOUND
  - `602f3ae` -- FOUND
