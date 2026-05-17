# Phase 30: CLI demotion + carry-forward UAT closure + docs rewrite - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning

> ⚠️ **REQUIREMENTS.md CLOSE-01 and CLOSE-03 are STALE — Phase 30 amends them.**
> CLOSE-01 still references `register(config=Config())` and CLOSE-03 still says "write three lines in `conftest.py`" — both pre-empted by Phase 27 D-01 (register() API dropped in favor of `[tool.pytest.ini_options] mcp_config_file`) and Phase 27 D-07 (framework dogfood already landed in Phase 27 D-06). ROADMAP.md Phase 30 goal text is already updated; REQUIREMENTS.md needs catch-up. See `<downstream_impact>`.

<domain>
## Phase Boundary

Phase 30 is the v1.4 **close** phase. It delivers four threads:

1. **Dogfood verification (SC1)** — Confirm the loop landed by Phase 27 D-06 (`[tool.pytest.ini_options] mcp_config_file = "./config.test.yaml"` in framework's own `pyproject.toml`) is still green at v1.4 close. No new code; a pytest-run + assertion + STATE.md note.
2. **CLI/library parity test (SC2)** — Only new production-shaped test in the phase. A framework self-test that drives both `mcp-contracts run --config config.test.yaml` and `pytest -o "mcp_config_file=./config.test.yaml"` against the same live config and asserts equivalent JUnit XML output. See `<decisions>` for the three locked design decisions.
3. **README + docs rewrite (SC3)** — Lead-with-library-mode rewrite of `README.md` ("Add to your `pyproject.toml`, set one line in `[tool.pytest.ini_options]`, run pytest"); CLI usage demotes to an Appendix section; new `docs/LIBRARY-MODE.md` becomes the primary reference for the library API surface. README currently still leads with MVP-flavor copy (`homelab-mcp` / `list_keyring_credentials` / Ollama setup) — heavy rewrite, not a polish pass.
4. **Carry-forward live-UAT closure (SC4)** — Four UATs deferred from v1.2 / v1.3 close, all requiring live homelab-mcp + Proxmox keyring access. Per memory `feedback_uat_must_be_user_driven`: these are user-driven captures, not framework assertions.

**What ships in Phase 30:**

1. **Dogfood verification plan** — runs framework's own contract suite end-to-end against `config.test.yaml` via the pytest-native ini route, asserts pass, records in STATE.md / VERIFICATION.md.
2. **CLI/library parity test** — new file under `tests/framework/` (planner picks exact path; suggested `tests/framework/parity/test_cli_vs_pytest_route.py`). Carries a new `@pytest.mark.parity` marker so inner subprocesses can exclude it via `-m 'not parity'`.
3. **`README.md` rewrite** — new top-of-README library-mode quickstart, CLI demotion to Appendix, scrub of operator-facing planning-ID leaks (per memory `project_doc_scrub_planning_artifacts`, v1.2-deferred scrub still pending in `README.md`, `config.example.yaml`, `.env.example`, `docs/EXTENDING.md`).
4. **`docs/LIBRARY-MODE.md`** — new primary reference for the library-mode API surface. Documents the `mcp_config_file` ini value, plugin auto-discovery, marker semantics, fixture surface (`mcp_*` prefixed names), reporter plugin opt-in (`--mcp-domain-ui`), and `gen-test-classes` CLI flow.
5. **REQUIREMENTS.md amendments** — CLOSE-01 and CLOSE-03 rewritten to match the Phase 27 D-01 / D-07 reality.
6. **Live-UAT capture protocols** — written into `30-UAT.md`-shape document(s) the user runs against live homelab-mcp + Proxmox in a follow-up session. Phase 30 plans produce the capture script/checklist; PASS evidence pastes into UAT.md after the session.

**Out of scope (explicitly):**

- **PyPI publish** — explicitly out of scope per REQUIREMENTS.md "Out of Scope" §1 ("Removing the CLI"; CLI continues to ship); v1.4 is a delivery-shape pivot, not a publish event. Push to git remote also deferred (see Claude's discretion below).
- **Schema v2→v3 migration** — explicitly deferred to v1.5 per REQUIREMENTS.md "Out of Scope".
- **`docs/SDET-AUTHORING.md` removal** — the file exists alongside `docs/TEST-CODE-AUTHORING.md` as a v1.4 deprecation alias per Phase 25. Removal lands in v1.5 cleanup with every other deprecation shim — NOT this phase.
- **Removing/deleting `mcp-test-framework run` CLI alias** — REQUIREMENTS.md "Out of Scope" §1 confirms CLI continues to ship; legacy command alias drops in v1.5 cleanup, not here.
- **README badge rewrites, branding, or marketing surface** — explicitly out of scope per REQUIREMENTS.md "Out of Scope" §7. The rewrite is operator-onboarding-first, not marketing.
- **xdist parallel parity testing** — parity test runs single-threaded; xdist parity gating deferred to v1.5 with the rest of xdist work.

</domain>

<decisions>
## Implementation Decisions

### CLI/library parity test design (SC2 — the only new production test)

- **D-01:** **Equivalence definition: per-test outcome match on a `{nodeid: outcome}` dict.** Parse both JUnit XMLs, build `{nodeid: outcome}` dict for each route, assert dicts equal. Outcome enum: `passed | failed | skipped | error`. Catches missing tests, divergent skip sets, and per-tool outcome divergence. Tolerates timestamps, durations, hostnames, worker PIDs, ordering — the operator-meaningful interpretation of "same pass/fail signal." Stricter than counts-only (which would miss "same totals, different test set" drift); looser than deep tree equality (which would flake on message-text wording drift). Rejected alternatives: counts-only (too loose); structured deep equal with noise-stripping (too much bikeshed surface); combined three-layer check (over-engineered for a v1.4 close gate).
- **D-02:** **Config source: reuse `./config.test.yaml` (live homelab-mcp) — same config Phase 27 D-06 dogfood already uses.** Zero new fixture infrastructure. The parity test becomes one more contract-test consumer of the live stack the framework's CI already exercises. Skips cleanly when the stack is unreachable (planner picks the skip marker — see Claude's discretion). Rejected alternatives: dedicated `parity_config.yaml` (subset of `config.test.yaml` for faster runs — adds a new fixture to keep in sync for no v1.4 benefit); hermetic stub MCP server under `tests/framework/parity/_fixtures/` (decouples from homelab-mcp but adds a stub-server maintenance burden and weakens "real stack" fidelity).
- **D-03:** **Invocation: two subprocesses + outer marker exclusion.** Route A invokes `mcp-contracts run --config config.test.yaml --junitxml <tmp>/a.xml` as a subprocess (full Typer entry — most faithful to operator invocation; per Phase 27 D-11 + Phase 29 D-05 the CLI internally subprocesses pytest with `-o "mcp_config_file=PATH"` and `--mcp-domain-ui=force`). Route B invokes `pytest -o "mcp_config_file=./config.test.yaml" --junitxml <tmp>/b.xml` as a subprocess (raw pytest-native route). **Recursion guard:** the parity test itself carries a new `@pytest.mark.parity` marker; both subprocesses pass `-m "not parity"` (composed with any other selectors) so inner pytest runs do not re-collect the parity test. Marker registered in plugin or `tests/framework/conftest.py` — planner picks. Rejected alternative: Typer `CliRunner.invoke` + `pytester.runpytest` in-process — faster but bypasses the subprocess boundary the CLI normally has, weakening fidelity to actual operator invocation.

### Claude's Discretion

The user opted to not deep-dive the other three areas (docs rewrite scope, live-UAT choreography, REQ amendments + push timing). Decisions below are Claude/planner-flexible; default direction noted.

- **Parity test file location** — Default: `tests/framework/parity/test_cli_vs_pytest_route.py` (new `parity/` subdir keeps the new marker scope clean; matches the established `tests/framework/<area>/test_<topic>.py` shape). Planner may flatten to `tests/framework/test_cli_library_parity.py` if `parity/` feels over-organized for a single file.
- **`@pytest.mark.parity` registration site** — Default: register in `tests/framework/conftest.py` (framework-self-test scope, doesn't leak to operators' plugin surface). Alternative: register in `src/mcp_test_framework/_plugin.py` if operators might want to filter out their own parity tests later — but the marker is currently a framework-internal recursion guard, so framework-conftest scope is sufficient.
- **Skip-when-stack-down behavior** — Default: match the existing skip pattern other live-stack framework tests use (e.g., `tests/framework/smoke/` — planner reads and mirrors). Likely an autouse fixture that pings the MCP server and `pytest.skip(reason=...)`s the test before subprocess launch. The parity test should NOT spawn subprocesses if the inner contract tests would all skip — that produces a misleading "both routes equivalent (both empty)" PASS.
- **`mcp-contracts` invocation in subprocess** — Default: `[sys.executable, "-m", "mcp_test_framework.cli", "run", ...]` to guarantee the test exercises the locally-installed source rather than a PATH-resolved binary that might be stale. Alternative: `["uv", "run", "mcp-contracts", "run", ...]` if the test is meant to also validate the entry-point installation. Planner picks; mirror Phase 26 PACK-04 wheel-introspection conventions if they exist.
- **README + docs rewrite scope** — Default direction: rewrite README top (Setup → Library-mode Quickstart), demote CLI to Appendix section *inside README* (not a separate `docs/CLI.md` — keeps operator surfaces in two files: README for orientation, `docs/LIBRARY-MODE.md` for depth). Create `docs/LIBRARY-MODE.md` as primary deep-reference for the library API surface (ini value, plugin auto-discovery, marker semantics, fixture surface, reporter plugin opt-in, gen-test-classes). Bundle the v1.2-deferred operator-doc ID-leak scrub (memory `project_doc_scrub_planning_artifacts`) into the same docs sweep — `README.md`, `config.example.yaml`, `.env.example`, `docs/EXTENDING.md`. NOT bundled: `docs/SDET-AUTHORING.md` cleanup (waits for v1.5 alias drop).
- **Live-UAT choreography (SC4)** — Default direction: Phase 30 plans produce a `30-UAT.md`-shape capture document with one section per carry-forward UAT, each containing the exact commands to run, the expected observable outcome, and a "Paste evidence here:" block. Phase 30 VERIFICATION.md does NOT block on UAT closure — UATs are tracked separately and closed in a follow-up user-driven session per memory `feedback_uat_must_be_user_driven`. Alternative: gate VERIFICATION.md on UAT closure (forces user to capture before phase closes; risk: blocks v1.4 close on user-availability and Proxmox-keyring readiness).
- **REQUIREMENTS.md / ROADMAP.md amendments** — Default direction: bundle REQUIREMENTS.md CLOSE-01 + CLOSE-03 rewrites into a Phase 30 docs-amendment plan (planner picks whether it bundles with the README rewrite plan or stands alone). ROADMAP.md Phase 30 goal text is already current (verified during discussion). Mirror the Phase 27 / Phase 28 pattern of CONTEXT.md > REQUIREMENTS.md / ROADMAP.md when stale.
- **Git push timing** — Default direction: defer the `git push origin main` to a separate `/gsd-complete-milestone v1.4` step *after* Phase 30 lands and UATs close, mirroring memory `project_v1_3_close_push_and_scrub` (v1.3 push deferred to milestone close so cleanup bundled). NOT in Phase 30 plans. Planner does NOT add a push task.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & roadmap

- `.planning/PROJECT.md` — Vibe-coded operator persona; v1.4 milestone framing; operator-vs-test-code persona split.
- `.planning/ROADMAP.md` §"Phase 30: CLI demotion + carry-forward UAT closure + docs rewrite" — Goal + SC1..SC4 + Depends-on (Phase 27, 28, 29).
- `.planning/REQUIREMENTS.md` CLOSE-01..04 — **NOTE: CLOSE-01 and CLOSE-03 text stale per Phase 27 D-01 / D-07**, see `<downstream_impact>`. CLOSE-02 and CLOSE-04 text current.
- `.planning/STATE.md` — Phase position; milestone counters; will be updated as Phase 30 progresses.

### Phase 27 carry-forward (the dogfood + ini-route substrate Phase 30 verifies)

- `.planning/phases/27-register-api-contracts-sub-package-test-extraction-lib/27-CONTEXT.md` — D-01 register() drop pivot; D-06 framework dogfood landed (`mcp_config_file = "./config.test.yaml"`); D-07 explicitly pre-empts Phase 30 CLOSE-01; D-11 CLI mode subprocesses `pytest -o "mcp_config_file=PATH"`; D-09 `MCPTF_CONFIG_FILE` deprecation.
- `.planning/phases/27-register-api-contracts-sub-package-test-extraction-lib/27-VERIFICATION.md` — Confirms `mcp_config_file` ini route is the locked single source of truth at Phase 27 close.

### Phase 28 carry-forward (codegen + config-resolution substrate)

- `.planning/phases/28-codegen-output-path-codegen/28-CONTEXT.md` — D-11 `gen-test-classes` reads pyproject ini; D-01..D-10 codegen safety policy. Phase 30 docs document this surface in `LIBRARY-MODE.md`.

### Phase 29 carry-forward (reporter shape — docs describe it)

- `.planning/phases/29-live-domain-ui-reporter-plugin/29-CONTEXT.md` — D-01 batch-render at session end; D-04 `--mcp-domain-ui` opt-in with `=auto|force|off`; D-05 CLI mode passes `--mcp-domain-ui=force`; D-05b xdist master-only. Phase 30 `LIBRARY-MODE.md` documents the operator-facing reporter opt-in.

### Phase 25 carry-forward (rename + deprecation pattern)

- `.planning/phases/25-public-api-rename-seed-023-sdet-test-code/25-CONTEXT.md` — `sdet → test_code` rename + deprecation alias pattern. Confirms `docs/SDET-AUTHORING.md` stays alongside `docs/TEST-CODE-AUTHORING.md` in v1.4 (do not delete in Phase 30).
- `docs/TEST-CODE-AUTHORING.md` — current canonical test-code-author walkthrough. Phase 30 `LIBRARY-MODE.md` links to this for the test-code-author surface; does NOT duplicate its content.

### Operator-facing surfaces Phase 30 rewrites or creates

- `README.md` — current top-of-README still MVP-era (homelab-mcp / list_keyring_credentials / Ollama setup); Phase 30 rewrites top to lead with library mode, demotes CLI to Appendix.
- `docs/LIBRARY-MODE.md` — **does not exist yet**; Phase 30 creates as primary library-mode reference.
- `docs/EXTENDING.md` — operator-facing; included in v1.2-deferred ID-leak scrub per memory `project_doc_scrub_planning_artifacts`.
- `docs/ERROR-STYLE.md` — operator-tone error template; LIBRARY-MODE.md error examples follow this style.
- `config.example.yaml` and `.env.example` — operator-onboarding fixtures; included in v1.2-deferred ID-leak scrub.

### Codebase landmarks (Phase 30 will touch / inspect)

- `tests/framework/` — destination for the new parity test. Planner reads `tests/framework/smoke/` and `tests/framework/conftest.py` to mirror existing skip-when-live-stack-down patterns.
- `tests/framework/test_runner_live_smoke.py` — referenced by SC4 carry-forward UAT (v1.2 Phase 14); the UAT script may invoke this as the live-stack regression marker.
- `src/mcp_test_framework/cli.py` — invoked by parity test Route A; no body changes needed in Phase 30 unless verification surfaces a divergence the test catches.
- `src/mcp_test_framework/_plugin.py` — sets the ini-route library mode the parity test exercises (Route B); no body changes needed.
- `pyproject.toml` — already carries `[tool.pytest.ini_options] mcp_config_file = "./config.test.yaml"` (Phase 27 D-06). Phase 30 verifies still present; if a new `parity` marker needs `markers = [...]` registration, add here.
- `config.test.yaml` — live homelab-mcp config Phase 27 D-06 wired up; parity test consumes verbatim.

### Memory anchors (drove discussion + Claude's-discretion defaults)

- `project_v1_3_close_push_and_scrub` — v1.3 push deferred to milestone close; same pattern proposed for v1.4 (push NOT in Phase 30).
- `project_doc_scrub_planning_artifacts` — operator-facing docs leak phase/plan/spec IDs; v1.2-deferred scrub bundled into Phase 30 docs sweep.
- `feedback_uat_must_be_user_driven` — UATs are user-driven captures; Phase 30 produces capture protocols, doesn't auto-assert.
- `feedback_phase_scope_intent` — phase title names the scope; CLI demotion + carry-forward UAT closure + docs rewrite ARE all in scope, do NOT defer.
- `feedback_option_presentation_with_context` — used during discussion to frame WHY before options.
- `project_framework_primitives_sdet_safety_principle` — confirmed parity test reuses live `config.test.yaml` (no SUT-aware logic injected into framework code; the live config is operator-supplied data the framework consumes).

### Python / pytest references (researcher should fetch)

- pytest JUnit XML schema — `<testsuite>` attrs (`tests`, `failures`, `errors`, `skipped`), `<testcase>` attrs (`classname`, `name`, `time`), `<failure>` / `<skipped>` / `<error>` child elements. https://docs.pytest.org/en/stable/how-to/output.html#creating-junitxml-format-files
- pytest `-m` marker expressions — composability with `and`/`not`/`or`; researcher confirms `-m "mcp_contract and not parity"` syntax works for inner subprocess command lines.
- `subprocess.run` with `capture_output=True, check=False` — parity test reads exit code + stdout/stderr from both routes; researcher confirms the cross-platform invocation shape (Windows shell escaping, `sys.executable` for `python -m mcp_test_framework.cli`).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **Phase 27 D-06 framework dogfood line** in `pyproject.toml` `[tool.pytest.ini_options]` — `mcp_config_file = "./config.test.yaml"` already present; parity test Route B uses the same value via `-o "mcp_config_file=./config.test.yaml"`.
- **`tests/framework/test_runner_live_smoke.py`** — existing live-stack regression test; parity test mirrors its skip-when-down pattern.
- **`tests/framework/conftest.py`** — existing framework-self-test conftest; destination for `parity` marker registration (default per Claude's discretion).
- **`src/mcp_test_framework/cli.py` Typer entry point** — the `mcp-contracts` console script the parity test Route A subprocesses. No body changes; Phase 30 only consumes it.
- **JUnit XML round-trip path** in `src/mcp_test_framework/_runner.py:491` `parse_junit_xml(Path) -> ParsedRun` — could be reused by the parity test for parsing, OR the parity test can use `xml.etree.ElementTree` directly for a smaller surface (it only needs `{nodeid: outcome}`, not the full ParsedRun shape). Planner picks.
- **`docs/ERROR-STYLE.md`** — operator-tone error template; reused verbatim by Phase 30's docs rewrite for any error examples in `LIBRARY-MODE.md`.

### Established Patterns

- **`tests/framework/<area>/test_<topic>.py` layout** — matches existing `tests/framework/smoke/`, `tests/framework/integration/`, `tests/framework/unit/` shape. Parity test fits as `tests/framework/parity/test_cli_vs_pytest_route.py`.
- **Subprocess invocation via `sys.executable -m mcp_test_framework.cli`** — guarantees the test exercises the in-tree source (matches Phase 26 PACK-04 wheel-introspection conventions if applicable).
- **Skip-when-live-stack-down via autouse fixture** — existing pattern in `tests/framework/smoke/` (planner reads to mirror).
- **Live-config-as-fixture** — Phase 27 D-06 established `./config.test.yaml` as the framework's CI live-stack config. Phase 30 parity test consumes it verbatim.
- **CLI demotion without removal** — REQUIREMENTS.md "Out of Scope" §1 explicit: CLI keeps shipping. Phase 30 docs demote presentation order; do NOT add deprecation warnings to the CLI itself.

### Integration Points

- **Parity test ↔ both routes** — pure black-box from the test's perspective; both routes consume the same `config.test.yaml`, both produce `--junitxml <path>` files the test parses + compares.
- **`@pytest.mark.parity` ↔ inner subprocess `-m "not parity"`** — recursion guard; marker registered in framework conftest (not in plugin) since it's framework-internal.
- **`docs/LIBRARY-MODE.md` ↔ Phase 27/28/29 surfaces** — docs reference (but do NOT duplicate) the locked decisions: `mcp_config_file` ini value (P27 D-02), `MCPTF_CONFIG_FILE` deprecation (P27 D-09), `gen-test-classes` pyproject resolution (P28 D-11), `--mcp-domain-ui` reporter opt-in (P29 D-04). Docs describe the operator-facing API; CONTEXT.md files of those phases remain the design rationale.
- **README rewrite ↔ Setup section** — current Setup section is `uv sync` + `homelab-mcp` install; rewrite leads with "add `mcp-contracts` to your `pyproject.toml`" library-mode flow, demotes the SUT-specific instructions to "Run against the example homelab-mcp stack" subsection within the new Appendix.

</code_context>

<downstream_impact>
## Downstream Impact (planner must produce amendment plans inside Phase 30)

### REQUIREMENTS.md amendments

- **CLOSE-01** — current text references `register(config=Config())` and `tests/conftest.py`'s `pytest_generate_tests`. Both dead per Phase 27 D-01 / D-05. Rewrite to: *"Framework's own `pyproject.toml` sets `[tool.pytest.ini_options] mcp_config_file = \"./config.test.yaml\"` (landed in Phase 27 D-06); Phase 30 verifies the dogfood loop is still green at v1.4 close. CLI-mode path (`mcp-contracts run`) continues to subprocess pytest with JUnit XML round-trip and shares the same `ParsedRun` domain model and renderer helpers."*
- **CLOSE-03** — current text says "write three lines in `conftest.py`". Dead per Phase 27 D-01. Rewrite to: *"New operator reading the README sees library-mode usage first (\"Add to your `pyproject.toml`, set one line in `[tool.pytest.ini_options]`, run pytest\"); CLI usage demotes to an \"Appendix: CLI usage\" section; `docs/LIBRARY-MODE.md` is the primary reference document for the library API surface."*  (This is already the ROADMAP.md text — REQUIREMENTS.md just needs to catch up.)
- **CLOSE-02 and CLOSE-04** — current text current; no amendment needed.
- **Traceability table** — leave Phase 30 entries; flip to `Complete` after Phase 30 closes.

### ROADMAP.md amendments

- **None required.** Phase 30 goal + SC1..SC4 already reflect the post-Phase-27-pivot reality (verified during discussion).

### Future-deferred items (no change)

- `docs/SDET-AUTHORING.md` removal — stays in v1.5 cleanup phase.
- `mcp-test-framework` CLI alias removal — stays in v1.5 cleanup phase.
- `MCPTF_CONFIG_FILE` env var removal — stays in v1.5 cleanup phase (deprecation lands in Phase 27 D-09).
- Schema v2→v3 migration — stays deferred to v1.5.
- xdist parallel execution + parity gating under xdist — stays deferred to v1.5.

</downstream_impact>

<specifics>
## Specific Ideas

- **"Identical pass/fail signal" is the operator-meaningful definition of equivalence** (drove D-01). Operator running `mcp-contracts run --config X` and operator running `pytest -o "mcp_config_file=X"` care about: did the same tests run, did each one pass or fail the same way. They do NOT care about durations or timestamps. D-01's `{nodeid: outcome}` dict is exactly this contract.
- **Live `config.test.yaml` is the realistic test substrate** (drove D-02). The whole v1.4 thesis is "library mode IS the CI loop" — the parity test naturally reuses what the rest of framework CI already runs against. No bespoke fixture, no synthetic stub, no stack divergence between parity and the rest of CI.
- **Two subprocesses keep the boundary honest** (drove D-03). Operators invoke `mcp-contracts run` and `pytest` from a shell, not from in-process API. The parity test exercises the same boundary, in the same way. `CliRunner` would cut the cost but skip the part that matters.
- **README rewrite is heavy, not polish.** Current README is MVP-shape (one tool, one server, one Ollama backend). New README is library-shape (any compatible MCP server, ini-route config, opt-in tools). Plan accordingly — this is more like writing a new README than editing the existing one.

</specifics>

<deferred>
## Deferred Ideas

### v1.5 cleanup phase (carry-over)

- `docs/SDET-AUTHORING.md` removal (deprecation alias drops).
- `mcp-test-framework` CLI alias removal (legacy console script drops).
- `MCPTF_CONFIG_FILE` env var removal (Phase 27 D-09 deprecation expires).
- All other Phase 25 / 26 / 27 deprecation shims drop in one round.
- Schema v2→v3 migration with `cfg.sdet.*` field-alias drop.
- xdist parallel execution support + parity-under-xdist gating.

### v1.4-close adjacent (post-Phase-30, pre-v1.5)

- **`/gsd-complete-milestone v1.4`** — archive v1.4 milestone, push to git remote per memory `project_v1_3_close_push_and_scrub` pattern. Phase 30 plans do NOT include the push.
- **Tool auto-discovery (operator omits `tools:`)** — deferred to v1.5 per REQUIREMENTS.md "Future Requirements".
- **OpenAI-compatible judge backend (SEED-005)** — deferred to v1.5.
- **Multi-server context-manager seam for monorepos** — deferred to v1.5.

### Explicitly REJECTED (do not resurrect)

- **Counts-only parity check** — rejected in D-01 as too loose.
- **Structured-deep-equal parity check with noise-stripping** — rejected in D-01 as too much bikeshed surface for v1.4 close.
- **Dedicated `parity_config.yaml` fixture** — rejected in D-02 in favor of reusing `config.test.yaml`.
- **Hermetic stub MCP server under `tests/framework/parity/_fixtures/`** — rejected in D-02 in favor of live `config.test.yaml`.
- **In-process Typer `CliRunner` + `pytester.runpytest`** — rejected in D-03 in favor of subprocess boundary fidelity.
- **Gating VERIFICATION.md on live-UAT closure** — explicitly NOT the default per Claude's discretion in `<decisions>`; UATs tracked separately, Phase 30 plans produce capture protocols.

### Other phases (already roadmapped)

- None — Phase 30 is the last phase of v1.4 per ROADMAP.md.

</deferred>

---

*Phase: 30-cli-demotion-carry-forward-uat-closure-docs-rewrite*
*Context gathered: 2026-05-17*
