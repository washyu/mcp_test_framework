---
phase: 23-test-suite-debt-cleanup
verified: 2026-05-14T00:00:00Z
status: passed
score: 14/14 must-haves verified
overrides_applied: 0
re_verification: null
---

# Phase 23: Test suite debt cleanup — Verification Report

**Phase Goal:** Clear pre-existing `tests/framework/` failures discovered during Phase 20 UAT (Config v1->v2 schema mismatches, `parents[2]` path resolution after Phase 15 folder split, missing `tests.test_mcp_tool_contract` module + `tests/docs/MIGRATION-v1-to-v2.md` doc, README line-104 doc drift); close 11 fails + 1 error so v1.3 close ships a green framework suite.

**Verified:** 2026-05-14
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

The single load-bearing close-gate for Phase 23 (per ROADMAP):

> `uv run pytest tests/framework/ --tb=no -q` exits 0 with `failed == 0 and errored == 0`.

Verifier re-ran the gate locally at HEAD (`5f4a263`):

```
575 passed, 1 skipped, 17 deselected, 2 xfailed in 15.67s
```

Exit code 0. `failed` and `error` keywords omitted from summary line (i.e. both == 0). Result reproduces the orchestrator-side number byte-for-byte (modulo wall-clock variance: 15.67s vs 15.50s).

### Observable Truths

Phase 23 has no formal ROADMAP Success Criteria array. The truths below merge the four PLANs' frontmatter `must_haves.truths` with the orchestrator-stated close-gate (D-07/D-08).

| #   | Truth                                                                                                                                                                  | Status     | Evidence                                                                                                                                              |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `uv run pytest tests/framework/ --tb=no -q` exits 0 with `failed==0 and errored==0` (D-07/D-08 close-gate)                                                             | VERIFIED   | Re-ran locally: `575 passed, 1 skipped, 17 deselected, 2 xfailed`. Exit 0. No `failed` or `error` keyword in summary line.                            |
| 2   | Every Cluster A red site has `Config(sdet=_SDET_STUB)` or `Config(sdet=SdetConfig(...))`; bare `Config()` survives only at intentional env-fallback sites              | VERIFIED   | 5 files modified per Plan 01 (test_tool_config, test_config_init_cli, both smoke files, test_isolation marker); pattern visible in each.                |
| 3   | `tests/framework/conftest.py` exists and shadows the production session-scoped `config` fixture supplying `_SDET_STUB`; `src/mcp_test_framework/fixtures.py` unchanged | VERIFIED   | File reads exactly the verbatim D-02 body (24 lines). `git diff 8d269ef..HEAD -- src/mcp_test_framework/` returns empty across the entire phase.       |
| 4   | After Plan 01, every Cluster A red goes green (`pydantic.ValidationError: sdet Field required` and version-1 stale assertions both gone)                                | VERIFIED   | Plan 01 SUMMARY pre/post: 12 failed -> 8 failed; close-gate later reaches 0 failed.                                                                    |
| 5   | `tests/framework/unit/test_migration_doc.py` `_repo_root()` uses `parents[3]` (was `parents[2]`)                                                                       | VERIFIED   | Read tests/framework/unit/test_migration_doc.py:15 -> `return Path(__file__).resolve().parents[3]`. `parents[2]` no longer present in file.            |
| 6   | `tests/framework/unit/test_cli_errors.py` `repo_root` resolution near line 407 uses `parents[3]`                                                                       | VERIFIED   | Grep: `parents[3]` at line 427 (line shifted slightly due to test additions in env-pollution seal commit). Zero `parents[2]` matches in file.          |
| 7   | No shared helper extracted; heterogeneous `parents[N]` vs walk-to-pyproject styles preserved (D-04)                                                                     | VERIFIED   | Two single-line changes only; no new helper module; `test_doc_scrub.py` walk-to-pyproject style untouched.                                             |
| 8   | All Cluster B reds (5 tests) green                                                                                                                                      | VERIFIED   | Plan 02 SUMMARY shows pre 5 failed -> post 24 passed; full suite green at HEAD confirms it stuck.                                                       |
| 9   | Every operator-facing `mcp-test-framework` invocation in README pairs with `--config config.yaml` (D-05)                                                                | VERIFIED   | `grep -n "mcp-test-framework run" README.md` shows all 6 invocations paired with `--config` (or are subdivided like `--sdet`/sample text).             |
| 10  | Zero banned-token regex matches remain in README under `BASE_BANNED + [r"src/[\w/.]+\.py:\d+"]` (D-06)                                                                  | VERIFIED   | Plan 03 captured one hit at line 274 (`Phase 21 D-14`), semantically rewritten to cite `docs/SDET-AUTHORING.md`. Doc-scrub test passes in close-gate.   |
| 11  | Banned-token hits scrubbed via semantic rewrite preserving prose meaning + citing surviving doc anchors — not regex-strip (Phase 12 D-10)                                | VERIFIED   | Read README:274 — replacement preserves "re-run when output format changes" intent + cites docs/SDET-AUTHORING.md. No `noqa`-style allowlist added.    |
| 12  | `test_doc_invocations_consistently_pair_with_config` and `test_readme_exists_and_no_banned_tokens` both pass                                                            | VERIFIED   | Both included in 575-passed close-gate. Plan 03 SUMMARY captured 2/2 + the EXTENDING.md `path1` parametrization green.                                  |
| 13  | No `src/mcp_test_framework/` files were modified during the entire phase (D-02 invariant)                                                                                | VERIFIED   | `git diff --stat 8d269ef..HEAD -- src/mcp_test_framework/` returns empty. `git log --oneline 8d269ef..HEAD -- src/mcp_test_framework/` returns empty. |
| 14  | Pre-existing xfailed (2) and skipped (1) counts may remain — out of scope per D-08                                                                                       | VERIFIED   | Close-gate result: 1 skipped, 2 xfailed — exactly the documented baseline. 17 deselected matches `live_homelab + live_ollama` addopts filter.          |

**Score:** 14/14 truths verified.

### Required Artifacts

| Artifact                                            | Expected                                              | Status     | Details                                                                                                                                |
| --------------------------------------------------- | ----------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/framework/conftest.py`                       | NEW; D-02 session-scoped `config` fixture override    | VERIFIED   | 24-line file matching plan's verbatim spec; imports `Config` + `SdetConfig`; `_SDET_STUB = SdetConfig(generated_root="tests/sdet/_generated")`; fixture is `@pytest.fixture(scope="session")`. |
| `tests/framework/test_tool_config.py`               | `_SDET_STUB` module constant + version-2 assertions   | VERIFIED   | Module-level `_SDET_STUB` present; bare `Config()` sites all carry `sdet=_SDET_STUB`; stale `version == 1` bumped to `version == 2`; parametrize `[2]` -> `[1]` (now-stale).             |
| `tests/framework/test_config_init_cli.py`           | S2 inline `Config(sdet=SdetConfig(...))` at line ~130 | VERIFIED   | Plan 01 SUMMARY records change applied; file is in tests/framework/ diff stat (+9 lines). Behind `live_homelab` marker, deselected by default.                                            |
| `tests/framework/smoke/test_smoke_homelab_mcp.py`   | S1 module stub at the 2 bare-`Config()` sites         | VERIFIED   | `_SDET_STUB` constant at line 42; `Config(sdet=_SDET_STUB)` at lines 47 and 69. WR-01 (`cfg.target.tool_name` at 58, 75) is a separate pre-existing live-marker red — see Notes.            |
| `tests/framework/smoke/test_smoke_ollama_judge.py`  | S2 inline kwarg                                       | VERIFIED   | Plan 01 SUMMARY records change applied; behind `live_ollama` marker, deselected by default.                                                                                                |
| `tests/framework/unit/test_migration_doc.py`        | `parents[3]` in `_repo_root()`                        | VERIFIED   | Line 15: `return Path(__file__).resolve().parents[3]`. Single one-line diff per Plan 02 SUMMARY.                                                                                            |
| `tests/framework/unit/test_cli_errors.py`           | `parents[3]` for `repo_root` near line 407            | VERIFIED   | `parents[3]` at line 427 (shifted from 407 by the env-pollution seal lines added in commit `6ee48b5`). Zero remaining `parents[2]` matches.                                               |
| `README.md` line ~104                                | `mcp-test-framework run --config config.yaml --explain` | VERIFIED   | Read: `$ mcp-test-framework run --config config.yaml --explain`.                                                                                                                          |
| `README.md` line ~274                                | Maintainer comment without banned tokens               | VERIFIED   | Replacement cites `docs/SDET-AUTHORING.md` instead of `Phase 21 D-14`. Operator/maintainer intent preserved.                                                                              |
| `docs/MIGRATION-v1-to-v2.md`                         | Exists at repo root (not under `tests/docs/`)          | VERIFIED   | `ls docs/MIGRATION-v1-to-v2.md` succeeds. `parents[3]` resolution from `tests/framework/unit/test_migration_doc.py` lands here.                                                          |
| `tests/contract/test_mcp_tool_contract.py`           | Exists; importable as `tests.contract.test_mcp_tool_contract` | VERIFIED   | `ls tests/contract/` shows the module. `tests/framework/test_tool_config.py:364` imports `from tests.contract.test_mcp_tool_contract import ...` — recovered post commit `24434f7`.    |

### Key Link Verification

| From                                                   | To                                                          | Via                                                  | Status   | Details                                                                                                                                            |
| ------------------------------------------------------ | ----------------------------------------------------------- | ---------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/framework/conftest.py`                           | `mcp_test_framework.config.Config` + `models.SdetConfig`     | session-scoped fixture override + `_SDET_STUB` import  | WIRED    | Imports + fixture body present; pytest's nested-conftest precedence shadows production `config` fixture for any test under `tests/framework/`.    |
| `tests/framework/unit/test_migration_doc.py`            | `docs/MIGRATION-v1-to-v2.md`                                 | Path resolution via `parents[3]`                     | WIRED    | `parents[3]` from `tests/framework/unit/test_migration_doc.py` (depth 3) reaches repo root; `MIGRATION_DOC` then resolves under `docs/`.            |
| `tests/framework/unit/test_cli_errors.py`               | `src/mcp_test_framework/cli.py`                              | Path resolution via `parents[3]`                     | WIRED    | Same depth math; AST-scan reads the real `cli.py` and asserts no banned tokens.                                                                    |
| `tests/framework/test_tool_config.py:364`               | `tests.contract.test_mcp_tool_contract`                     | import retarget post Phase 15 SURFACE split          | WIRED    | Stale `tests.test_mcp_tool_contract` rewritten in recovery commit `24434f7`; module exists at `tests/contract/test_mcp_tool_contract.py`.            |
| `README.md`                                              | `tests/framework/unit/test_doc_scrub.py`                     | doc-scrub close-gate tests                           | WIRED    | Both `test_doc_invocations_consistently_pair_with_config` and `test_readme_exists_and_no_banned_tokens` pass in the 575-passed close-gate run.    |
| Plan 04 close-gate                                       | Plans 01, 02, 03                                             | depends_on chain (wave: 2)                           | WIRED    | Wave-2 `files_modified: []` plan; ran after Wave-1 plans + recovery commit; recorded GREEN in 23-04-SUMMARY.md.                                    |

### Data-Flow Trace (Level 4)

N/A — no rendered data flow in this debt-cleanup phase. The artifacts are test code, not user-facing components. Behavioral verification is the close-gate (Step 7b) below.

### Behavioral Spot-Checks

| Behavior                                                      | Command                                                          | Result                                          | Status |
| ------------------------------------------------------------- | ---------------------------------------------------------------- | ----------------------------------------------- | ------ |
| Full `tests/framework/` suite passes under default addopts    | `uv run pytest tests/framework/ --tb=no -q`                       | `575 passed, 1 skipped, 17 deselected, 2 xfailed in 15.67s` (exit 0) | PASS   |
| `src/mcp_test_framework/` invariant holds (D-02)              | `git diff --stat 8d269ef..HEAD -- src/mcp_test_framework/`        | empty                                           | PASS   |
| No commits even touched `src/mcp_test_framework/`             | `git log --oneline 8d269ef..HEAD -- src/mcp_test_framework/`      | empty                                           | PASS   |
| `parents[3]` present at the two patched sites                 | Grep on the two test files                                        | 1 match in `test_migration_doc.py:15`, 1 match in `test_cli_errors.py:427` | PASS   |
| `parents[2]` removed from the two patched sites               | Grep on the two test files                                        | zero matches                                    | PASS   |
| `pyproject.toml` `addopts` unchanged (T-23-04-01 anti-tamper) | Read pyproject.toml line 53                                       | `addopts = "-m 'not live_homelab and not live_ollama'"` (verbatim) | PASS   |

### Requirements Coverage

Phase 23 PLAN frontmatter declares `requirements: []` for all four plans (pure debt cleanup). REQUIREMENTS.md allocates no IDs to Phase 23 (per orchestrator note). No requirement-coverage gaps to report.

### Anti-Patterns Found

| File                                                     | Line(s) | Pattern                                              | Severity | Impact                                                                                                                                                                                           |
| -------------------------------------------------------- | ------- | ---------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `tests/framework/smoke/test_smoke_homelab_mcp.py`        | 58, 75  | `cfg.target.tool_name` accesses removed `Config.target` field | INFO     | WR-01 from 23-REVIEW.md. Pre-existing bug; deselected by `live_homelab` marker so doesn't fail the close-gate. Out of phase 23 scope-as-executed; would surface under `pytest -m live_homelab`. |
| `tests/framework/conftest.py`                            | 22-24   | Override discards `MCPTF_CONFIG_FILE` overlay for tests under tests/framework/ | INFO     | WR-02/WR-03 from 23-REVIEW.md. D-02 trade-off: stub `Config(sdet=_SDET_STUB)` does not consult YAML/env layers. Acceptable for framework-self-tests; out of phase 23 scope.                  |
| (cross-cutting)                                           | n/a     | Preflight predicate path-prefixed to `tests/contract/` + `tests/sdet/` doesn't fire on the new `live_homelab` opt-in in `tests/framework/` | INFO     | WR-04 from 23-REVIEW.md. Advisory; doesn't affect default-addopts close-gate.                                                                                                                  |

All three are flagged as INFO per orchestrator instruction: "These are advisory and outside Phase 23 scope-as-executed (the close-gate IS green). Surface them in the report but do NOT fail the phase on them."

### Human Verification Required

None. The phase goal is mechanically observable (pytest exit code + diff invariants), and all checks are programmatic. No UI, no real-time behavior, no external service integration is in scope. Per Step 9: with zero gaps and zero human items, status = `passed`.

### Gaps Summary

No gaps. The close-gate D-07/D-08 contract is satisfied:

- `uv run pytest tests/framework/ --tb=no -q` exits 0 with 0 failed and 0 errored at HEAD `5f4a263`.
- D-02 invariant (`src/mcp_test_framework/` untouched) holds across the full phase range `8d269ef..HEAD`, including the post-Wave-1 recovery commit `24434f7`.
- All Cluster A (config-construction policy), Cluster B (parents[N] depth bump), and Cluster C (README doc drift) red sites enumerated in the Plan 01 inventory are now green.
- The two residual reds patched in recovery commit `24434f7` (stale `tests.test_mcp_tool_contract` import + missing `live_homelab` marker on `test_isolation.py`) were correctly classified under D-07 ("any additional reds that appear during phase execution are in scope").
- Pre-existing xfailed=2 and skipped=1 counts match the documented D-08 baseline; the 17 deselected count matches `pyproject.toml` `addopts`.

The three review WARNINGS (WR-01..WR-04) are recorded as INFO anti-patterns above per orchestrator guidance: they are scoped behind opt-in markers (`live_homelab`/`live_ollama`) that the default close-gate deselects, and the phase title scopes the work to `tests/framework/` debt — not to a live-run hardening pass. They remain available as deferred items for a future live-marker hardening phase.

### Phase Boundary Discipline

| Boundary check                                                   | Verdict                                                              |
| ---------------------------------------------------------------- | -------------------------------------------------------------------- |
| Only `tests/framework/conftest.py` is a NEW file in `tests/framework/` | OK — diff stat shows 1 new file, 7 modified files                  |
| `README.md` change limited to Plan 03 sentences (lines 104, 274) | OK — diff stat shows 4 lines (2 ins, 2 del)                          |
| `pyproject.toml` `addopts` unchanged                              | OK — `addopts = "-m 'not live_homelab and not live_ollama'"` verbatim |
| `tests/framework/unit/test_homelab_config.py` (pattern source) untouched | OK — Plan 01 SUMMARY self-check verified empty `git diff` |
| `src/mcp_test_framework/fixtures.py` (production fixture) untouched | OK — covered by the broader `src/` invariant                       |

---

_Verified: 2026-05-14 by Claude (gsd-verifier, Opus 4.7 1M)_
_Phase 23 close-gate: GREEN (575 passed, 0 failed, 0 errored)_
