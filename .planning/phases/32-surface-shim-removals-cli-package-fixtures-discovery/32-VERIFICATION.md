---
phase: 32-surface-shim-removals-cli-package-fixtures-discovery
verified: 2026-05-25T00:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: none
  previous_score: N/A
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 32: Surface-shim removals — Verification Report

**Phase Goal:** Every v1.4-introduced `sdet`-flavored surface shim is gone; operator invoking any legacy name hits an operator-tone error pointing at the post-v1.4 name.
**Verified:** 2026-05-25
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Locked Success Criteria)

| #   | Truth                                                                                                                                                       | Status     | Evidence |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | -------- |
| SC#1 | `import mcp_test_framework.sdet` raises `ModuleNotFoundError` with operator-tone message pointing at `mcp_test_framework.test_code` (per D-03)              | ✓ VERIFIED | Live import test: `ModuleNotFoundError: mcp_test_framework.sdet was removed in v1.5 ... next: replace `from mcp_test_framework.sdet import X` with `from mcp_test_framework.test_code import X` in your tests.` Stub at `src/mcp_test_framework/sdet/__init__.py:11-21`. |
| SC#2 | `mcp-contracts run --sdet` AND `mcp-contracts gen-sdet-classes` raise operator-tone `typer.BadParameter` errors naming `--test-code` / `gen-test-classes`. Hidden-intercept invariant preserved. | ✓ VERIFIED | Live CLI test (a): `+- Error -+ ... --sdet was removed in v1.5 ... next: pass --test-code instead of --sdet to mcp-contracts run.` Live CLI test (b): `gen-sdet-classes was removed in v1.5 ... next: invoke mcp-contracts gen-test-classes (same flags).` Both options registered `hidden=True` at `cli.py:742` (flag) and `cli.py:1418` (command). |
| SC#3 | `mcp-test-framework` console script hard-rejects with operator-tone message naming `mcp-contracts` and exits non-zero. `[project.scripts]` wiring preserved (clean-delete deferred per D-07). | ✓ VERIFIED | Live shell test: `[mcp-contracts] mcp-test-framework was removed in v1.5 ... next: invoke mcp-contracts instead of mcp-test-framework (same args).` RC=2 (non-zero, matches Typer UsageError exit). `pyproject.toml:25` wires `mcp-test-framework = "mcp_test_framework._deprecated_script:main"`. `_deprecated_script.py:14-28` implements hard-raise via `print(stderr) + sys.exit(2)`. |
| SC#4 | `tests/sdet/` no longer auto-discovered; six unprefixed fixture aliases fail at fixture-resolution time surfacing the `mcp_*`-prefixed name. | ✓ VERIFIED | `_runner.py:130-139` collects only `tests/contract` / `tests/test_code` / `tests/framework` — `tests/sdet` absent. Six fixture stubs at `_plugin.py:468-567` (`config`/`judge`/`target_tool`/`rubric_clarity`/`rubric_disambiguation`/`rubric_parameters`) each call `pytest.fail` with operator-tone message naming the `mcp_*`-prefixed equivalent. Regression `tests/framework/unit/test_plugin_unprefixed_fixtures_removed.py` parametrizes all six aliases with `result.assert_outcomes(errors=1)` and pins the message text — passed (6/6). `tests/sdet/` warn-on-presence detector at `_plugin.py:293-314` (intentional per D-05). |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/mcp_test_framework/sdet/__init__.py` | Hard-raise stub with operator-tone `ModuleNotFoundError` | ✓ VERIFIED | 22 lines; raise fires at module-load; message names `mcp_test_framework.test_code` and lists all four re-exports. |
| `src/mcp_test_framework/cli.py:645-662` | `_sdet_flag_removed` Click callback (eager) raising `typer.BadParameter` | ✓ VERIFIED | `is_eager=True`, `callback=_sdet_flag_removed`; `if value:` guard works because Click registers `--sdet` as presence-only flag (verified `--sdet=false` errors with "Option does not take a value" — CR-02 attack vector blocked at Click parse layer before callback fires). |
| `src/mcp_test_framework/cli.py:1418-1433` | `gen-sdet-classes` hidden command raising `typer.BadParameter` | ✓ VERIFIED | `@app.command("gen-sdet-classes", hidden=True)`; unconditional raise. |
| `src/mcp_test_framework/_plugin.py:296-314` | Loud collection-time `tests/sdet/` presence detector | ✓ VERIFIED | Uses `_mcptf_formatwarning` for `[mcp-contracts]` prefix; restores original formatter in `finally`. |
| `src/mcp_test_framework/_plugin.py:468-567` | Six unprefixed fixture stubs (`config`, `judge`, `target_tool`, `rubric_clarity`, `rubric_disambiguation`, `rubric_parameters`) | ✓ VERIFIED | All six present; each calls `pytest.fail(MSG, pytrace=False)`; prefixed-fixture parameter dropped (Pitfall 1 protection). |
| `src/mcp_test_framework/_deprecated_script.py` | Hard-raise console-script entry | ✓ VERIFIED | `print(stderr) + sys.exit(2)`; message names `mcp-contracts`. |
| `pyproject.toml:25` | `mcp-test-framework` → `_deprecated_script:main` wiring preserved | ✓ VERIFIED | Entry intact for v1.5 (clean-delete deferred to v1.6 per D-07). |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `cli.py` `--sdet` option | `_sdet_flag_removed` | `callback=`, `is_eager=True`, `hidden=True` | ✓ WIRED | `cli.py:739-746` — option-to-callback wiring verified; eager firing triggers BadParameter before pytest spawn. |
| `cli.py` `gen-sdet-classes` | `_gen_sdet_classes_removed` | `@app.command("gen-sdet-classes", hidden=True)` | ✓ WIRED | Typer command registration verified via live invocation. |
| `_plugin.py` `pytest_collection` | `tests/sdet/` legacy-presence detection | `legacy_dir.glob("test_*.py")` | ✓ WIRED | Pinned by `tests/framework/unit/test_plugin_tests_sdet_warning.py` (3 tests passed). |
| `_plugin.py` removal-stub fixtures | `pytest.fail` with operator-tone text | `@pytest.fixture` registration via `pytest11` entry point | ✓ WIRED | Pinned by `tests/framework/unit/test_plugin_unprefixed_fixtures_removed.py` (6/6 parametrized cases passed). |
| `pyproject.toml` `[project.scripts]` | `_deprecated_script.main` | `mcp-test-framework = "mcp_test_framework._deprecated_script:main"` | ✓ WIRED | Live `uv run mcp-test-framework run` exits 2 with operator-tone message. |
| Leak-gate scanner | `src/**/*.py` | `tests/framework/test_sdet_rename_leak_gate.py` | ✓ WIRED | 4/4 passed; confirms surviving `sdet` tokens are all `# noqa: sdet-rename-shim`-tagged. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| SC#1 import-time hard-raise | `uv run python -c "import mcp_test_framework.sdet"` | `ModuleNotFoundError` with operator-tone message; exit 1 | ✓ PASS |
| SC#2a `--sdet` hidden intercept | `uv run mcp-contracts run --sdet` | `typer.BadParameter` rendered as `+- Error -+` box; names `--test-code` | ✓ PASS |
| SC#2b `gen-sdet-classes` hidden intercept | `uv run mcp-contracts gen-sdet-classes` | `typer.BadParameter`; names `gen-test-classes` | ✓ PASS |
| SC#3 legacy console script | `uv run mcp-test-framework run; echo RC=$?` | Operator-tone message to stderr; RC=2 | ✓ PASS |
| SC#4 fixture stub-raise | `uv run python -m pytest tests/framework/unit/test_plugin_unprefixed_fixtures_removed.py -q` | 6 passed in 13.86s | ✓ PASS |
| SC#4 `tests/sdet/` warn detector | `uv run python -m pytest tests/framework/unit/test_plugin_tests_sdet_warning.py -q` | 3 passed | ✓ PASS |
| Leak-gate (residual token sweep) | `uv run python -m pytest tests/framework/test_sdet_rename_leak_gate.py -q` | 4 passed | ✓ PASS |
| Full framework regression | `uv run python -m pytest tests/framework/ -q --tb=short` | 700 passed, 2 skipped, 18 deselected, 1 xfailed, 2 warnings in 73.88s | ✓ PASS |
| CR-02 edge-case probe | `uv run mcp-contracts run --sdet=false` | Click rejects: "Option '--sdet' does not take a value." (RC=2) — callback's `if value:` never reachable via this argv | ✓ PASS (non-defect) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| SHIM-01 | 32-01-PLAN | `from mcp_test_framework.sdet import ...` raises `ModuleNotFoundError` pointing at `mcp_test_framework.test_code` | ✓ SATISFIED | Live import probe + `test_error_style.py` registry entry. |
| SHIM-02 | 32-02-PLAN | `--sdet` removed; UsageError points at `--test-code` | ✓ SATISFIED | Live CLI probe + `test_runner_sdet_kwarg.py` / `test_runner_sdet_rows.py` regression coverage. |
| SHIM-03 | 32-03-PLAN | `gen-sdet-classes` removed; UsageError points at `gen-test-classes` | ✓ SATISFIED | Live CLI probe + `test_gen_sdet_classes_cli.py` / `test_gen_sdet_classes_config_driven.py`. |
| SHIM-06 | 32-04-PLAN | `tests/sdet/` no longer auto-discovered | ✓ SATISFIED | `_runner.py:130-139` lists only contract/test_code/framework paths; warn-on-presence detector pinned. |
| SHIM-07 | 32-05-PLAN | Six unprefixed fixture aliases fail at fixture-resolution time surfacing prefixed name | ✓ SATISFIED | `_plugin.py:468-567` (all six stubs) + `test_plugin_unprefixed_fixtures_removed.py` (6/6 parametrized cases passed). |
| SHIM-08 | 32-06-PLAN | Legacy `mcp-test-framework` console script removed (operator-visible hard-raise) | ✓ SATISFIED | Live shell probe + `test_console_script_removed.py`. |

All six declared requirement IDs verified. No orphaned IDs (REQUIREMENTS.md §SHIM lists SHIM-01..09; SHIM-04/05 belong to Phase 31, SHIM-09 belongs to Phase 35 per CONTEXT.md "Out of scope").

### Anti-Patterns Found

No anti-patterns blocking goal achievement.

Notable items (not blockers — all align with locked design decisions):

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `src/mcp_test_framework/sdet/__init__.py` | 11 | Module-load-time raise | ℹ️ Info (per CR-01) | Reviewer suggested PEP 562 `__getattr__` lazy hook. CONTEXT D-03 explicitly chose import-time raise; intentional. Locked decision overrides review suggestion. |
| `src/mcp_test_framework/_plugin.py` | 297 | `legacy_dir.glob("test_*.py")` non-recursive | ⚠️ Warning (WR-02 in REVIEW) | Operator with nested `tests/sdet/subgroup/test_x.py` does not trigger warning. SC#4 minimum bar = "no longer auto-discovered" — still satisfied. Loud detection is the loud-and-friendly upgrade; recursive scan would be more thorough. Recommend Phase 35 SHIM-09 regression gate or follow-up cleanup. Not a SC blocker. |
| `src/mcp_test_framework/_plugin.py` | 293 | Detector runs unconditionally before library-mode opt-in gate | ⚠️ Warning (WR-03 in REVIEW) | Third-party pytest users with unrelated `tests/sdet/` paths get framework's chatter. Not an SC defect; minor UX concern. |
| `src/mcp_test_framework/_deprecated_script.py` | 27 | `print(file=sys.stderr)` without explicit `flush=True` | ℹ️ Info (WR-04 in REVIEW) | Message ends with `\n` so current behavior is safe; future drift risk only. |
| `src/mcp_test_framework/_plugin.py` | 468-567 | Six fixture stubs duplicate near-identical message body | ℹ️ Info (IN-01 in REVIEW) | Acknowledged trade-off — verbatim message-pinning is current pattern. Helper extraction would conflict with `test_error_style.py` literal pinning. |
| `src/mcp_test_framework/cli.py` | 1420 | `gen-sdet-classes` stub accepts but ignores `--config` | ℹ️ Info (CR-03 in REVIEW) | Reviewer flagged; CONTEXT D-04 intentionally preserves `--config` for clean argv parsing. Locked decision; not a defect. |

### CR-02 Investigation Result

The code-review report (CR-02) claimed `mcp-contracts run --sdet=false` produces a silent fallthrough because `_sdet_flag_removed`'s `if value:` guard rejects only truthy values.

**Verification result: CR-02 is NOT reproducible as described.**

Live probe `uv run mcp-contracts run --sdet=false` returns RC=2 with Click error: `Option '--sdet' does not take a value.` This happens because the `--sdet` option is declared as a presence-only flag (single name, no `/--no-X` companion) — Click rejects `=value` syntax at parse time, BEFORE the eager callback fires. The callback's `if value:` is reachable only with the presence-truthy path (`--sdet` alone), which correctly raises. The CR-02 attack vector (silent acceptance of `--sdet=false`) does not exist under the declared option pattern.

**Conclusion:** CR-02 is NOT a defect. No remediation required for Phase 32 goal.

### Human Verification Required

None. All four locked Success Criteria are programmatically verifiable and were verified via live CLI / import probes plus the framework regression suite.

### Gaps Summary

No gaps. Phase 32 goal achieved:
- Six v1.4 `sdet`-flavored surface shims are retired (sdet package, `--sdet` flag, `gen-sdet-classes` command, `tests/sdet/` discovery, six unprefixed fixtures, `mcp-test-framework` console script).
- Each legacy surface emits an operator-tone migration error naming the post-v1.4 replacement (`mcp_test_framework.test_code`, `--test-code`, `gen-test-classes`, `tests/test_code/`, `mcp_*`-prefixed fixtures, `mcp-contracts`).
- Hidden-intercept invariant preserved per CONTEXT D-04 (Typer `hidden=True` on `--sdet` and `gen-sdet-classes`); clean-delete deferred to v1.6 per D-07.
- Full framework suite (700 tests) passes with the new shim-retirement code paths.

Code review's three BLOCKER findings (CR-01, CR-02, CR-03) are either (a) addressing intentional locked CONTEXT decisions overriding the reviewer's preference (CR-01 hard-raise on import; CR-03 keep `--config` on hidden command), or (b) non-reproducible as described under the actual flag-registration pattern (CR-02). No remediation needed for Phase 32 goal.

Three WARNING items (WR-02 non-recursive glob, WR-03 unconditional walk, WR-04 missing explicit flush) are non-blocking UX-polish suggestions worth carrying forward to a follow-up cleanup pass but do not affect SC achievement.

---

_Verified: 2026-05-25_
_Verifier: Claude (gsd-verifier)_
