---
phase: 30-cli-demotion-carry-forward-uat-closure-docs-rewrite
verified: 2026-05-19T12:00:00Z
status: gaps_found
score: 3/4 must-haves verified
overrides_applied: 0
gaps:
  - truth: "mcp-contracts run --config PATH and pytest -o mcp_config_file=PATH produce identical pass/fail signal — gated by a CI parity test"
    status: partial
    reason: >
      The parity test file exists and is structurally correct (D-01 dict equality, D-02
      config substrate, D-02a defensive assert, D-03 two subprocesses). However CR-01
      from 30-REVIEW.md identifies a real scope mismatch: Route A (CLI) internally
      defaults to tests/contract/ while Route B (raw pytest) is invoked with tests/ —
      the full suite. The {nodeid: outcome} dicts produced by these two routes are
      structurally non-comparable on any real stack run: Route B will collect all
      tests/framework/ self-tests that Route A never sees. The D-02a guard only masks
      this under the vacuous case (tools: {} empty allowlist). The CI parity test cannot
      validly close CLOSE-02 with this scope mismatch.
    artifacts:
      - path: "tests/framework/parity/test_cli_vs_pytest_route.py"
        issue: "Route B subprocess uses 'tests/' (line 114); Route A CLI internally defaults to tests/contract/ per _runner.py:145. Scope mismatch produces non-comparable outcome dicts on live stack."
    missing:
      - "Route B must target tests/contract (or the same explicit scope Route A uses) — change line 114 from 'tests/' to 'tests/contract'"
      - "Optionally: add symmetric assert outcomes_b guard (WR-01 from REVIEW.md) and compose marker expressions to include 'not live_homelab and not live_ollama' (WR-02 from REVIEW.md)"
human_verification:
  - test: "UAT-1: README test-code-scenarios PASS-sample re-capture"
    expected: "All test-code scenarios pass against live Proxmox + homelab-mcp; output matches README snapshot format with PASS rows; re-snapshot pasted into README §test-code-scenarios replacing the pre-Phase-24 FAIL block"
    why_human: "Requires live Proxmox keyring access (MCPTF_DOGFOOD_PROXMOX_HOST=192.168.10.20), uvx homelab-mcp reachable, Ollama running. Agent shell cannot reach these services."
  - test: "UAT-2: Phase 17 SC1 — gen-test-classes at ~70-tool scale + pyright clean"
    expected: "gen-test-classes writes ~70 typed Pydantic Params + Response class pairs; pyright reports exit code 0 with zero errors and zero warnings on the generated output"
    why_human: "Requires live homelab-mcp exposing ~70 tools via uvx, plus pyright installed as a dev dep. Cannot be run without the live stack."
  - test: "UAT-3: v1.2 Phase 13 v2 config + migration walkthrough — library-mode example"
    expected: "First pytest --collect-only emits fail-loud v1->v2 migration error naming version: 1 and pointing at mcp-contracts config-init; second pytest --collect-only succeeds and shows injected contract tests under <mcp-contracts>::test_*[*] nodeids"
    why_human: "Requires a v1-schema config.yaml fixture and pyproject.toml with mcp_config_file set. Interactive walkthrough that must be observed by a human operator."
  - test: "UAT-4: v1.2 Phase 14 live-smoke + visual domain UI under both CLI and library modes"
    expected: "Both CLI mode (mcp-contracts run) and library mode (pytest --mcp-domain-ui=force) produce domain UI with matching per-tool verdicts and summary lines; CLI shows domain UI without pytest framing; library mode shows both pytest native output AND domain UI"
    why_human: "Requires live homelab-mcp + Ollama + config.yaml with 2-3 enabled tools. Visual output comparison requires human observation."
---

# Phase 30: CLI demotion + carry-forward UAT closure + docs rewrite — Verification Report

**Phase Goal:** Library mode is dogfooded by the framework's own CI; CLI continues to ship but README and docs/LIBRARY-MODE.md lead with library-mode usage; carry-forward live-UAT items from v1.2/v1.3 close as part of the dogfood pass.
**Verified:** 2026-05-19T12:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Framework's pyproject.toml dogfood line intact; Phase 30 verifies dogfood loop green at v1.4 close. CLI-mode path continues to subprocess pytest with JUnit XML round-trip. | VERIFIED | `pyproject.toml` line 67: `mcp_config_file = "./config.test.yaml"` inside `[tool.pytest.ini_options]`. 30-04-SUMMARY.md records `uv run pytest` exit 0, 670 passed / 0 failed / 0 errored. CLOSE-01 checkbox flipped to `[x]` in REQUIREMENTS.md. |
| 2 | `mcp-contracts run --config PATH` and `pytest -o mcp_config_file=PATH` produce identical pass/fail signal — gated by a CI parity test | PARTIAL (BLOCKER) | Parity test file `tests/framework/parity/test_cli_vs_pytest_route.py` exists, collects cleanly, and implements D-01/D-02/D-02a/D-03. However CR-01 (30-REVIEW.md) identifies a real scope mismatch: Route B invokes `pytest tests/` (full suite, line 114) while Route A CLI defaults to `tests/contract/` (_runner.py:145). The outcome dicts are structurally non-comparable on any real stack run. The parity gate cannot validly close CLOSE-02. |
| 3 | README leads with library-mode usage; CLI demoted to Appendix; docs/LIBRARY-MODE.md is the primary library-mode reference | VERIFIED | README.md: `## Quickstart` at line 5, `## Library mode (recommended)` at line 22, `## Appendix: CLI usage` at line 394. `docs/LIBRARY-MODE.md` exists at 381 lines with all 14 required sections including cross-links to TEST-CODE-AUTHORING.md and ERROR-STYLE.md. No planning-ID leaks in either file. |
| 4 | Carry-forward live-UAT items close as part of the dogfood pass (README re-capture, Phase 17 SC1, Phase 13+14 live-stack UATs) | HUMAN NEEDED | Per CONTEXT.md explicit non-blocking decision: Phase 30 authors a CAPTURE PROTOCOL (30-UAT.md exists with all 4 UAT sections at 201 lines) but the actual UAT runs require live homelab-mcp + Proxmox keyring + Ollama — classified as human_verification items, not gaps. |

**Score:** 3/4 truths verified (1 partial/blocker, 1 deferred to human verification)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/framework/parity/test_cli_vs_pytest_route.py` | CLI vs pytest-route JUnit XML equivalence gate | PARTIAL | Exists, structurally correct (D-01/D-02/D-02a/D-03 implemented). Blocker: Route B scope mismatch (tests/ vs tests/contract/). |
| `tests/framework/conftest.py` | parity marker registration + existing Phase 23 fixture | VERIFIED | `pytest_configure` hook appended. `_TEST_CODE_STUB` constant and `config` fixture preserved. Marker registered via `config.addinivalue_line(...)`. |
| `docs/LIBRARY-MODE.md` | Primary operator-facing library-mode reference (220+ lines) | VERIFIED | 381 lines. All required H2 sections present. 16 occurrences of `mcp_config_file`. Links to TEST-CODE-AUTHORING.md (3 mentions) and ERROR-STYLE.md (1 mention). "Running the parity gate locally" section at line 349. No planning-ID leaks. |
| `README.md` | Library-mode Quickstart leads; CLI in Appendix | VERIFIED | `## Quickstart` at line 5 with `mcp_config_file` within first 40 lines. `## Appendix: CLI usage` at line 394. 8 occurrences of `mcp-contracts run` preserved. No planning-ID leaks. No `register(config=Config())` references. |
| `.planning/REQUIREMENTS.md` | CLOSE-01 + CLOSE-03 text amended; CLOSE-02 + CLOSE-04 unchanged | VERIFIED | CLOSE-01 (line 57): new ini-route text present, `register(config=Config())` and `tests/contract/conftest.py` references gone. CLOSE-03 (line 59): "set one line in `[tool.pytest.ini_options]`" present, "write three lines in `conftest.py`" gone. CLOSE-02 and CLOSE-04 checkboxes unchanged (`[ ]`). Traceability rows unchanged (`Pending` except CLOSE-01 now `Complete`). |
| `.planning/phases/30-.../30-UAT.md` | Capture-protocol document for 4 carry-forward UATs | VERIFIED | 201 lines. 4 UAT sections. All status lines `[ ] pending`. Summary: total: 4, pending: 4. Intro states "VERIFICATION.md does NOT block on UAT closure." |
| `.planning/STATE.md` | Dogfood verification record + Performance Metrics row | VERIFIED | `[Phase 30 P04]` entry in Accumulated Context. `| Phase 30 P04 |` row in Performance Metrics. Session Continuity updated to `/gsd-verify-phase 30` then `/gsd-complete-milestone v1.4`. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `tests/framework/parity/test_cli_vs_pytest_route.py` | `mcp_test_framework.cli` run subprocess | `sys.executable -m mcp_test_framework.cli run` | WIRED | Line 99: `sys.executable, "-m", "mcp_test_framework.cli", "run"` confirmed present. |
| `tests/framework/parity/test_cli_vs_pytest_route.py` | `pytest` with ini override | `sys.executable -m pytest -o mcp_config_file=./config.test.yaml` | WIRED BUT SCOPE MISMATCH | Line 110-114: subprocess present. Route B passes `"tests/"` — should be `"tests/contract"` to match Route A's default scope. This is the CR-01 blocker. |
| `tests/framework/parity/test_cli_vs_pytest_route.py` | `tests/framework/conftest.py pytest_configure` | `pytest.mark.parity` marker | WIRED | `pytestmark = [pytest.mark.parity, ...]` at line 46. Marker registered in conftest.py via `config.addinivalue_line(...)`. No `PytestUnknownMarkerWarning` (verified by 30-04 pytest run: 670 passed, 0 errors). |
| `README.md` | `docs/LIBRARY-MODE.md` | markdown relative link | WIRED | `grep -c "docs/LIBRARY-MODE.md" README.md` confirms presence. |
| `docs/LIBRARY-MODE.md` | `docs/TEST-CODE-AUTHORING.md` | markdown relative link in test-code-scenarios section | WIRED | 3 occurrences in LIBRARY-MODE.md. |
| `docs/LIBRARY-MODE.md` | `docs/ERROR-STYLE.md` | markdown relative link in error-tone section | WIRED | 1 occurrence in LIBRARY-MODE.md. |
| `pyproject.toml` | `config.test.yaml` | `mcp_config_file` ini key | WIRED | `mcp_config_file = "./config.test.yaml"` at line 67 inside `[tool.pytest.ini_options]` block. |

---

### Data-Flow Trace (Level 4)

Not applicable for this phase. All deliverables are static documentation, planning artifacts, and a framework self-test (no components that render dynamic data from a database or external source). The dogfood verification (SC1/CLOSE-01) is a pytest run result recorded in STATE.md — flow verified by 30-04 execution evidence.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| parity test collects under `-m parity` | `uv run pytest --collect-only -m "parity"` | 1 item: `tests/framework/parity/test_cli_vs_pytest_route.py::test_cli_route_equals_pytest_route` (per 30-04-SUMMARY.md) | PASS |
| parity test default-deselected | `uv run pytest --collect-only -m "not live_homelab and not live_ollama"` | 0 items selected (per 30-01-SUMMARY.md) | PASS |
| parity marker not in pyproject | `grep '"parity:' pyproject.toml` | 0 matches (verified) | PASS |
| parity marker in framework conftest | `grep '"parity:' tests/framework/conftest.py` | 1 match (verified) | PASS |
| full pytest suite green | `uv run pytest -q` | exit 0; 670 passed, 3 skipped, 1 xfailed, 0 failed, 0 errored (per 30-04-SUMMARY.md) | PASS |
| zero injected contract tests | `pytest --collect-only \| grep "<mcp-contracts>"` | 0 matches — `config.test.yaml` has `tools: {}` (correct per Phase 27 D-13/D-16) | PASS |
| LIBRARY-MODE.md line count | `wc -l docs/LIBRARY-MODE.md` | 381 lines (>= 220 required) | PASS |
| README leads with library mode | `head -n 40 README.md \| grep mcp_config_file` | `mcp_config_file = "./config.yaml"` within first 40 lines | PASS |
| README has CLI appendix at correct position | `awk '/## Quickstart/{q=NR} /## Appendix/{a=NR} END{exit (a>q)?0:1}' README.md` | Appendix at line 394, Quickstart at line 5 (a > q: PASS) | PASS |
| REQUIREMENTS CLOSE-01 amended | `grep -F 'register(config=Config())' .planning/REQUIREMENTS.md` | 0 matches | PASS |
| REQUIREMENTS CLOSE-03 amended | `grep -F "set one line" .planning/REQUIREMENTS.md` | 1 match at line 59 | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CLOSE-01 | Plan 30-04 (verification act) + Plan 30-02 (text amendment) | Dogfood loop green; REQUIREMENTS.md text updated | SATISFIED | pyproject.toml dogfood line intact; pytest exit 0 (670 passed); REQUIREMENTS.md CLOSE-01 text updated; checkbox `[x]` |
| CLOSE-02 | Plan 30-01 | CLI/library parity CI gate | BLOCKED | Parity test exists and is structurally sound but CR-01 scope mismatch (Route B: tests/ vs Route A: tests/contract/) means the gate cannot validate the stated contract on a live stack |
| CLOSE-03 | Plan 30-02 | README leads with library mode; CLI in Appendix; LIBRARY-MODE.md primary reference | SATISFIED | README structure verified; LIBRARY-MODE.md 381 lines; no planning-ID leaks; REQUIREMENTS.md CLOSE-03 text updated |
| CLOSE-04 | Plan 30-03 | Carry-forward live-UAT capture protocols authored | PARTIALLY SATISFIED — protocol authored, execution pending | 30-UAT.md exists with 4 sections (UAT-1..UAT-4); all 8 fields per section; non-blocking per CONTEXT.md decision; UAT execution requires live stack access |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/framework/parity/test_cli_vs_pytest_route.py` | 114 | Route B subprocess passes `"tests/"` (full suite) while Route A CLI defaults to `tests/contract/` (_runner.py:145) | BLOCKER | Parity comparison is between non-equivalent scopes on any live stack run; CLOSE-02 cannot be validated |
| `tests/framework/parity/test_cli_vs_pytest_route.py` | 102, 113 | Inner subprocess marker expression is only `-m "not parity"`, which overrides `addopts = "-m 'not live_homelab and not live_ollama'"` when pytest processes both flags | WARNING | Inner subprocesses may collect live-stack tests that the parity gate's own markers were intended to guard against (WR-02 from REVIEW.md) |
| `tests/framework/parity/test_cli_vs_pytest_route.py` | 72-84 | `_parse_outcomes` implements last-seen-wins for duplicate nodeids, not the documented any-fail-wins (failure > error > skipped > passed) | WARNING | If duplicate testcase entries appear in JUnit XML, the documented priority is not enforced; a `passed` entry can overwrite an earlier `failure` entry (WR-03 from REVIEW.md) |

---

### Human Verification Required

The following items require a live homelab-mcp + Proxmox keyring + Ollama environment. Per CONTEXT.md non-blocking decision, Phase 30 VERIFICATION.md does NOT block on these UAT closures — they are user-driven captures tracked in `30-UAT.md`.

#### 1. UAT-1: README test-code-scenarios PASS-sample re-capture

**Test:** In an operator shell with Proxmox keyring access:
```powershell
$env:MCPTF_DOGFOOD_PROXMOX_HOST = "192.168.10.20"
uv run mcp-contracts run --test-code --config config.yaml
```
**Expected:** All test-code scenarios pass; output matches README §"test-code scenarios" snapshot format with PASS rows instead of FAIL. Re-snapshot pasted verbatim into README §"test-code scenarios", replacing the pre-Phase-24 FAIL block.
**Why human:** Requires live Proxmox keyring (agent shell cannot reach `uvx homelab-mcp` or keyring secrets). User-driven capture per `feedback_uat_must_be_user_driven` memory anchor.

#### 2. UAT-2: Phase 17 SC1 — gen-test-classes at ~70-tool scale + pyright clean

**Test:**
```bash
uv run mcp-contracts gen-test-classes --config config.yaml
uv run pyright <path-from-cfg.test_code.generated_root>/<server_slug>/
```
**Expected:** `gen-test-classes` writes ~70 typed Pydantic Params + Response class pairs; `pyright` exit code 0 with zero errors and zero warnings.
**Why human:** Requires live homelab-mcp exposing ~70 tools via `uvx` and `pyright` installed as a dev dep. Cannot be verified without the live stack.

#### 3. UAT-3: v1.2 Phase 13 v2 config + migration walkthrough — library-mode example

**Test:**
```bash
uv run pytest --collect-only   # with v1-schema config — expect migration error
uv run mcp-contracts config-init -o config.yaml.new
uv run pytest --collect-only   # after migration — expect injected contract tests
```
**Expected:** First invocation emits fail-loud v1→v2 migration error naming `version: 1` and pointing at `mcp-contracts config-init`; second invocation succeeds and shows contract tests under `<mcp-contracts>::test_*[*]` nodeids with no `MCPTF_CONFIG_FILE` env var set.
**Why human:** Interactive walkthrough requiring a v1-schema config fixture and human observation of error output quality.

#### 4. UAT-4: v1.2 Phase 14 live-smoke + visual domain UI under both CLI and library modes

**Test:**
```powershell
uv run mcp-contracts run --config config.yaml *>&1 | Tee-Object -FilePath cli_output.txt
uv run pytest -o "mcp_config_file=./config.yaml" --mcp-domain-ui=force *>&1 | Tee-Object -FilePath lib_output.txt
Compare-Object (Get-Content cli_output.txt) (Get-Content lib_output.txt)
```
**Expected:** Both outputs show domain UI (header / per-tool rows / summary); per-tool verdicts and `Result:` summary line agree between routes; CLI shows domain UI without pytest framing; library mode shows both pytest native output AND domain UI.
**Why human:** Requires live homelab-mcp + Ollama + config.yaml with 2-3 enabled tools. Visual output comparison must be reviewed by a human operator.

---

### Gaps Summary

One blocker prevents full goal achievement:

**CR-01: Route B scope mismatch in the parity test (CLOSE-02 cannot validly close)**

The parity test at `tests/framework/parity/test_cli_vs_pytest_route.py` invokes Route A (CLI) and Route B (raw pytest) with different test collection scopes:

- Route A: internally calls `_runner.py:145` which defaults to `tests/contract` (operator-facing contract surface only)
- Route B: invoked with `"tests/"` (line 114) — the full suite including `tests/framework/` self-tests

On any real stack run with `tools:` populated in `config.test.yaml`, Route A produces only `<mcp-contracts>::test_*[tool]` virtual nodes while Route B also produces all 670+ framework self-test nodeids. The `outcomes_a == outcomes_b` assertion will always fail on a live stack, or produce a misleading vacuous PASS (D-02a only guards Route A being empty, not the scope divergence). The CLOSE-02 requirement — "identical pass/fail signal" — cannot be validated by this gate as written.

**Fix required:** Change Route B's subprocess argument from `"tests/"` to `"tests/contract"` (the same default scope Route A uses). This is a single-line change.

**Secondary issues (WR-01, WR-02, WR-03 from REVIEW.md):** The reviewer also identified the asymmetric D-02a guard (only checks `outcomes_a`, not `outcomes_b`), the `-m "not parity"` marker override that bypasses `addopts` live-marker exclusions in inner subprocesses, and a last-seen-wins vs any-fail-wins discrepancy in `_parse_outcomes`. These are actionable but secondary to CR-01. The gap plan should address CR-01 as the blocker; WR-01/WR-02/WR-03 are recommended co-fixes.

**Human verification items (non-blocking):** The four carry-forward live-UAT items (UAT-1 through UAT-4) require live homelab-mcp + Proxmox keyring + Ollama access. Per the CONTEXT.md explicit decision, Phase 30 VERIFICATION.md does NOT block on UAT closure. These are tracked in `30-UAT.md` and close in a follow-up operator-driven session.

---

_Verified: 2026-05-19T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
