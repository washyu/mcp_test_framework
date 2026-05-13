---
id: SEED-017
status: dormant
planted: 2026-05-12
planted_during: Phase 17 (schema-driven-codegen-surface) planning
trigger_when: Phase 16 reporter UX overhaul, OR any milestone touching operator-facing CLI safety / SAFE-* "fail loud" decisions / runner output contract
scope: Small
---

# SEED-017: Warn or fail when `--junit-xml=PATH` would overwrite an existing file

## Why This Matters

`_runner.run_pytest_subprocess` silently overwrites the operator's
`--junit-xml=PATH` destination if a file already exists at that path. The
relevant code in `src/mcp_test_framework/_runner.py:234-241` is:

```python
if junit_xml is not None and tmp.exists():
    try:
        shutil.copy(str(tmp), str(junit_xml))
    except OSError:
        pass
```

No `dest.exists()` check, no warning, no confirmation. A stale or hand-edited
file at the destination is clobbered without trace.

**Failure modes this exposes:**

1. **CI artifact loss** — operator points two runs at the same `--junit-xml`
   path; the second silently overwrites the first. If both were uploaded to a
   CI artifact store, only the second survives in local checkout — the local
   tree no longer matches what was archived. Surprising in incident reviews.
2. **Hand-edited XML clobber** — operator tweaks the XML between runs for a
   downstream tool (rare but real) and loses it.
3. **Disk-pointed-at-wrong-place** — operator typos the path (e.g., points
   at `~/Downloads/report.xml` they meant to keep) and overwrites unrelated
   content. Worst case if the path happens to land on a file they cared about.

This is the same shape as the SAFE-03 "missing config = fail loud" decision
from v1.2 — silent destructive behavior gets converted to loud safe behavior
by adding an existence check.

## When to Surface

**Trigger:** Phase 16 reporter UX overhaul, OR any milestone touching
operator-facing CLI safety / SAFE-* "fail loud" decisions / runner output
contract.

This seed should be presented during `/gsd-new-milestone` when the milestone
scope matches any of:
- Operator CLI safety / "fail loud" patterns (SAFE-* lineage)
- Reporter UX / runner output story (sister: SEED-008, SEED-013, SEED-016)
- Any milestone that revisits `_runner.run_pytest_subprocess` for related
  reasons — the fix is one-screen-of-code; bundle it with the surrounding work

## Scope Estimate

**Small** — under an hour. The fix is mechanical; the decision is policy.

### Proposed policy options (planner picks)

| Option | Behavior | Tradeoff |
|--------|----------|----------|
| A. Warn + overwrite (default) | Emit `⚠ Overwriting existing junit.xml at PATH` to stderr, then proceed | Lightest touch. Matches CI norms (latest run wins). Preserves backward compat. |
| B. Fail by default, `--junit-xml-overwrite` flag to permit | Refuse if dest exists; operator opts in with explicit flag | Strongest safety; one extra step in CI. Matches `git push` semantics. |
| C. Backup-then-overwrite | Rename existing to `PATH.bak` before copy | Preserves history; clutters disk; introduces a second silent behavior |
| D. Atomic timestamp suffix | If dest exists, write `PATH.{ISO timestamp}.xml` instead | Never overwrites; never warns; cleanest but changes the path the operator asked for |

**Recommendation:** Option A for v1.x (preserves backward compat, surfaces the
behavior on stderr where CI logs capture it). Option B for v2.0 (breaking-change
window, matches SAFE-03's hard-fail posture).

### Implementation sketch (Option A)

```python
if junit_xml is not None and tmp.exists():
    dest = Path(junit_xml)
    if dest.exists():
        typer.echo(
            f"⚠ Overwriting existing JUnit XML at {dest}",
            err=True,
        )
    try:
        shutil.copy(str(tmp), str(dest))
    except OSError:
        pass
```

Plus:
- A unit test in `tests/framework/unit/test_runner_junit_fanout.py` (or wherever
  the fan-out is already covered) that asserts the warning fires when the
  destination pre-exists and is silent when it doesn't.
- A note in the operator-facing docs (`--junit-xml` `--help` text) that
  re-running against the same path overwrites.

## Breadcrumbs

Related code (verified present 2026-05-12):
- `src/mcp_test_framework/_runner.py:234-241` — the silent copy. Add the
  existence check here.
- `src/mcp_test_framework/_runner.py:1-21` — module docstring already documents
  the fan-out contract; update it once policy is picked.
- `src/mcp_test_framework/cli.py:355-391` — `--junit-xml` Typer option. Add
  policy note to the help text.

Related decisions:
- **SAFE-03** (v1.2 config-discovery + safety) — "fail loud on missing config";
  same principle applied to a different surface. Cite this in the future plan's
  CONTEXT.md to anchor the design choice.
- Phase 09 OUTPUT-01 — `--junit-xml=PATH` contract origin. The contract
  guarantees a valid XML at PATH; it does NOT guarantee anything about pre-
  existing content. SEED-017 tightens that gap.
- Phase 14 D-16 — JUnit XML **parse** error → exit 2. Symmetric: write error
  (overwrite of important file) should be at least loud, ideally a soft fail.

Related seeds:
- SEED-008 (reporter UX overhaul — parent UX theme)
- SEED-013, SEED-016 (runner output story — closely related but about display,
  not file safety)

## Notes

Captured during Phase 17 planning on 2026-05-12. The user noticed the silent
clobber during a recent run. Phase 17 is codegen-focused and doesn't touch the
runner, so this gets parked as a seed rather than tacked onto Phase 17 scope.

The fix is genuinely small (≤ 10 lines + test), so if Phase 16 (reporter UX)
runs first, this should be bundled into one of its plans rather than its own
phase. If a v1.x.y hotfix cycle opens for any unrelated reason and `_runner.py`
is being touched, fold this in opportunistically.
