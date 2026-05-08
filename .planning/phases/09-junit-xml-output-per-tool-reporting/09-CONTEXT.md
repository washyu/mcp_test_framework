# Phase 09: JUnit XML output & per-tool reporting - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning

<domain>
## Phase Boundary

A CI engineer can wire `mcp-test-framework run` into their pipeline using JUnit XML and trend per-tool failure rates over time. Locally, an always-on per-tool summary section in the terminal output shows `<tool_name>: PASS|FAIL|SKIP — <reason>` for every discovered tool — readable at a glance without scrolling through pytest detail.

**In scope (per ROADMAP.md and REQUIREMENTS.md):** OUTPUT-01 (`--junit-xml=<path>` CLI argument with passthrough to pytest's `--junitxml=<path>`), OUTPUT-02 (per-tool granularity in JUnit test names — already free-rides on Phase 07 parametrize IDs), OUTPUT-03 (per-tool summary section in terminal output).

**Explicitly NOT in scope:**
- Custom JUnit XML schema / non-standard `<testcase>` extensions — accept pytest's defaults so generic CI dashboards (GitHub Actions, Jenkins, etc.) can ingest without config.
- HTML reports / `pytest-html` integration — JUnit XML is the contract; HTML is operator preference and out of v1.1.
- JSON output formats — explicitly noted in PROJECT.md "What NOT to use" / "JSON / JUnit output formats — pytest default terminal output is enough" before Phase 09; JUnit XML is the v1.1 deliverable, JSON deferred.
- Per-tool failure-rate trending logic — that's a CI-side concern (the dashboard ingests the JUnit and computes trends). Phase 09 just emits the data.
- xdist / parallel execution — v1.2 (SEED-002).
- README / docs — Phase 10 (DOC-04..07).
- New requirements beyond OUTPUT-01..03 — phase boundary is fixed.

</domain>

<decisions>
## Implementation Decisions

### `--junit-xml` flag surface

- **D-01:** `mcp-test-framework run` gains an explicit `--junit-xml=PATH` Typer option that translates internally to pytest's `--junitxml=PATH` (note pytest's spelling has no dash). The existing extras-passthrough (`run -- --junitxml=PATH`, Phase 5 D-cli-flags-1) **stays preserved** as an escape hatch; both surfaces produce the same pytest invocation. Rationale: explicit flag for CI engineer discoverability (the README snippet copy-pastes a single invocation), passthrough for forward-compat with other pytest flags users may want.
- **D-01a:** When BOTH the explicit `--junit-xml=PATH` flag AND a passthrough `--junitxml=...` are supplied, the passthrough wins (last-occurrence rule in pytest's argparse). The explicit flag adds the equivalent argument BEFORE the passthrough args, so the user's later override takes effect. Document this precedence in the `--help` text but do NOT add cross-flag validation — pytest's own duplicate handling is sufficient.
- **D-01b:** Spelling: the public CLI flag is `--junit-xml` (with the dash, matching ROADMAP success criterion #1 wording: `--junit-xml=results.xml`). Internally we translate to pytest's `--junitxml` (no dash, pytest convention). Document the spelling difference once in `--help` so operators don't get tripped up.

### Per-tool summary mechanism (OUTPUT-03)

- **D-02:** The per-tool summary lives in a new pytest plugin module: `src/mcp_test_framework/_reporter.py`. It is registered via the existing `pytest_plugins` chain in `tests/conftest.py` (parallel to `mcp_test_framework.fixtures`, sibling pattern). Mechanism: subscribe to `pytest_runtest_logreport` to accumulate per-tool outcomes during the run, then emit the summary in `pytest_terminal_summary`. Live state — no JUnit XML re-parse, no extra parser dep, no decoupling from pytest internals.
- **D-02a:** Tool-name extraction from test IDs uses the parametrize ID convention from Phase 07 (`<test_name>[<tool_name>]`). The plugin parses the bracketed suffix from `report.nodeid`. Tests WITHOUT the `[...]` suffix (e.g. unit tests in `tests/unit/`) are excluded from the per-tool summary entirely — they don't have a tool affinity. CI engineers running `mcp-test-framework run` see only the multi-tool surface.
- **D-02b:** Module placement under `src/` (NOT `tests/`) is deliberate: the plugin ships with the framework, gets discovered when the package is installed in any project, and is testable via standard `uv run pytest` against `tests/` rather than living as a test-only conftest hook. Underscore prefix signals "internal — public surface is the rendered output, not the API".
- **D-02c:** The plugin emits to `terminalreporter` (the pytest fixture for the terminal section), NOT raw `print(...)` / `sys.stdout.write(...)`. This keeps formatting consistent with the rest of pytest's section dividers and respects `-q` / `--quiet` modes (the framework's per-tool summary is INFO-level — visible by default, suppressed under `-q`).

### Per-tool aggregate verdict rule (OUTPUT-03 row state)

- **D-03:** Strict any-fail-wins. Aggregation algorithm per tool:
  1. If any test for the tool has outcome `failed` or `error` → row state is `FAIL`.
  2. Else if any test has outcome `passed` → row state is `PASS`.
  3. Else → row state is `SKIP` (all tests were skipped).
  Matches the ROADMAP success criterion #3 wording verbatim (`<tool_name>: PASS|FAIL|SKIP — <reason if skip>`). No 4th bucket.
- **D-03a:** "any failed/errored" includes pytest's `error` outcome (collection failures, fixture-setup errors). They collapse into `FAIL` in the per-tool summary because the user-facing distinction is "this tool's coverage is broken" — not "the framework had a fixture issue at this tool". The granular `<error>` vs `<failure>` distinction is preserved in the JUnit XML for CI dashboards that want it (see CD-02).
- **D-03b:** When state is `PASS`, no reason text. When `FAIL`, no reason text on the summary row (the failure reasoning lives in pytest's standard FAILURES section above the summary — duplicating it here would be noise). Reason text is rendered ONLY for `SKIP` rows per D-05.

### Summary on/off

- **D-04:** Per-tool summary is **always-on** in `mcp-test-framework run`'s terminal output. No toggle, no flag. Rationale: it's the value-prop of OUTPUT-03; CI logs are grep-friendly; adding a flag for "show me this useful thing" creates discoverability tax. Operators who want pytest's raw output without the section can already invoke `uv run pytest tests/` directly (the plugin is registered through `tests/conftest.py`'s `pytest_plugins` chain — bypassing the framework CLI bypasses it too).
- **D-04a:** The summary section appears in the terminal section sequence after `pytest_terminal_summary`-time built-ins (FAILURES, ERRORS, summary line) — pytest_terminal_summary hook order makes this natural. It does NOT appear in the JUnit XML (XML is per-test detail; the summary is human-readable aggregation).
- **D-04b:** Under `-q` / `--quiet`, the per-tool summary is suppressed (matches pytest convention — quiet means SUMMARY-LINE only, no extra sections). Under `-v`, behavior is identical to default. Under `-s`, behavior is identical to default.

### Skip-reason rendering

- **D-05:** When a tool's row state is `SKIP`, the rendered reason text is built as follows:
  1. Collect all `report.longrepr` skip-reason strings for the tool's skipped tests.
  2. De-duplicate while preserving first-seen order.
  3. If exactly one distinct reason: render `<tool>: SKIP — <that reason>`.
  4. If multiple distinct reasons: render `<tool>: SKIP — <reason1>; <reason2>; ...` (semicolon-space separator).
  Rationale: Phase 08 D-16's required-non-empty-`skip_reason` validator means every skipped test has a reason; for Phase 08 config-skipped tools all 10 tests share the same reason (single — first-seen suffices). For tools with mixed reasons (e.g. `list_keyring_credentials`: 8 PASS + 2 judge-subset SKIPs with `judge 'disambiguation' not selected for tool ...` reason) the `;`-joined form surfaces both kinds of skip explicitly. Cap to first 3 distinct reasons; if more, append `; ... (N more)` to keep rows scannable.
- **D-05a:** Reason text is rendered VERBATIM from `pytest.skip(reason=...)` — no truncation, no quoting, no normalization. The Phase 08 reasons are operator-authored and meant to be readable; the plugin does not transform them.

### Inherited locks (do NOT re-decide)

- **L-01:** Per-tool test IDs already render as `<test_name>[<tool_name>]` in BOTH terminal and JUnit XML output via Phase 07's `pytest_generate_tests` hook (`tests/conftest.py:124-136`). This satisfies OUTPUT-02 with **zero new code** — the JUnit reporter pytest ships with picks up the parametrized IDs natively. Phase 09 work for OUTPUT-02 is verification + a reference snippet in tests, NOT implementation.
- **L-02:** `pytest.skip(reason=...)` is the universal skip mechanism (Phase 08 D-09). Skip reasons reach the JUnit XML through pytest's standard `<skipped message="..." type="pytest.skip">` element automatically. Phase 09 reads them out of `report.longrepr` for the terminal summary; XML emission is automatic.
- **L-03:** `cli.py:run` uses `pytest.main(["tests", *forwarded])` with NO try/except wrap (Phase 5 D-cli-flags-3). Phase 09's `--junit-xml=PATH` flag MUST preserve this contract — it adds the argument to the forwarded list, doesn't wrap or intercept. Same goes for the `pytest.main()` exit code propagation.
- **L-04:** `pytest` is a dev-only dependency, function-local import inside `cli.py:run` (cli.py:127). Phase 09's `--junit-xml` flag handler stays inside the `run` function body — it does NOT pull pytest into module-scope.
- **L-05:** Markers `live_homelab` + `live_ollama` are already declared in `pyproject.toml`'s `[tool.pytest.ini_options].markers` (Phase 04/05) and the default `addopts = "-m 'not live_homelab and not live_ollama'"` excludes them. Phase 09 does NOT alter marker semantics — `--junit-xml=PATH` produces a JUnit file containing the same test set the run executed (live tests excluded by default in CI; visible if user opts in via `-m live_homelab`).
- **L-06:** Phase 08 D-09 explicitly notes "Phase 09 OUTPUT-02 free-rides" on `pytest.skip(reason=...)` — confirming the design call from Phase 08 that the skip mechanism flows through whatever reporter is active. This is the contract Phase 09 builds on; no changes to Phase 08's skip/judges-subset guard placement.

### Claude's Discretion

- **CD-01:** JUnit XML output customization — accept pytest's defaults. `<skipped message="..." type="pytest.skip">` for `pytest.skip()` calls; `<testcase classname="tests.test_mcp_tool_contract" name="test_X[<tool>]">` for parametrized tests; `<failure>` for assertion failures; `<error>` for fixture/collection errors. CI dashboards (GitHub Actions's `dorny/test-reporter`, Jenkins's `JUnit Plugin`, GitLab) all consume this default shape natively. NO `<properties>` extensions, NO custom `pytest_collection_modifyitems` reordering for XML output. Verifier task: confirm a sample XML file produced by `--junit-xml=results.xml` is well-formed against the JUnit XSD that GitHub Actions consumes.
- **CD-02:** Error vs Fail bucketing — terminal summary collapses `error` outcomes into `FAIL` (matches ROADMAP's `PASS|FAIL|SKIP` literal three-bucket vocabulary). The JUnit XML preserves the granular `<error>` vs `<failure>` distinction (pytest emits both natively). Operators who care about the distinction read the XML; the terminal summary stays scannable.
- **CD-03:** Per-tool summary row ordering — group by status: `FAIL` rows first (alphabetical within), then `SKIP` (alphabetical within), then `PASS` (alphabetical within). Rationale: failures need triage attention, skips are informational, passes are the bulk and least interesting per-row. Header line above the table notes the grouping (`failures (alphabetical) → skipped (alphabetical) → passing (alphabetical)`).
- **CD-04:** Plan-cut within the phase. Likely shape: P1 — `--junit-xml` Typer flag wiring (cli.py only; smallest change; verifies OUTPUT-01); P2 — `_reporter.py` plugin + `tests/conftest.py` registration + tool-name extraction + verdict rule + skip-reason rendering (the OUTPUT-03 build); P3 — verification tests for both surfaces (a fixture YAML run + sample XML inspection + sample terminal output snapshot test). Planner picks; the dependency edge is `--junit-xml` flag → plugin → tests, but P1 and P2 could parallelize since they touch disjoint files.
- **CD-05:** Naming of the plugin module. Options: `_reporter.py`, `_per_tool_reporter.py`, `_pytest_plugin.py`. Planner picks the cleanest fit — `_reporter.py` is shortest and accurate (it IS a pytest reporter plugin); `_per_tool_reporter.py` is more searchable but longer. Either works; `_pytest_plugin.py` is too generic.
- **CD-06:** Where the `--junit-xml` flag's translation to `--junitxml` happens — three viable spots:
  1. Inside the `run` function body before `pytest.main()` is called (build the args list with `--junitxml=PATH` prepended)
  2. As a Typer callback that munges the argument
  3. As a small helper `_build_pytest_args(config, junit_xml, pytest_args)` extracted for testability
  Planner picks based on testability needs. Recommendation lean: option 3 (helper) — it isolates the translation logic so unit tests can assert on the resulting argv without spawning pytest.

### Folded Todos

None. The pending todo `2026-05-07-v1-1-isolate-test-runs-from-user-state.md` is a stale artifact from before Phase 06 shipped (ISOL-01..07 all verified) — it should be moved to `.planning/todos/completed/` independently, not folded here. The unresolved debug session `fixture-teardown-cancel-scope.md` is a Phase 04.1 artifact that should similarly migrate to `.planning/debug/resolved/` — out of scope for Phase 09 but worth a cleanup pass before Phase 10.

</decisions>

<specifics>
## Particular references

- **JUnit XML target:** standard pytest output (`--junitxml=PATH`) — no custom schema. Reference: pytest docs `https://docs.pytest.org/en/stable/how-to/output.html#creating-junitxml-format-files`.
- **CI ingestion examples** (Phase 10 will document, Phase 09 just verifies the file is well-formed):
  - GitHub Actions: `dorny/test-reporter@v1` with `reporter: java-junit`
  - Jenkins: built-in JUnit Plugin
  - GitLab: `artifacts.reports.junit` field in `.gitlab-ci.yml`
- **Sample output target shape** (D-03 verdict + D-05 skip reason rendering applied to current Phase 08 live run):
  ```
  ============= per-tool summary =============
  failures:
    suggest_deployments       FAIL
  skipped:
    analyze_network_topology  SKIP — requires live homelab infrastructure
    bulk_discover_and_map     SKIP — side effects on homelab inventory: bulk discovery writes
    [...54 more SKIP rows...]
    list_keyring_credentials  SKIP — judge 'disambiguation' not selected for tool 'list_keyring_credentials'; judge 'parameters' not selected for tool 'list_keyring_credentials'
    list_registered_servers   SKIP — Description does not pass disambiguation rubric; tracked for upstream homelab-mcp doc fix.
  passing:
    suggest_deployments       PASS
  =============================================
  ```
  Note: `list_keyring_credentials` shows up as SKIP (per D-03 — all 8 of its non-skipped tests were PASS, but if 8 PASS + 2 SKIP, the verdict is PASS by D-03 rule 2 — re-evaluate sample). Concrete numbers: it has 4 PASS schema + 1 PASS clarity judge + 0 disambiguation/parameters (skipped via judge guard) + 3 PASS call_tool = **8 PASS + 2 SKIP → PASS** per D-03 rule 2. Sample above corrected:
  ```
  passing:
    list_keyring_credentials  PASS
    suggest_deployments       PASS  (NOTE: currently FAIL until upstream fixes disambiguation rubric per Phase 08 retained failure)
  ```
- **Test fixture for Phase 09 verification:** the existing Phase 08 retained failure (`test_description_disambiguation[suggest_deployments]`) is the canonical real-world `<failure>` example. Phase 09 verifier reads the JUnit XML emitted from a live run, confirms the `<failure>` element exists with the expected nodeid, classname, and message — no need to contrive a synthetic failing test.

</specifics>

<canonical_refs>
## Canonical refs

These docs are the source of truth for Phase 09 decisions. Researcher and planner MUST read each one before producing RESEARCH.md / PLAN.md respectively.

| Path | Why it's canonical |
|---|---|
| `.planning/ROADMAP.md` (Phase 09 entry, lines ~for "JUnit XML output") | Phase goal + 3 success criteria + dependencies |
| `.planning/REQUIREMENTS.md` (OUTPUT-01..03) | Requirement IDs with normative wording |
| `.planning/PROJECT.md` ("JSON / JUnit output formats" deferred-list entry) | Confirms JUnit XML is the only output format for v1.1; JSON is explicitly out |
| `src/mcp_test_framework/cli.py` (especially `run` at lines ~98-131) | The Typer command Phase 09 extends; preserves D-cli-flags-3 no-wrap contract |
| `tests/conftest.py` (especially `pytest_generate_tests` at lines ~124-136) | The Phase 07 hook that emits `[<tool_name>]` IDs Phase 09 reads |
| `.planning/phases/07-multi-tool-discovery-and-parameterized-testing/07-01-SUMMARY.md` | Phase 07 record of how parametrize IDs were chosen and what they look like in the JUnit XML |
| `.planning/phases/08-per-tool-config-registry/08-CONTEXT.md` (D-09) | Confirms `pytest.skip(reason=...)` flows through the active reporter — the contract Phase 09 builds on |
| `.planning/phases/08-per-tool-config-registry/08-02-SUMMARY.md` | Skip-reason format produced by the Phase 08 runtime (used in D-05 sample output above) |
| `tests/test_mcp_tool_contract.py` (current Phase 08 modified state) | The test surface whose outcomes Phase 09 aggregates per-tool |
| pytest docs: `pytest_terminal_summary`, `pytest_runtest_logreport` hooks | The plugin API D-02 builds on |
| pytest docs: `--junitxml` and JUnit XML structure | The format OUTPUT-01 emits |

</canonical_refs>

<deferred>
## Deferred ideas (out of Phase 09 scope)

- **HTML report** — `pytest-html` integration would give operators a richer offline view than terminal output. Out of v1.1 scope. Could be an SEED idea for v1.2+ if operator demand surfaces.
- **JSON output format** — Explicitly NOT in v1.1 per PROJECT.md "What NOT to use". JUnit XML covers the CI ingestion path; JSON would be redundant.
- **Per-tool failure-rate trending** — A dashboard concern. Phase 09 emits the data; trend computation is the CI side's job.
- **Custom JUnit XML extensions** (`<properties>`, classname rewriting, custom `<system-out>` injection) — accept pytest defaults so generic CI dashboards consume without config. Would be a v2 concern if a specific dashboard requires it.
- **Pretty terminal colors / Rich integration** — the per-tool summary is plain text by default. pytest's existing color machinery (red FAIL / yellow SKIP / green PASS) flows through naturally if `terminalreporter.write_sep(...)` and `terminalreporter.write_line(..., red=True)` are used; planner verifies. NO explicit `rich` dep.
- **Configurable summary location** (above vs below pytest's standard FAILURES section) — accept pytest's `pytest_terminal_summary` natural ordering. Operator preference; not v1.1 scope.
- **Parallelism (xdist) per-tool aggregation correctness** — v1.2 (SEED-002). The current per-tool plugin design is single-process safe; xdist's per-worker reports would need a coordinator. Phase 09 does NOT need to handle this; v1.2 will revisit.

</deferred>
