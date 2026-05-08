---
phase: 06
fixed_at: 2026-05-07
review_path: .planning/phases/06-per-session-host-state-isolation/06-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 06: Code Review Fix Report

**Fixed at:** 2026-05-07
**Source review:** `.planning/phases/06-per-session-host-state-isolation/06-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (all WARNING; no BLOCKERs)
- Fixed: 6
- Skipped: 0

All six WARNING-level findings from the standard-depth code review were
applied. Black-box rule preserved (no `homelab_mcp` imports anywhere in
`src/`). Phase 04.1 invariant ("no anyio cancel scope across the yield")
marker still present in `fixtures.py`. D-06 honored (no new public Config
fields). `uv run pytest tests/unit -q` passes (56/56). `uv run ruff check`
on the touched files (`_isolation.py`, `fixtures.py`, `test_isolation.py`)
passes; the one ruff finding in `src/mcp_test_framework/rubrics.py` is
pre-existing from Phase 04 (commit `4bab74d`) and unrelated to this fix
session.

## Fixed Issues

### WR-01: `_isolated_home` fixture has incorrect return type annotation

**Files modified:** `src/mcp_test_framework/fixtures.py`
**Commit:** `14089ea`
**Applied fix:** Dropped the `-> Path` return annotation on the
`_isolated_home` async-generator fixture so it matches the convention of
sibling generator fixtures in the same file (`mcp_client`, `_preflight`,
`judge`), which all omit the annotation. The body uses `yield`, so a
non-generator `Path` annotation was incorrect.

### WR-02: Unused `Config` fixture parameter and import in `test_real_state_unchanged`

**Files modified:** `tests/test_isolation.py`
**Commit:** `6ce01e9`
**Applied fix:** Removed `from mcp_test_framework.config import Config`
and the `config: Config` parameter from the test's signature. Preflight
is still triggered transitively via `mcp_client`'s `_preflight`
dependency, so the gate remains intact.

### WR-03: Misleading comment claims ISOL-03 covers the keyring axis with `cmdkey`

**Files modified:** `src/mcp_test_framework/_isolation.py`
**Commit:** `faaf011`
**Applied fix:** Rewrote the second half of the ISOL-04 paragraph in the
module docstring to make clear that ISOL-03 covers ONLY the
`~/.homelab_mcp/` filesystem state (sha256 of three registry files per
D-08), and that the cmdkey before/after diff lives in
`06-keyring-recon.md §2` as a one-time recon (D-03), NOT a permanent
test. Added an explicit statement that there is no continuous
keyring-axis regression guard in the suite.

### WR-04: POSIX user identity not allowlisted (`USER` missing alongside `USERNAME`)

**Files modified:** `src/mcp_test_framework/_isolation.py`
**Commit:** `9caa462`
**Applied fix:** Took the safe option per the orchestrator decision —
added an inline NOTE near the `USERNAME` allowlist entry documenting
that POSIX `USER` is intentionally NOT in the allowlist per D-07 (the
locked allowlist names exactly `USERNAME`). Widening the allowlist
would require a CONTEXT.md amendment / EXTENDING.md update and is out
of scope for a code-review fix. Did NOT widen the allowlist.

### WR-05: Redundant `Path` recomputation in step-4 assertion message

**Files modified:** `tests/test_isolation.py`
**Commit:** `c8cc188`
**Applied fix:** Replaced the recomputed
`(_isolated_home / ".homelab_mcp").exists()` in the assertion with the
already-bound `tempdir_homelab.exists()`. Both the assertion and the
failure message now use the same bound variable, so a future refactor
cannot silently desync them.

### WR-06: D-11 skip is too coarse — passes vacuously when `~/.homelab_mcp/` is empty

**Files modified:** `tests/test_isolation.py`
**Commit:** `7202924`
**Applied fix:** Tightened the D-11 skip predicate from
`if not REAL_HOMELAB_DIR.exists()` to
`if not REAL_HOMELAB_DIR.exists() or not any(p.exists() for p in REAL_FILES)`
so a host where the directory exists but contains none of the three
named registry files also skips, instead of passing step 3's equality
assertion vacuously (all `before`/`after` hashes `None`). Updated the
skip message to match (`files` instead of directory).

---

_Fixed: 2026-05-07_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
