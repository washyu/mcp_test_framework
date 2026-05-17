# Phase 29: Live domain-UI reporter plugin - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-16
**Phase:** 29-live-domain-ui-reporter-plugin
**Areas discussed:** Renderer reuse, Output coexistence, CI/no-TTY detection + force syntax, CLI wrapper integration

---

## Renderer reuse strategy

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Build ParsedRun at session end, batch-render | Reporter accumulates TestReports in pytest_runtest_logreport; at pytest_sessionfinish builds ParsedRun via new `_build_parsed_run_from_reports()` (mirror of parse_junit_xml); calls existing render_domain_ui unchanged. One renderer, no live row emission. | ✓ |
| (b) Stream rows live + summary at end | Refactor `_render_per_tool_rows` into per-row helper; reporter emits rows inside `pytest_runtest_logreport`; summary at sessionfinish. Live operator feedback but parametrize interleaving problem. | |
| (c) Parallel live renderer | New `_live_renderer.py` from scratch with own event-driven row emission. Cleanest separation but two renderers to maintain; violates "refactor not rewrite" line. | |

**User's choice:** (a) Build ParsedRun at session end, batch-render.
**Notes:** Aligns with v1.4 roadmap framing "renderer is already input-agnostic; refactor not rewrite" and the research-suggested `_build_parsed_run_from_reports(TestReport[...])` alongside `parse_junit_xml(path)` pattern.

---

## Output coexistence with pytest-native

| Option | Description | Selected |
|--------|-------------|----------|
| Alongside (additive) | Don't touch pytest's stdout. pytest's dots/-v + native summary all still print; reporter adds domain header + per-tool rows + domain summary. pytest-sugar/pytest-html untouched. Visually busy. | ✓ |
| Replace (suppress pytest native) | Reporter hooks pytest_collection_modifyitems / pytest_report_header / pytest_terminal_summary to suppress pytest progress + summary, prints only domain UI. Cleaner but clobbers pytest-sugar/pytest-html. | |
| Alongside, but reorder | Don't suppress pytest, but emit header BEFORE collection and rows + summary AFTER pytest's summary. Compromise. | |

**User's choice:** Alongside (additive).
**Notes:** Matches ROADMAP SC3 "pytest-html / pytest-sugar / similar terminal-coexistence plugins not hijacked." Simplest, least invasive.

---

## CI / no-TTY detection signal

| Option | Description | Selected |
|--------|-------------|----------|
| `isatty()` only | Auto-OFF when `sys.stdout.isatty()` is False. Simple, covers nohup/piping/CI broadly. | ✓ |
| `isatty()` OR `CI=true` env | Adds standard CI env-var heuristic. Covers CI-with-allocated-TTY edge case. | |
| `isatty()` + `CI` + specific CI vars | GITHUB_ACTIONS / JENKINS_URL / etc. explicitly checked. Most thorough; diminishing returns. | |

**User's choice:** `isatty()` only.
**Notes:** Fewer surprise auto-OFFs; rare CI-with-TTY case is exactly when operators want the UI on. CI-env-var heuristic deferred — revisit only with operator-pain evidence.

---

## Override syntax (force ON in CI)

| Option | Description | Selected |
|--------|-------------|----------|
| `--mcp-domain-ui=force` (valued option) | One flag, three states: absent / `--mcp-domain-ui` / `--mcp-domain-ui=force`. | ✓ |
| `--mcp-domain-ui` + `--mcp-domain-ui-force` (two flags) | Two booleans. More verbose. | |
| `--mcp-domain-ui` + `MCPTF_DOMAIN_UI_FORCE=1` env | Single boolean + env-var force. CI workflows set env once; invisible at call site. | |

**User's choice:** `--mcp-domain-ui=force` (valued option, `choices=auto|force|off`).
**Notes:** Operator intent visible at the call site. The literal value `force` (not `always` / `on`) chosen to make "forcing against the no-TTY default" explicit.

---

## CLI wrapper (`mcp-contracts run`) integration

| Option | Description | Selected |
|--------|-------------|----------|
| CLI passes `--mcp-domain-ui=force`; drop JUnit-parse path | mcp-contracts run becomes thin pytest wrapper. Delete JUnit-XML→ParsedRun callsite in cli.py. One renderer, one input path. | ✓ |
| CLI keeps JUnit parsing; reporter serves pytest-direct only | mcp-contracts run unchanged. Reporter serves pytest direct invokers. Two input paths to ParsedRun. Lower risk; permanent duplicate code. | |
| CLI passes `--mcp-domain-ui=force` AND keeps JUnit parsing as fallback | Defensive double-path. Most resilient; bakes in both paths permanently. Overkill for v1.4. | |

**User's choice:** CLI passes `--mcp-domain-ui=force`; drop JUnit-parse path.
**Notes:** Cleanest end-state — single input adapter at the framework's UI boundary. Aligns with v1.4 "library is the source of truth" direction. `--junitxml=...` still passed to pytest so the XML file is still written for external CI consumers; framework no longer reads it back. Planner: audit `parse_junit_xml` callers before declaring the function deletable.

---

## Claude's Discretion

- Reporter module path: `src/mcp_test_framework/_reporter.py` (matches `_runner.py` / `_plugin.py` convention).
- Header emission hook: `pytest_collection_finish` preferred (matches existing pre-run digest timing); fall back to `pytest_sessionstart` if RenderContext is not yet constructible.
- xdist master-only mechanism: standard `config.workerinput` presence check; planner validates against pytest-xdist's documented `pytest_runtest_logreport` semantics during research.
- Config loading inside the reporter: reuse the `mcp_config_file` ini route Phase 27 locked, NOT a parallel config-load path.

## Deferred Ideas

- xdist per-worker domain-UI surfaces (only master emits aggregate UI in Phase 29; per-worker progress = future phase).
- CI-env-var heuristic auto-OFF (revisit in v1.5 only with operator-pain evidence).
- Per-tool live row streaming (rejected in D-01; revisit if multi-minute-run blind-wait pain emerges).
- JUnit XML parsing as defensive fallback (rejected in D-05 as overkill).
- `-p no:mcp_test_framework_reporter` documentation lands in Phase 30 (CLOSE), not here.
