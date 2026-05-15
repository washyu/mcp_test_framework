---
phase: 22-scrub-requirement-id-leaks-from-src
plan: 03
subsystem: infra
tags: [docs, scrub, src-hygiene, semantic-rewrite]

# Dependency graph
requires:
  - phase: 22
    provides: "D-02 semantic-rewrite policy, locked grep regex, surviving doc anchors"
provides:
  - "Ten src/ modules (everything outside cli.py and sdet/) scrubbed of planning IDs and Phase NN prefixes"
  - "Behavior preserved: 119 runner unit tests + 70 config/error-style tests + 47 schema/client/judge/rubric tests pass"
  - "Locked invariants survive as prose: pytest-subprocess contract, AsyncExitStack teardown, isolation allowlist, Ollama temperature:0 + format:json, em-dash separator, locked skip-reason constants"
affects: [22-04-regression-gate, future-maintainer-grep]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Semantic comment rewrite (drop pure-provenance; rewrite rationale-bearing) per Phase 22 D-02"
    - "Surviving anchors cite only docs/ERROR-STYLE.md, README.md, CLAUDE.md, docs/SDET-AUTHORING.md"

key-files:
  created: []
  modified:
    - src/mcp_test_framework/_runner.py
    - src/mcp_test_framework/_isolation.py
    - src/mcp_test_framework/fixtures.py
    - src/mcp_test_framework/config.py
    - src/mcp_test_framework/models.py
    - src/mcp_test_framework/schema_validator.py
    - src/mcp_test_framework/mcp_client.py
    - src/mcp_test_framework/judge_protocol.py
    - src/mcp_test_framework/ollama_judge.py
    - src/mcp_test_framework/rubrics.py

key-decisions:
  - "Rewrote the _runner.py module docstring as a runner-contract description (pytest-subprocess + tempfile + exit-code mapping) rather than enumerating D-01..D-16 anchors."
  - "Preserved the SAFE-NN/Phase-NN comments in fixtures.py and config.py as docs/ERROR-STYLE.md references — the canonical operator-tone error strings live there now."
  - "Kept all locked invariants (skip-reason constants, allowlist tuple, Ollama temperature:0, AsyncExitStack contract) as prose; the locking is now enforced by their pinning unit tests, not the comments."

patterns-established:
  - "Pure-provenance comments dropped wholesale (e.g. # Phase 14 D-13: --debug appends after...)"
  - "Rationale-bearing comments rewrote in place, dropping the planning prefix while keeping the rule"
  - "When a comment pointed at a .planning/ doc, the anchor was dropped (D-03); when it pointed at a docs/ anchor that still adds maintainer value, the anchor was kept"

requirements-completed: [SCRUB-SRC-01]

# Metrics
duration: 35min
completed: 2026-05-14
---

# Phase 22 Plan 03: Scrub planning IDs from the remaining 10 src/ modules Summary

**Removed 175 ID matches + 136 Phase NN prefixes from ten src/ files (the bulk of remaining planning leakage in src/) while keeping locked invariants — pytest-subprocess + tempfile contract, isolation allowlist, Ollama request body, AsyncExitStack teardown — readable as prose.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 3 (one per file-cluster)
- **Files modified:** 10
- **Tests run:** 236 unit tests across the three task-acceptance sweeps; all passed

## Accomplishments

- Ten files now have ZERO matches for the locked regex `(CLI|PERSONA|CODEGEN|SAFE|RUNNER|UX|ISOL|JUNIT|SURFACE|TEST|CLEAN|DOC|UI|SDET|STATE|PREFLIGHT|SCRUB|RELOC)-[0-9]+|\bD-[0-9]+\b` and zero `Phase NN(.M)?` prefixes.
- Module docstrings rewrote as forward-looking contracts (what the module does), not planning history (which D-NN told us to do what).
- Surviving doc anchors point at `docs/ERROR-STYLE.md` (operator-tone error rendering rationale in `_runner.py`, `fixtures.py`, `config.py`, `models.py`).
- Locked invariants survive verbatim in code (constants, defaults, request bodies) and in prose (comments around them) — pinning unit tests catch any future drift.
- Behavior preserved end-to-end: 119 runner unit tests + 70 config/error-style/isolation tests + 47 schema/client/judge/rubric tests all pass.
- Phase 23 baseline preserved: full `tests/framework` run shows 12 failed + 1 error, byte-identical to the pre-scrub baseline (same failures, all pre-existing Phase 23 debt — config schema v1→v2 mismatch on tests that pre-date Phase 21.1 making `sdet` required; README/docs containing `Phase NN` for Phase 22 cleanup; missing `tests/docs/MIGRATION-v1-to-v2.md`).

## Per-file Hit Counts

| File | ID (before → after) | Phase NN (before → after) |
| --- | --- | --- |
| `_runner.py` | 76 → 0 | 75 → 0 |
| `_isolation.py` | 17 → 0 | 2 → 0 |
| `fixtures.py` | 16 → 0 | 16 → 0 |
| `config.py` | 15 → 0 | 10 → 0 |
| `models.py` | 16 → 0 | 6 → 0 |
| `schema_validator.py` | 7 → 0 | 3 → 0 |
| `mcp_client.py` | 9 → 0 | 12 → 0 |
| `judge_protocol.py` | 3 → 0 | 3 → 0 |
| `ollama_judge.py` | 14 → 0 | 8 → 0 |
| `rubrics.py` | 2 → 0 | 1 → 0 |
| **Total** | **175 → 0** | **136 → 0** |

## Task Commits

Each task was committed atomically:

1. **Task 1: Scrub `_runner.py`** — `7d94433` (docs)
   - Rewrote the top-of-file module docstring as a runner-contract description (no D-01..D-16 enumeration).
   - Dropped Phase NN / D-NN prefixes from comments around `_compose_pre_run_skip_reasons`, `_compose_unparametrized_skips_from_config`, `_render_pre_run_digest`, `render_debug_appendix`, and the JUnit XML parser.
   - Kept all em-dash literals (U+2014) verbatim and the locked skip-reason constants `_REASON_NOT_SELECTED` / `_REASON_EXPLICIT_DEFAULT` unchanged.
   - Verified: 119 runner unit tests pass.

2. **Task 2: Scrub `_isolation.py`, `fixtures.py`, `config.py`** — `1985ac1` (docs)
   - `_isolation.py`: rewrote module docstring as a "what the module does" description; kept the allowlist tuple (`PATH`, `SYSTEMROOT`, `LANG`, `USERNAME`, `MCP_*`) verbatim and the always-on / no-toggle rule as prose.
   - `fixtures.py`: dropped planning prefixes from `_preflight`, `mcp_client`, `_isolated_home` docstrings; preserved the cancel-scope-no-anyio-across-yield invariant, AsyncExitStack lifecycle, single-source-of-truth tempdir, and the operator-tone missing-config error reference (now cites `docs/ERROR-STYLE.md` instead of `SAFE-03`).
   - `config.py`: dropped `SAFE-NN` / `Phase NN` anchors; kept precedence chain (CLI > env > YAML > defaults), v2-only validator with operator-tone version-mismatch reference to `docs/ERROR-STYLE.md`, env-var-is-path-pointer rule, and the IPC fallback for the in-process pytest session.
   - Verified: 70 config + error-style + isolation tests pass.

3. **Task 3: Scrub the six lighter-density files** — `06067e5` (docs)
   - `models.py`: rewrote module/class docstrings; kept env-var routing rationale (`AliasChoices`), `ToolConfig.skip` requires non-empty `skip_reason`, `judges=None` means "all rubrics" vs `judges=[]` means "explicit opt-out", and `SdetConfig.generated_root` required-no-default rule with the canonical missing-required-field reference.
   - `schema_validator.py`: dropped planning anchors from the 7-check overview; kept `Draft202012Validator` default-fallback rule, the empty-list-is-success contract, and the JSON-Pointer (RFC 6901) format note.
   - `mcp_client.py`: rewrote module docstring as a "what the wrapper does" description; preserved the `stdio_client` (no raw `subprocess.Popen`) rule, AsyncExitStack teardown contract, no-5s-force-kill posture, `asyncio.timeout` uniform-ceiling rule, and `server_info` serverInfo-discard workaround.
   - `judge_protocol.py`: rewrote as a "why Protocol over ABC + one-way dep on `ollama_judge.JudgeResult`" docstring; kept the `@runtime_checkable` signature-validation caveat.
   - `ollama_judge.py`: preserved the locked request body invariants (`stream:false`, `format:"json"`, `think:false`, `keep_alive:"30m"`, `temperature:0`, `num_predict:256`, `Timeout(timeout, connect=10.0)`), the four-step defensive parser, the prompt-injection mitigation via `<<<SUBJECT>>>` markers, and the `JudgeResult` raw-response-preserved-on-every-branch rule.
   - `rubrics.py`: kept the SUBJECT-marker single-source-of-truth note linking back to `ollama_judge._build_request_body` / `_SYSTEM_PROMPT`, and the "default to 4" score-5 caution as prose without the "Pitfall 6" anchor.
   - Verified: 47 schema/client/judge/rubric unit tests pass.

## Files Created/Modified

Ten files, all under `src/mcp_test_framework/`. See per-file table above for hit-count deltas.

## Decisions Made

- **`_runner.py` module docstring rewrite (Task 1).** The original docstring enumerated `D-01: pytest runs as a child subprocess via [sys.executable, '-m', 'pytest']…D-02: default mode allocates an internal tempfile JUnit XML…`. Rewrote as plain prose describing the same contract (pytest-as-subprocess, tempfile JUnit, exit-code mapping, raw-mode passthrough, AsyncExitStack teardown). The contract survives without the D-NN anchors because the docstring is now organized by *what the runner does*, not by *which plan decided what*.
- **Surviving `docs/ERROR-STYLE.md` references (Task 2 + Task 3).** Three locations (`_runner.py:_emit_operator_error`, `fixtures.py:_pytest_exit_operator_tone`, `config.py` v2-validator) now cite `docs/ERROR-STYLE.md` directly. This replaces the prior `SAFE-03` / `SAFE-06` / `PERSONA-03` anchors while keeping the maintainer-value: a future maintainer reading the comment can still locate the canonical operator-tone style guide.
- **Comment shape preserved for locked constants (Task 1).** The skip-reason constants `_REASON_NOT_SELECTED` / `_REASON_EXPLICIT_DEFAULT` had a comment `# Phase 13 D-12 / SAFE-01: two distinct skip-reason strings…`. Rewrote as `# Locked skip-reason constants for opt-in tool selection. Module-level constants so they cannot drift silently. Tests pin both verbatim.` The "tests pin both verbatim" half is the load-bearing maintainer warning; the planning anchor was pure provenance.
- **Phase 21.1 RELOC-01 references replaced with the rule, not the anchor (Task 2).** `fixtures.py:_preflight` and `config.py:sdet` had `Phase 21.1 RELOC-01 (Rule 3 deviation, plan 21.1-01)` prefixes. Replaced with "Fetching the fixture only inside the live-MCP branch preserves the missing-config fail-loud behavior described in docs/ERROR-STYLE.md" — the rule survives, the anchor is gone.

## Deviations from Plan

None - plan executed exactly as written.

The plan's task ordering (densest file first, then the three mid-density files, then the six light-density files) held up: `_runner.py` consumed the bulk of the editing time, and the lighter files completed quickly because their comment patterns repeated (mostly drop-pure-provenance with the occasional rewrite for a load-bearing rule).

## Issues Encountered

None. One observation: the pre-existing Phase 23 test failures (12 failed + 1 error in `tests/framework`) are byte-identical before and after the scrub, confirming no new behavior regression. The plan acknowledged these as Phase 23 debt; they remain so.

## Verification

Final phase-wide grep gates (the plan's `<verification>` block):

```
$ for f in _runner.py _isolation.py fixtures.py config.py models.py schema_validator.py mcp_client.py judge_protocol.py ollama_judge.py rubrics.py; do
    n=$(grep -cE "(CLI|PERSONA|CODEGEN|SAFE|RUNNER|UX|ISOL|JUNIT|SURFACE|TEST|CLEAN|DOC|UI|SDET|STATE|PREFLIGHT|SCRUB|RELOC)-[0-9]+|\bD-[0-9]+\b" "src/mcp_test_framework/$f")
    p=$(grep -cE "\bPhase [0-9]+(\.[0-9]+)?\b" "src/mcp_test_framework/$f")
    echo "$f ID=$n Phase=$p"
  done
_runner.py ID=0 Phase=0
_isolation.py ID=0 Phase=0
fixtures.py ID=0 Phase=0
config.py ID=0 Phase=0
models.py ID=0 Phase=0
schema_validator.py ID=0 Phase=0
mcp_client.py ID=0 Phase=0
judge_protocol.py ID=0 Phase=0
ollama_judge.py ID=0 Phase=0
rubrics.py ID=0 Phase=0
```

Imports:

```
$ uv run python -c "from mcp_test_framework import _runner, _isolation, fixtures, config, models, schema_validator, mcp_client, judge_protocol, ollama_judge, rubrics; print('ok')"
ok
```

Acceptance test sweeps:

- Task 1: 119 passed (`tests/framework/unit/test_runner_*.py` — 9 files)
- Task 2: 70 passed (`tests/framework/unit/test_config*.py`, `test_error_style.py`, `test_homelab_config.py`, `test_session_loader_invariants.py`)
- Task 3: 47 passed (`tests/framework/unit/test_schema_validator.py`, `test_mcp_client.py`, `test_judge_errors.py`, `test_ollama_judge.py`, `test_rubrics.py`)

Full non-live `tests/framework` baseline: 562 passed, 12 failed + 1 error (all pre-existing Phase 23 debt — byte-identical to the pre-scrub state).

## Next Phase Readiness

- Plan 22-04 (regression-prevention test) can now write a pure grep gate against `src/mcp_test_framework/` because `cli.py` (Plan 22-01) and `sdet/` (Plan 22-02) finish in the same wave, and this plan covers the remaining 10 files.
- After the wave merges, the phase-wide grep `grep -crE '...regex...' src/mcp_test_framework/ --include="*.py"` should print zero for every file. Plan 22-04's test will lock that in.
- No blockers. Phase 23 debt is acknowledged and tracked separately on the roadmap.

## Self-Check: PASSED

- Created files: none (this plan only modifies).
- Modified files: all 10 confirmed present and edited (per `git status` after each task).
- Commits: `7d94433` ✓, `1985ac1` ✓, `06067e5` ✓ (verified via `git log --oneline -5`).

---
*Phase: 22-scrub-requirement-id-leaks-from-src*
*Plan: 03*
*Completed: 2026-05-14*
