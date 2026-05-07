---
phase: 06
phase_name: per-session-host-state-isolation
reviewed: 2026-05-07
reviewer: gsd-code-reviewer (Claude Opus 4.7)
depth: standard
status: issues_found
files_reviewed: 4
findings:
  blocker: 0
  warning: 6
---

# Phase 06: Code Review Report

**Reviewed:** 2026-05-07
**Depth:** standard
**Files Reviewed:** 4
- `src/mcp_test_framework/_isolation.py` (NEW)
- `src/mcp_test_framework/fixtures.py` (MODIFIED)
- `src/mcp_test_framework/mcp_client.py` (MODIFIED)
- `tests/test_isolation.py` (NEW)

**Status:** issues_found
**Findings:** 0 BLOCKER / 6 WARNING

## Summary

Phase 06 delivers per-session host-state isolation via an env allowlist + HOME redirect, with a verification test for real-state immutability. The implementation faithfully honors locked decisions D-05/D-06/D-07/D-12/D-14/D-16/D-17, preserves the Phase 04.1 "no anyio cancel scope across the yield" invariant, and respects the black-box rule (no `homelab_mcp` imports). The keyring-recon SHIP/DEFER conditional was applied correctly (recon says SHIP, `_KEYRING_OVERRIDES` is wired).

No BLOCKERs found. The black-box guard, Phase 04.1 invariant, env construction site, allowlist contents, hash-based verification, in-process driver, and graceful skip on absent `~/.homelab_mcp/` all look correct.

What surfaced is a cluster of correctness-adjacent WARNINGs: a misleading return-type annotation on the new generator fixture, an unused `Config` fixture parameter and import in the test, two minor doc/comment inaccuracies, a redundant Path-recomputation, and a cross-platform identity gap (POSIX uses `USER`, allowlist names only `USERNAME`).

## Warnings

### WR-01: `_isolated_home` fixture has incorrect return type annotation

**File:** `src/mcp_test_framework/fixtures.py:178`
**Severity:** WARNING

The fixture is declared `async def _isolated_home() -> Path:` but its body uses `yield`, which makes it an async generator returning `AsyncGenerator[Path, None]`, not `Path`. The annotation is wrong and would mislead a type checker. Other generator fixtures in this same file (`mcp_client`, `_preflight`, `judge`) deliberately omit a return annotation for this reason — `_isolated_home` should match.

**Fix:** Drop the `-> Path` annotation, or use `AsyncGenerator[Path, None]` from `collections.abc`.

### WR-02: Unused `Config` fixture parameter and import in `test_real_state_unchanged`

**File:** `tests/test_isolation.py:42, 94`
**Severity:** WARNING

The test signature includes `config: Config,` and the module imports `from mcp_test_framework.config import Config`, but `config` is never referenced inside the test body. Preflight is still triggered through `mcp_client`'s `_preflight` dependency, so removing `config` does NOT remove the preflight gate.

**Fix:** Remove the parameter and import.

### WR-03: Misleading comment claims ISOL-03 covers the keyring axis with `cmdkey`

**File:** `src/mcp_test_framework/_isolation.py:30-31`
**Severity:** WARNING

The module docstring states: "ISOL-03 in Plan 06-03 covers the residual surface with a `cmdkey /list` snapshot." This is incorrect. Per D-08, ISOL-03 verifies sha256 of three registry files only — it does NOT snapshot `cmdkey`. The cmdkey before/after diff lives in §2 of the one-time recon doc (`06-keyring-recon.md`), per D-03 explicitly NOT a permanent test. A future maintainer reading this comment may assume continuous keyring coverage exists when it does not.

**Fix:** Correct the citation to clarify that the cmdkey-axis check was a one-time recon (D-03) and that ISOL-03 covers `~/.homelab_mcp/` filesystem state only.

### WR-04: POSIX user identity not allowlisted (`USER` missing alongside `USERNAME`)

**File:** `src/mcp_test_framework/_isolation.py:52`
**Severity:** WARNING

The allowlist passes `USERNAME` (Windows) but not `USER` (POSIX). On Linux/macOS, `USERNAME` is rarely set; `USER` is what `getpass.getuser()` consults. The spawned subprocess on POSIX therefore sees no user identity at all — contrary to the inline comment "informational; some servers log it for diagnostics". D-07 names the allowlist exactly as written, so this is spec-faithful — but the spec itself appears to have a Windows-bias gap that contradicts ISOL-06's cross-platform claim.

**Fix:** Either (a) widen the allowlist to include `USER` (requires a CONTEXT amendment / EXTENDING.md update) or (b) document explicitly that USER is intentionally stripped on POSIX.

### WR-05: Redundant `Path` recomputation in step-4 assertion message

**File:** `tests/test_isolation.py:145-150`
**Severity:** WARNING

Line 145 binds `tempdir_homelab = _isolated_home / ".homelab_mcp"` but line 146's assertion recomputes the same expression. The bound variable is then used only in the failure message. Functionally fine, but a future refactor that changes one expression but not the other would silently desync the assertion from its diagnostic.

**Fix:** Use the bound variable consistently in both the assertion and the message.

### WR-06: D-11 skip is too coarse — passes vacuously when `~/.homelab_mcp/` is empty

**File:** `tests/test_isolation.py:113-117`
**Severity:** WARNING

The skip predicate is `if not REAL_HOMELAB_DIR.exists()`, but the test asserts equality of sha256 dicts where missing files map to `None`. If `~/.homelab_mcp/` exists but is empty, all `before` and `after` hashes are `None`, so step 3's equality assertion passes vacuously. Step 4's tempdir-positive check still provides a positive signal, but ISOL-03's primary regression guard is effectively a no-op in this state.

**Fix:** Tighten the skip to also require at least one of the three files to exist, OR document explicitly that the tempdir-existence check is the ONLY load-bearing signal in the empty-dir case.

```python
if not REAL_HOMELAB_DIR.exists() or not any(p.exists() for p in REAL_FILES):
    pytest.skip(
        "No real ~/.homelab_mcp/ files to compare against — "
        "ISOL-03 vacuous on this host"
    )
```

---

_Reviewed: 2026-05-07_
_Reviewer: Claude Opus 4.7 (gsd-code-reviewer)_
_Depth: standard_
