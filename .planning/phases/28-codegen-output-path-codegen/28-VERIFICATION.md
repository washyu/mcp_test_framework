---
phase: 28-codegen-output-path-codegen
verified: 2026-05-16T00:00:00Z
status: passed
score: 3/3 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: none
  previous_score: n/a
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 28: Codegen Output Path (CODEGEN) Verification Report

**Phase Goal (ROADMAP.md line 141):** `gen-test-classes` refuses to invent an output path or write under its own install tree, and reads the same `mcp_config_file` ini route pytest uses. Driver: the framework knows nothing about the operator's project layout (rejecting "smart default" framing); single config-resolution route extended from the pytest plugin to the Typer CLI.

**Verified:** 2026-05-16
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria SC1/SC2/SC3 + CONTEXT.md D-01..D-13)

| # | Truth (ROADMAP SC + supporting CONTEXT decisions) | Status | Evidence |
|---|----|----|----|
| 1 | **SC1**: Operator running `mcp-contracts gen-test-classes` without `cfg.test_code.generated_root` set sees a fail-loud operator-tone error naming the missing field and pointing at `mcp-contracts config-init`. Field-set: target dir created if missing; non-empty TTY prompts; non-empty non-TTY aborts exit 2; no `--yes`/`--force` flag exists. (D-01, D-02, D-05, D-06) | ✓ VERIFIED | `_emit_operator_error_for_validation` missing-field branch in cli.py:299-312 — summary `"config file is missing a required field: {loc}"`, next_step `"... or run mcp-contracts config-init -o config.yaml"`; `TestCodeConfig.generated_root` is still `Field(...)` (required). `_confirm_or_abort_non_empty_target` at cli.py:147-224 implements all five branches (missing → silent, empty → silent, non-empty TTY → `typer.confirm`, non-empty non-TTY → exit 2). Helper wired into `gen_test_classes` at cli.py:1300, AFTER slug derivation and BEFORE `_codegen.generate()`. Regression-test `test_gen_test_classes_command_has_no_yes_or_force_flag` enforces no `--yes`/`--force` flag on the command. Backed by 7 new tests in `tests/framework/unit/test_gen_test_classes_overwrite_prompt.py` + 1 test in `tests/framework/unit/test_missing_generated_root_error.py` — all passing per 624-green suite. |
| 2 | **SC2**: `gen-test-classes` refuses to write under any directory containing the installed `mcp_test_framework` package; resolved-absolute target checked at command start BEFORE the MCP handshake; aborts with operator-tone error naming `test_code.generated_root`, resolved target path, and framework install root. No bypass flag/config knob. (D-07, D-08, D-09, D-10) | ✓ VERIFIED | `_guard_against_site_packages_target` at cli.py:100-144: resolves `framework_install_root = Path(mcp_test_framework.__file__).resolve().parent.parent`; descendant check via `is_relative_to` (no `site-packages` / `dist-packages` directory-name special-casing per D-07); operator-tone error names the field (`test_code.generated_root`), resolved target, and framework install root (D-10). Helper wired at cli.py:1241 — BEFORE the `asyncio.Runner()` handshake at cli.py:1244 (D-08 pre-handshake timing confirmed). No bypass surface: grep across `src/mcp_test_framework/` finds zero `--unsafe`, zero `allow_unsafe_generated_root`, zero `allow-site-packages` tokens (D-09 holds). The `--force` matches under `src/mcp_test_framework/cli.py` are all scoped to `config-init` (unrelated command). 5 tests in `tests/framework/unit/test_gen_test_classes_site_packages_guard.py` cover descendant-aborts-exit-2, tmp_path-passes, sibling-passes, error-message-contents, and pre-handshake-timing (subprocess never spawned). |
| 3 | **SC3**: Operator who set `[tool.pytest.ini_options] mcp_config_file = PATH` in pyproject.toml sees `mcp-contracts gen-test-classes` use the same config file as `pytest`, without passing `--config`. Precedence: `--config` > pyproject.toml ini > `MCPTF_CONFIG_FILE` (deprecated) > `./config.yaml` > fail-loud. (D-11, D-12, D-13) | ✓ VERIFIED | `_read_mcp_config_file_from_pyproject` at cli.py:333-397 uses stdlib `tomllib` (lazy import line 362), walks `tool.pytest.ini_options.mcp_config_file`, resolves relative paths against pyproject.toml's directory (mirrors `_plugin.py:165-166`), fail-soft on parse problems / missing key / empty value, fail-loud on typo'd value (resolved-but-missing). Wired into `_load_config` at cli.py:463-468 as Branch 1.5 — between `--config` and `MCPTF_CONFIG_FILE`, exactly per D-11 precedence ladder. `_load_config` docstring (cli.py:405-407) lists the new branch in the Precedence ladder. `MCPTF_CONFIG_FILE` env-var path preserved verbatim per D-12 (cli.py:471-487). 9 tests in `tests/framework/unit/test_gen_test_classes_pyproject_config.py` cover all eight behaviors (uses-pyproject, --config-overrides, env-still-works, missing/malformed/no-section/empty-value all fall through, relative-path resolves against pyproject directory, typo'd value fail-loud exit 2). |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----|----|----|----|
| `src/mcp_test_framework/cli.py` | `_guard_against_site_packages_target` helper (D-07/D-08/D-09/D-10) | ✓ VERIFIED | Defined at line 100; called at line 1241 in `gen_test_classes` BEFORE `asyncio.Runner()` (line 1244). |
| `src/mcp_test_framework/cli.py` | `_confirm_or_abort_non_empty_target` helper (D-05/D-06) | ✓ VERIFIED | Defined at line 147; called at line 1300 AFTER slug derivation (line 1298) and BEFORE `_codegen.generate(...)` (line 1305-1311). |
| `src/mcp_test_framework/cli.py` | `_read_mcp_config_file_from_pyproject` helper (D-11/D-13) | ✓ VERIFIED | Defined at line 333; called from `_load_config` at line 463 in Branch 1.5 position. |
| `src/mcp_test_framework/cli.py` | `_emit_operator_error_for_validation` missing-field branch flipped to `mcp-contracts config-init` (D-02) | ✓ VERIFIED | cli.py:310 reads `mcp-contracts config-init -o config.yaml` (was `mcp-test-framework config-init`). v1→v2 + no-config-found branches still carry legacy name per ERROR-STYLE.md pin (documented v1.5 cleanup item). |
| `tests/framework/unit/test_gen_test_classes_site_packages_guard.py` | 4+ tests covering guard behavior | ✓ VERIFIED | File exists; 5 tests (descendant abort, tmp_path passes, sibling passes, error message, CLI aborts before handshake). |
| `tests/framework/unit/test_gen_test_classes_pyproject_config.py` | 6+ tests covering pyproject ini route | ✓ VERIFIED | File exists; 9 tests across the eight specified behaviors (incl. fail-loud-on-typo). |
| `tests/framework/unit/test_gen_test_classes_overwrite_prompt.py` | 5+ tests covering prompt + non-TTY abort + no-bypass-flag | ✓ VERIFIED | File exists; 7 tests including the `test_gen_test_classes_command_has_no_yes_or_force_flag` regression guard. |
| `tests/framework/unit/test_missing_generated_root_error.py` | 1+ test pinning `mcp-contracts config-init` in missing-field next-step | ✓ VERIFIED | File exists; 1 test asserting field name, presence of `mcp-contracts config-init`, absence of `mcp-test-framework config-init`, and exit code 2. |
| `.planning/REQUIREMENTS.md` CODEGEN-LIB-01 rewrite + CODEGEN-LIB-02 preserved | Docs aligned with actual scope | ✓ VERIFIED | REQUIREMENTS.md:47 contains the full rewrite (fail-loud + no-output-dir + TTY/non-TTY + pyproject ini precedence ladder); line 48 (CODEGEN-LIB-02) preserved verbatim; Traceability table rows 125-126 marked Complete. |
| `.planning/ROADMAP.md` Phase 28 Goal + SC1/SC2/SC3 amended | Roadmap aligned with actual scope | ✓ VERIFIED | ROADMAP.md:141 Goal contains "refuses to invent an output path or write under its own install tree, and reads the same `mcp_config_file` ini route pytest uses"; SC1 (line 145) contains "fail-loud operator-tone error naming the missing field" + "no `--yes` / `--force` flag exists"; SC2 (line 146) contains "BEFORE the MCP handshake" + "No bypass flag or config knob exists"; SC3 (line 147) covers pyproject ini parity + full precedence ladder. |

### Key Link Verification

| From | To | Via | Status | Details |
|----|----|----|----|----|
| `gen_test_classes` (cli.py:1205) | `_guard_against_site_packages_target` | Direct call after out_root resolution, before handshake | ✓ WIRED | Call at cli.py:1241; handshake at cli.py:1244 (line numbers confirm pre-handshake ordering). |
| `gen_test_classes` (cli.py:1205) | `_confirm_or_abort_non_empty_target` | Direct call after slug derivation, before _codegen.generate | ✓ WIRED | Call at cli.py:1300 (slug at 1298, _codegen.generate at 1305). |
| `_load_config` (cli.py:400) | `_read_mcp_config_file_from_pyproject` | Branch 1.5 between --config and MCPTF_CONFIG_FILE | ✓ WIRED | Call at cli.py:463 inside the `else:` of the `--config` branch; sits above the MCPTF_CONFIG_FILE branch at line 471 (D-11 precedence holds). |
| `_read_mcp_config_file_from_pyproject` | stdlib `tomllib` | Lazy import inside helper body | ✓ WIRED | `import tomllib` at cli.py:362 (lazy). |
| `_emit_operator_error_for_validation` missing-field branch | operator-facing next-step copy | Flipped to `mcp-contracts config-init` per D-02 | ✓ WIRED | cli.py:310 next_step body contains `mcp-contracts config-init` (verified by `test_missing_generated_root_error.py`). |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----|----|----|----|----|
| `gen_test_classes` `out_root` | `cfg.test_code.generated_root` (cli.py:1238) | `Config(yaml_file=resolved)` in `_load_config` (cli.py:522) | YAML-loaded value from operator's config | ✓ FLOWING |
| `gen_test_classes` `target_dir` | `out_root / slug` (cli.py:1299) | `slug = server_slug(server_name)` (cli.py:1298), `server_name` from MCP handshake (cli.py:1245) | Live MCP `serverInfo.name` post-handshake; non-empty enforced at cli.py:1269 | ✓ FLOWING |
| `_read_mcp_config_file_from_pyproject` `raw` | `data.get(...).get("mcp_config_file", "")` (cli.py:371-376) | `tomllib.load(open(pyproject, "rb"))` (cli.py:367-368) | Live read of operator's pyproject.toml | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----|----|----|----|
| `_guard_against_site_packages_target` defined | `Grep "def _guard_against_site_packages_target("` | 1 match at cli.py:100 | ✓ PASS |
| `_confirm_or_abort_non_empty_target` defined | `Grep "def _confirm_or_abort_non_empty_target("` | 1 match at cli.py:147 | ✓ PASS |
| `_read_mcp_config_file_from_pyproject` defined | `Grep "def _read_mcp_config_file_from_pyproject("` | 1 match at cli.py:333 | ✓ PASS |
| Guard called before handshake | Verify line numbers: guard call < `asyncio.Runner()` | guard at 1241 < runner at 1244 | ✓ PASS |
| Prompt called after slug, before codegen | Verify line numbers | slug at 1298 < prompt at 1300 < codegen at 1305 | ✓ PASS |
| No bypass surface for site-packages guard (D-09) | `Grep "--unsafe|allow_unsafe_generated_root|allow-site-packages"` in src/ | Zero matches | ✓ PASS |
| No `--yes`/`--force` on `gen-test-classes` (D-06) | All `--force` matches scoped to `config-init` (separate command) | Confirmed via line-by-line review of cli.py:1040/1045/1079/1097/1099/1190 — all `config-init` | ✓ PASS |
| Full framework test suite green | `uv run pytest tests/framework/` (per user-provided result) | 624 passed, 1 skipped, 17 deselected, 1 xfailed | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|----|----|----|----|----|
| CODEGEN-LIB-01 | 28-02 (pyproject route), 28-03 (overwrite prompt + D-02 next-step flip) | Fail-loud missing field + pyproject ini route + non-empty prompt + non-TTY abort + no --yes/--force + no --output-dir | ✓ SATISFIED | All sub-behaviors realized in cli.py:147-224 (prompt), 310 (D-02 copy), 333-397 (pyproject helper), 463-468 (precedence wiring); REQUIREMENTS.md:125 marked Complete. |
| CODEGEN-LIB-02 | 28-01 (site-packages guard) | Pre-handshake site-packages guard with operator-tone error + no bypass | ✓ SATISFIED | Helper at cli.py:100-144, wired at cli.py:1241 before handshake; no bypass surface confirmed; REQUIREMENTS.md:126 marked Complete. |

No orphaned requirements: ROADMAP.md Phase 28 declares only CODEGEN-LIB-01 + CODEGEN-LIB-02, both claimed by plans 28-01..03 and verified above.

### Anti-Patterns Found

None. The 6 advisory WARNING-level findings in 28-REVIEW.md (WR-01..WR-06) were reviewed and none invalidate a Success Criterion:

- They are polish items (e.g. helper docstring wording, copy refinements, doc cross-references, follow-on test ideas) rather than functional gaps.
- The planning-ID leak gate is GREEN (28-01 auto-fix landed in commit 4a88ba9; subsequent plans pre-empted the issue).
- The locked v1→v2 migration + no-config-found error branches still reference legacy `mcp-test-framework config-init` per the documented v1.5 cleanup track (pinned to ERROR-STYLE.md + `test_error_style.py`); this is a deliberate scope cut documented in 28-03 SUMMARY decisions.

### Human Verification Required

None. All three SCs are programmatically verifiable through existing tests + grep against the codebase, and the user-supplied suite result (624 passed) confirms behavioral wholeness.

### Gaps Summary

No blocking gaps. Phase 28 closes the codegen-side seam to the pytest plugin's ini route (Phase 27 D-11) cleanly:

1. **SC1 fail-loud + prompt + no-bypass-flag** — implemented end-to-end with 8 new tests + the missing-field copy flip.
2. **SC2 pre-handshake site-packages guard** — helper + wiring + 5 tests; no bypass; D-09 invariant grep-clean across `src/`.
3. **SC3 pyproject-ini config route** — helper + Branch 1.5 wiring + 9 tests; precedence ladder matches D-11 exactly; relative resolution mirrors `_plugin.py:165-166` (Phase 27 carry-forward).

The v1.4 milestone goal — "Operator adds the framework to their MCP server's `pyproject.toml`, sets one line in `[tool.pytest.ini_options]` pointing at their YAML config, runs their existing `pytest`" — is materially advanced: `gen-test-classes` now reads the same single ini key the plugin reads, so the operator never has to maintain two config paths. The codegen-side seam to Phase 27's pytest-plugin route is closed.

WR-01..WR-06 in 28-REVIEW.md are tracked as polish candidates for a future phase (likely Phase 30 docs / dogfood close), not Phase 28 failures.

---

*Verified: 2026-05-16*
*Verifier: Claude (gsd-verifier)*
