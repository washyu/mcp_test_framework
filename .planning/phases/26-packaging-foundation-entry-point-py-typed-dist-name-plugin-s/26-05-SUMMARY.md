---
plan: 26-05
phase: 26-packaging-foundation-entry-point-py-typed-dist-name-plugin-s
status: complete
completed: 2026-05-16
tasks: 1/2 (Task 2 deferred to Phase 30 per user decision)
key-files:
  created: []
  modified:
    - README.md
    - CLAUDE.md
---

## What was built

**Task 1 (operator-doc sweep):** README.md and CLAUDE.md rewritten so all
operator-facing prose uses the new `mcp-contracts` console-script name.
Verbatim D-07 deprecation copy embedded in both files so a single
`grep "mcp-test-framework command is deprecated since v1.4"` enumerates
the three v1.5-cleanup sites:

- `src/mcp_test_framework/_deprecated_script.py`
- `README.md`
- `CLAUDE.md`

**Task 2 (TestPyPI dry-run): DEFERRED to Phase 30** (see Deviations).

## Doc-sweep grep audit

### Before (Task 1 start)

```
README.md: 17 legacy `mcp-test-framework` occurrences (all Class A — operator-facing prose)
CLAUDE.md:  3 legacy `mcp-test-framework` occurrences (all Class A)
```

### After (Task 1 commit `8a0bdab`)

```
README.md: 18 `mcp-contracts` occurrences + 1 verbatim D-07 deprecation paragraph
CLAUDE.md:  4 `mcp-contracts` occurrences + 1 verbatim D-07 deprecation paragraph

Verbatim-copy sites (grep "mcp-test-framework command is deprecated since v1.4"):
  README.md:41
  CLAUDE.md:37
  src/mcp_test_framework/_deprecated_script.py:22
```

Three sites, all character-identical to the warning literal in
`_deprecated_script.py:main`. Single-grep cleanup invariant satisfied.

## Deviations from plan

### Task 2 (TestPyPI publish) deferred to Phase 30 — user decision 2026-05-16

The operator couldn't log into TestPyPI during the checkpoint window.
After reviewing the deferral options, the user chose to skip the
TestPyPI dry-run entirely and roll the publish-pathway exercise into
Phase 30 (production PyPI publish, CLOSE-01..04).

**Rationale for the deferral being acceptable:**

1. **PACK-04 (wheel-shape invariants) is already locally enforced.**
   Plan 26-04's `tests/framework/test_wheel_shape.py` builds the wheel
   via `uv build --wheel` on every CI run and asserts all seven content
   invariants (three `py.typed` markers, `contracts/__init__.py`, no
   `tests/` leakage, pytest11 entry point declaration, both console
   scripts declared). The wheel-shape gate is the load-bearing check
   for PACK-04; the TestPyPI publish was a *pathway* exercise — useful
   but redundant with the local gate.

2. **PACK-01 / PACK-02 are exercisable without TestPyPI.** The
   pytest11 entry point and `py.typed` marker invariants can be
   verified against the locally-built wheel in a fresh venv without
   uploading to any index. (Plan 26-04's wheel-shape test asserts the
   `entry_points.txt` content directly from the zipfile.)

3. **Phase 30 already owns the production publish pathway.** The
   project roadmap defers the operator-facing PyPI publish + README
   rewrite leading with library mode to Phase 30 (CLOSE-01..04). Doing
   a TestPyPI dry-run now and then a production publish in Phase 30
   would have duplicated the credential-and-recipe workflow.

**What's traded off:** the TestPyPI dry-run would have given
end-to-end evidence that `pip install --index-url
https://test.pypi.org/simple/ mcp-contracts` works against the actual
index resolver, including the `--extra-index-url` fallback for
transitive deps. That pathway will be exercised for real in Phase 30
against production PyPI.

**Phase 26 SC1 verification status:** local wheel-shape gate (11
assertions, all passing) substitutes for the TestPyPI install-pathway
acceptance. SC1's intent — "PACK-04 wheel-content invariants are
enforced against drift" — is met by the gate that runs every CI cycle.
The publish-pathway evidence will land in Phase 30.

## What was NOT changed (per plan)

- `docs/` — the v1.5 cleanup phase sweeps `docs/` comprehensively; Phase
  26 D-08 limited the doc surface to README + CLAUDE + inline CLI
  docstrings (Plan 26-01 Task 2 updated the inline docstrings).
- Historical phase narratives — sentences describing pre-Phase-26
  behavior keep their legacy script-name references unchanged.
- `.planning/REQUIREMENTS.md` PACK-03 + `.planning/ROADMAP.md` Phase 26
  Goal/SC1 — these were moved to Plan 26-01 Task 3 during revision 1
  (plan-checker Issue #5). See `26-01-SUMMARY.md` for the amendment
  diffs.

## State of carry-forwards

NONE in Phase 26 — packaging foundation is hermetic with respect to
operator-config concerns. Phase 28 owns CFG-01/02.

## Self-check

- [x] Task 1 doc sweep committed (`8a0bdab`)
- [x] Verbatim D-07 string appears in exactly 3 files; single-grep cleanup invariant holds
- [x] All operator-facing `mcp-test-framework` occurrences in README + CLAUDE rewritten to `mcp-contracts`
- [x] Inline verification command (uv run python -c "...") exits 0
- [-] Task 2 TestPyPI publish — **deferred to Phase 30** per user decision (TestPyPI login blocked 2026-05-16)
- [x] PACK-04 SC1 satisfied by local wheel-shape gate as substitute (acceptable per deferral rationale above)
