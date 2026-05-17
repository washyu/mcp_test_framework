---
phase: 28-codegen-output-path-codegen
plan: 02
subsystem: cli

tags: [typer, gen-test-classes, pyproject-toml, ini-config, tomllib, _load_config]

# Dependency graph
requires:
  - phase: 27-register-api-contracts-sub-package-test-extraction-lib
    provides: "mcp_config_file ini key as the canonical pytest-side config-resolution route; _plugin.py:pytest_configure pattern this helper mirrors on the CLI side."
  - phase: 28-codegen-output-path-codegen/plan-01
    provides: "Pre-handshake site-packages guard stable anchor; out_root resolution semantics this plan does NOT touch (28-01 kept cwd-relative; 28-02 only changes config-file lookup, not generated_root resolution)."
provides:
  - "_read_mcp_config_file_from_pyproject(cwd) helper exported from mcp_test_framework.cli."
  - "Extended _load_config precedence chain inserting the pyproject branch between --config and MCPTF_CONFIG_FILE."
  - "Fail-loud-on-typo behavior for the new branch (resolved-but-missing pyproject ini value emits operator-tone error and exits 2; parse-problem cases stay fail-soft)."
affects:
  - "28-03 (overwrite prompt): no impact — operates on out_root after config has already been resolved."
  - "28-04 (docs sweep): operator-facing docs should mention the pyproject.toml route as a config source for gen-test-classes."

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "stdlib tomllib lazy-import inside the helper body (matches cli.py's lazy-import convention for non-startup-critical imports)."
    - "Fail-soft-on-parse + fail-loud-on-resolved-but-missing: silent fall-through on parse problems (missing/malformed pyproject, no section, no key, empty value) preserves Phase 27 D-09's no-noise-for-unmigrated-operators posture; fail-loud on a populated-but-broken value prevents typo defense from silently masking the bug."
    - "Pyproject-relative path resolution: relative ini values resolve against the pyproject.toml's parent directory, mirroring `_plugin.py`'s `config.rootpath / path` convention so CLI + plugin reach the same file from the same ini value."

key-files:
  created:
    - tests/framework/unit/test_gen_test_classes_pyproject_config.py
  modified:
    - src/mcp_test_framework/cli.py

key-decisions:
  - "Branch ordering locked at --config > pyproject > MCPTF_CONFIG_FILE > ./config.yaml — pyproject is the new canonical library-mode source so it sits ABOVE the deprecated env-var path (Phase 27 D-09 deprecation continues to fire when env var is consulted)."
  - "Helper inserted between _emit_operator_error_for_validation and _load_config to keep the call-site source-local (helper is consumed exactly once by _load_config; placing it directly above the caller preserves reading order)."
  - "Branch wiring used the existing else-arm depth pattern (deepest branch nests inside MCPTF_CONFIG_FILE's else) rather than restructuring _load_config — keeps the diff focused and avoids unrelated refactoring risk."
  - "Lazy `import tomllib` inside the helper body — cli.py reserves top-of-module imports for startup-critical deps; tomllib is only touched when an operator without --config invokes any CLI command from a directory with a pyproject.toml."
  - "Direct-helper test for pyproject-relative path resolution semantics (test_relative_path_resolves_against_pyproject_directory) calls _read_mcp_config_file_from_pyproject directly. Round-tripping through _load_config from a different cwd would just exercise the missing-pyproject fall-through; the direct call isolates the relative-path-resolution semantics from cwd interference."
  - "BANNED_RE scan of _emit_operator_error call sites (tests/framework/unit/test_cli_errors.py:422) verified: the new operator-tone error has no D-\\d{2} / src/...py:N / planning-ID tokens. No follow-up scrub needed (unlike the 28-01 deviation)."

patterns-established:
  - "CLI-side config-source pyramid: --config (override) > pyproject.toml ini (library-mode default) > MCPTF_CONFIG_FILE (deprecated, fires D-09 warning) > ./config.yaml autodiscovery > fail-loud. Phase 28-02 makes pyproject.toml the canonical default that closes the seam to the pytest plugin."
  - "Fail-soft-vs-fail-loud split inside a single config-resolution branch: parse-problem fail-soft (operator hasn't onboarded library mode yet), populated-but-broken fail-loud (operator has onboarded and made a typo). Reusable pattern for future config-source additions."

requirements-completed: [CODEGEN-LIB-01]

# Metrics
duration: ~2.5min
completed: 2026-05-17
---

# Phase 28 Plan 02: Pyproject ini Config Route Summary

**Typer CLI now reads `[tool.pytest.ini_options] mcp_config_file` from pyproject.toml between the `--config` flag and the `MCPTF_CONFIG_FILE` env-var branches — `gen-test-classes` and `pytest` find the operator's config through the same single ini key (closing the Phase 27 single-config-route seam).**

## Performance

- **Duration:** ~2.5 min
- **Started:** 2026-05-17T04:17:08Z
- **Completed:** 2026-05-17T04:19:32Z
- **Tasks:** 1 (TDD)
- **Files modified:** 1 (cli.py)
- **Files created:** 1 (test_gen_test_classes_pyproject_config.py)

## Accomplishments

- `_read_mcp_config_file_from_pyproject(cwd)` helper added to `src/mcp_test_framework/cli.py` (line 253). Uses lazy `import tomllib`; opens `cwd / "pyproject.toml"` in binary mode; walks `tool.pytest.ini_options.mcp_config_file`; resolves relative values against the pyproject.toml's parent directory; returns `(resolved_config_path, pyproject_path)` on success or `(None, None)` on any fail-soft case.
- `_load_config` precedence chain extended (line 376-383 in the new layout). The new branch sits in the `else:` arm of the `--config` check and BEFORE the MCPTF_CONFIG_FILE branch — so `--config` still wins, env var still works (with the existing Phase 27 D-09 deprecation warning), and the operator who has set `mcp_config_file` in pyproject.toml gets that path consumed automatically.
- `_load_config` docstring's Precedence ladder updated to list the new branch in position 1.5.
- Fail-loud-on-typo decision: if `mcp_config_file` IS set but resolves to a non-existent file, the helper calls `_emit_operator_error` with summary `"config file not found via pyproject.toml: <path>"`, detail naming the pyproject.toml path + ini value + resolved path, and next-step pointing at fixing the value or running `mcp-contracts config-init -o config.yaml`. Exits 2. This prevents the typo from silently masking via fall-through to the env-var or autodiscovery branches.
- 9/9 new unit + helper tests pass; 616-test `tests/framework/` suite stays green (was 607 before this plan); leak gates clean (planning-ID + sdet-terminology + BANNED_RE on `_emit_operator_error` call sites all green).
- pyproject.toml dogfood line `mcp_config_file = "./config.test.yaml"` unchanged (confirmed via `git diff pyproject.toml` returning empty).

## Task Commits

Each task was committed atomically (TDD RED -> GREEN):

1. **Task 1 RED: failing pyproject.toml mcp_config_file route tests** - `850e563` (test)
2. **Task 1 GREEN: helper + _load_config wiring** - `f652bd5` (feat)

_Final plan-metadata commit (SUMMARY + STATE + ROADMAP) follows this file._

## Files Created/Modified

- `src/mcp_test_framework/cli.py` — Added `_read_mcp_config_file_from_pyproject` helper (line 253-318); extended `_load_config` precedence chain with the new pyproject branch in position 1.5 (line 376-383); updated `_load_config` docstring to list the new branch in the Precedence ladder.
- `tests/framework/unit/test_gen_test_classes_pyproject_config.py` — 9 tests covering: (1) pyproject ini consumed when no --config + no env var, (2) --config beats pyproject, (3) env var still works when no pyproject ini, (4) missing pyproject falls through to ./config.yaml, (5) malformed pyproject falls through silently, (6) pyproject without `[tool.pytest.ini_options]` falls through, (7) empty-string ini value falls through, (8) relative path resolves against pyproject directory (direct helper call to isolate semantics from cwd), (9) typo'd ini value (resolved-but-missing) raises `typer.Exit(2)`.

## Decisions Made

- **Branch ordering: pyproject ABOVE env var.** The canonical library-mode source belongs above the deprecated env-var path. Operators who onboarded library mode (set `mcp_config_file` in pyproject) get that value used even if they also have a stale `MCPTF_CONFIG_FILE` in their shell — the deprecated path is only reached when pyproject doesn't speak.
- **Fail-soft on parse, fail-loud on typo (D-13 interpretation).** Parse problems (missing/malformed pyproject, no section, no key, empty value) silently fall through — operators who haven't onboarded library mode see zero noise from this code path. But a populated-and-broken `mcp_config_file` is operator intent (they meant to point at a file); silently masking that via fall-through would let the typo evade detection until much later. The exit-2 error names the offending pyproject.toml + ini value + resolved path so the operator can fix it inline.
- **Lazy `import tomllib` inside the helper body.** cli.py's convention reserves top-of-module imports for startup-critical deps; tomllib is only touched when an operator without `--config` invokes any CLI command from a directory containing a pyproject.toml. The lazy import keeps cold-start cost identical for operators who haven't migrated to library mode yet.
- **Helper placed between `_emit_operator_error_for_validation` and `_load_config`.** Reading order matches call order: the helper is consumed exactly once by `_load_config`, so siting it immediately above the caller keeps the relevant code colocated. The 28-01 site-packages guard sits with the other operator-error-cluster helpers (line ~100); this helper belongs near `_load_config` because its only consumer is `_load_config`.
- **Direct-helper assertion for pyproject-relative path resolution (test 8).** Routing through `_load_config` from a different cwd would just exercise the missing-pyproject fall-through (because `_load_config` looks for pyproject in `Path.cwd()`, not in the test's tmp_path). Calling `_read_mcp_config_file_from_pyproject(tmp_path)` directly isolates the relative-path-resolution semantics from cwd interference and proves the resolved path is pyproject-relative regardless of where the operator is sitting.
- **`isinstance(raw, str)` guard before `.strip()`.** A pyproject.toml with `mcp_config_file = 42` (TOML integer) would otherwise crash the helper with `AttributeError`. The guard coerces non-string values to `""`, falling through silently — pyproject schema enforcement is pytest's job, not this helper's, and a silent fall-through is consistent with the fail-soft posture for other parse problems.

## Deviations from Plan

Two cosmetic deviations; no behavioral changes from the plan:

1. **[Cosmetic] Helper docstring planning-ID scrub.** The plan's literal helper docstring referenced `(Phase 27 D-06 / D-11)`, `(Phase 27 D-09)`, and `D-13`. The `D-\d{2}` references would not have tripped the planning-ID leak gate (the regex matches `(SDET|RENAME|...|LIB|...)-\d+`, not `D-\d+`), but per the 28-01 leak-gate precedent and the `docs/ERROR-STYLE.md` posture (no internal jargon in src/), the docstring + wiring comment were rewritten to descriptive prose (e.g. "Mirrors the pytest-plugin ini-resolution behavior..." instead of "Phase 27 D-06 / D-11 ini-resolution"). Semantics unchanged.
2. **[Cosmetic] Unused-local rename in _load_config wiring.** Plan's literal wiring uses `pyproject_path, pyproject_source = _read_mcp_config_file_from_pyproject(...)`. Renamed `pyproject_source` to `_pyproject_source` (leading underscore) since the second tuple slot is unused inside `_load_config` — Ruff's unused-variable lint would otherwise flag it. Same value, no behavior change.
3. **[Cosmetic] Removed redundant inline comment in test_relative_path_resolves_against_pyproject_directory.** Plan's literal test included an explanatory block-comment about why the direct helper call is used; the test's docstring already conveys the intent. Kept the docstring, dropped the inline comment.

No Rule-1/Rule-2/Rule-3 auto-fixes triggered. No architectural questions surfaced. RED -> GREEN was clean on first attempt.

## Issues Encountered

None beyond the cosmetic items above. RED gate fired on ImportError (expected); GREEN gate passed on first run after helper + wiring landed.

## User Setup Required

None — no external service configuration required. Operators who already have `[tool.pytest.ini_options] mcp_config_file = PATH` set (e.g. the framework's own dogfood line at pyproject.toml:62) get the new behavior automatically.

## Next Phase Readiness

- 28-03 (overwrite prompt) unblocked: operates on `out_root` after config has been resolved; this plan's changes are upstream of any out_root logic and do not affect the prompt's call site.
- 28-04 (docs sweep) unblocked: operator-facing docs that describe `gen-test-classes` config resolution should mention the pyproject.toml route as a config source. Suggested copy: "If you have `[tool.pytest.ini_options] mcp_config_file = PATH` in your pyproject.toml (the same key `pytest` reads), `gen-test-classes` will use that path automatically — no `--config` needed."
- No blockers carried into 28-03.

## Self-Check: PASSED

- FOUND: src/mcp_test_framework/cli.py (`def _read_mcp_config_file_from_pyproject(` at line 253; `_read_mcp_config_file_from_pyproject(...)` invocation inside `_load_config` else-arm at line 383; `import tomllib` inside the helper body at line 282)
- FOUND: tests/framework/unit/test_gen_test_classes_pyproject_config.py (9 test functions; all PASS via `uv run pytest`)
- FOUND: commit 850e563 (test RED)
- FOUND: commit f652bd5 (feat GREEN)
- Verified: `uv run pytest tests/framework/unit/test_gen_test_classes_pyproject_config.py -x -v` -> 9 passed
- Verified: `uv run pytest tests/framework/unit/test_cli_errors.py tests/framework/test_config_init_cli.py -x` -> 22 passed, 4 deselected
- Verified: `uv run pytest tests/framework/ -x` -> 616 passed, 1 skipped, 17 deselected, 1 xfailed
- Verified: `git diff pyproject.toml` -> empty (dogfood line intact)
- Verified: leak gates green (`tests/framework/test_sdet_rename_leak_gate.py` + `tests/framework/unit/test_no_planning_ids_in_src.py` -> 5 passed)

## TDD Gate Compliance

- RED gate: `850e563` — test commit precedes GREEN; ImportError on `_read_mcp_config_file_from_pyproject` confirmed RED.
- GREEN gate: `f652bd5` — feat commit follows RED; all 9 tests pass on first run after helper + wiring landed.
- REFACTOR gate: not required (helper landed in final shape on first GREEN; no follow-up cleanup needed).

---
*Phase: 28-codegen-output-path-codegen*
*Completed: 2026-05-17*
