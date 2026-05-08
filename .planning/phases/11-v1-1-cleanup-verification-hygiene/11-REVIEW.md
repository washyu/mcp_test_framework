---
phase: 11-v1-1-cleanup-verification-hygiene
reviewed: 2026-05-08T00:00:00Z
depth: quick
files_reviewed: 1
files_reviewed_list:
  - docs/EXTENDING.md
findings:
  critical: 0
  warning: 1
  info: 1
  total: 2
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-05-08
**Depth:** quick
**Files Reviewed:** 1
**Status:** issues_found

## Summary

Reviewed the new "## Environment passthrough allowlist" section (lines 152-234) added to `docs/EXTENDING.md` in Phase 11. Cross-checked every code-location claim and code-behavior claim against `src/mcp_test_framework/_isolation.py`. The prose is largely accurate and faithful to the source: the allowlist enumeration matches `_PASSTHROUGH_ALLOWLIST` + `_MCP_PREFIX`, the `_HOME_OVERRIDES` count of five matches the tuple, the `_KEYRING_OVERRIDES` value matches verbatim, and the cross-platform `USERNAME` vs `USER` rationale matches the inline note in `_isolation.py:55-62`. Internal anchor `#environment-passthrough-allowlist` (line 243) correctly resolves to the new heading at line 152.

One factual line-range citation is wrong, and one structural enumeration claim is loose enough to be misleading on a casual read.

## Warnings

### WR-01: Wrong line range citation for warning block in `_isolation.py`

**File:** `docs/EXTENDING.md:181`
**Issue:** The doc states:

> This is the warning currently living at
> `src/mcp_test_framework/_isolation.py:33-36`, copied verbatim so contributors
> see it before reading source:

Cross-check against `src/mcp_test_framework/_isolation.py`: the quoted warning text ("DO NOT widen `_PASSTHROUGH_ALLOWLIST`...") actually starts at **line 36** ("DO NOT widen ``_PASSTHROUGH_ALLOWLIST`` without updating ``EXTENDING.md``") and ends at **line 39** (closing `"""` is line 40). Line 33 is mid-paragraph about a cmdkey recon ("06-keyring-recon.md §2 as a one-time recon (D-03) — it is NOT a permanent test...") — entirely unrelated to the widening warning.

The correct range is `_isolation.py:36-39`. This matters because the doc explicitly tells contributors to look at those specific lines before reading source; sending them to lines 33-36 lands them in the middle of an unrelated paragraph and they will not see the closing sentence ("not 'the test wouldn't run otherwise' without a root cause") which is part of the verbatim quote.

**Fix:**
```diff
-This is the warning currently living at
-`src/mcp_test_framework/_isolation.py:33-36`, copied verbatim so contributors
-see it before reading source:
+This is the warning currently living at
+`src/mcp_test_framework/_isolation.py:36-39`, copied verbatim so contributors
+see it before reading source:
```

## Info

### IN-01: "exactly five entries" wording conflates `_PASSTHROUGH_ALLOWLIST` tuple with the `MCP_*` prefix branch

**File:** `docs/EXTENDING.md:162-170`
**Issue:** The doc says:

> Instead, `src/mcp_test_framework/_isolation.py` ships a module-level
> `_PASSTHROUGH_ALLOWLIST` of exactly five entries:

and then lists PATH, SYSTEMROOT, LANG, USERNAME, MCP_* (prefix match).

In the actual source, `_PASSTHROUGH_ALLOWLIST` is a tuple of **four** entries (PATH, SYSTEMROOT, LANG, USERNAME — `_isolation.py:50-63`). The MCP_* prefix is a *separate* mechanism — `_MCP_PREFIX = "MCP_"` on line 64, applied via a separate loop in `_build_isolated_env` (lines 100-102). The source's own widening warning likewise scopes itself to `_PASSTHROUGH_ALLOWLIST` only.

The doc's framing is user-facing-conceptually-correct (five passthrough categories), but a contributor who reads "module-level `_PASSTHROUGH_ALLOWLIST` of exactly five entries" and opens the file will count four entries in the tuple and may either (a) think they've found a bug, or (b) try to add MCP_* to the tuple to "fix" the doc, breaking the prefix-match semantics.

**Fix:** Either tighten the structural claim to match the code:
```diff
-Instead, `src/mcp_test_framework/_isolation.py` ships a module-level
-`_PASSTHROUGH_ALLOWLIST` of exactly five entries:
+Instead, `src/mcp_test_framework/_isolation.py` ships a module-level
+`_PASSTHROUGH_ALLOWLIST` tuple of four exact-match entries plus a
+separate `_MCP_PREFIX` prefix-match branch — five passthrough categories total:
```

Or keep the prose framing but add a parenthetical that MCP_* is a prefix-match handled alongside the tuple, not an entry within it.

---

_Reviewed: 2026-05-08_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: quick_
