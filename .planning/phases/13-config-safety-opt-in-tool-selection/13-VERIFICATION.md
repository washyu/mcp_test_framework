---
phase: 13-config-safety-opt-in-tool-selection
verified: 2026-05-11T01:10:45Z
status: human_needed
score: 6/6 must-haves verified
overrides_applied: 0
human_verification:
  - test: "End-to-end run with a real MCP server (e.g. homelab-mcp via uvx) and a v2 config opting in 1-2 tools"
    expected: "Listed tools parametrize as contract tests; unlisted/skipped tools render in the per-tool summary with the correct SAFE-01 reason strings ('not selected in config' vs operator's curated skip_reason)."
    why_human: "Requires a live MCP server + Ollama on PATH; the CR-01/CR-02 IPC fix is unit-pinned (test_cr01_*, test_cr02_*) but the full pytest.main -> fixtures.config -> _reporter chain only fires end-to-end with a live server."
  - test: "Operator follows MIGRATION-v1-to-v2.md to port a real v1 config (re-run config-init, port call_arguments/judges/skip_reason, drop target: and .env reliance)"
    expected: "Port completes; resulting v2 config loads cleanly; only opted-in tools run; the operator finds the doc clear and actionable."
    why_human: "UX-level acceptance — operator perception of doc clarity and porting workflow cannot be programmatically verified."
---

# Phase 13: config-safety-opt-in-tool-selection Verification Report

**Phase Goal:** "An operator running `mcp-test-framework run` against an unconfigured directory cannot accidentally exercise destructive tools. Config becomes mandatory, opt-in, and unambiguous about which tools will be invoked. The new `version: 2` schema migration is loud, not silent."

**Verified:** 2026-05-11T01:10:45Z
**Status:** human_needed
**Re-verification:** No — initial verification (post code-review fix iteration 1)

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth (Success Criterion) | Status | Evidence |
|---|---------------------------|--------|----------|
| 1 | Operator running `mcp-test-framework run` from an unconfigured directory (no `config.yaml`, no `--config`, no `MCPTF_CONFIG_FILE`) sees a clear error pointing at `mcp-test-framework config-init -o config.yaml`, exits 2, never spawns MCP server. | VERIFIED | Behavioral spot-check (Step 7b): from `/tmp/p13-safe03` with no config, env unset, the CLI emitted the verbatim SAFE-03 LOCKED message and exit 2. No subprocess fired. Source-text pinned by `test_error_style_safe_03_body_matches_cli_wiring` (cli.py:269-280 matches docs/ERROR-STYLE.md:46-55). |
| 2 | Listing exactly two tools in `tools:` (no `skip:`) -> only those two run; every other discovered tool auto-skips with `"not selected in config"`. Master config + focus toggle preserved. | VERIFIED | tests/conftest.py:142-145 implements the opt-in filter (`name in config.tools and not config.tools[name].skip`). `_reporter._compose_unparametrized_skips` (lines 170-203) composes state-(a)/(c) rows. Constants `_REASON_NOT_SELECTED = "not selected in config"` and `_REASON_EXPLICIT_DEFAULT = "explicit skip in config"` at _reporter.py:62-63. Pinned by `test_safe_01_allowlist_includes_listed_unskipped`, `test_safe_01_allowlist_excludes_unlisted_and_skipped`, `test_safe_01_reporter_constants_locked` (PASSED). |
| 3 | Auto-discovery of `./config.yaml` when no `--config` and no env var. | VERIFIED | cli.py:257-261 (`Path.cwd() / "config.yaml"`). Behavioral spot-check (Step 7b): from `/tmp/p13-safe03` with `config.yaml` present, the CLI fell through to pytest collection (no SAFE-03 raised, autodiscovery succeeded). Pinned by `test_safe_02_cwd_autodiscovery_picks_up_local_config`. |
| 4 | Typo'd `MCPTF_CONFIG_FILE` errors with exit 2, parity with `--config /missing`. | VERIFIED | cli.py:241-253 (env-var typo branch). Behavioral spot-check (Step 7b): with `MCPTF_CONFIG_FILE=/nonexistent`, output named `MCPTF_CONFIG_FILE` and `the path in MCPTF_CONFIG_FILE does not exist`, exit 2. Pinned by `test_safe_04_mcptf_config_file_typo_exits_2` and `test_error_style_safe_04_body_matches_cli_wiring`. |
| 5 | Loading a `version: 1` config produces the LOCKED SAFE-06 migration error naming the opt-out -> opt-in flip and referencing `docs/MIGRATION-v1-to-v2.md`. The doc itself exists and walks porting steps. | VERIFIED | config.py:67-73 (`_validate_version` rejects v != 2). cli.py:133-156 emits the verbatim ERROR-STYLE.md:57-73 body. Behavioral spot-check (Step 7b): loading a v1 YAML produced the locked message verbatim incl. `docs/MIGRATION-v1-to-v2.md` reference. `docs/MIGRATION-v1-to-v2.md` exists (106 lines) with all 6 required substrings (version: 2, opt every tool in, config-init -o config.yaml.new, target:, not selected in config, .env). Pinned by `test_safe_06_v1_config_emits_locked_migration_message`, `test_error_style_safe_06_body_matches_cli_wiring`, and 4 migration-doc regression tests. |
| 6 | `.env` file in cwd has no behavioral difference from absent .env. Env vars never override config values. | VERIFIED | config.py has no `env_file`/`env_file_encoding`; `_BareNameNestedEnvSource`/`_alias_env_names`/`_maybe_json_decode`/`from dotenv import` are all gone (grep returned 0 matches). `settings_customise_sources` returns `(init_settings, YamlConfigSettingsSource, file_secret_settings)` only. Pinned by `test_safe_05_env_var_does_not_override_yaml` and `test_safe_05_dotenv_file_in_cwd_has_no_effect` (PASSED). |

**Score:** 6/6 success criteria verified.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/mcp_test_framework/cli.py` | 4-branch resolver, `allow_missing` bypass, scaffold `version: 2`, SAFE-06 message body | VERIFIED | `_load_config` (lines 191-293) implements all 4 branches; `allow_missing=True` at list-tools (428) and config-init (548); scaffold body emits `version: 2` (line 864); SAFE-06 LOCKED message body at lines 138-156. |
| `src/mcp_test_framework/config.py` | env-overlay stripped, v2 validator, pop-yaml-from-init-kwargs source pipeline | VERIFIED | All deletions confirmed (grep gates all return 0). `_validate_version` flips on `v != 2`. `settings_customise_sources` uses `init_settings.init_kwargs.pop("yaml_file", None)` (line 98) with MCPTF_CONFIG_FILE path-pointer fallback (lines 105-106, CR-01 fix). |
| `src/mcp_test_framework/models.py` | `TargetConfig` removed | VERIFIED | `grep -n TargetConfig src/mcp_test_framework/models.py` returns 0. Sub-models `OllamaConfig`, `McpServerConfig`, `ToolConfig` survive intact. |
| `src/mcp_test_framework/fixtures.py` | `target.tool_name` consumers removed; unknown-tool warning at 268-274 survives | VERIFIED | `grep -rnE "config\.target\.tool_name\|config\.target\b" src/` returns 0. Unknown-tool warning loop at fixtures.py:267-274 intact. |
| `src/mcp_test_framework/_reporter.py` | Two locked reason constants + `_compose_unparametrized_skips` composition | VERIFIED | Constants at lines 62-63; `_DISCOVERED_TOOL_NAMES` cache at line 71; `_compose_unparametrized_skips` at 170-203; merged-skip rendering at 245-278. `pytest_terminal_summary` reloads `_FwConfig()` via bare `Config()` to pick up MCPTF_CONFIG_FILE path-pointer (CR-02 fix). |
| `tests/conftest.py` | Allowlist filter, explicit-target short-circuit removed, `_reporter._DISCOVERED_TOOL_NAMES` cache | VERIFIED | Lines 142-145 implement opt-in filter; `_resolve_tool_names` has no `if explicit:` short-circuit; reads/writes `_rep._DISCOVERED_TOOL_NAMES` (line 22 import, 106/108 cache access). |
| `docs/MIGRATION-v1-to-v2.md` | Standalone diff-driven port guide; ≥60 lines | VERIFIED | 106 lines; 6 sections (Why this matters, What stays the same, What changes, Step-by-step port, Side-by-side per-tool example, What about .env). Before/after YAML diff present. All 6 pinned substrings present. No banned planning IDs. |
| `tests/unit/test_migration_doc.py` | 4 regression tests pinning doc keywords + banned-token check | VERIFIED | 4 tests all PASSED: exists, pins_v2_keywords, uses_ascii_dashes_not_emdash, does_not_leak_planning_ids. |
| `pyproject.toml` | No direct `python-dotenv` declaration | VERIFIED | `grep -nE "dotenv\|python-dotenv" pyproject.toml` returns 0. Dependencies block has 4 entries (mcp[cli], pydantic, pydantic-settings[yaml], jsonschema). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `cli.py:_load_config` | `config.py:Config()` | `Config(yaml_file=resolved_path)` kwarg | WIRED | cli.py:291 `return Config(yaml_file=str(resolved))`. config.py:98 pops `yaml_file` from init_kwargs. |
| `cli.py:_load_config` | in-process pytest session's bare `Config()` | `os.environ["MCPTF_CONFIG_FILE"] = str(resolved)` (CR-01 fix) | WIRED | cli.py:289 exports env var; config.py:105-106 reads it as path-pointer fallback. Pinned by `test_cr01_bare_config_picks_up_mcptf_config_file` and `test_cr01_resolver_writes_mcptf_config_file_env_var` (PASSED). |
| `cli.py:config_init`, `cli.py:list_tools` | `cli.py:_load_config` | `allow_missing=True` kwarg | WIRED | cli.py:428 (list_tools), cli.py:548 (config_init). |
| `cli.py:_emit_operator_error_for_validation` | docs/ERROR-STYLE.md SAFE-06 message | verbatim copy via `_emit_operator_error` | WIRED | cli.py:138-156 contains the verbatim ERROR-STYLE.md:57-73 body. Pinned by `test_error_style_safe_06_body_matches_cli_wiring`. |
| `tests/conftest.py:_resolve_tool_names` | `_reporter._DISCOVERED_TOOL_NAMES` | module-level write/read | WIRED | conftest.py:106/108 access; _reporter.py:71 declares; _reporter.py:186 reads. |
| `_reporter._compose_unparametrized_skips` | reporter skip rows | merged into `pytest_terminal_summary` SKIP block | WIRED | _reporter.py:245-278 unions `_PER_TOOL` skips with `unparam_skips`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `_load_config` resolved path | `resolved: Path` | --config flag / MCPTF_CONFIG_FILE env / ./config.yaml autodiscovery | Yes — three real branches with `is_file()` guards | FLOWING |
| `Config(yaml_file=...)` | YAML file contents | `YamlConfigSettingsSource(yaml_file=resolved)` | Yes — pydantic-settings reads file via yaml.safe_load | FLOWING |
| Bare `Config()` in pytest session | YAML file contents (via path-pointer) | `os.environ.get("MCPTF_CONFIG_FILE")` fallback | Yes — confirmed by `test_cr01_bare_config_picks_up_mcptf_config_file` (PASSED) | FLOWING |
| `_resolve_tool_names` allowlist | tool names | `config.tools` (dict-keyed) filtered against `_DISCOVERED_TOOL_NAMES` | Yes — empty config.tools -> empty selection (state a everywhere); the data flows through | FLOWING |
| `_compose_unparametrized_skips` reasons | per-tool skip reason strings | `tools_cfg.get(name).skip_reason` or default constants | Yes — three branches (state c with reason, state c default, state a) all exercised in unit tests | FLOWING |

### Behavioral Spot-Checks (Step 7b)

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| SAFE-03: no-config fail-loud | `cd /tmp/p13-safe03 && unset MCPTF_CONFIG_FILE && mcp-test-framework run` | stderr exactly matches LOCKED SAFE-03 body; exit=2; no subprocess spawned | PASS |
| SAFE-06: v1 config rejected | `mcp-test-framework run --config /tmp/p13-safe03/old.yaml` (v1 yaml) | stderr matches LOCKED SAFE-06 body incl. "schema version 2 (opt-in", "docs/MIGRATION-v1-to-v2.md", "config-init -o config.yaml.new"; exit=2 | PASS |
| SAFE-04: typo'd env var | `MCPTF_CONFIG_FILE=/nonexistent mcp-test-framework run` | stderr names `MCPTF_CONFIG_FILE` and `the path in MCPTF_CONFIG_FILE does not exist`; exit=2 | PASS |
| SAFE-02: cwd autodiscovery | `cd /tmp/p13-safe03 (with config.yaml) && unset MCPTF_CONFIG_FILE && mcp-test-framework run` | No SAFE-03 raise; falls through to pytest collection; resolver picked up `./config.yaml` | PASS |
| Unit test suite | `uv run pytest tests/unit -v` | 183 passed, 1 warning, 0 failures (in 0.63s) | PASS |
| Migration doc regression | `uv run pytest tests/unit/test_migration_doc.py -v` | 4 PASSED | PASS |
| Reporter SAFE-01 + CR-01/CR-02 regression | `uv run pytest tests/unit/test_reporter.py -v` | 11 PASSED (including 3 CR-01/CR-02 IPC regression tests) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SAFE-01 | 13-03, 13-04 | Three-state opt-in allowlist (a unlisted / b listed-unskipped / c listed-skipped) | SATISFIED | conftest.py filter + _reporter constants + composition; 8 SAFE-01 unit tests PASSED. |
| SAFE-02 | 13-01, 13-02 | `./config.yaml` cwd autodiscovery | SATISFIED | cli.py:257-261; spot-check PASSED. |
| SAFE-03 | 13-01 | Fail loud (exit 2) with locked message when no config found | SATISFIED | cli.py:269-280; source-text pinned; spot-check PASSED. |
| SAFE-04 | 13-01 | Typo'd MCPTF_CONFIG_FILE errors with exit 2 (parity with --config) | SATISFIED | cli.py:241-253; spot-check PASSED. |
| SAFE-05 | 13-02 | Drop .env and env-overlay; YAML+CLI only as config sources | SATISFIED | All deletions in config.py verified by grep gates; SAFE-05 tests PASSED. (CR-01 fix preserves SAFE-05: MCPTF_CONFIG_FILE remains a PATH POINTER, not a value source.) |
| SAFE-06 | 13-02 | v1 config -> loud migration error with LOCKED ERROR-STYLE body | SATISFIED | config.py:_validate_version flip + cli.py:138-156 verbatim body; spot-check PASSED. |
| SAFE-07 | 13-05 | `docs/MIGRATION-v1-to-v2.md` walkthrough | SATISFIED | 106 lines, 6 sections, before/after YAML, 4 regression tests PASSED. |

No orphan requirements: ROADMAP.md maps SAFE-01..07 to Phase 13, all 7 satisfied.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/mcp_test_framework/cli.py` | 191, 194, 196, 209 | `Phase 13` / `D-NN` planning IDs in docstrings | Info | Internal docstring leakage; not operator-facing (banned-token tests only scan operator-emitted strings). Tracked as IN-03 in 13-REVIEW.md; deferred to v1.2 doc-scrub initiative. |
| `tests/test_tool_config.py` | 192-206 | Stale test `test_resolve_tool_names_explicit_target_overrides_skip_true` uses removed `Config(target=...)` and `_conftest_module._DISCOVERED_TOOL_NAMES` | Info | Pre-existing test code unreachable in this environment (collection aborts at `_preflight` because homelab-mcp is not on PATH). The phase plan touched `tests/conftest.py` and `tests/unit/test_reporter.py` but did not enumerate cleanup of `tests/test_tool_config.py`. The test would explode if collection ever succeeded. Recommended cleanup in a follow-up phase or as part of SURFACE-01 (Phase 15) split. Does not affect Phase 13 goal achievement — the v2 Config + opt-in allowlist works correctly. |
| `tests/smoke/test_smoke_homelab_mcp.py` | 52, 69 | `cfg.target.tool_name` references | Info | Behind `@pytest.mark.live_homelab` marker (deselected by default `addopts`). Would crash if anyone runs `-m live_homelab` after Phase 13. Recommended cleanup in a follow-up. |
| `src/mcp_test_framework/cli.py` | 289 | `os.environ["MCPTF_CONFIG_FILE"] = str(resolved)` | Info | This is the documented CR-01 fix (review iteration 1). Phase 13 D-03 forbade env-var-as-IPC, but the in-process pytest session needs a process-local handoff for bare `Config()` calls. The fix is explicitly justified in cli.py:283-288 ("PATH POINTER, not a scalar-value source") and preserves SAFE-05 semantics. Pinned by 3 unit tests (test_cr01_*, test_cr02_*). |

### Human Verification Required

1. **End-to-end live run with real MCP server**
   - Test: Install/configure homelab-mcp (or any MCP server), write a v2 config opting in 1-2 tools, run `mcp-test-framework run`.
   - Expected: Listed tools parametrize as contract tests; unlisted/skipped tools render in the per-tool summary with `"not selected in config"` (state a) or operator's curated `skip_reason` (state c) — NOT all state-a (which was the CR-01 pre-fix symptom).
   - Why human: The CR-01/CR-02 fix is unit-pinned via the path-pointer regression tests, but the full `pytest.main -> fixtures.config -> _reporter` chain only fires end-to-end with a live server. Without a live MCP server in this verifier environment, full integration cannot be programmatically confirmed.

2. **Migration doc walkthrough**
   - Test: Take a real v1 config (from a prior v1.1 install) and follow `docs/MIGRATION-v1-to-v2.md` step-by-step.
   - Expected: Port completes; resulting v2 config loads cleanly; only opted-in tools run; the doc reads as clear and actionable.
   - Why human: UX-level acceptance — operator perception of clarity and porting workflow can only be verified by an actual operator.

### Gaps Summary

No gaps. All 6 ROADMAP success criteria verified through a combination of:
- Source-code presence (4-branch resolver, env-overlay strip, TargetConfig removal, locked message bodies)
- Source-text regression tests (3 verbatim message pins: SAFE-03, SAFE-04, SAFE-06)
- Behavioral regression tests (183 unit tests passing, including 8 SAFE-01 reporter tests, 3 CR-01/CR-02 IPC regression tests, 4 SAFE-05/06 config tests, 4 migration-doc tests)
- Manual behavioral spot-checks for SAFE-02, SAFE-03, SAFE-04, SAFE-06

The CR-01/CR-02 IPC fix (commits a521489 + 47120bc) holds: bare `Config()` calls inside the in-process pytest session pick up the resolver's YAML via MCPTF_CONFIG_FILE path-pointer fallback. SAFE-05 is preserved because the env var is only a path pointer — it can direct the YAML loader to a file but never inject scalar values into the model.

Two pre-existing stale-test artifacts (`tests/test_tool_config.py:191-206` and `tests/smoke/test_smoke_homelab_mcp.py:52,69`) reference removed APIs but are unreachable in the default test path (preflight gate / live marker). These are noted as Info-severity in the anti-patterns table; they do not block Phase 13's goal but should be cleaned up in a follow-up phase.

Human verification items above gate the final live-acceptance call before considering Phase 13 fully shipped.

---

_Verified: 2026-05-11T01:10:45Z_
_Verifier: Claude (gsd-verifier)_
