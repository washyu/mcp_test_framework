---
id: SEED-011
status: dormant
planted: 2026-05-08
planted_during: v1.1 milestone complete + manual UAT post-v1.1.1-hotfix-merge
trigger_when: v1.2 milestone framing — surface during /gsd-new-milestone questioning step. Decide BEFORE committing SEED-010's folder split, since the runner choice shapes what the folder structure needs to support
scope: Medium
---

# SEED-011: Hybrid runner with domain-language UI (operator never sees pytest)

## Why This Matters

After running `mcp-test-framework run --config config.yaml -- -k mcp_tool_contract -v` and seeing the actual operator output on 2026-05-08, user surfaced the deeper question that SEED-010 only partially answers:

> "should we be doing our own runner or moving the judge tests to a different folder and point pytest to use that folder for the mcp runs?"

SEED-010 ("folder split") solves *what to run* but not *how to render*. Even with `tests/contract/` as the only thing the CLI sweeps, the operator still sees:

- `collected/deselected` framing (pytest's mental model)
- Fixture error stacktraces with `_pytest.outcomes.Exit`
- `addopts` / marker syntax leaking into output
- `[<param>]` parametrize suffixes embedded in test IDs
- Per-test-function granularity (operator thinks in tools, pytest thinks in test functions)

The output is for *test authors*, not for *MCP operators*. An operator's mental model is:

```
Testing 2 tools...

✓ list_keyring_credentials  8/10  (2 judges skipped per config)
✗ suggest_deployments       9/10  (disambiguation: scored 3, expected ≥4)
                                   "lacks specific details to distinguish from
                                    similar tools (e.g., calculate_latency)"

Tools passed: 1/2
Run time: 21s
```

Pytest cannot natively produce this shape. It can be coaxed close (the existing `_reporter.py` plugin already aggregates per-tool — see `tests/test_reporter.py`'s 30+ tests pinning that contract), but it always leaks pytest framing around the edges.

## When to Surface

**Trigger:** v1.2 milestone framing — surface during `/gsd-new-milestone` questioning step.

**Critical:** Decide this BEFORE committing SEED-010's folder split. The runner choice shapes what the folder structure needs to support. If we go hybrid (B below), the contract folder may not even need a `conftest.py` accessible to operators — pytest fixtures become an internal implementation detail.

This seed should be presented when the new milestone scope mentions any of:
- Reporter UX (compounds with SEED-008's pre-run digest)
- Custom runner / runner / CLI surface
- Operator UX / what does the operator see
- Pytest output / pytest framing

## Scope Estimate

**Medium** — One phase if hybrid (Option B); a milestone if full custom runner (Option C). Recommended path is B.

## Three Design Points on the Spectrum

### Option A — Folder split only (status quo + SEED-010)

Operator runs `pytest tests/contract/` via the CLI. Output is pytest's, with all its conventions and leakage. Already captured in SEED-010.

**Cost:** Small.
**Operator UX:** Improved (filtered noise) but still pytest-shaped.

### Option B — Hybrid runner (RECOMMENDED)

Custom thin CLI layer wraps `pytest.main()` underneath:

1. CLI invokes pytest with `--junit-xml` (already wired in v1.1) or `pytest-json-report`
2. Pytest runs the contract tests in `tests/contract/` (per SEED-010)
3. CLI captures pytest's exit code AND the structured output (XML/JSON)
4. CLI renders domain UI from the structured output: per-tool aggregation, judge-failure reasoning extraction, descriptive verdicts
5. Pytest's stdout is suppressed (`-q --no-header --no-summary`) or piped to a verbose-only sink
6. Operator sees ONLY the domain UI

The orchestration logic in pytest (parametrize over discovered tools, run fixtures, gate on `_preflight`, isolation, judge calls) is already correct and battle-tested through v1.0/v1.1. Rebuilding it would be expensive and risky.

The reporter plugin in `src/mcp_test_framework/_reporter.py` already extracts per-tool aggregation logic. Extract it further so it can run as a post-processor on JUnit XML, not only as an in-process pytest hook. Then the same logic powers both the in-process summary (for framework dev) and the operator-facing CLI render (for vibe-coded persona).

**Cost:** Medium. One phase to wire the runner, refactor reporter logic for post-processing, suppress pytest output, add domain-UI rendering. The XML emission is already wired (Phase 09 OUTPUT-01).
**Operator UX:** Optimal — pytest is invisible. Domain language throughout.
**Risk:** Adds one layer to maintain, but the layer is small, well-bounded, and isolates pytest's quirks behind a stable XML contract.

### Option C — Full custom runner (replace pytest in operator path)

Build orchestration from scratch: discover tools → instantiate rubrics → call judge → call MCP → aggregate → render. No pytest in the operator path. Pytest stays for `tests/framework/` (per SEED-010).

**Cost:** Large — at least a milestone of work. Re-implements parametrize, fixtures, isolation, preflight gating, async session management, judge call patterns, retry/timeout semantics. All of this is already debugged in pytest hooks; doing it again is risky.
**Operator UX:** Optimal — same as B.
**Risk:** Significantly more code to maintain. Likely diverges from pytest patterns over time, creating a fork the framework dev team has to maintain alongside pytest.

### Recommendation: B (Hybrid)

The framework's value prop is **MCP contract testing + Ollama judge orchestration** — not "build a pytest replacement." Keep pytest as the engine; replace its UI. This is exactly the role pytest was designed to support (it's a testing framework, not an end-user product), and the JUnit-XML emission already shipped in Phase 09 makes the post-processor a small lift.

## Open Design Questions

- **JUnit XML vs pytest-json-report:** XML is already emitted (Phase 09 OUTPUT-01) and is industry-standard. JSON via `pytest-json-report` is richer (carries fixture state, custom data) but adds a dep. **Lean: stick with JUnit XML for v1.2; revisit if domain UI needs richer data than XML provides.**
- **What does `mcp-test-framework run` show by default?** Domain UI. What does `--verbose` or `--raw-pytest` show? Pass-through pytest output for debugging. **Lean: domain UI default; pytest pass-through behind an explicit flag.**
- **Where does the per-tool reporter logic live after extraction?** Probably `src/mcp_test_framework/runner.py` (new module) or split between `_reporter.py` (in-process pytest plugin, for framework dev) and `runner.py` (XML post-processor, for operator path). The two should share a common aggregation core to avoid drift.
- **JUnit XML still emitted to a file?** Yes — operator runs `mcp-test-framework run --junit-xml=results.xml` for CI ingestion (Phase 09 contract preserved). The hybrid runner consumes its own XML output for the domain UI.

## Cumulative Pattern Reinforcement

This is the **sixth** operator-vs-developer pain point in the 2026-05-08 UAT session. Pattern is now overwhelming:

1. SEED-007 — black-box rule reframed as user-persona feature
2. `feedback_scaffold_completeness.md` — `config-init` produces incomplete scaffolds
3. SEED-009 — examples saturated with maintainer's homelab
4. SEED-008 — pytest's "N collected, M deselected" framing buries tool counts
5. SEED-010 — `tests/` directory layout assumes single dev/CI audience
6. **This seed** — pytest's output framing is for test authors, not MCP operators

v1.2's milestone theme is now obviously **operator-first design**. These seeds are not independent features; they're a coherent rebuild of the operator surface. Milestone framing should treat them as a unit.

## How to Apply During v1.2 Planning

- **Sequence: B before A.** Decide hybrid vs custom-runner BEFORE committing SEED-010's folder structure, since the runner choice shapes what the folder structure needs to support. If hybrid, `tests/contract/conftest.py` is internal-only; if custom runner, `tests/contract/` may not need pytest config at all (or even exist).
- Compounds heavily with SEED-008 (pre-run digest) — same domain-UI surface, just at startup instead of summary. Probably one phase delivering both.
- Compounds with SEED-007 (persona) — this seed is the technical implementation of the persona reframe at the runner layer.

## Breadcrumbs

- `src/mcp_test_framework/cli.py:run` (lines 118-172) — Typer command that calls `pytest.main()`. The hybrid runner wraps this.
- `src/mcp_test_framework/cli.py:_build_pytest_args` — argv builder; the hybrid runner adds `--junit-xml=<tempfile>` and `-q --no-header --no-summary` automatically.
- `src/mcp_test_framework/_reporter.py` — existing per-tool aggregation logic; extract aggregation core for reuse in XML post-processor.
- `tests/test_reporter.py` — 30+ tests pinning the aggregation contract (D-03, D-05). The hybrid runner's domain UI must preserve these contracts.
- Phase 09 (`.planning/phases/09-junit-xml-output-per-tool-reporting/`) — JUnit XML emission already wired; the runner consumes its own output.

## Related Memories / Seeds

- SEED-010 — folder split (sequence: decide this seed first; folder split adapts to chosen runner shape)
- SEED-008 — pre-run digest (same domain-UI surface, different lifecycle stage)
- SEED-007 — vibe-coded persona (the why)
- `feedback_uat_must_be_user_driven.md` — same operator-vs-developer pattern at the UAT-design level
