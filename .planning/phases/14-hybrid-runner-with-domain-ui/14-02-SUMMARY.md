---
phase: 14-hybrid-runner-with-domain-ui
plan: 02
subsystem: cli
tags: [parser, junit-xml, xml-etree, fixtures, parametrize-id, dataclasses]

# Dependency graph
requires:
  - phase: 14-01-subprocess-spine
    provides: "src/mcp_test_framework/_runner.py module (subprocess + tempfile JUnit + exit-code map); the wrapper-owned tempfile that Plan 14-02 parses"
provides:
  - "parse_junit_xml(xml_path) -> ParsedRun: the data-transform half of RUNNER-02; stdlib xml.etree.ElementTree only, zero new deps"
  - "ParsedRun + ToolVerdict dataclasses: typed domain model consumed by the renderer in Plan 14-03"
  - "_extract_tool_name, _strip_pytest_skipped_prefix, _format_skip_reasons: aggregation helpers ported verbatim from _reporter.py before its deletion in Plan 14-05"
  - "_SKIP_REASON_CAP, _REASON_NOT_SELECTED, _REASON_EXPLICIT_DEFAULT: locked Phase 13 D-12 constants present in the new module"
  - "Four hand-written JUnit XML fixtures under tests/fixtures/: all-pass, one-fail-with-reasoning, all-skip, mixed"
  - "tests/unit/test_runner_parser.py: 24 unit tests pinning the parser against the four fixtures + synthesized aggregation cases"
affects: [14-03-domain-renderer, 14-05-reporter-cleanup]

# Tech tracking
tech-stack:
  added: []  # no new deps -- stdlib xml.etree.ElementTree + dataclasses + typing.Literal only
  patterns:
    - "Hand-written XML fixtures over live-generation (Phase 14 D-claude bullet 4): stable across pytest version bumps and test-count changes; checked in once"
    - "Dataclass domain model at parser->renderer seam: no pydantic validation needed for an internal seam where the writer (parser) is the only source"
    - "Transient aggregation tracker outside the dataclass (`_has_pass: dict[str, bool]` local to parse_junit_xml): keeps the public ToolVerdict surface clean while preserving order-independence in any-fail-wins aggregation"

key-files:
  created:
    - "tests/fixtures/junit-all-pass.xml - 3 parametrized tools [alpha], [beta], [gamma], all PASS"
    - "tests/fixtures/junit-one-fail-with-reasoning.xml - 1 PASS + 1 FAIL with <failure message='parameters 3/5: ...'> attribute"
    - "tests/fixtures/junit-all-skip.xml - 4 skipped cases pinning Phase 13 D-12 verbatim reason strings"
    - "tests/fixtures/junit-mixed.xml - FAIL/SKIP/PASS ordering + a no-bracket testcase for D-09 exclusion"
    - "tests/unit/test_runner_parser.py - 24 unit tests against the four fixtures + 4 synthesized aggregation cases"
  modified:
    - "src/mcp_test_framework/_runner.py - appended parse_junit_xml, ParsedRun, ToolVerdict, _extract_tool_name, _strip_pytest_skipped_prefix, _format_skip_reasons, _SKIP_REASON_CAP, _REASON_NOT_SELECTED, _REASON_EXPLICIT_DEFAULT (+ xml.etree.ElementTree, dataclass, Literal imports). Plan 14-01 code untouched."

key-decisions:
  - "Placed tests/unit/test_runner_parser.py under tests/unit/ (not tests/) so it bypasses the autouse _preflight session gate. Pure-data XML round-trip tests have no MCP/Ollama dependency and match the established convention in tests/unit/test_reporter.py. Plan acceptance grep targets the file CONTENT not its path; all greps satisfied at the new path. Tracked as deviation Rule 1 below."
  - "Transient `_has_pass: dict[str, bool]` local tracker (parse_junit_xml-scoped) instead of attaching `_has_pass` to ToolVerdict instances. Keeps the dataclass surface clean and pyright-friendly; consumers (renderer) never see aggregation scaffolding. Differs from the plan's `setattr/delattr` suggestion -- same aggregation semantics, cleaner type signature."
  - "Hand-written XML fixtures (NOT live-generated) per CONTEXT D-claude bullet 4. Live regeneration would drift on test-count changes and pytest-version upgrades; hand-written shape lets the parser be verified without a working homelab-mcp / Ollama. Trade-off: tests don't catch real pytest dialect drift; mitigation: tests/test_reporter.py:456-528 still round-trip-parses a live-generated XML to pin the dialect in integration tests."

patterns-established:
  - "Hand-written JUnit XML fixtures under tests/fixtures/ for pure-data parser tests: stable, no live pytest run required, easy to extend for future Phase 14/15/16 surfaces"
  - "Local aggregation tracker (vs. attribute on the public model) for transient state during a single parse pass"

requirements-completed: []  # RUNNER-02 is split across plans 02 (parser) + 03 (renderer); marking it complete is Plan 14-03's responsibility

# Metrics
duration: ~6min
completed: 2026-05-11
---

# Phase 14 Plan 02: JUnit XML Parser + Domain Model

**Ported Phase 09's per-tool aggregation algorithm (any-fail-wins, parametrize-id `[<tool_name>]` extraction, skip-reason stripping) from `_reporter.py` into a new `parse_junit_xml(path) -> ParsedRun` function on `_runner.py` -- adapted to read XML elements instead of pytest report objects. Shipped four hand-written XML fixtures and a 24-test unit suite so the parser is verified without a live pytest run. Locked Phase 13 D-12 constants preserved verbatim. No new runtime dependency.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-05-11T03:28:52Z
- **Completed:** 2026-05-11T03:35:21Z
- **Tasks:** 3 (Task 1 fixtures, Task 2 parser+model, Task 3 unit tests; Task 3 satisfied by Task 2's RED commit per Plan 14-01 precedent)
- **Files modified:** 1 production (`_runner.py` appended); 5 created (4 fixtures + 1 test file)

## Accomplishments

- **Parser delivered (Plan 14-03's input is now locked).** `parse_junit_xml(Path) -> ParsedRun` reads a JUnit XML tempfile (the one Plan 14-01's `run_pytest_subprocess` returns) and emits a typed `ParsedRun` model with per-tool `ToolVerdict` records. The renderer (Plan 14-03) consumes this verbatim.
- **Phase 09 aggregation algorithm ported (D-03 any-fail-wins, D-05 dedup+cap, D-02a parametrize-suffix extraction).** Three helpers ported verbatim from `_reporter.py`: `_extract_tool_name`, `_strip_pytest_skipped_prefix`, `_format_skip_reasons`. The XML-element-presence checks (`tc.find("failure")` / `tc.find("error")` / `tc.find("skipped")`) substitute for the v1.1 plugin's `report.failed` / `report.outcome` checks; aggregation semantics are identical.
- **Phase 13 D-12 locked constants preserved verbatim.** `_REASON_NOT_SELECTED = "not selected in config"` and `_REASON_EXPLICIT_DEFAULT = "explicit skip in config"` appear in the new module with the exact strings. Both pinned by `test_runner_skip_reason_constants_locked` regression test.
- **Four hand-written XML fixtures committed under `tests/fixtures/`.** Each is valid UTF-8 XML, parses via `xml.etree.ElementTree.parse`, and pins the regression-pin strings the plan's acceptance gates require:
  - `junit-all-pass.xml`: 3 parametrized tools all PASS, `total_time=2.45`
  - `junit-one-fail-with-reasoning.xml`: 1 FAIL with `<failure message="parameters 3/5: 'unclear param name'">` (D-08 surface)
  - `junit-all-skip.xml`: 4 SKIPs with verbatim Phase 13 D-12 strings (state-a x2, state-c x1, custom reason x1)
  - `junit-mixed.xml`: FAIL/SKIP/PASS ordering + a no-bracket case to exercise D-09 exclusion
- **24 unit tests pinning the contract.** Coverage: locked constants (2), `_extract_tool_name` cases (3 incl. nested-brackets rindex), `_strip_pytest_skipped_prefix` cases (3), `_format_skip_reasons` cases (3), fixture round-trips (8), synthesized any-fail-wins / order-independence / PASS-over-SKIP / error-as-FAIL (4), per-tool duration aggregation (1).
- **No regressions.** All 207 tests under `tests/unit/` pass, including the 11 Phase 13 D-12 reporter tests. All 18 Plan 14-01 subprocess tests still pass under the worktree config (`MCPTF_CONFIG_FILE=./config-v2-worktree.yaml`).
- **No new runtime dependency.** Stdlib `xml.etree.ElementTree`, `dataclasses`, and `typing.Literal` only. `pyproject.toml` untouched.

## Task Commits

Each task was committed atomically (TDD: test commit + implementation commit):

1. **Task 1: hand-written JUnit XML fixtures** -- `c66c2ec` (test) -- four fixtures under `tests/fixtures/` exercising all-pass, one-fail-with-reasoning, all-skip, mixed; all 9 Task 1 acceptance greps pass.
2. **Task 2 RED: failing parser tests** -- `dc719fe` (test) -- `tests/unit/test_runner_parser.py` with 24 tests that fail with `ImportError` because `ParsedRun`/`ToolVerdict`/`parse_junit_xml` do not yet exist on `_runner`.
3. **Task 2 GREEN: parser + dataclasses + ported helpers** -- `6a6ca6b` (feat) -- appended ~225 lines to `_runner.py`; all 24 RED tests turn green; all 9 Task 2 import-shape and grep acceptance criteria pass.

Task 3 (the dedicated test file) was satisfied by the Task 2 RED commit (`dc719fe`): all 24 named test functions, the locked-constant regression pins, and the `def test_` >=15 acceptance gate are met. No additional commit needed -- same pattern as Plan 14-01 Task 3.

## Files Created/Modified

### Created

- **`tests/fixtures/junit-all-pass.xml`** (8 lines) -- 3 parametrized tools `[alpha]`, `[beta]`, `[gamma]`, all PASS, `total_time="2.45"`.
- **`tests/fixtures/junit-one-fail-with-reasoning.xml`** (14 lines) -- 1 PASS `[alpha]` + 1 FAIL `[beta]` with `<failure message="parameters 3/5: 'unclear param name'">long traceback body</failure>`.
- **`tests/fixtures/junit-all-skip.xml`** (16 lines) -- 4 SKIP cases with verbatim Phase 13 D-12 strings (state-a x2, state-c x1, custom reason "hits production registry" x1).
- **`tests/fixtures/junit-mixed.xml`** (14 lines) -- `[alpha]` PASS, `[gamma]` SKIP, `[mango]` PASS, `[zoo]` FAIL, plus `test_unit_no_param` without bracket suffix (D-09 exclusion).
- **`tests/unit/test_runner_parser.py`** (281 lines, 24 tests) -- placed under `tests/unit/` (NOT `tests/`) to bypass the autouse `_preflight` session gate.

### Modified

- **`src/mcp_test_framework/_runner.py`** -- appended ~225 lines:
  - Added imports: `xml.etree.ElementTree as ET`, `dataclass` + `field` from `dataclasses`, `Literal` from `typing`.
  - Module-level constants: `_SKIP_REASON_CAP = 3`, `_REASON_NOT_SELECTED = "not selected in config"`, `_REASON_EXPLICIT_DEFAULT = "explicit skip in config"`.
  - Helpers: `_extract_tool_name`, `_strip_pytest_skipped_prefix`, `_format_skip_reasons`.
  - Domain model: `Verdict = Literal["PASS", "FAIL", "SKIP"]`, `ToolVerdict` dataclass (name/verdict/failure_message/failure_body/skip_reasons/case_count/duration), `ParsedRun` dataclass (per_tool/total_time/total_cases/total_failures/total_skipped/total_errors).
  - Parser: `parse_junit_xml(xml_path: Path) -> ParsedRun` -- handles both `<testsuites>` and bare `<testsuite>` roots; D-03 any-fail-wins; D-09 excludes testcases without `[<tool>]` suffix; D-08 separates `<failure>` `message` attribute from element body text.
  - Plan 14-01 code (lines 1-256 before this plan) was NOT touched.

## Decisions Made

1. **Test file placed at `tests/unit/test_runner_parser.py` (not `tests/test_runner_parser.py`).** The plan specifies `tests/test_runner_parser.py`, but the project's autouse `_preflight` session fixture (`fixtures.py:108-152`) gates every collection under `tests/` (non-unit) on MCP-server-on-PATH + Ollama reachability + a brief MCP handshake. These parser tests are pure-data XML round-trips with zero MCP/Ollama dependency, matching the existing `tests/unit/test_reporter.py` convention which lives under `tests/unit/` for exactly the same reason. The plan's acceptance criteria target file CONTENT (greps + `def test_` count + import smoke) not the path; all criteria are satisfied at the new path. Tracked as deviation Rule 1 below.
2. **Transient `_has_pass: dict[str, bool]` LOCAL to `parse_junit_xml` instead of `setattr/delattr` on `ToolVerdict` instances** (plan suggested the attribute approach). Same aggregation semantics; keeps the public dataclass surface clean and pyright/mypy-friendly. Consumers (the renderer in Plan 14-03) never see aggregation scaffolding.
3. **Stdlib `xml.etree.ElementTree` over a third-party XML library** (plan-locked). Pytest's JUnit dialect is shallow; the parser is one pass over a flat element tree. `junitparser` is deferred to v1.3+ if multi-XML merging (xdist) becomes a real need.
4. **Hand-written fixtures over live-generated XML** (plan-locked, CONTEXT D-claude bullet 4). Live regeneration would drift on pytest-version bumps and test-count changes. Hand-writing the four small fixtures lets the parser be verified on any developer's box without a working homelab-mcp.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug / environmental correctness] Moved `tests/test_runner_parser.py` to `tests/unit/test_runner_parser.py`**
- **Found during:** Task 2 RED commit (immediately after writing the test file, before commit).
- **Issue:** The plan specifies `tests/test_runner_parser.py`. The project's `fixtures.py:_session_needs_preflight` gates every pytest collection under top-level `tests/` (non-unit) on MCP server PATH + Ollama reachability. Pure-data XML round-trip tests cannot pass on a box without homelab-mcp / Ollama at the top-level path -- they'd be blocked by `pytest.exit(...)` in the autouse `_preflight` fixture before any test function ran. The existing `tests/unit/test_reporter.py` (Phase 13 D-12 unit tests) sets the precedent: its docstring explicitly says "These tests live HERE (tests/unit/test_reporter.py) so they skip preflight via fixtures._session_needs_preflight."
- **Fix:** Created the file at `tests/unit/test_runner_parser.py` instead. Adjusted the `_FIXTURES` path computation accordingly (`Path(__file__).resolve().parent.parent / "fixtures"` to walk up tests/unit -> tests -> fixtures). All plan acceptance criteria target file CONTENT (greps + def-count + import smoke + named test cases) -- they all pass at the new path. No content was changed; only the path.
- **Files modified:** new file at `tests/unit/test_runner_parser.py` (instead of `tests/test_runner_parser.py`).
- **Verification:** `uv run pytest tests/unit/test_runner_parser.py -v` runs all 24 tests, all pass. `grep -c "^def test_" tests/unit/test_runner_parser.py` returns 24 (>= 15 plan minimum). Phase 13 D-12 regression pins (`"not selected in config"`, `"explicit skip in config"`) present.
- **Committed in:** `dc719fe` (Task 2 RED).

---

**Total deviations:** 1 auto-fixed (Rule 1: environmental correctness -- the plan's path would have blocked the tests on every machine without a live homelab-mcp / Ollama, contradicting the plan's own behavior contract that the parser must be verified without a live pytest run).

**Impact on plan:** Zero scope creep. The plan's parser/model/test contract is delivered exactly as specified; only the test FILE path changed by one directory level. Downstream Plan 14-03 should be aware that the parser tests live at `tests/unit/test_runner_parser.py`.

## Issues Encountered

- **Worktree environment lacked the v2 schema config (same issue documented in Plan 14-01 SUMMARY).** Plan 14-01's regression suite (`tests/test_runner_subprocess.py`) requires `MCPTF_CONFIG_FILE=./config-v2-worktree.yaml` to pass on this worktree. I created a new `config-v2-worktree.yaml` (v2 schema, `command: uvx`, `args: ["homelab-mcp"]`, `model: qwen3:0.6b` matching the installed Ollama model, `tools: {}`); this file is a per-worktree convenience and remains git-untracked (NOT committed). My Plan 14-02 tests live under `tests/unit/` so they bypass this requirement entirely -- they run with zero env-var setup.
- **Pytest warning: "Module already imported so cannot be rewritten; mcp_test_framework._reporter".** Cosmetic warning that fires when `_reporter` is loaded twice (once as a plugin via conftest, once via a `from mcp_test_framework import _reporter` in a unit test). Pre-existing -- not introduced by this plan -- and goes away when Plan 14-05 deletes `_reporter.py`.

## User Setup Required

None. No external service configuration required. The `config-v2-worktree.yaml` mentioned above is a per-worktree convenience for running Plan 14-01's regression suite; Plan 14-02's tests do not require it.

## Next Phase Readiness

- **Plan 14-03 (domain renderer) unblocked.** The renderer consumes `ParsedRun` produced by `parse_junit_xml(tmp_xml)`. Plan 14-03 inserts the call between `_dispatch_default_mode_or_error` and the transitional verbatim stdout emit (marked `# PLAN-03 REMOVES` in `cli.py:run` per Plan 14-01 SUMMARY). All field shapes (`per_tool: dict[str, ToolVerdict]`, `total_time`, `total_cases`, `total_failures`, `total_skipped`, `total_errors`, `ToolVerdict.failure_message`, `ToolVerdict.skip_reasons`, `ToolVerdict.failure_body`, `ToolVerdict.duration`, `ToolVerdict.case_count`) are stable contracts.
- **Plan 14-05 (`_reporter.py` deletion) unblocked.** The three helpers ported into `_runner.py` (`_extract_tool_name`, `_strip_pytest_skipped_prefix`, `_format_skip_reasons`) plus the two locked constants (`_REASON_NOT_SELECTED`, `_REASON_EXPLICIT_DEFAULT`) plus `_SKIP_REASON_CAP` are byte-equivalent ports. Plan 14-05's deletion of `_reporter.py` will not break any of the ported logic -- only its in-pytest-process plugin role goes away.
- **Plan 14-04 (`--debug` / `-q` flags) compatible.** `ToolVerdict.failure_body` is captured separately from `failure_message` exactly so Plan 14-04 can gate body rendering behind `--debug` without touching the parser. `--debug` reads `failure_body`; default mode reads only `failure_message`.

**No blockers.** Plan 14-02 plugs into the seams Plan 14-01 left open and exposes the seams Plans 14-03 / 14-04 / 14-05 will plug into.

---
*Phase: 14-hybrid-runner-with-domain-ui*
*Completed: 2026-05-11*

## Self-Check: PASSED

- tests/fixtures/junit-all-pass.xml: FOUND
- tests/fixtures/junit-one-fail-with-reasoning.xml: FOUND
- tests/fixtures/junit-all-skip.xml: FOUND
- tests/fixtures/junit-mixed.xml: FOUND
- tests/unit/test_runner_parser.py: FOUND
- src/mcp_test_framework/_runner.py: FOUND
- .planning/phases/14-hybrid-runner-with-domain-ui/14-02-SUMMARY.md: FOUND
- c66c2ec (Task 1: fixtures): FOUND
- dc719fe (Task 2 RED: failing parser tests): FOUND
- 6a6ca6b (Task 2 GREEN: parser + dataclasses): FOUND
