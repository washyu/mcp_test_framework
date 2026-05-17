# Phase 29: Live domain-UI reporter plugin - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a second pytest plugin (separate from the contract-tests plugin) that emits the existing MCP domain UI (header / per-tool rows / summary) driven by live `pytest_runtest_logreport` events. Opt-in via `--mcp-domain-ui`, default OFF, auto-OFF in no-TTY environments unless `--mcp-domain-ui=force`. Reporter ships under a separate `[project.entry-points.pytest11]` key (`mcp_test_framework_reporter`) so operators can `-p no:mcp_test_framework_reporter` while keeping contract fixtures.

In-scope: new reporter plugin module + its entry-point declaration + CLI rewire to drive the live path instead of JUnit-parse. Out-of-scope: changing the rendered UI itself, xdist load-balancing strategy, ANY new domain-UI features.

</domain>

<decisions>
## Implementation Decisions

### Renderer reuse
- **D-01:** **Build `ParsedRun` at session end, batch-render.** Reporter accumulates `TestReport` objects in `pytest_runtest_logreport`, then at `pytest_sessionfinish` builds a `ParsedRun` via a new `_build_parsed_run_from_reports()` helper (mirror of `_runner.py:491` `parse_junit_xml`) and calls the existing `render_domain_ui(parsed, ctx)` unchanged. Single renderer, no per-tool live emission. Per-tool rows print at session end exactly like today — no row-streaming, no parametrize interleaving problem.
- **D-01a:** `_build_parsed_run_from_reports` lives alongside `parse_junit_xml` in `_runner.py` (NOT inside the reporter plugin) so both input adapters sit next to the renderer they feed.

### Output coexistence with pytest-native
- **D-02:** **Alongside (additive).** Reporter does NOT suppress pytest's native dots/-v progress, native summary, native tracebacks, or any other pytest plugin's output. Reporter emits the domain header (pre-run) + per-tool rows + domain summary at session end. Operator sees BOTH outputs. Visually busy but: `pytest-sugar`, `pytest-html`, `pytest-xdist` all untouched (matches ROADMAP SC3 "not hijacked"); failure tracebacks remain pytest's; reporter additions are clearly bracketed.

### CI / no-TTY detection
- **D-03:** **`sys.stdout.isatty()` only.** Auto-OFF when `sys.stdout.isatty()` is `False`. NO checks for `CI`, `GITHUB_ACTIONS`, `JENKINS_URL`, or any other CI-env-var heuristics. Rationale: CI environments almost universally pipe stdout (no TTY); the rare CI-with-TTY case is exactly when operators want the UI on. Simpler to document, fewer surprise auto-OFFs.

### Override syntax
- **D-04:** **`--mcp-domain-ui=force` (valued option, choices=`auto|force|off`).** Single flag, three states:
  - flag absent → OFF entirely (ROADMAP SC2)
  - `--mcp-domain-ui` (alone, no value) → defaults to `auto` → ON when `isatty()=True`, OFF when `False` (ROADMAP SC3 first half)
  - `--mcp-domain-ui=force` → ON regardless of TTY state (ROADMAP SC3 second half)
  - `--mcp-domain-ui=off` → OFF (covers the rare "registered via auto-mechanism but I want it suppressed this run" case)
- Pytest `addoption` declares with `action='store'`, `nargs='?'`, `const='auto'`, `default='off'`, `choices=['auto','force','off']`.

### CLI wrapper integration
- **D-05:** **`mcp-contracts run` passes `--mcp-domain-ui=force`; JUnit-parse path is deleted.** The CLI becomes a thin pytest subprocess wrapper:
  - Pytest invocation gains `--mcp-domain-ui=force` (operators invoking `mcp-contracts run` always want the domain UI, even in non-TTY CI).
  - The current JUnit-XML→`ParsedRun`→`render_domain_ui` path inside `cli.py` (around `cli.py:947-956`) is removed.
  - `--junitxml=...` is still passed to pytest so the XML file is still written for external CI consumers, but the framework no longer reads it back.
- **D-05a:** **Single-renderer, single-input-path end-state.** Only one input adapter to `ParsedRun` survives at the framework's UI boundary: `_build_parsed_run_from_reports`. The legacy `parse_junit_xml` reader callsite is removed from `cli.py`; the function itself MAY remain in `_runner.py` if other callers exist, but it is no longer wired into the operator path. Planner: audit `parse_junit_xml` callers before deletion.
- **D-05b:** **xdist master-only emission** lands in the reporter plugin via `pytest-xdist`'s standard worker_id detection (`config.workerinput` presence → worker; absence → master). Per-tool row aggregation happens on master only; workers ship test results back through xdist's normal channel; reporter consumes the master-side reassembled events. Planner: verify this matches xdist's documented `pytest_runtest_logreport` semantics under `-n auto`.

### Claude's Discretion
- Exact reporter module path: `src/mcp_test_framework/_reporter.py` (matches existing `_runner.py` / `_plugin.py` underscore-prefix convention; the stale `_reporter.pyc` artifact in `__pycache__/` is from a removed file and irrelevant).
- Entry-point key name **locked by ROADMAP**: `[project.entry-points.pytest11] mcp_test_framework_reporter = "mcp_test_framework._reporter"`.
- Header emission timing: pre-run via `pytest_collection_finish` (after collection, before any test runs) — matches the existing `_render_pre_run_digest` pre-run timing in `_runner.py:841`. Planner double-checks that the reporter has access to `RenderContext` (discovered tools, judges, server_cmd) at that hook; if not, defer header to `pytest_sessionstart` or accept it appearing after the first test result.
- `RenderContext` construction inside the reporter: read config via the same `mcp_config_file` ini route the contract plugin uses (Phase 27 D-locked), so the reporter sees the same `Config` object pytest does.
- No new operator-facing CLI flags beyond `--mcp-domain-ui` and its three values.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap / requirements
- `.planning/ROADMAP.md` §"Phase 29: Live domain-UI reporter plugin" (lines 154-163) — Goal, SC1-SC4, REPORTER-01/02 mapping.
- `.planning/REQUIREMENTS.md` lines 52-53 — REPORTER-01 (live event-driven domain UI, default OFF, CI auto-OFF, `--mcp-domain-ui=force` override) and REPORTER-02 (xdist master-only, separate pytest11 entry-point key).
- `.planning/PROJECT.md` — operator-vs-test_code persona framing, framework-primitives principle (no SUT-aware logic in plugins).

### Prior phase context (locks Phase 29 inherits)
- `.planning/phases/27-register-api-contracts-sub-package-test-extraction-lib/27-CONTEXT.md` lines 189, 258-259 — `pytest_addoption` reserved for Phase 29's `--mcp-*` group; reporter plugin separation already foreshadowed; `mcp_config_file` ini route is the single config-load mechanism.
- `.planning/phases/28-codegen-output-path-codegen/28-CONTEXT.md` — `mcp_config_file` pyproject-ini precedence and `_load_config` tuple-return refactor (cli.py:333-397, cli.py:463-468).

### Existing renderer & current JUnit-parse path (the code the reporter has to coexist with / replace at the CLI boundary)
- `src/mcp_test_framework/_runner.py:469` `ParsedRun` — frozen dataclass; the renderer's input contract.
- `src/mcp_test_framework/_runner.py:491` `parse_junit_xml(Path) -> ParsedRun` — the existing JUnit adapter; `_build_parsed_run_from_reports` mirrors its output shape exactly (same `ParsedRun` fields populated equivalently).
- `src/mcp_test_framework/_runner.py:655` `RenderContext` — non-XML metadata (discovered_tools, tools_config, server_cmd, judges). The reporter constructs this from the same `Config` object the contract plugin loads.
- `src/mcp_test_framework/_runner.py:841` `_render_pre_run_digest` — current pre-run header emission location.
- `src/mcp_test_framework/_runner.py:1041` `_render_per_tool_rows` and `_runner.py:1140` `_render_summary_line` — the post-run rendering primitives consumed by `render_domain_ui` at line 1171.
- `src/mcp_test_framework/_runner.py:1171` `render_domain_ui(parsed, ctx, file=None)` — the renderer the reporter calls verbatim at `pytest_sessionfinish`.
- `src/mcp_test_framework/cli.py:947-956` — the CLI callsite that currently parses JUnit XML and calls `render_domain_ui`; D-05 deletes this branch.
- `src/mcp_test_framework/_plugin.py` — existing contract pytest11 plugin; the reporter is a sibling module, NOT a body change here. `pytest_addoption` lives here today as a no-op stub (per Phase 27 D-13); D-04 fills it in the reporter module under the new entry-point.

### Packaging
- `pyproject.toml` lines 27-32 — current pytest11 entry-point block. Phase 29 adds a second key (`mcp_test_framework_reporter`); does NOT touch the existing `mcp_test_framework` key.

### Spike findings
- None — no project-local spike skills detected for Phase 29's surface. Roadmap notes a Phase 29 spike for "verify `pytest_runtest_logreport` event ordering under pytest-xdist" — research is expected to validate this, not a separate spike phase.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ParsedRun` + `RenderContext` + `render_domain_ui` in `_runner.py` — frozen renderer surface; the reporter is purely a new INPUT adapter, not a renderer change. D-01 mandates reuse, not parallel implementation.
- `_runner.py:491` `parse_junit_xml` — model implementation for `_build_parsed_run_from_reports`. Same fields populated (per-tool dict, total_time, pass/fail/skip counts, error rows).
- Existing pre-run digest helper `_render_pre_run_digest` (`_runner.py:841`) — reporter can reuse it at `pytest_collection_finish` if `RenderContext` is available at that hook.

### Established Patterns
- **Two-plugin separation under pytest11** (Phase 26 / Phase 27 lineage) — `_plugin.py` is the contract plugin; `_reporter.py` is the new reporter plugin; both register under separate entry-point keys so `-p no:` works independently.
- **Renderer is input-agnostic** (locked by v1.4 roadmap framing line 119) — refactor not rewrite. D-01 + D-05 together honor this: the renderer body is untouched; only the input adapters change.
- **Operator CLI is a thin pytest wrapper** (Phase 27 + 28 direction) — `mcp-contracts run` increasingly delegates to pytest behavior. D-05 continues this — CLI passes flags, doesn't post-process output.
- **Config loading via `mcp_config_file` ini route** (Phase 27 D-lock) — both plugins read the same `Config`; reporter does NOT introduce a parallel config-load path.

### Integration Points
- `pyproject.toml` `[project.entry-points.pytest11]` block — second key (`mcp_test_framework_reporter`) added pointing at `mcp_test_framework._reporter`. Existing `mcp_test_framework = "..._plugin"` key untouched.
- `src/mcp_test_framework/cli.py:947-956` (and `cli.py:_build_pytest_args` around `cli.py:81`) — pytest argv construction; D-05 adds `--mcp-domain-ui=force` and removes the JUnit-read postprocessing.
- `src/mcp_test_framework/_runner.py` — gains one new function (`_build_parsed_run_from_reports`); existing functions untouched.
- New file: `src/mcp_test_framework/_reporter.py` — the reporter plugin (pytest hooks: `pytest_addoption`, `pytest_configure`, `pytest_collection_finish`, `pytest_runtest_logreport`, `pytest_sessionfinish`).

</code_context>

<specifics>
## Specific Ideas

- Match the existing `--mcp-*` flag style for the option (no new flag prefix invented).
- Reporter output is **additive** to pytest's — operator running `pytest -v --mcp-domain-ui` sees BOTH pytest's verbose output AND the domain UI bracketed by our header/summary.
- The reporter's pre-run header should be the same `_render_pre_run_digest` content operators see today via `mcp-contracts run` — visual parity preserved.
- The `--mcp-domain-ui=force` value (not `=always` or `=on`) was chosen to make the operator's intent explicit at the call site: "I am forcing this on against the no-TTY default."

</specifics>

<deferred>
## Deferred Ideas

- **xdist load-balancing strategy / per-worker domain-UI surfaces** — out of scope for Phase 29. xdist coexistence here is master-only emission of the aggregate UI; surfacing per-worker progress is a future capability and would be its own phase.
- **CI-env-var heuristic auto-OFF (`CI=true`, `GITHUB_ACTIONS`, etc.)** — explicitly rejected as D-03. If real-world CI runs surface false negatives (TTY allocated where operator wants OFF), revisit in v1.5 — but only with evidence from actual operator pain.
- **Domain-UI live row streaming (per-tool rows printed as each test finishes)** — explicitly rejected as D-01 (option b). Reconsider in v1.5+ if operators report blind-wait pain on multi-minute runs. Would require row-buffering-by-tool to avoid parametrize interleaving.
- **JUnit XML parsing as resilient fallback path** — explicitly rejected as D-05 (option c). Defensive double-path was deemed overkill for v1.4.
- **`--mcp-domain-ui=off` value** — included in the choices set but listed here as the lowest-priority sub-case. If never used in real operator workflows by v1.5, can be removed.
- **`-p no:mcp_test_framework_reporter` documentation** — falls in Phase 30 (CLOSE) docs sweep, not here. Phase 29 just makes the toggle WORK; docs come later.

</deferred>

---

*Phase: 29-live-domain-ui-reporter-plugin*
*Context gathered: 2026-05-16*
