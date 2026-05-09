---
id: SEED-011
status: active
planted: 2026-05-08
planted_during: v1.1 manual UAT exploration (formalized at v1.2 milestone framing 2026-05-08)
trigger_when: v1.2 milestone framing (active for v1.2). Decide BEFORE SEED-010 folder split — runner contract drives the split.
scope: Medium
target_milestone: v1.2 (cohort with SEED-007/008/009/010)
---

# SEED-011: Hybrid runner with domain UI

## Why This Matters

Even with the folder split (SEED-010) and the pre-run digest (SEED-008), pytest framing still leaks into operator output: `=== test session starts ===`, `collected N items / M deselected`, `===== passed in Xs =====`, per-test `.` / `F` markers, framework-jargon tracebacks. An operator testing an MCP server doesn't care about pytest internals — they care about which tools passed, which failed the rubric, and why.

Memory: `Hybrid runner with domain UI (SEED-011) — pytest framing leaks into operator output even with folder split. Wrap pytest.main() to render domain UI from JUnit XML. Decide BEFORE SEED-010 folder split. 6th operator-vs-dev pattern` (2026-05-08).

## When to Surface

**Active for v1.2.** Decided BEFORE SEED-010 — the runner contract defines what "operator-facing" means, which then drives the folder split.

## Scope Estimate

**Medium.** The mechanism is well-understood (subprocess pytest with `--junit-xml` to a tempfile, parse JUnit XML, render domain UI), but the design space is non-trivial:
- What to show / hide
- How to surface failures (full traceback? rubric reasoning? both?)
- Quiet mode parity with `-q`
- Pass-through to raw pytest for power users (`mcp-test-framework run --raw` or `pytest tests/contract/` directly)
- Live progress (stream pytest output and translate, or run silent and render at end?)

## Components

### 1. Wrap `pytest.main()` (or subprocess pytest)

`mcp-test-framework run` no longer invokes pytest directly via `pytest.main([...])` returning the exit code. Instead it:

1. Runs pytest with `--junit-xml=<tempfile>` and pytest's own output suppressed (or piped to a hidden log file for `--debug`).
2. Parses the JUnit XML.
3. Renders domain UI: pre-run digest (SEED-008) + per-tool table + summary.
4. Returns the appropriate exit code (0 / 1 / 130 / 2).

### 2. Domain UI shape (initial sketch)

```
========================================
MCP Test Framework
========================================
MCP server:  uvx <your-mcp-command>
Discovered:  58 tools
Running:      2  (list_keyring_credentials, suggest_deployments)
Skipping:    56  (use --explain to list)
Judges:       clarity, disambiguation, parameters

Test plan: 20 contract cases

[1/2] list_keyring_credentials   ✓ PASS  (clarity 5/5)
[2/2] suggest_deployments        ✗ FAIL  (parameters 3/5: "params field has no description")

Result: 1 PASS / 1 FAIL  in 8.3s
========================================
```

### 3. Failure rendering

For judge-rubric failures, surface `JudgeResult.reasoning` directly. For schema failures, surface `ValidationIssue.message`. Stack traces only on `--debug`.

### 4. Pass-through escape hatch

`mcp-test-framework run --raw` (or `--pytest-pass-through`) bypasses the wrapper and runs pytest verbatim with all flags forwarded. Maintainers and CI debugging stay productive.

### 5. Quiet & verbose modes

- `-q` / `--quiet` — final summary line only ("1 PASS / 1 FAIL").
- (default) — domain UI as above.
- `--explain` (from SEED-008) — adds skipped-tool detail.
- `-v` / `--verbose` — adds per-judge breakdown per tool.
- `--debug` — adds raw pytest output + tracebacks.

### 6. JUnit XML stays available

`--junit-xml=PATH` flag (existing, from v1.1 OUTPUT-01) still emits to the operator-specified path. The wrapper uses a separate tempfile internally so `--junit-xml=PATH` semantics don't change.

## Sequencing Within v1.2

**FIRST among the runner / split / UX trio:** SEED-011 (this seed) → SEED-010 (folder split) → SEED-008 (pre-run digest is a section of the domain UI, so its design folds into this seed's UI design). All three may land in adjacent phases or as a single phase pair.

Memory rule: `Decide BEFORE SEED-010 folder split` — the runner's collection scope IS the split decision. If SEED-011 lands first, SEED-010 is a mechanical follow-on.

## Tradeoffs

- **Pro:** Operators see a clean MCP-domain interface; pytest becomes an implementation detail.
- **Pro:** SEED-008 reporter UX folds naturally — the "pre-run digest" is just one section of the domain UI, not a pytest plugin contract.
- **Con:** Two layers of output (pytest's, then ours). Errors in pytest itself (collection errors, fixture setup errors) need translation or pass-through.
- **Con:** Live progress is harder than batch render — likely defer streaming progress to v1.3 if it complicates v1.2.

## Open Design Questions

1. **Subprocess vs `pytest.main()`?** Subprocess is cleaner (full output capture), but slower (extra process). `pytest.main()` with output redirection works but couples our process to pytest's globals.
2. **Live progress?** Tail JUnit XML during the run (not really supported), or stream stdout and parse pytest's own line markers (fragile)? Likely defer.
3. **Color / TTY detection?** Use `rich` for the domain UI? Adds a dependency but the UX gain is significant. **Open.**
4. **JUnit-XML schema dependency.** Pytest's JUnit dialect is stable but not contractual. Pin a parser (`junitparser`?) and unit-test the round-trip.

## Breadcrumbs

- `src/mcp_test_framework/cli.py:118-172` — current `run` Typer command (calls `pytest.main`)
- `src/mcp_test_framework/_reporter.py` — current pytest plugin for per-tool summary; this seed likely OBSOLETES the plugin model in favor of post-run XML parsing
- `tests/test_reporter.py` — existing reporter tests (re-target at the new UI renderer)
- `pyproject.toml` — gains `junitparser` (optional) or stdlib `xml.etree.ElementTree`; possibly `rich`
- v1.1 OUTPUT-01..03 — `--junit-xml=PATH` flag stays; wrapper uses internal tempfile

## Related Memories

- `Hybrid runner with domain UI (SEED-011)` (memory entry)
- `Operator vs framework test surface (SEED-010)` (memory entry; downstream)
- `Pre-run tool summary (v1.2)` (memory entry; SEED-008 folds into the domain UI)
- `Output ergonomics at scale` (memory entry; the UI must work at N=70)
