---
phase: 06-per-session-host-state-isolation
plan: 01
subsystem: testing
tags: [isolation, recon, keyring, phase-06, findings]

# Dependency graph
requires:
  - phase: (none — first plan of Phase 06; recon foundation came from quick spike 260506-qxs)
    provides: PyPI README pattern + cmdkey diff procedure
provides:
  - "Recorded SHIP/DEFER decision on ISOL-04 (decision: SHIP)"
  - "PyPI README evidence (raw/pypi-readme.txt) — homelab-mcp v1.7.0 documents OS keyring as the credential store"
  - "Empirical cmdkey before/after diff (raw/keyring-{before,after,diff}.txt) — empty diff for v1.1 read-only surface"
  - "Minimal black-box driver (raw/drive-tools.py) — exercises both v1.1 tools without pytest preflight"
  - "5 open questions surfaced for Plans 06-02 / 06-03"
affects: [06-02, 06-03]

# Tech tracking
tech-stack:
  added: []   # recon-only; no code dependencies introduced
  patterns:
    - "FINDINGS-style recon doc mirroring 260506-qxs template (CONTEXT D-02)"
    - "Black-box PyPI-README evidence-gathering (PyPI JSON API; no source-read)"
    - "cmdkey before/after diff capture procedure (Windows credential mutation surface)"
    - "Minimal stdio driver for tool-surface invocation when pytest preflight gates fail"
    - "Grep-readable decision marker (regex `\\*\\*(SHIP|DEFER): ISOL-04\\*\\*` count == 1)"

key-files:
  created:
    - ".planning/phases/06-per-session-host-state-isolation/06-keyring-recon.md (recon doc with sections 1, 2, 3, 5)"
    - ".planning/phases/06-per-session-host-state-isolation/raw/pypi-readme.txt (PyPI README evidence-of-record)"
    - ".planning/phases/06-per-session-host-state-isolation/raw/keyring-before.txt"
    - ".planning/phases/06-per-session-host-state-isolation/raw/keyring-after.txt"
    - ".planning/phases/06-per-session-host-state-isolation/raw/keyring-diff.txt"
    - ".planning/phases/06-per-session-host-state-isolation/raw/drive-tools.py (minimal black-box driver)"
    - ".planning/phases/06-per-session-host-state-isolation/raw/driver.log (driver run with v1.7.0 startup banner)"
    - ".planning/phases/06-per-session-host-state-isolation/raw/fetch-pypi.ps1, cmdkey-before.ps1, cmdkey-after.ps1, run-tests.ps1, verify-task{1,2,3}.ps1"
  modified: []   # no source code modified

key-decisions:
  - "SHIP: ISOL-04 — homelab-mcp PyPI README v1.7.0 explicitly documents OS keyring as 'the sole credential store'; defense-in-depth justifies the one-line env-var injection even though current v1.1 read-only surface does not mutate the keyring"
  - "Empty cmdkey diff is non-load-bearing for the decision: it reflects the read-only nature of v1.1's two tools, not the ABSENCE of a keyring touchpoint (the §1 README evidence is the load-bearing signal)"
  - "Pytest preflight degraded to minimal driver: Ollama qwen3.6:latest not pulled in this dev environment; documented in §2 Caveats per Task 2 fallback clause"
  - "Five open questions tracked for downstream plans, including Q1 (cmdkey-vs-Python-keyring-library axis distinction — relevant to ISOL-03 test design)"

patterns-established:
  - "Recon doc: §1 PyPI README quotes, §2 empirical diff with raw evidence subdirectory, §3 ship-or-defer with `**SHIP|DEFER: <REQ>**` marker, §5 open questions; NO §4 effort estimate (recon, not implementation)"
  - "Decision marker grep convention: regex `\\*\\*(SHIP|DEFER): ISOL-04\\*\\*` matched exactly once; verified mechanically in raw/verify-task3.ps1"
  - "raw/ subdir owns recon evidence files distinct from the recon doc — same shape as 260506-qxs/raw/"

requirements-completed: [ISOL-01]

# Metrics
duration: 7min
completed: 2026-05-07
---

# Phase 06 Plan 01: ISOL-01 Keyring-Touch Recon Summary

**SHIP: ISOL-04 — homelab-mcp PyPI README v1.7.0 explicitly states "Credentials are stored in the OS keyring"; v1.7.0 startup banner names keyring as "the sole credential store"; Plan 06-02 must inject `PYTHON_KEYRING_BACKEND=keyring.backends.null.Null` into the spawned subprocess env.**

## Performance

- **Duration:** ~7 min (start 2026-05-07T15:24:17Z; end ~15:31)
- **Started:** 2026-05-07T15:24:17Z
- **Completed:** 2026-05-07
- **Tasks:** 3
- **Files modified:** 0 source files modified; 1 recon doc + 14 raw evidence files created

## Accomplishments

- **Recorded the gating ISOL-01 answer** with two independent evidence sources (PyPI README + cmdkey diff + driver-log startup banner). Phase 06 success criterion #3 satisfied.
- **Decision is grep-readable for Plan 06-02:** `grep '\*\*SHIP: ISOL-04\*\*' .planning/phases/06-.../06-keyring-recon.md` returns exactly one hit; the matching "Plan 06-02 consequence:" sentence directs Plan 06-02 to add `PYTHON_KEYRING_BACKEND=keyring.backends.null.Null` to `_build_isolated_env`.
- **Bonus evidence captured during recon:**
  - homelab-mcp v1.7.0 emits a startup banner explicitly stating *"v1.6: keyring is now the sole credential store"* (raw/driver.log) — author-side confirmation independent of the README.
  - homelab-mcp exposes 58 MCP tools (raw/driver.log) including credential-mutation candidates (`register_server`, `decommission_device`, `purge_devices`) — useful surface inventory for Plan 06-03's ISOL-03 test design.
- **Black-box rule preserved end-to-end:** zero homelab-mcp source files read. PyPI JSON API + the framework's existing `McpTestClient` (which already treats homelab-mcp as a subprocess) were the only code touchpoints.

## Plan 06-02 Consequence (verbatim from §3)

> Plan 06-02 MUST add `PYTHON_KEYRING_BACKEND=keyring.backends.null.Null` to the `_build_isolated_env` return dict.

Recommended placement (per PATTERNS.md `_isolation.py` shape) — a fourth module-level constant alongside `_PASSTHROUGH_ALLOWLIST`, `_MCP_PREFIX`, and `_HOME_OVERRIDES`:

```python
_KEYRING_BACKEND_OVERRIDE: dict[str, str] = {
    "PYTHON_KEYRING_BACKEND": "keyring.backends.null.Null",
}
```

## Caveats Affecting ISOL-03 Test Design (Plan 06-03)

These are flagged from this recon's §2 / §5 for Plan 06-03's awareness:

1. **Q1: cmdkey-vs-Python-keyring-library distinction.** `PYTHON_KEYRING_BACKEND=null` only short-circuits the Python `keyring` library's backend chain. If homelab-mcp ever bypasses `keyring` and calls Win32 `CredWrite` / libsecret directly via `ctypes`, the env var has no effect. The §1 README evidence ("When the OS keyring is unavailable (headless servers), credentials fall back to environment variables") strongly implies the standard `keyring` library is the path — that fallback semantics is exactly what the `keyring` library provides — but ISOL-03 should NOT rely on the env var alone as proof of isolation. **Implication for Plan 06-03:** include a `cmdkey /list` snapshot in the ISOL-03 test scaffolding (or a follow-up smoke test) that asserts no new `Target:` lines appear post-run. Sha256 of registry JSON files alone is insufficient to catch a direct-Win32 keyring write.

2. **Q3: Stale `.db` artifacts under `~/.homelab_mcp/`.** The v1.7.0 startup log says *"Dropped legacy ssh_credentials table"* and *"Dropped legacy drift_baselines table"* — implying earlier homelab-mcp versions stored data in a SQLite DB inside `~/.homelab_mcp/`. ISOL-03's hash list (per CONTEXT D-08: `credential_registry.json`, `known_hosts`, `migration_state.json`) does NOT cover any `*.db` file. **Implication for Plan 06-03:** check `dir %USERPROFILE%\.homelab_mcp\` for `*.db` artifacts; if present, add to the hash-equality list under an `if exists` guard (additive, doesn't break the v1.1 surface).

3. **Q4: 58-tool surface inventory.** `register_server`, `decommission_device`, `purge_devices`, `update_device_config` are credential/state mutation candidates. v1.1's parameterized test surface (Phase 07) will eventually exercise more of these. ISOL-04's null-keyring backend covers the WHOLE surface defensively — but the ISOL-03 test only directly exercises the 2 v1.1 tools. **Implication for Plan 06-03:** scope decision — keep ISOL-03 test surface narrow (the 2 v1.1 tools per CONTEXT D-08) and rely on ISOL-04's universal env-var coverage for the rest, OR widen ISOL-03 to fan out across all 58 tools. PATTERNS.md's CONTEXT D-08 step 2 already specifies the narrow scope; recommend keeping it that way unless Phase 07 work reveals a tool that mutates credentials silently.

4. **Q5: homelab-mcp runs destructive schema migrations on subprocess start.** Each driver invocation triggered the "Dropped legacy" banners. ISOL-02's HOME redirect should neutralize this (the redirected tempdir won't have a legacy table to drop), but Plan 06-03 should verify no "Dropped legacy ..." messages appear in subsequent isolated runs as a side-check.

## Task Commits

1. **Task 1: Capture PyPI README evidence (no source-read)** — `0c788e5` (docs)
2. **Task 2: Run cmdkey before/after diff and write §2** — `6a52d3d` (docs)
3. **Task 3: Write §3 ship-or-defer decision and §5 open questions** — `d08b969` (docs)

**Plan metadata:** _(pending — final commit will include this SUMMARY.md + STATE.md + ROADMAP.md + REQUIREMENTS.md)_

## Files Created

- `.planning/phases/06-per-session-host-state-isolation/06-keyring-recon.md` — FINDINGS-shaped recon doc with §§1–3 + 5; SHIP marker for Plan 06-02 grep
- `.planning/phases/06-per-session-host-state-isolation/raw/pypi-readme.txt` — full homelab-mcp v1.7.0 README (PyPI evidence-of-record)
- `.planning/phases/06-per-session-host-state-isolation/raw/keyring-before.txt`, `keyring-after.txt`, `keyring-diff.txt` — cmdkey diff evidence (empty diff)
- `.planning/phases/06-per-session-host-state-isolation/raw/drive-tools.py` — minimal black-box driver (preflight-bypass) that calls both v1.1 tools
- `.planning/phases/06-per-session-host-state-isolation/raw/driver.log` — driver output: 58-tool listing + v1.7.0 startup banner + tool-call results
- `.planning/phases/06-per-session-host-state-isolation/raw/fetch-pypi.ps1`, `cmdkey-before.ps1`, `cmdkey-after.ps1`, `run-tests.ps1` — capture scripts (reproducible)
- `.planning/phases/06-per-session-host-state-isolation/raw/verify-task1.ps1`, `verify-task2.ps1`, `verify-task3.ps1` — automated acceptance verifications
- `.planning/phases/06-per-session-host-state-isolation/raw/test-pass1.log`, `test-pass2.log` — pytest preflight-failure logs (recorded for completeness)

## Decisions Made

- **SHIP: ISOL-04** — see §3 of recon doc. §1 produced unambiguous positive evidence; §2 cmdkey diff was empty but only reflects the v1.1 read-only surface (not the absence of a keyring touchpoint). Defense-in-depth + zero-cost env-var injection makes shipping the right call.
- **Empty cmdkey diff is non-decisive** — distinguished read-traffic invisibility from absence-of-mutation in the §2 Caveats subsection. Documented for Plan 06-03 test design.
- **Pytest preflight fallback executed** — Ollama `qwen3.6:latest` not pulled in this dev environment; per Task 2's documented fallback clause, used a minimal driver instead. Recorded as a §2 Caveat with confidence calibration (HIGH for v1.1 read-side surface).

## Deviations from Plan

None — plan executed exactly as written. The Task 2 fallback clause ("If preflight fails ... use a minimal driver instead ... document whichever path was taken") was anticipated by the planner and exercised as designed; this is not a deviation.

## Issues Encountered

- **Pytest preflight blocked** by missing Ollama model `qwen3.6:latest` (not pulled in this worktree's environment; `/api/tags` returned `[]`). Resolved by using the planner's documented minimal-driver fallback. Documented in §2 Caveats with explicit confidence calibration. The Ollama-judge tests would not have called any additional MCP tools beyond what the minimal driver did, so the empirical evidence quality is unaffected.
- **PowerShell-via-Bash quoting friction** — `$` characters in inline `powershell -NoProfile -Command "..."` invocations were stripped by Bash before reaching PowerShell. Resolved by writing scripts to `.ps1` files and invoking them via `powershell -File`. Side benefit: the scripts are now reproducible artifacts under `raw/`.

## User Setup Required

None — recon-only plan; no external service configuration required.

## Next Phase Readiness

- **Plan 06-02 unblocked:** can grep `\*\*SHIP: ISOL-04\*\*` in `06-keyring-recon.md` and proceed to wire `PYTHON_KEYRING_BACKEND=keyring.backends.null.Null` into `_build_isolated_env`. The exact constant shape is recommended in §3 of the recon doc and reproduced in this Summary's "Plan 06-02 Consequence" section.
- **Plan 06-03 has design input:** four downstream test-design questions (Q1, Q3, Q4, Q5) flagged in this Summary's "Caveats Affecting ISOL-03 Test Design" section. Q1 (cmdkey-vs-keyring-library distinction) is the highest-value follow-up.

## Self-Check: PASSED

All 8 claimed files exist on disk; all 3 task commits found in `git log --oneline --all`:
- Task commits: `0c788e5` (Task 1), `6a52d3d` (Task 2), `d08b969` (Task 3)
- Files: 06-keyring-recon.md, 06-01-SUMMARY.md, raw/pypi-readme.txt, raw/keyring-{before,after,diff}.txt, raw/drive-tools.py, raw/driver.log

---
*Phase: 06-per-session-host-state-isolation*
*Completed: 2026-05-07*
