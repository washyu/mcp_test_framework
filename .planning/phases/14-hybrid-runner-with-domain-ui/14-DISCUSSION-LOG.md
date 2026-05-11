# Phase 14: Hybrid runner with domain UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `14-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-05-10
**Phase:** 14-hybrid-runner-with-domain-ui
**Areas discussed:** Pytest invocation, Live progress, Rendering library, Pre-run digest scope, Failure detail, `_reporter.py` fate, XML parsing, `--raw` contract, `-q` plumbing, `--debug` shape

---

## Pytest invocation strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Subprocess (clean isolation) | Spawn `python -m pytest ...`; stdout/stderr fully captured; wrapper process stays clean; ~150ms extra startup. | ✓ |
| pytest.main() in-process | Call `pytest.main(argv)` with `redirect_stdout`; no extra process; couples to pytest globals; capture is trickier. | |
| pytest plugin (terminalreporter override) | Replace pytest's terminal reporter; no XML parsing; live progress free; higher coupling to pytest internals. | |

**User's choice:** Subprocess (clean isolation)
**Notes:** Recommended option; SEED-011 §"Open Design Questions" Q1 resolved in favor of subprocess cleanliness.

---

## Live progress vs batch render

| Option | Description | Selected |
|--------|-------------|----------|
| Batch render from JUnit XML (Recommended) | Run silent; parse tempfile at end; render UI in one shot; slow runs feel frozen. | ✓ |
| Live per-tool rows | Stream + translate; better UX at N=70; fragile parsing or plugin coupling. | |
| Minimal heartbeat | Static "Running…" line, then full table at end. | |

**User's choice:** Batch render from JUnit XML
**Notes:** Live progress deferred to v1.3 per SEED-011 §Tradeoffs.

---

## Rendering library

| Option | Description | Selected |
|--------|-------------|----------|
| stdlib + ANSI escapes (Recommended) | f-strings + ANSI guarded by `sys.stdout.isatty()`; zero new deps; table alignment via `str.ljust`. | ✓ |
| Add `rich` dependency | `rich.console.Console` + `rich.table.Table`; better tables, true-color, TTY detection; ~700kb dep. | |
| Plain text, no color | ASCII only; identical TTY/pipe output; loses PASS/FAIL/SKIP visual distinction. | |

**User's choice:** stdlib + ANSI escapes
**Notes:** SEED-011 Q3 closed; `rich` reconsiderable in Phase 16 or v1.3.

---

## Pre-run digest scope

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 14 ships minimal header; Phase 16 polishes (Recommended) | Ship header (server/discovered/running/skipping/judges/totals) here; defer `--explain`, N=70 tweaks, post-run aggregation polish to Phase 16. | ✓ |
| Phase 14 ships full pre-run digest (subsume UX-01) | Build complete digest now; Phase 16 only owns `--explain` + readability. Larger Phase 14 scope. | |
| Phase 14 ships rows + summary only | No header at all; Phase 16 owns entire digest. Contradicts Phase 14 SC-1's explicit header requirement. | |

**User's choice:** Phase 14 ships minimal header; Phase 16 polishes
**Notes:** Matches ROADMAP Phase 14 SC-1 read; SEED-008 polish + UX-02 `--explain` cleanly land in Phase 16.

---

## Failure detail surface

| Option | Description | Selected |
|--------|-------------|----------|
| Judge reasoning only (Recommended) | `JudgeResult.reasoning` for judge fails, `ValidationIssue.message` for schema fails; one-line under tool row; no traceback by default. | ✓ |
| Judge reasoning + short assertion excerpt | Reasoning PLUS first line of assertion message; more context; risks pytest framing leaking back in. | |
| Full longrepr block | Dump JUnit `<failure>` longrepr verbatim; most info but includes tracebacks — contradicts "no pytest framing leak" success criterion. | |

**User's choice:** Judge reasoning only
**Notes:** Tracebacks gated to `--debug` only.

---

## `_reporter.py` fate

| Option | Description | Selected |
|--------|-------------|----------|
| Obsolete + delete in Phase 14 (Recommended) | Post-run XML parsing replaces the plugin entirely; delete plugin + registration + targeted tests. | ✓ |
| Keep + adapt as `--raw` fallback | Under `--raw`, plugin's per-tool summary still emits; two code paths to maintain. | |
| Keep + always-on | Plugin emits as before; wrapper adds domain UI on top; double output. | |

**User's choice:** Obsolete + delete in Phase 14
**Notes:** Phase 09 D-03 / D-05 / CD-03 grouping invariants port into the new renderer before plugin deletion.

---

## JUnit XML parsing

| Option | Description | Selected |
|--------|-------------|----------|
| stdlib `xml.etree.ElementTree` (Recommended) | Zero new deps; pytest's JUnit dialect is shallow; ~30 lines; fixture round-trip test pins the dialect. | ✓ |
| `junitparser` library | Typed API; useful if we plan to merge multiple XML files later — not in scope for Phase 14. | |

**User's choice:** stdlib `xml.etree.ElementTree`
**Notes:** Revisit if xdist (SEED-002) requires multi-XML merge in v1.3.

---

## `--raw` contract

| Option | Description | Selected |
|--------|-------------|----------|
| Bypass wrapper entirely; preserve config pre-flight (Recommended) | `_load_config` still runs (SAFE-03 preserved); no tempfile, no XML parse, no domain UI; exit code = pytest's. | ✓ |
| Pure pass-through (skip config pre-flight too) | True "don't touch" mode; loses SAFE-03 safety net. | |
| Domain UI off, pre-flight + JUnit emit still happen | Hybrid for CI debugging; larger API surface. | |

**User's choice:** Bypass wrapper entirely; preserve config pre-flight
**Notes:** SAFE-03 destructive-defaults gate is non-negotiable; `--raw` is a maintainer escape hatch, not a safety bypass.

---

## `-q` plumbing

| Option | Description | Selected |
|--------|-------------|----------|
| Typer owns it; not forwarded to pytest (Recommended) | Framework-level flag; wrapper runs pytest at default verbosity internally (XML stays complete); renders only summary line. | ✓ |
| Forward to pytest; let pytest's quiet drive | Pass `-q` through; only affects `--raw`; confusing dual ownership. | |
| Both — Typer parses + forwards | Extra coupling for no benefit. | |

**User's choice:** Typer owns it; not forwarded to pytest
**Notes:** `-q` becomes framework-shaped (summary-line-only), decoupled from pytest's own `-q` semantics.

---

## `--debug` shape

| Option | Description | Selected |
|--------|-------------|----------|
| Domain UI + raw pytest stdout + tracebacks appended (Recommended) | Render UI normally; then `--- raw pytest output ---` section with pytest stdout + JUnit `<failure>` longrepr bodies. | ✓ |
| Replace domain UI with raw pytest output | Bypass UI entirely; loses RUNNER-04 "adds info, doesn't re-shape" guarantee. | |
| Domain UI + tracebacks inline per row | Tracebacks under each FAIL row; better locality but less clean visual layering. | |

**User's choice:** Domain UI + raw pytest stdout + tracebacks appended
**Notes:** RUNNER-04 invariant preserved — each rung adds information; none re-shapes the layer below.

---

## Claude's Discretion

- Plan ordering within Phase 14 (subprocess wrapper → parser → renderer → flags → plugin deletion).
- Module split: `_runner.py` vs `_renderer.py` vs single file.
- Header layout details (long server-command wrapping, "Running (2)" count format).
- Whether `--debug` also passes `-v` to pytest.
- JUnit XML fixture set for renderer unit tests (all-pass, one-fail-with-reasoning, all-skip, mixed).
- Whether to extract the `[<tool_name>]` parser into a shared helper.
- Whether `pytest_args` (post-`--` passthrough) stays in default-mode signature or is gated behind `--raw`.

## Deferred Ideas

- Live per-tool progress streaming → v1.3 (SEED-011 §Tradeoffs).
- `rich` rendering library upgrade → Phase 16 or v1.3 (reconsider if UX gain justifies dep).
- `junitparser` library → v1.3 if xdist (SEED-002) needs multi-XML merge.
- `--explain` flag plumbing → Phase 16 (UX-02).
- N=70 readability polish → Phase 16 (UX-04).
- `-v` per-judge breakdown verbosity mode → Phase 16 (verbosity ladder).
- Folder-split retarget (`tests/` → `tests/contract/`) → Phase 15.
- `--with-framework` opt-in flag → Phase 15 (SURFACE-02).
- `NO_COLOR` env-var support beyond `isatty()` guard → v1.3+ if requested.
- Streaming JUnit XML parsing during the run → v1.3 (requires plugin re-introduction).
