---
phase: 23-test-suite-debt-cleanup
plan: 01
subsystem: testing
tags: [tests, pytest, fixtures, conftest, cluster-a, sdet-config, env-pollution]

requires:
  - phase: 21.1-sdet-generated-relocation
    provides: "Config.sdet REQUIRED with no default (RELOC-01) — established the breakage Cluster A repairs"
provides:
  - "tests/framework/conftest.py session-scoped `config` fixture override (D-02 seam) — supplies _SDET_STUB to every test under tests/framework/"
  - "Cluster A reds resolved at the test layer (D-01: tests adapt, framework does not)"
  - "MCPTF_CONFIG_FILE env-pollution audit (D-03) — two leaking sites in tests/framework/unit/test_cli_errors.py sealed with monkeypatch.delenv baselines"
affects: [23-02-cluster-b-parents-bump, 23-03-cluster-c-readme, 23-04-close-gate]

tech-stack:
  added: []
  patterns:
    - "Pattern S1 (module-level _SDET_STUB constant) — applied to test_tool_config.py and test_smoke_homelab_mcp.py"
    - "Pattern S2 (inline SdetConfig kwarg) — applied to test_smoke_ollama_judge.py and test_config_init_cli.py"
    - "Test-side conftest override (nested pytest conftest precedence) — shadows the production session-scoped `config` fixture without modifying src/"
    - "monkeypatch.delenv baseline for SUT-mutated env vars — when cli._load_config writes os.environ['MCPTF_CONFIG_FILE'] directly, monkeypatch.delenv(var, raising=False) gives MonkeyPatch a baseline to restore on teardown"

key-files:
  created:
    - tests/framework/conftest.py
    - .planning/phases/23-test-suite-debt-cleanup/23-01-SUMMARY.md
  modified:
    - tests/framework/test_tool_config.py
    - tests/framework/test_config_init_cli.py
    - tests/framework/smoke/test_smoke_homelab_mcp.py
    - tests/framework/smoke/test_smoke_ollama_judge.py
    - tests/framework/unit/test_cli_errors.py

key-decisions:
  - "Followed D-02 verbatim: `tests/framework/conftest.py` overrides the session-scoped `config` fixture; production `src/mcp_test_framework/fixtures.py` is unchanged (verified via empty `git diff`)"
  - "Coupled v1→v2 schema-version assertion bugs in test_tool_config.py treated as Rule 1 (auto-fix bug) — the sdet error was masking a stale `assert cfg.version == 1` and a stale `parametrize(2)` rejection case; both updated to current schema while applying the Cluster A fix"
  - "D-03 env pollution root-caused to cli._load_config:299 mutating os.environ directly — fix landed at the test layer (monkeypatch.delenv baseline) per the plan's 'fix the leaking test' guidance, not in src/ (the SUT mutation IS the documented IPC channel for the in-process pytest session)"
  - "Smoke + config-init bare Config() sites fixed per the plan even though they are deselected by the live_homelab/live_ollama markers and not in the current red set — keeps the seam forward-compatible with live-run hardening"

patterns-established:
  - "Nested-conftest precedence as a test-side seam for production-fixture shadowing — the override applies only to tests collected under tests/framework/, leaves tests/contract/ and tests/sdet/ on the production fixture"
  - "Direct-env-mutation IPC channel + monkeypatch.delenv baseline — when the SUT mutates os.environ as part of its production contract, a test invoking that SUT must take a monkeypatch baseline so MonkeyPatch can restore the original (unset) state on teardown"

requirements-completed: []

duration: ~20min
completed: 2026-05-15
---

# Phase 23 Plan 01: Cluster A — Config-construction policy Summary

**Cluster A reds eliminated end-to-end: 4 explicit sdet/version failures resolved + 1 fixture-setup ERROR moved off the sdet branch + a previously-hidden MCPTF_CONFIG_FILE env-pollution leak sealed at the leaking-test side. tests/framework/ pre-state 12 fails + 1 error → post-state 8 fails + 1 error, with every remaining red belonging to Cluster B (parents[2] off-by-one) or Cluster C (README) — i.e. exactly the inventory Plans 23-02 and 23-03 own.**

## Performance

- **Duration:** ~20 minutes (worktree base reset, full inventory, 5-file fix, env-pollution bisection, full-suite verification)
- **Started:** 2026-05-15
- **Completed:** 2026-05-15
- **Tasks:** 4 (1 diagnostic + 3 source-edit + 1 verification)
- **Files modified:** 5 (4 tests + 1 conftest CREATE)

## Accomplishments

- **D-02 seam created:** `tests/framework/conftest.py` shadows the production session-scoped `config` fixture with `Config(sdet=_SDET_STUB)`. Pytest's nested-conftest precedence gives this override priority for any test collected under `tests/framework/`; `tests/contract/` and `tests/sdet/` continue to exercise the production fixture. Body matches the plan's verbatim spec.
- **Cluster A reds → green:**
  - `tests/framework/test_isolation.py::test_real_state_unchanged` — fixture-setup `pydantic.ValidationError: sdet Field required` resolved by the conftest override (the test itself was untouched per the plan's done criteria).
  - `tests/framework/test_tool_config.py::test_default_config_version_and_tools` — bare `Config()` → `Config(sdet=_SDET_STUB)`; stale `assert cfg.version == 1` → `== 2`.
  - `tests/framework/test_tool_config.py::test_config_rejects_unsupported_version[2]` — parametrize replaced `2` (now-supported) with `1` (now-stale) so the rejection contract still covers a non-current version; sdet kwarg supplied.
  - `tests/framework/test_tool_config.py::test_yaml_overlay_loads_tools_block` — YAML bumped to `version: 2` with the required `sdet:` block.
  - `tests/framework/unit/test_homelab_config.py::test_config_default_homelab` — passed alone in pre-state but failed under the full suite (D-03 env pollution); resolved by the env-pollution audit below.
- **D-03 env pollution audit completed:** Root cause = `cli._load_config` (`src/mcp_test_framework/cli.py:299`) writes `os.environ["MCPTF_CONFIG_FILE"]` directly so the in-process pytest session sees the resolved YAML path. Two tests in `tests/framework/unit/test_cli_errors.py` invoked the CLI without first taking a monkeypatch baseline, so the SUT's mutation persisted across test boundaries:
  - `test_safe_06_v1_config_emits_locked_migration_message` (line 349) — leaked `tmp_path/old.yaml` (version: 1).
  - `test_load_config_validation_error_version` (line 90) — leaked `tmp_path/config.yaml` (version: 99).

  Both sealed by adding `monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)` at the top of the body so MonkeyPatch records the original (unset) state and restores it on teardown. No SUT change — the direct env mutation in `cli.py:299` is the documented IPC channel and is preserved verbatim.
- **Smoke + config-init future-proofing:** All four bare `Config()` sites in `tests/framework/smoke/test_smoke_homelab_mcp.py` (S1), `tests/framework/smoke/test_smoke_ollama_judge.py` (S2), and `tests/framework/test_config_init_cli.py` (S2) updated per the plan even though they are deselected by `live_homelab`/`live_ollama` markers and not in the current close-gate red set. Keeps the seam forward-compatible with any live-run hardening pass.

## Task 1 inventory (pre-edit failure capture)

Pre-state: `uv run pytest tests/framework/ --tb=short -q` → **12 failed, 563 passed, 1 skipped, 16 deselected, 2 xfailed, 1 error.**

### Cluster A reds (in scope for this plan)

| file:line | test_name | red? | root cause | pattern applied | commit |
|---|---|---|---|---|---|
| `src/mcp_test_framework/fixtures.py:101` (via test_isolation) | `test_real_state_unchanged` | ERROR (setup) | bare `Config()` raises `sdet Field required` | conftest override (D-02) | `b907722` |
| `tests/framework/test_tool_config.py:53` | `test_default_config_version_and_tools` | FAILED | bare `Config()` + stale `version == 1` assertion | S1 module stub + version assertion bumped to 2 | `11fb73f` |
| `tests/framework/test_tool_config.py:117` | `test_config_rejects_unsupported_version[2]` | FAILED (DID NOT RAISE) | parametrize includes `2`, now the supported version | parametrize updated to `[0, 1, -1, 99]` | `11fb73f` |
| `tests/framework/test_tool_config.py:150` | `test_yaml_overlay_loads_tools_block` | FAILED | YAML wrote `version: 1`; bare `Config()` then asserted `cfg.version == 1` | YAML bumped to `version: 2` + sdet block; assertion bumped to 2 | `11fb73f` |
| `tests/framework/unit/test_homelab_config.py:64` | `test_config_default_homelab` | FAILED (full-suite only) | env pollution from `MCPTF_CONFIG_FILE` left set by upstream test | sealed via monkeypatch.delenv in two leaker tests (D-03) | `6ee48b5` |

### Out of Cluster A (deferred to later plans)

| file:test | failure | cluster |
|---|---|---|
| `tests/framework/test_tool_config.py::test_call_arguments_forwarded_to_call_tool_via_asyncmock` | `ModuleNotFoundError: No module named 'tests.test_mcp_tool_contract'` (moved to `tests/contract/test_mcp_tool_contract.py` in Phase 15 SURFACE split) | NEITHER — stale import path; deferred-items |
| `tests/framework/unit/test_cli_errors.py::test_cli_errors_static_call_sites_no_banned_tokens` | `parents[2]` resolves to `tests/` instead of repo root | Cluster B (Plan 23-02) |
| `tests/framework/unit/test_doc_scrub.py::test_readme_exists_and_no_banned_tokens` | banned tokens `\bPhase \d`, `\bD-\d{2}` in README | Cluster C (Plan 23-03) |
| `tests/framework/unit/test_doc_scrub.py::test_doc_invocations_consistently_pair_with_config[path0]` | README line 104 bare `mcp-test-framework run --explain` | Cluster C (Plan 23-03) |
| `tests/framework/unit/test_migration_doc.py::test_migration_doc_*` (×4) | `parents[2]` resolves to `tests/`; expected `tests/docs/MIGRATION-...` instead of `docs/MIGRATION-...` | Cluster B (Plan 23-02) |

### Bare `Config()` audit (deselected by addopts but fixed for forward-compat)

| file:line | in current red set? | action |
|---|---|---|
| `tests/framework/smoke/test_smoke_ollama_judge.py:78` | NO (deselected via `live_ollama`) | S2 inline applied (Task 3) — commit `3708855` |
| `tests/framework/smoke/test_smoke_homelab_mcp.py:41,63` | NO (deselected via `live_homelab`) | S1 module stub applied — commit `3708855` |
| `tests/framework/unit/test_runner_migration.py:192` | NO (intentional bare-Config + env-fallback contract) | left bare per plan |
| `tests/framework/test_config_init_cli.py:130` | NO (deselected via `live_homelab`) | S2 inline + version 1→2 assertion — commit `3708855` |

## Task 4 close-gate result

Post-state: `uv run pytest tests/framework/ --tb=no -q` → **8 failed, 567 passed, 1 skipped, 16 deselected, 2 xfailed, 1 error.**

| metric | pre-state | post-state | delta |
|---|---|---|---|
| failed | 12 | 8 | -4 (all Cluster A) |
| passed | 563 | 567 | +4 |
| errored | 1 | 1 | 0 (sdet error gone, replaced by pre-existing homelab-mcp PATH dep — see Deferred below) |

All Cluster A reds resolved. Remaining 8 fails + 1 error split cleanly across the next-plan inventory:

- **5 → Cluster B (Plan 23-02 parents[2] mechanical bump):** `test_cli_errors_static_call_sites_no_banned_tokens` + `test_migration_doc_*` ×4
- **2 → Cluster C (Plan 23-03 README):** `test_readme_exists_and_no_banned_tokens` + `test_doc_invocations_consistently_pair_with_config[path0]`
- **1 stale import (deferred):** `test_call_arguments_forwarded_to_call_tool_via_asyncmock` — `from tests.test_mcp_tool_contract import ...` should be `from tests.contract.test_mcp_tool_contract import ...` post Phase 15 SURFACE-01..04
- **1 error (deferred):** `test_real_state_unchanged` — Cluster A sdet error gone (verified — no longer mentions `sdet Field required`); now hits a pre-existing `FileNotFoundError [WinError 2]` because the worktree dev box has no `homelab-mcp` on PATH and no `MCPTF_CONFIG_FILE` env var set. Per scope-boundary discipline this is not caused by the conftest fix — it was masked by the earlier sdet error. The test lacks a skip-on-binary-missing guard analogous to its existing skip-on-empty-`~/.homelab_mcp/` guard; that hardening is left as deferred.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Stale `assert cfg.version == 1` in test_tool_config.py**
- **Found during:** Task 3
- **Issue:** With the sdet error masked, `test_default_config_version_and_tools` and `test_yaml_overlay_loads_tools_block` then asserted the pre-Phase 13 schema version. Config defaults to `version: 2` since the v1→v2 migration; the validator rejects `version: 1`.
- **Fix:** Bumped both assertions to `2`; bumped the YAML overlay literal to `version: 2` and added the required `sdet:` block to mirror the operator-facing scaffold shape.
- **Files modified:** `tests/framework/test_tool_config.py`
- **Commit:** `11fb73f`

**2. [Rule 1 — Bug] Stale `[2]` in test_config_rejects_unsupported_version parametrize**
- **Found during:** Task 3
- **Issue:** `pytest.parametrize("bad_version", [0, 2, -1, 99])` failed at `[2]` because `2` is now the supported version (DID NOT RAISE). The contract under test (rejection of non-current versions) is still useful, just needs a non-2 value.
- **Fix:** Replaced `2` with `1` (now-stale) so the rejection contract still covers a fresh non-current version.
- **Files modified:** `tests/framework/test_tool_config.py`
- **Commit:** `11fb73f`

**3. [Rule 3 — Blocking] D-03 env-pollution leak in test_cli_errors.py**
- **Found during:** Task 4
- **Issue:** `test_config_default_homelab` passed alone but failed in the full suite. Bisection traced the leak to two tests that invoke `cli._load_config` (which mutates `os.environ["MCPTF_CONFIG_FILE"]` directly) without first taking a monkeypatch baseline.
- **Fix:** Added `monkeypatch.delenv("MCPTF_CONFIG_FILE", raising=False)` at the top of both tests so MonkeyPatch records the original unset state and restores it on teardown. No `src/` change — the SUT's direct env mutation IS the documented IPC channel for the in-process pytest session.
- **Files modified:** `tests/framework/unit/test_cli_errors.py` (`test_safe_06_v1_config_emits_locked_migration_message`, `test_load_config_validation_error_version`)
- **Commit:** `6ee48b5`

### Out-of-scope deviations

**1. Smoke + config-init Cluster A targets are deselected from the close-gate.** The plan listed them as Task 3 targets. They never enter the default `addopts = "-m 'not live_homelab and not live_ollama'"` run, so they aren't in the current Cluster A red inventory. Applied the S1/S2 patterns anyway per the plan to keep the seam forward-compatible. Pre-existing breakages in those files (`cfg.target` removed by Phase 13 v2 schema rework; `version: 1` literals in the live config-init scaffold tests) are NOT fixed here — they remain behind the live markers and are left for a future live-run hardening pass.

## Self-Check: PASSED

Verified files exist:
- `tests/framework/conftest.py` — created with verbatim D-02 body
- `.planning/phases/23-test-suite-debt-cleanup/23-01-SUMMARY.md` — this file

Verified commits exist (in `git log`):
- `b907722` — `test(23-01): add tests/framework/conftest.py with config fixture override`
- `11fb73f` — `fix(23-01): apply _SDET_STUB to test_tool_config.py Cluster A red sites`
- `6ee48b5` — `fix(23-01): seal MCPTF_CONFIG_FILE env pollution in test_cli_errors.py (D-03)`
- `3708855` — `fix(23-01): apply _SDET_STUB to live-marker bare Config() sites`

Verified untouched (per D-02 + pattern-source preservation):
- `git diff src/mcp_test_framework/fixtures.py` → empty
- `git diff tests/framework/unit/test_homelab_config.py` → empty

## Deferred Issues

The following are out of Plan 23-01 scope per the plan's explicit boundaries and are tracked here for the wave's deferred-items log:

1. **`test_call_arguments_forwarded_to_call_tool_via_asyncmock` stale import** — `from tests.test_mcp_tool_contract import ...` needs to become `from tests.contract.test_mcp_tool_contract import ...` post Phase 15 SURFACE-01..04 folder split. Independent of Cluster A; consider folding into Plan 23-04 close-gate or a future hygiene pass.
2. **`test_real_state_unchanged` lacks a skip-on-binary-missing guard** — the test correctly skips when `~/.homelab_mcp/` is empty (D-11), but the `mcp_client` fixture spawns the configured `mcp_server.command` (default `homelab-mcp`) before the test body runs and crashes with `FileNotFoundError [WinError 2]` on hosts without the binary on PATH. Adding an analogous skip-on-binary-missing guard at fixture setup would close the residual ERROR — not Cluster A scope.
3. **Live-marker scaffold drift in `test_config_init_cli.py`** — `test_overwrite_with_force_succeeds` and `test_scaffold_round_trips_through_config` still assert v1-era scaffold content. Behind `live_homelab`/`live_ollama` markers; deferred until a live-run hardening pass.
4. **Smoke `cfg.target.tool_name` references the removed-by-Phase-13 `Config.target` field** — separate pre-existing bug behind `live_homelab` marker; deferred.
