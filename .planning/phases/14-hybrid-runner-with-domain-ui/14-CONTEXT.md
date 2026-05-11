# Phase 14: Hybrid runner with domain UI - Context

**Gathered:** 2026-05-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Wrap `mcp-test-framework run` around a subprocess pytest invocation so the operator sees an MCP-domain UI (header / per-tool result rows / summary) rendered from a captured JUnit XML, with pytest's native framing fully suppressed under the default mode. `--raw` keeps the maintainer escape hatch. `--junit-xml=PATH` (v1.1 OUTPUT-01) still emits to the operator-specified path via a separate internal tempfile. Exit codes 0 / 1 / 2 / 130 preserved.

**In scope:** RUNNER-01..06 (6 requirements). Subprocess pytest plumbing in `cli.py:run`; internal tempfile JUnit XML capture; new XML→domain-model parser; new domain UI renderer (header + rows + summary + failure detail); deletion of `src/mcp_test_framework/_reporter.py` and its registration in `tests/conftest.py`; verbosity flags `-q` / `--debug` / `--raw` on the Typer command; pre-flight config gate preserved via `_load_config` on both default and `--raw` paths.

**Out of scope:**
- **Phase 15** — `tests/contract/` vs `tests/framework/` folder split. Phase 14 leaves the default collection scope as `tests/` (current state); Phase 15 retargets the wrapper to `tests/contract/` after the `git mv`.
- **Phase 16** — Full pre-run digest polish (`--explain` flag, verbosity ladder beyond `-q` / default / `--debug`, post-run aggregation tweaks, N=70 readability passes). Phase 14 ships a *minimal* header section per RUNNER-02; Phase 16 owns the layout polish and `--explain`.
- Live per-tool progress (stream pytest output and translate as it runs). Deferred — batch render is the v1.2 baseline; live progress can land in v1.3 if needed.
- Color/TTY library upgrade to `rich`. Deferred — stdlib + ANSI is the v1.2 baseline.

**Hard dependency:** Phase 13 must be complete (it is — shipped 2026-05-10). Phase 14's pre-flight reuses Phase 13's `_load_config` resolver as the single config-error surface; the "Skipping (N)" header count derives from Phase 13's three-state allowlist (`tools.<name>` listed vs unlisted vs `skip: true`).

**Sequencing note:** SEED-011 rule — Phase 14 (runner contract) decides BEFORE Phase 15 (folder split), because the wrapper's collection-scope contract drives where the contract folder lives.

</domain>

<decisions>
## Implementation Decisions

### Wrapper invocation contract (RUNNER-01)
- **D-01:** **Subprocess pytest.** The wrapper invokes pytest as a child process (`python -m pytest ...` or equivalent), capturing stdout/stderr fully. Clean isolation from pytest's plugin globals; predictable lifecycle; the wrapper process stays uncoupled to pytest's reporter/terminalreporter internals. Trade-off accepted: ~150ms startup overhead per run is acceptable for a CI tool that already spawns the MCP server subprocess and talks to Ollama.
- **D-02:** **Internal tempfile JUnit XML.** The wrapper invokes pytest with `--junitxml=<tempfile>` (alongside any operator-supplied `--junit-xml=PATH` which routes through `_build_pytest_args` unchanged per Phase 09 D-01a precedence). After pytest exits, the wrapper parses the tempfile, renders the domain UI, deletes the tempfile. RUNNER-05: the operator-visible `--junit-xml=PATH` semantics do NOT change.
- **D-03:** **Pre-flight gate preserved on both paths.** `_load_config(config)` from Phase 13 runs BEFORE the subprocess in both default and `--raw` modes. SAFE-03's "refuse-on-no-config" failsafe must not be bypassable via `--raw`; the wrapper is responsible for never reaching pytest without a resolved config. Phase 13 D-03's `MCPTF_CONFIG_FILE` export (`cli.py:289`) flows through to the subprocess so the in-pytest-process Config() construction picks up the same resolved YAML.

### Rendering pipeline (RUNNER-02)
- **D-04:** **Batch render from JUnit XML at the end of the run.** Pytest runs silent (stdout captured by the subprocess wrapper); when it exits, the wrapper parses the JUnit XML and renders the full domain UI in one shot. No live per-tool progress in v1.2. Trade-off accepted: slow runs feel frozen between "Running…" and the final render; live progress is deferred to v1.3. SEED-011 Q2 → batch is the safe MVP.
- **D-05:** **`xml.etree.ElementTree` for parsing.** Stdlib only — no new dep. Pytest's JUnit dialect is shallow (`<testsuite>` containing `<testcase classname="…" name="tool_name[<parametrize_id>]" time="…">` with optional `<failure message="…">…</failure>`, `<error>…</error>`, or `<skipped message="…">…</skipped>` children). The parser lives in a new module (suggested `_runner.py` or `_render.py`); a round-trip test against a fixture XML pins the dialect.
- **D-06:** **stdlib f-strings + ANSI escapes for the renderer.** No `rich`. Color codes guarded by `sys.stdout.isatty()` so piped output stays plain. Table alignment via `str.ljust`/`str.rjust` and a fixed-width column model. Matches the v1.1 `_reporter.py` style and keeps the dependency surface flat. Phase 16 can revisit `rich` if the UX gain justifies the dep.

### Domain UI shape (RUNNER-02, Phase 14 minimal)
- **D-07:** **Header section ships in Phase 14.** RUNNER-02 / Phase 14 SC-1 explicitly lists the header (server command, discovered count, running count + names, skipping count, judges-per-tool, test-plan totals) as in scope. Ship a *minimal but complete* header here — exact layout per SEED-011 §2 mockup, no `--explain` plumbing yet. Phase 16 owns: `--explain` per-tool skip reasons (UX-02), N=70 readability tweaks (UX-04), post-run aggregation polish (UX-03), grep-able formatting.
- **D-08:** **Failure detail = judge reasoning + schema message; no traceback by default.** On FAIL, the per-tool row appends `JudgeResult.reasoning` (for judge failures) or `ValidationIssue.message` (for schema failures), extracted from the JUnit `<failure message="…">` attribute and/or its body text. SEED-011 §3. Tracebacks are gated to `--debug` only; default output must contain zero pytest framing. Surface from JUnit attribute is sufficient because `pytest.fail(msg)` and assertions on `JudgeResult.passed` both surface `reasoning` into the failure message via the existing `_reporter.py` skip-reason extraction pattern (which we then port to the new renderer before deleting the plugin).
- **D-09:** **Parametrize-id suffix `[<tool_name>]` is the row key.** Mirror Phase 07 / Phase 09 D-02a's `tests/conftest.py:124-136` `ids=names` convention. Each `<testcase name="test_…[<tool_name>]">` groups under `<tool_name>`. Cases without the suffix (framework unit tests) are excluded from the per-tool table — they should not be there under the default collection scope (and Phase 15's folder split will make this structural).

### _reporter.py fate (RUNNER-02, RUNNER-03)
- **D-10:** **Delete `_reporter.py` entirely in Phase 14.** Post-run JUnit XML parsing in the wrapper replaces the plugin. Delete:
  - `src/mcp_test_framework/_reporter.py` (the plugin)
  - Its registration in `tests/conftest.py` (`pytest_plugins = [...]`)
  - The targeted reporter tests under `tests/` (re-target as renderer tests against XML fixtures)
- Migration of reporter behavior into the new renderer: port the skip-reason de-dup + cap (Phase 09 D-05), the "FAIL → SKIP → PASS alphabetical" row ordering (Phase 09 CD-03), the any-fail-wins per-tool collapse (Phase 09 D-03), and the SAFE-01 two-distinct-skip-reason rendering (Phase 13 D-12 — `"not selected in config"` vs operator `skip_reason`).
- Under `--raw` no per-tool summary plugin runs — pytest's native output is the entire surface. Operators using `--raw` are maintainers; they don't need the v1.1 grouping.

### --raw escape hatch (RUNNER-03)
- **D-11:** **`--raw` bypasses the wrapper but NOT the config pre-flight.** Implementation:
  1. `_load_config(config)` still runs first (SAFE-03 preserved — destructive defaults can't slip through `--raw`).
  2. No internal tempfile; the wrapper doesn't supply `--junitxml`. Operator-supplied `--junit-xml=PATH` still flows through `_build_pytest_args` per Phase 09 D-01a.
  3. Subprocess pytest with all forwarded flags; stdout/stderr passthrough (not captured).
  4. Exit code = pytest's; no domain UI rendering.
- Equivalent to `uv run pytest tests/` modulo the config gate. Phase 15 retargets the default collection scope to `tests/contract/` later.

### Verbosity ladder (RUNNER-04)
- **D-12:** **`-q` is a Typer-level flag, not forwarded to pytest.** When passed, the wrapper still runs pytest at its default verbosity internally (so JUnit XML stays complete), then renders only the final summary line (one-line summary, no header, no per-tool rows). Framework-shaped quiet semantics, independent of pytest's `-q`.
- **D-13:** **`--debug` appends raw pytest output + tracebacks AFTER the domain UI.** Default UI renders normally; then a `--- raw pytest output ---` separator, followed by the captured pytest stdout, followed by any JUnit `<failure>` longrepr bodies. RUNNER-04 invariant: "each rung adds information; none re-shapes the layer below." Default UI is unchanged regardless of `--debug`.
- **D-14:** **`--explain` is OWNED by Phase 16, not Phase 14.** Phase 14 may scaffold the flag as a no-op or omit it — Phase 16 owns UX-02 plumbing. Recommended: omit the flag in Phase 14 so Typer's `--help` doesn't promise something the build doesn't deliver. Phase 16 adds the flag with the full per-tool-skip-reasons rendering.

### Exit code preservation (RUNNER-06)
- **D-15:** **Map subprocess exit code → typer.Exit unchanged.** Pytest returns 0 (all pass), 1 (test failures), 2 (collection/usage errors), 5 (no tests collected — map to 0 with a warning line, matching v1.1 behavior). SIGINT (130) is preserved by not catching `KeyboardInterrupt` in the wrapper — Phase 04.1's AsyncExitStack ownership still applies inside the subprocess; the wrapper just propagates. `_load_config` already raises `typer.Exit(2)` on config errors.
- **D-16:** **JUnit XML parse errors → exit 2** with a domain-shaped error pointing at `--debug` for raw output. If pytest crashes hard enough that no XML is emitted, fall back to dumping raw stdout + exit code under a "pytest exited without producing a JUnit XML" error message.

### Claude's Discretion
- **Plan ordering within Phase 14.** Suggested sequence: (1) subprocess wrapper + `_load_config` gate + tempfile JUnit emit + exit-code mapping (RUNNER-01/03/05/06 spine); (2) XML→domain-model parser (`_runner.py` or `_render.py` module); (3) renderer (header + rows + summary) — port Phase 09's any-fail-wins / row-ordering / skip-reason-dedup logic; (4) `--raw` and `--debug` and `-q` flags; (5) delete `_reporter.py` + registration + re-target reporter tests as renderer tests against XML fixtures.
- **Exact module split.** `_runner.py` for subprocess + parse + dispatch, vs `_renderer.py` for the UI rendering, vs collapsing both into one. Pure code-org judgment.
- **Header layout details.** Server-command wrapping for long `uvx --from … script-name`, "Running (2)" count format vs comma-joined names — pick whatever scans cleanly. Phase 16 will polish at N=70.
- **Whether `--debug` also turns on pytest `-v`.** Likely yes (more raw info is the point), but verify it doesn't change JUnit XML shape.
- **JUnit XML fixture generation for renderer tests.** Pin a small set of XML fixtures (all-pass, one-fail-with-reasoning, all-skip, mixed) under `tests/` so renderer tests don't require a live pytest run.
- **Whether to extract the `[<tool_name>]` parser into a shared helper** used by both the renderer and any future tools that consume parametrize-suffixed nodeids.
- **`run` command signature** — whether `pytest_args` (the Typer `Argument` for post-`--` passthrough) stays in the default-mode signature or is gated behind `--raw`. Recommend keeping it for both (default mode forwards them to the subprocess inside the wrapper); maintainers can pass `-k pattern` and still get the domain UI.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/REQUIREMENTS.md` §RUNNER-01..06 — the 6 locked requirements for this phase
- `.planning/ROADMAP.md` Phase 14 row (lines 84–93 and 41) — goal, depends-on, success criteria
- `.planning/PROJECT.md` "Current Milestone: v1.2 Operator-First Design" — milestone framing and anti-vision
- `.planning/STATE.md` — current execution position (Phase 13 shipped 2026-05-10)

### SEED-011 — primary design spec for this phase
- `.planning/seeds/SEED-011-hybrid-runner-domain-ui.md` — full design space, mockup at §2, open design questions §"Open Design Questions" (this CONTEXT.md resolves them), breadcrumbs §"Breadcrumbs" (file paths in `src/`)

### Cross-seed coordination
- `.planning/seeds/SEED-008-reporter-ux-overhaul.md` — Phase 16 owns full pre-run digest + `--explain` + N=70 readability; Phase 14 ships the *minimal* header + rows + summary surface that SEED-008 polishes
- `.planning/seeds/SEED-010-operator-vs-framework-test-surface.md` — Phase 15 owns the folder split; Phase 14's default collection scope stays `tests/` until Phase 15 retargets to `tests/contract/`

### Phase 13 forward-refs (LOCKED — implement against, do not modify)
- `.planning/phases/13-config-safety-opt-in-tool-selection/13-CONTEXT.md` §decisions D-01, D-03, D-12 — `_load_config` resolver contract (the wrapper's pre-flight gate), three-state skip-reason strings (rendered by the new renderer)
- `src/mcp_test_framework/cli.py:191-293` — `_load_config` implementation (reused as pre-flight gate, do not duplicate)
- `src/mcp_test_framework/cli.py:296-319` — `_build_pytest_args` (passthrough/junit precedence — reused in the subprocess argv builder)

### v1.1 contracts preserved by this phase
- v1.1 Phase 09 D-01a / D-01b — `--junit-xml=PATH` operator spelling translates to pytest `--junitxml=PATH`; passthrough wins via last-occurrence (`_build_pytest_args` in `cli.py`)
- v1.1 Phase 09 OUTPUT-01 / OUTPUT-02 / OUTPUT-03 contracts — JUnit XML emission to operator-specified path stays; per-tool grouping logic ports into the new renderer
- v1.1 Phase 04.1 — AsyncExitStack-owned `mcp_client` fixture inside the subprocess still owns MCP server lifecycle; SIGINT contract (exit 130) preserved by not catching `KeyboardInterrupt` in the wrapper
- v1.1 Phase 07 `ids=names` parametrize convention at `tests/conftest.py:124-136` — the `[<tool_name>]` row-key extraction depends on this; do not change

### Files affected by this phase
- `src/mcp_test_framework/cli.py:322-376` (the `run` Typer command) — rewrite around subprocess + tempfile JUnit + render flow; new flags `--raw`, `--debug`, `-q`
- `src/mcp_test_framework/cli.py:296-319` (`_build_pytest_args`) — reused; the wrapper builds an inner argv that pytest sees, plus an outer subprocess invocation argv
- `src/mcp_test_framework/_reporter.py` — DELETED in this phase (logic ports into new renderer)
- `tests/conftest.py` — remove the `pytest_plugins = ["mcp_test_framework._reporter"]` registration (or equivalent)
- `tests/test_reporter.py` (or wherever the v1.1 reporter tests live) — retarget as renderer tests against XML fixtures
- `pyproject.toml` — no new deps; stdlib `xml.etree.ElementTree` + ANSI strings

### Files created by this phase
- `src/mcp_test_framework/_runner.py` (or `_render.py`) — new module: subprocess invocation, JUnit XML parsing, domain UI rendering, exit-code mapping (final module split is Claude's discretion per D's)
- `tests/fixtures/junit-*.xml` (or equivalent) — small set of JUnit XML fixtures for renderer unit tests (all-pass, one-fail-with-reasoning, all-skip, mixed)
- `tests/test_runner.py` and/or `tests/test_renderer.py` — XML-fixture-driven unit tests for parser + renderer

### Pre-existing context worth re-reading
- `docs/mcp_test_framework_mvp_spec.md` — authoritative MVP spec; the subprocess/JUnit/render rewrite must not break stdio-only / black-box / strict-asyncio invariants
- `src/mcp_test_framework/_reporter.py` (before deletion) — current per-tool grouping algorithm is the reference for the new renderer's grouping logic; copy the Phase 09 D-03 / D-05 / CD-03 invariants into the new renderer's docstring
- Memory: `project_output_ergonomics_at_scale.md`, `project_pre_run_tool_summary.md` — the N=70 backdrop (Phase 16 owns polish; Phase 14 must not block it)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_load_config` in `src/mcp_test_framework/cli.py:191-293` — already raises `typer.Exit(2)` on all SAFE-* error paths (Phase 13 D-01..D-04); the wrapper reuses it as the pre-flight gate verbatim. No re-checking, no duplication.
- `_build_pytest_args` in `src/mcp_test_framework/cli.py:296-319` — already translates `--junit-xml=PATH` to pytest's `--junitxml=PATH` with D-01a passthrough precedence; the wrapper's inner argv builder calls into this. Phase 14 augments by inserting `--junitxml=<tempfile>` as a *prefix* (passthrough wins is preserved).
- `_emit_operator_error` (Phase 12) — operator-tone error writer; reused for "pytest exited without producing JUnit XML" and "JUnit XML parse failed" error sites (D-16).
- `_reporter.py` per-tool grouping algorithm (Phase 09 D-03 any-fail-wins + D-05 skip-reason de-dup-and-cap + CD-03 FAIL→SKIP→PASS alphabetical) — these invariants port directly into the new renderer before the plugin is deleted. The algorithm has shipped on `homelab-mcp` and is correct; do not redesign it.
- Phase 13 D-12 skip-reason constants in `_reporter.py` (lines 59ff: `"not selected in config"` and `"explicit skip in config"`) — port to the new renderer module as the canonical constants; SAFE-01's exact wording is locked.

### Established Patterns
- Subprocess-with-tempfile pattern is new to this codebase, but the project already spawns the MCP server as a subprocess via the `mcp` SDK's `stdio_client` (inside the pytest run). Phase 14 adds a second subprocess layer at the wrapper level — pytest as the child, MCP server as the grandchild. SIGINT propagation through both layers is the operational concern (validate: Ctrl+C kills pytest → pytest cleans up the MCP subprocess via Phase 04.1's AsyncExitStack → wrapper exits 130).
- `typer.Exit(code=...)` is the canonical exit pattern; the wrapper raises `typer.Exit(code=pytest_exit_code)` after rendering. Matches existing `cli.py:376` shape.
- Stdlib-only renderer style — v1.1's `_reporter.py` uses `terminalreporter.write_sep`/`write_line`; the new renderer uses plain `print`/`sys.stdout.write` since it owns the output channel entirely. ANSI guard via `sys.stdout.isatty()`.

### Integration Points
- `cli.py:run` → `_load_config(config)` (Phase 13 pre-flight) → wrapper subprocess (pytest) → JUnit XML tempfile → renderer → `typer.Exit(code)`. Single linear flow; no plugin coupling.
- The in-subprocess pytest still constructs `Config()` from `MCPTF_CONFIG_FILE` (Phase 13 CR-01/CR-02 export at `cli.py:289`). No change needed — the env-var export already propagates.
- `tests/conftest.py` plugin registration line is the seam for deleting `_reporter.py`; nothing else imports it directly.
- The `--junit-xml=PATH` flag stays on the `run` Typer command and routes through `_build_pytest_args` unchanged. RUNNER-05 is "preserve existing behavior"; no rework.

</code_context>

<specifics>
## Specific Ideas

- **SEED-011 §2 header mockup is the reference shape** for Phase 14's minimal header. Reproduce the layout verbatim for v1.2; Phase 16 polishes:
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
  ```
- **Per-row format** (from SEED-011 §2): `[i/N] <tool_name>   ✓ PASS  (clarity 5/5)` on PASS; `[i/N] <tool_name>   ✗ FAIL  (parameters 3/5: "<reason>")` on FAIL; `[i/N] <tool_name>   – SKIP  (<reason>)` on SKIP. Use the existing `—` (U+2014 em-dash) separator from Phase 09 SC-3 wording inside FAIL/SKIP detail lines.
- **Summary line** (from SEED-011 §2): `Result: 1 PASS / 1 FAIL  in 8.3s`. Wall-clock duration comes from the JUnit XML `<testsuite time="…">` attribute (or by timing the subprocess call).
- **`--raw` is equivalent to `uv run pytest tests/`** (modulo the `_load_config` pre-flight gate) — SEED-011 §4 anchor wording; preserve it.
- **"use --explain to list"** hint in the header is a forward-reference to Phase 16's UX-02. Phase 14 can render this literal hint string; the flag itself is implemented in Phase 16. If Phase 14 ships without `--explain` registered, the hint still reads correctly to operators (they'll discover the flag when Phase 16 ships).
- **No traceback in default mode** — even when a fixture raises, the renderer must surface the message via JUnit `<error>` extraction and NOT the longrepr body. Tracebacks only on `--debug`.

</specifics>

<deferred>
## Deferred Ideas

### Cross-phase tasks (Phase 15)
- Retarget the wrapper's default collection scope from `tests/` to `tests/contract/` after `git mv`. Phase 14 leaves this seam easy to flip — a single string in the subprocess argv builder. Phase 15 also flips `--raw`'s equivalence target (`uv run pytest tests/` → `uv run pytest tests/contract/`).
- The `--with-framework` opt-in flag (SURFACE-02) lives in Phase 15, not Phase 14.

### Cross-phase tasks (Phase 16)
- **`--explain` flag** (UX-02) — Phase 14 may include the literal "use --explain to list" hint string in the header, but the flag itself is registered in Phase 16. Renderer must expose a hook (e.g., a no-op `explain` parameter) that Phase 16 can wire without touching the parser.
- **N=70 readability polish** (UX-04) — column-width tuning, name truncation rules, grep-ability of `--explain` output. Phase 14 ships a layout that works at small N; Phase 16 measures at homelab-mcp's full ~70-tool surface and adjusts.
- **Post-run aggregation tweaks** (UX-03) — Phase 14's per-tool table IS the post-run aggregation surface. Phase 16 polishes per-judge breakdowns and reasoning rendering.
- **Verbose / `-v` mode** beyond `-q` / default / `--debug`. SEED-011 §5 mentions `-v` for per-judge breakdown; Phase 14 defers this to Phase 16's verbosity ladder.
- **`rich` library upgrade.** Phase 14 ships stdlib + ANSI; Phase 16 may revisit if the UX gain justifies the dep.

### v1.3+ todos (post-milestone)
- **Live per-tool progress** — stream pytest stdout and translate line markers to live row updates. SEED-011 §"Open Design Questions" Q2 flags as the v1.3 candidate. Requires either a pytest plugin (re-introducing the coupling Phase 14 is removing) or fragile stdout-tail parsing.
- **`junitparser` library** — only if multi-XML merging becomes a real need (e.g., xdist parallelism from SEED-002). For v1.2, stdlib `xml.etree.ElementTree` is sufficient.
- **Color theme / `NO_COLOR` env-var support** beyond the basic `isatty()` guard. Defer until someone asks.
- **Streaming JUnit XML parsing** during the run (tail the tempfile, render rows as they appear). Not practically supported by pytest's JUnit writer (it writes at end). Use a plugin if live progress lands in v1.3.

### Out of phase scope (already deferred at scoping)
- `tests/contract/` vs `tests/framework/` folder split — Phase 15
- Full pre-run digest with `--explain` + N=70 polish — Phase 16
- xdist process-parallel execution — v1.3 (SEED-002)
- OpenAI-compat judge backend — v1.3 (SEED-005)

</deferred>

---

*Phase: 14-hybrid-runner-with-domain-ui*
*Context gathered: 2026-05-10*
