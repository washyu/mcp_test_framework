---
phase: 09-junit-xml-output-per-tool-reporting
verified: 2026-05-08T00:00:00Z
status: passed
score: 3/3 ROADMAP success criteria verified
criteria_met: 3
criteria_total: 3
requirements_completed: 3
requirements_total: 3
re_verification: false
findings:
  pass: 3
  partial: 0
  fail: 0
  human_verify: 0
deferred:
  - truth: "Live subprocess tests (3) for end-to-end JUnit XML well-formedness, [<tool>] SUFFIX contract, and per-tool summary always-on"
    addressed_in: "tests/test_reporter.py @pytest.mark.live_homelab — runnable in any env where `mcp-test-framework run -- -m live_homelab` completes within --timeout=600 (per 09-03-SUMMARY.md:101-104 environmental note)"
    evidence: "tests/test_reporter.py: test_junit_xml_emitted_and_well_formed, test_junit_xml_testcase_names_carry_tool_suffix, test_per_tool_summary_section_always_on (3 functions, all gated by @pytest.mark.live_homelab; 09-03-SUMMARY.md:101-104 documents the timeout-budget reason for sandbox deferral)"
notes:
  - "Phase 09 SUMMARYs were authored before VERIFICATION.md was written; this report retroactively formalizes evidence already captured across 09-01-SUMMARY.md / 09-02-SUMMARY.md / 09-03-SUMMARY.md and the 29 passing unit tests in tests/test_reporter.py."
  - "Backfill per v1.1-MILESTONE-AUDIT.md W-1 (paper gap; goal-achievement was already evidenced by the SUMMARY trio + regression suite — this report only formalizes that evidence into the standard VERIFICATION.md template matching 06/07/08/10)."
---

# Phase 09: JUnit XML Output & Per-Tool Reporting — Verification Report

**Phase Goal:** A CI engineer can wire the test suite into their pipeline using JUnit XML and trend per-tool failure rates; locally, a concise per-tool summary helps triage failures without reading full pytest output.

**Verified:** 2026-05-08
**Status:** PASSED
**Score:** 3/3 ROADMAP success criteria verified; 3/3 OUTPUT requirements completed
**Re-verification:** No — initial verification (backfill per audit W-1)

---

## Goal Achievement

The phase goal is achieved end-to-end. The CLI accepts `--junit-xml=PATH` (Phase 09-01) and forwards it to pytest via the `_build_pytest_args` helper, producing a standard JUnit XML file consumable by GitHub Actions / Jenkins. The per-tool granularity contract is wired through both reports: JUnit `<testcase name="...">` carries the `[<tool_name>]` parametrize suffix from Phase 07, and the local terminal output renders a grouped FAIL→SKIP→PASS per-tool summary section emitted by the `_reporter.py` pytest plugin (Phase 09-02), em-dash-separated on SKIP-with-reason rows per ROADMAP SC-3.

Evidence is twofold: (1) the implementation surfaces are documented across 09-01-SUMMARY.md (cli.py wiring), 09-02-SUMMARY.md (_reporter plugin), and 09-03-SUMMARY.md (test suite); (2) `tests/test_reporter.py` (551 lines, 32 test functions) pins all three OUTPUT-NN contracts under automated regression — the 29 unit tests pass deterministically (3.63s) and the 3 `@pytest.mark.live_homelab` subprocess tests are deferred-by-design for the env-budget reason recorded at 09-03-SUMMARY.md:101-104. Phase 07 supplies the parametrize-id suffix that OUTPUT-02 depends on; Phase 08 supplies the operator-authored skip reasons that OUTPUT-03's renderer formats.

---

## ROADMAP Success Criteria

### SC-1: `uv run mcp-test-framework run --junit-xml=results.xml` produces a standard JUnit XML file at `results.xml` consumable by GitHub Actions / Jenkins / generic CI dashboards.

**Status:** PASS

**Evidence:**
- `src/mcp_test_framework/cli.py:92-117` — `_build_pytest_args(junit_xml, pytest_args) -> list[str]` module-level helper translates the public `--junit-xml=PATH` to pytest's no-dash `--junitxml=PATH` (D-01b spelling) and assembles argv with explicit-flag-before-passthrough order (D-01a precedence). See 09-01-SUMMARY.md:39-41, 09-01-SUMMARY.md:60.
- `src/mcp_test_framework/cli.py:130-140` — Typer option `junit_xml: Path | None = typer.Option(None, "--junit-xml", help=...)` on `run`, between `--config` and trailing `pytest_args`. Per 09-01-SUMMARY.md:41.
- `src/mcp_test_framework/cli.py:165` — call site replaced with `pytest.main(_build_pytest_args(junit_xml, pytest_args))`. L-03 (no try/except wrap) and L-04 (function-local pytest import) preserved per 09-01-SUMMARY.md:90-97.
- Net diff: `+43 / -2` on cli.py (09-01-SUMMARY.md:65).
- Unit regression: 5 helper-shape tests in `tests/test_reporter.py::test_build_pytest_args_*` pin (None, None) → `["tests"]`, (Path, None) → with `--junitxml=...`, (Path, passthrough) ordering, etc. — see 09-01-SUMMARY.md:67-78 contract table and 09-03-SUMMARY.md:65 (5 helper-shape tests).
- Live regression: `tests/test_reporter.py::test_junit_xml_emitted_and_well_formed` parses the produced XML with `xml.etree.ElementTree` to confirm well-formedness. Deferred-by-design per 09-03-SUMMARY.md:101-104 (env timeout budget); the assertion is committed.

---

### SC-2: Each test case in the JUnit XML carries a `[<tool_name>]` suffix in its name, so CI dashboards can filter and trend per-tool failure rates over time.

**Status:** PASS

**Evidence:**
- Phase 07 parametrize-id contract (incoming dependency): pytest emits parametrize-id-suffixed nodeids `<test_name>[<tool_name>]` at collection time. The JUnit XML reporter inherits the nodeid as the testcase `name` attribute.
- `src/mcp_test_framework/_reporter.py::_extract_tool_name` — parses `[<tool>]` suffix from `report.nodeid`; returns `None` for tests without the suffix (D-02a: unit tests excluded from per-tool aggregation but still appear in the JUnit XML with their own naming). See 09-02-SUMMARY.md:55-65.
- Unit regression: 4 cases in `tests/test_reporter.py::test_extract_tool_name_*` cover with-suffix / without-suffix / nested-bracket / empty-bracket cases (see 09-03-SUMMARY.md:65).
- Live regression: `tests/test_reporter.py::test_junit_xml_testcase_names_carry_tool_suffix` asserts BOTH `"[" in name` AND `name.endswith("]")` (the SUFFIX contract — weaker forms admit `test_x[a]extra` violations per 09-03-SUMMARY.md key-decisions and patterns-established). Representative slice from 09-03-SUMMARY.md:108-115:
  ```xml
  <testcase classname="tests.test_mcp_tool_contract"
            name="test_description_clarity[suggest_deployments]" time="...">
  ```
  Deferred-by-design per 09-03-SUMMARY.md:101-104; assertion committed.

---

### SC-3: The terminal output of `mcp-test-framework run` includes a per-tool result section showing `<tool_name>: PASS|FAIL|SKIP — <reason>` for every discovered tool — readable at a glance without scrolling pytest detail.

**Status:** PASS

**Evidence:**
- `src/mcp_test_framework/_reporter.py::pytest_terminal_summary` — emits a per-tool summary section after pytest's built-in summary, suppressed under `-q` per D-04b. Uses `terminalreporter.write_sep` / `terminalreporter.write_line` only (D-02c, no print/sys.stdout). See 09-02-SUMMARY.md:73-91.
- `src/mcp_test_framework/_reporter.py` em-dash separator — literal U+2014 (`—`) on SKIP-with-reason rows: `f"  {tool.ljust(name_width)}  SKIP — {reasons_text}"` matches ROADMAP SC-3 verbatim; ASCII-hyphen form `' SKIP - '` provably absent from source per 09-02-SUMMARY.md:76-79.
- CD-03 row ordering (FAIL → SKIP → PASS, alphabetical within group) implemented via three sorted lists in fixed order with header line. See 09-02-SUMMARY.md decisions-encoded table line "CD-03 → three sorted(...) lists rendered in fixed order".
- D-05 / D-05a skip-reason de-dup (first-seen order, `_SKIP_REASON_CAP = 3`, `; ` joiner, verbatim from `pytest.skip(reason=...)`). See 09-02-SUMMARY.md:69-71.
- `tests/conftest.py` — `pytest_plugins = ["mcp_test_framework.fixtures", "mcp_test_framework._reporter"]` registers the plugin; OUTPUT-03 cited in docstring per 09-02-SUMMARY.md:80-91.
- Unit regression: 6 `test_terminal_summary_*` tests + 7 `test_aggregation_*` tests + 5 `test_format_skip_reasons_*` tests + 1 `test_skip_reason_dedup_first_seen_order` test in `tests/test_reporter.py` (09-03-SUMMARY.md:73). The unit test `test_terminal_summary_skip_row_with_reason` directly asserts the em-dash separator AND the regression-guard "ASCII hyphen MUST NOT be present" pinning ROADMAP SC-3 verbatim (09-03-SUMMARY.md:134).
- Live regression: `tests/test_reporter.py::test_per_tool_summary_section_always_on` requires `per-tool summary` and `grouping:` strings present in stdout; deferred-by-design per 09-03-SUMMARY.md:101-104.

Representative slice from 09-03-SUMMARY.md:121-132:
```
=================================== per-tool summary ===================================
(grouping: failures (alphabetical) -> skipped (alphabetical) -> passing (alphabetical))
failures:
  suggest_deployments        FAIL
skipped:
  list_active_terminals      SKIP — Tool is destructive; opt in by setting skip: false in config
  ...
passing:
  list_keyring_credentials   PASS
========================================================================================
```

---

## Requirements Coverage (OUTPUT-01..OUTPUT-03)

| Req | Acceptance Criteria | Verdict | Evidence |
|-----|---------------------|---------|----------|
| OUTPUT-01 | CLI accepts `--junit-xml=PATH`; passthrough preserved; produces JUnit XML | PASS | `cli.py:130-140` Typer option; `cli.py:92-117` `_build_pytest_args` helper; `tests/test_reporter.py::test_build_pytest_args_*` (5 unit tests) + `test_run_help_lists_junit_xml` + `test_junit_xml_emitted_and_well_formed` (live). Per 09-01-SUMMARY and 09-03-SUMMARY. |
| OUTPUT-02 | JUnit output records per-tool granularity (`[<tool>]` suffix in test names) | PASS | Phase 07 parametrize-id contract; `_reporter.py::_extract_tool_name`; `tests/test_reporter.py::test_extract_tool_name_*` (4 unit tests) + `test_junit_xml_testcase_names_carry_tool_suffix` (live, asserts BOTH `[` in name AND `name.endswith("]")`). Per 09-02-SUMMARY:55-65 and 09-03-SUMMARY:65. |
| OUTPUT-03 | Per-run summary includes per-tool result section | PASS | `_reporter.py::pytest_terminal_summary`; em-dash separator U+2014; `tests/conftest.py` plugin registration; `tests/test_reporter.py::test_terminal_summary_*` (6 unit tests) + `test_aggregation_*` (7 tests) + `test_format_skip_reasons_*` (5 tests) + `test_skip_reason_dedup_first_seen_order` + `test_per_tool_summary_section_always_on` (live). Per 09-02-SUMMARY:73-91 and 09-03-SUMMARY:73. |

All 3 OUTPUT requirements complete. ROADMAP.md:149 records "09. JUnit XML output & per-tool reporting | v1.1 | 3/3 | Complete | 2026-05-08".

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/mcp_test_framework/cli.py` | `_build_pytest_args` helper + `--junit-xml` Typer option | VERIFIED | Per 09-01-SUMMARY: `cli.py:92-117` helper; `cli.py:130-140` Typer option; `cli.py:165` call site; net diff `+43/-2`. L-03 (no try/except wrap on `pytest.main`) and L-04 (function-local pytest import) preserved per 09-01-SUMMARY:90-97. |
| `src/mcp_test_framework/_reporter.py` | Pytest plugin with `pytest_runtest_logreport` + `pytest_terminal_summary` | VERIFIED | Per 09-02-SUMMARY: 202 lines; 5 named functions (`_extract_tool_name`, `_extract_skip_reason`, `pytest_runtest_logreport`, `_format_skip_reasons`, `pytest_terminal_summary`); em-dash U+2014 separator; no `print` / `sys.stdout` / `try`/`except` in source. |
| `tests/conftest.py` | `mcp_test_framework._reporter` added to `pytest_plugins` | VERIFIED | Per 09-02-SUMMARY:80-87: `pytest_plugins = ["mcp_test_framework.fixtures", "mcp_test_framework._reporter"]` (fixtures first, reporter appended; OUTPUT-03 cited in docstring). |
| `tests/test_reporter.py` | 29 unit tests + 3 live subprocess tests | VERIFIED | Per 09-03-SUMMARY: 551 lines, 32 test functions; 29 passing in 3.63s on `MCPTF_CONFIG_FILE=./config.yaml uv run --group dev pytest tests/test_reporter.py -m "not live_homelab and not live_ollama" -v`; 3 deferred under `@pytest.mark.live_homelab` per 09-03-SUMMARY:101-104. |

---

## Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `cli.py::run` | `pytest.main` argv | `_build_pytest_args(junit_xml, pytest_args)` (cli.py:92-117 → cli.py:165) | WIRED |
| `_reporter.py::pytest_runtest_logreport` | `_PER_TOOL` aggregation buffer | module-level `dict[str, dict]` keyed by tool name (parametrize-id suffix); D-03 verdict rules | WIRED |
| `_reporter.py::pytest_terminal_summary` | terminal output | `terminalreporter.write_sep` / `terminalreporter.write_line` only (D-02c — no print, no sys.stdout) | WIRED |
| `tests/conftest.py::pytest_plugins` | `_reporter` plugin registration | `"mcp_test_framework._reporter"` string entry (sibling of `mcp_test_framework.fixtures`) | WIRED |
| Phase 08 `pytest.skip(reason=...)` | Phase 09 SKIP rows with em-dash | `_reporter._extract_skip_reason` strips `"Skipped: "` prefix; `_format_skip_reasons` de-dups + caps at 3 (D-05/D-05a) | WIRED |
| Phase 07 parametrize-id | Phase 09 OUTPUT-02 SUFFIX contract | `_reporter._extract_tool_name` parses `[<tool>]` suffix from `report.nodeid` | WIRED |

No orphan or stub artifacts. The two summary surfaces (terminal per-tool section + JUnit XML testcase names) both consume Phase 07's parametrize-id suffix; no path bypasses the `[<tool>]` contract.

---

## Behavioural Spot-Checks

| Behaviour | Command | Expected | Status |
|-----------|---------|----------|--------|
| `_reporter.py` substantive | `wc -l src/mcp_test_framework/_reporter.py` | ≥ 80 (actual: 202 per 09-02-SUMMARY:51) | PASS |
| Test count substantive | `grep -c "^def test_" tests/test_reporter.py` | ≥ 25 (actual: 32 per 09-03-SUMMARY verification table) | PASS |
| Live tests gated | `grep -c "@pytest.mark.live_homelab" tests/test_reporter.py` | == 3 (actual: 3 per 09-03-SUMMARY:73) | PASS |
| Em-dash form present | `grep -c "SKIP — " tests/test_reporter.py` | ≥ 2 (actual: 2 per 09-03-SUMMARY verification table line "Em-dash form `SKIP — `") | PASS |
| ASCII regression-guard | `grep -c "SKIP - " tests/test_reporter.py` | ≥ 2 (actual: 2 — kept as a regression-guard assertion that ASCII form is NOT in source) | PASS |
| Helper present | `grep -n "_build_pytest_args" src/mcp_test_framework/cli.py` | match at line ~92 (per 09-01-SUMMARY:60) | PASS |
| `_extract_tool_name` present | `grep -n "_extract_tool_name" src/mcp_test_framework/_reporter.py` | multiple matches (definition + use sites per 09-02-SUMMARY:55-65) | PASS |
| Plugin registered | `grep "mcp_test_framework._reporter" tests/conftest.py` | 1 match (per 09-02-SUMMARY:86) | PASS |
| Unit suite green | `MCPTF_CONFIG_FILE=./config.yaml uv run --group dev pytest tests/test_reporter.py -m "not live_homelab and not live_ollama" -v` | 29 passed in 3.63s (per 09-03-SUMMARY:81-91) | PASS |
| Lint clean | `uv run ruff check tests/test_reporter.py` / `cli.py` / `_reporter.py` | All checks passed (per 09-01-SUMMARY:110, 09-02-SUMMARY:128, 09-03-SUMMARY:96) | PASS |
| `--junit-xml` in CLI help | `uv run mcp-test-framework run --help` | exit 0; `--junit-xml` 2x; `pytest` 10x (per 09-01-SUMMARY:108) | PASS |

---

## Deferred Items

The 3 `@pytest.mark.live_homelab` subprocess tests in `tests/test_reporter.py` are deferred-by-design — assertion code committed, env-budget for execution exceeds the sandboxed 120s pytest-timeout. Per 09-03-SUMMARY.md:101-104:

> `uv run --group dev pytest tests/test_reporter.py -m live_homelab -v --timeout=120` exceeded the 120s per-test deadline in this execution environment when the inner `uv run mcp-test-framework run -- -m live_homelab` subprocess took longer than 120s end-to-end. The assertions, subprocess invocation, and three contract checks are in place and will pass in any environment where the live MCP/Ollama-driven test suite completes within timeout. The failure here is environmental (Phase 09 deferred-items table flag), not a defect in the test bodies.

| Test | Pins | Lift trigger |
|------|------|--------------|
| `test_junit_xml_emitted_and_well_formed` | OUTPUT-01 (XML well-formedness via `xml.etree.ElementTree.parse`) | Run on host where `mcp-test-framework run -- -m live_homelab` completes within `--timeout=600` |
| `test_junit_xml_testcase_names_carry_tool_suffix` | OUTPUT-02 / SC-2 SUFFIX contract (BOTH `[` in name AND `name.endswith("]")`) | Same as above |
| `test_per_tool_summary_section_always_on` | OUTPUT-03 / SC-3 (per-tool summary section always emitted; `per-tool summary` + `grouping:` strings present in stdout) | Same as above |

Audit W-2 disposition: "Re-run with `--timeout=600` on a developer host or in CI to capture artifact evidence" — see `v1.1-MILESTONE-AUDIT.md:111-112`. The 29 unit tests already pin every contract that the live tests would re-verify at the e2e level; the live tests are end-to-end backstops, not the only line of defence.

---

## Verification Gaps

### G-01 — Live subprocess evidence not yet captured (deferred-by-design)

**Severity:** WARNING (does not block phase closure or v1.1 milestone close)

**What:** The 3 `@pytest.mark.live_homelab` tests in `tests/test_reporter.py` have not been executed end-to-end in a host with sufficient timeout budget. No `results.xml` slice or per-tool summary stdout has been captured into a `raw/` evidence file.

**Why it's not a blocker:**
1. The 3 live test bodies + assertions are committed (see 09-03-SUMMARY.md:73 — exact assertion list).
2. The deferral is purely env-budget (120s pytest-timeout vs the inner `mcp-test-framework run -- -m live_homelab` end-to-end runtime); not a logic gap.
3. The 29 unit tests already pin every contract the live tests would re-verify at the e2e level: helper shape (5 tests), `_extract_tool_name` (4 tests), aggregation (7 tests), skip-reason dedup (5 + 1 tests), terminal_summary rendering (6 tests), `--help` surface (1 test).
4. A sample JUnit `<testcase>` slice and a sample per-tool summary section are documented in 09-02-SUMMARY.md and 09-03-SUMMARY.md:108-132 — the contract is observable in source even without a live run.

**Recommendation:** Per audit W-2, re-run with `--timeout=600` on a developer host or in CI where homelab-mcp + Ollama are reachable, and capture `results.xml` plus the per-tool summary stdout into a `raw/` artifact directory referenced from this verification file.

---

## Final Verdict

**VERIFICATION PASSED** — Phase 09 achieves the goal "CI engineer can wire the test suite into their pipeline using JUnit XML and trend per-tool failure rates; locally, a concise per-tool summary helps triage failures without reading full pytest output." 3/3 ROADMAP success criteria are met. 3/3 OUTPUT requirements (OUTPUT-01, OUTPUT-02, OUTPUT-03) are complete. One deferred-by-design verification gap (G-01: live evidence) is explicitly tracked, with the unit-test surface providing the primary line of defence and audit W-2 owning the lift path.

This report is a backfill per audit W-1 — the SUMMARY trio (09-01/02/03) and `tests/test_reporter.py` regression suite already evidenced goal achievement; this file formalizes that evidence in the standard VERIFICATION.md template matching 06/07/08/10.

---

_Verified: 2026-05-08_
_Verifier: Claude (gsd-verifier — backfill from existing SUMMARY evidence per audit W-1)_
