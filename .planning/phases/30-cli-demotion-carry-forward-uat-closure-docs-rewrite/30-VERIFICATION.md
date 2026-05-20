---
phase: 30-cli-demotion-carry-forward-uat-closure-docs-rewrite
verified: 2026-05-19T14:00:00Z
status: human_needed
score: 3/4 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 3/4
  gaps_closed:
    - "mcp-contracts run --config PATH and pytest -o mcp_config_file=PATH produce identical pass/fail signal — gated by a CI parity test (CR-01 scope mismatch fixed)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "UAT-1: README test-code-scenarios PASS-sample re-capture"
    expected: "All test-code scenarios pass against live Proxmox + homelab-mcp; output matches README snapshot format with PASS rows; re-snapshot pasted into README replacing the pre-Phase-24 FAIL block"
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

# Phase 30: CLI demotion + carry-forward UAT closure + docs rewrite — Re-Verification Report

**Phase Goal:** Library mode is dogfooded by the framework's own CI (framework pyproject.toml sets `[tool.pytest.ini_options] mcp_config_file = './config.test.yaml'`); CLI continues to ship but README and docs/LIBRARY-MODE.md lead with library-mode usage; carry-forward live-UAT items from v1.2/v1.3 close as part of the dogfood pass.
**Verified:** 2026-05-19T14:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (commits 1b6b235 and 5500cd5)

## Re-Verification Context

The previous verification (`30-VERIFICATION.pre-fix.md`) found `status: gaps_found` (score 3/4) with one blocker: CR-01 — Route B of the parity test invoked `"tests/"` (the full suite) while Route A CLI defaults to `tests/contract/`, making the `{nodeid: outcome}` dicts structurally non-comparable on any real stack run.

Two fix commits closed that gap:

- `1b6b235` — fix(30): CR-01 WR-01 WR-02 WR-03 parity test scope+markers+guard+priority
- `5500cd5` — fix(30): restore parity test fixes (after inadvertent revert in docs commit 17e51e6)

The current HEAD is `5500cd5`. All four fixes have been verified directly in the live file at `tests/framework/parity/test_cli_vs_pytest_route.py`.

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Framework's pyproject.toml dogfood line intact; uv run pytest green at v1.4 close | VERIFIED | `pyproject.toml` line 67: `mcp_config_file = "./config.test.yaml"` inside `[tool.pytest.ini_options]`. 30-04-SUMMARY.md records `uv run pytest -q` → exit 0, 670 passed / 0 failed / 0 errored. |
| 2 | `mcp-contracts run --config PATH` and `pytest -o mcp_config_file=PATH` produce identical pass/fail signal — gated by a CI parity test | VERIFIED | CR-01 CLOSED. Post-fix file at line 118: `"tests/contract", # match Route A scope`. WR-01 closed: symmetric `assert outcomes_b` at line 158. WR-02 closed: both inner `-m` args expanded to `"not parity and not live_homelab and not live_ollama"` (lines 106, 117). WR-03 closed: `PRIORITY` dict (lines 72-73) + any-fail-wins conditional update (line 87). File confirmed at HEAD (`5500cd5`). |
| 3 | README leads with library mode; CLI demoted to Appendix; docs/LIBRARY-MODE.md is the primary library-mode reference | VERIFIED | `README.md`: `## Quickstart` at line 5, `## Library mode (recommended)` at line 22, `## Appendix: CLI usage` at line 394. `docs/LIBRARY-MODE.md` exists with library-mode-first content. No planning-ID leaks in either file. |
| 4 | Carry-forward live-UAT items close as part of library-mode dogfood pass (user-driven captures — non-blocking per CONTEXT.md) | HUMAN NEEDED | Per CONTEXT.md explicit non-blocking decision: Phase 30 authored capture protocol in `30-UAT.md` (201 lines, 4 UAT sections). Actual UAT execution requires live homelab-mcp + Proxmox keyring + Ollama — classified as human_verification items per `feedback_uat_must_be_user_driven` memory anchor. |

**Score:** 3/4 truths verified (SC4 deferred to human verification — non-blocking per CONTEXT.md)

---

### Closed Gap: CR-01 Detailed Evidence

The blocker from the previous verification was Route B scope mismatch. Evidence that all four fixes are present in the live file:

| Fix | Location | Evidence |
|-----|----------|----------|
| CR-01: Route B scope | Line 118 | `"tests/contract", # match Route A scope` (was `"tests/"`) |
| WR-02: Expanded inner `-m` guard | Lines 106, 117 | `"not parity and not live_homelab and not live_ollama"` (was `"not parity"`) |
| WR-01: Symmetric outcomes_b guard | Line 158 | `assert outcomes_b, (` added after the existing `assert outcomes_a` |
| WR-03: Any-fail-wins priority | Lines 72, 87 | `PRIORITY: dict[str, int] = {"failed": 0, "error": 1, "skipped": 2, "passed": 3}` + `if nodeid not in out or PRIORITY[outcome] < PRIORITY[out[nodeid]]:` |

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/framework/parity/test_cli_vs_pytest_route.py` | CLI vs pytest-route JUnit XML equivalence gate | VERIFIED | Exists. All four design decisions implemented (D-01 dict equality, D-02 config.test.yaml substrate, D-02a defensive non-vacuous assert, D-03 two subprocesses). All four review findings fixed (CR-01, WR-01, WR-02, WR-03). |
| `tests/framework/conftest.py` | parity marker registration + existing Phase 23 fixture | VERIFIED | `pytest_configure` hook appended. `_TEST_CODE_STUB` constant and `config` fixture preserved. Marker registered via `config.addinivalue_line(...)`. Parameter named `config` (not `pytestconfig`) per pluggy hookspec constraint. |
| `docs/LIBRARY-MODE.md` | Primary operator-facing library-mode reference | VERIFIED | Exists. Content confirmed from line 1. Pre-fix verification confirmed 381 lines with all 14 required H2 sections. |
| `README.md` | Library-mode Quickstart leads; CLI in Appendix | VERIFIED | `## Quickstart` at line 5. `## Library mode (recommended)` at line 22. `## Appendix: CLI usage` at line 394. |
| `.planning/REQUIREMENTS.md` | CLOSE-01 + CLOSE-03 text amended; CLOSE-02 + CLOSE-04 unchanged | VERIFIED | Pre-fix verification confirmed: `register(config=Config())` gone from CLOSE-01; "set one line in `[tool.pytest.ini_options]`" present in CLOSE-03; CLOSE-02 and CLOSE-04 unchanged. |
| `.planning/phases/30-.../30-UAT.md` | Capture-protocol document for 4 carry-forward UATs | VERIFIED | Exists (201 lines, 4 UAT sections) per 30-03-SUMMARY.md. All status lines pending. Non-blocking per CONTEXT.md. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `tests/framework/parity/test_cli_vs_pytest_route.py` | `mcp_test_framework.cli run` subprocess | `sys.executable -m mcp_test_framework.cli run --config config.test.yaml` | WIRED | Line 103: `sys.executable, "-m", "mcp_test_framework.cli", "run"` |
| `tests/framework/parity/test_cli_vs_pytest_route.py` | `pytest tests/contract` with ini override | `sys.executable -m pytest -o mcp_config_file=./config.test.yaml tests/contract` | WIRED (scope fix confirmed) | Line 115-118: `-o mcp_config_file=./config.test.yaml` + `"tests/contract"`. CR-01 CLOSED. |
| `tests/framework/parity/test_cli_vs_pytest_route.py` | `tests/framework/conftest.py pytest_configure` | `pytest.mark.parity` marker | WIRED | `pytestmark = [pytest.mark.parity, ...]` at line 45. Marker registered in conftest via `config.addinivalue_line(...)`. |
| `pyproject.toml` | `config.test.yaml` | `mcp_config_file` ini key | WIRED | `mcp_config_file = "./config.test.yaml"` at line 67 inside `[tool.pytest.ini_options]`. |
| `README.md` | `docs/LIBRARY-MODE.md` | markdown relative link | WIRED | Confirmed present in pre-fix verification (ref: 30-VERIFICATION.pre-fix.md key link table). |
| `docs/LIBRARY-MODE.md` | `docs/TEST-CODE-AUTHORING.md` | markdown relative link | WIRED | 3 occurrences confirmed in pre-fix verification. |

---

### Data-Flow Trace (Level 4)

Not applicable. All phase deliverables are static documentation, planning artifacts, and a framework self-test (no components rendering dynamic data from a database or external source). The dogfood verification (SC1) is a pytest run result — flow verified by 30-04 execution evidence (670 passed, exit 0).

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| parity test collects under `-m parity` | `uv run pytest --collect-only -m "parity"` | 1 item: `test_cli_route_equals_pytest_route` (per 30-04-SUMMARY.md) | PASS |
| parity test default-deselected | `uv run pytest --collect-only -m "not live_homelab and not live_ollama"` | 0 items selected (per 30-01-SUMMARY.md) | PASS |
| parity marker not in pyproject markers list | `grep '"parity:' pyproject.toml` | 0 matches (confirmed) | PASS |
| parity marker registered in framework conftest | `grep '"parity:' tests/framework/conftest.py` | 1 match (confirmed) | PASS |
| full pytest suite green | `uv run pytest -q` | exit 0; 670 passed, 3 skipped, 1 xfailed, 0 failed, 0 errored (per 30-04-SUMMARY.md) | PASS |
| zero injected contract tests | `pytest --collect-only \| grep "<mcp-contracts>"` | 0 matches — `config.test.yaml` has `tools: {}` (correct per Phase 27 D-13/D-16) | PASS |
| Route B targets tests/contract (post-fix) | Line 118 of parity file | `"tests/contract", # match Route A scope` | PASS |
| WR-03: any-fail-wins in `_parse_outcomes` | Lines 72+87 of parity file | PRIORITY dict + conditional update present | PASS |
| WR-01: symmetric outcomes_b guard | Line 158 of parity file | `assert outcomes_b, (` present | PASS |
| WR-02: expanded inner marker guards | Lines 106+117 of parity file | `"not parity and not live_homelab and not live_ollama"` | PASS |
| LIBRARY-MODE.md leads with library mode | Line 1 of LIBRARY-MODE.md | `# Library Mode — pytest-native MCP contract testing` | PASS |
| README leads with Quickstart | Line 5 of README | `## Quickstart` | PASS |
| README CLI demoted to Appendix | Line 394 of README | `## Appendix: CLI usage` | PASS |
| dogfood ini line in pyproject | Line 67 of pyproject.toml | `mcp_config_file = "./config.test.yaml"` inside `[tool.pytest.ini_options]` | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CLOSE-01 | Plan 30-04 (verification act) + Plan 30-02 (text amendment) | Dogfood loop green; REQUIREMENTS.md text updated | SATISFIED | pyproject.toml dogfood line intact at line 67; pytest exit 0 (670 passed); REQUIREMENTS.md CLOSE-01 text updated to ini-route wording. |
| CLOSE-02 | Plan 30-01 (parity test) + fix commits 1b6b235/5500cd5 | CLI/library parity CI gate | SATISFIED | Parity test exists with all four design decisions (D-01/D-02/D-02a/D-03) and all four review findings fixed (CR-01/WR-01/WR-02/WR-03). Route B now targets `tests/contract` matching Route A's scope. |
| CLOSE-03 | Plan 30-02 | README leads with library mode; CLI in Appendix; LIBRARY-MODE.md primary reference | SATISFIED | README structure verified. LIBRARY-MODE.md exists. No planning-ID leaks. REQUIREMENTS.md CLOSE-03 text updated to "set one line in `[tool.pytest.ini_options]`". |
| CLOSE-04 | Plan 30-03 | Carry-forward live-UAT capture protocols authored | PROTOCOL AUTHORED — execution pending (non-blocking) | `30-UAT.md` exists with 4 sections (UAT-1..UAT-4). Non-blocking per CONTEXT.md explicit decision (`feedback_uat_must_be_user_driven` memory anchor). |

---

### Anti-Patterns Found

No anti-patterns remain from the previous verification. All three previously flagged items have been resolved:

| File | Fix | Status |
|------|-----|--------|
| `test_cli_vs_pytest_route.py` line 118 | Route B changed from `"tests/"` to `"tests/contract"` | RESOLVED |
| `test_cli_vs_pytest_route.py` lines 106+117 | Inner `-m` expanded to include `not live_homelab and not live_ollama` | RESOLVED |
| `test_cli_vs_pytest_route.py` `_parse_outcomes` | PRIORITY dict + any-fail-wins conditional update | RESOLVED |

No new anti-patterns introduced by the fix commits.

---

### Human Verification Required

The following items require a live homelab-mcp + Proxmox keyring + Ollama environment. Per CONTEXT.md non-blocking decision, Phase 30 VERIFICATION.md does NOT block on these UAT closures — they are user-driven captures tracked in `30-UAT.md`.

#### 1. UAT-1: README test-code-scenarios PASS-sample re-capture

**Test:** In an operator shell with Proxmox keyring access:
```powershell
$env:MCPTF_DOGFOOD_PROXMOX_HOST = "192.168.10.20"
uv run mcp-contracts run --test-code --config config.yaml
```
**Expected:** All test-code scenarios pass; output matches README "test-code scenarios" snapshot format with PASS rows instead of FAIL. Re-snapshot pasted verbatim into README replacing the pre-Phase-24 FAIL block.
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
**Expected:** First invocation emits fail-loud v1->v2 migration error naming `version: 1` and pointing at `mcp-contracts config-init`; second invocation succeeds and shows contract tests under `<mcp-contracts>::test_*[*]` nodeids with no `MCPTF_CONFIG_FILE` env var set.
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

No gaps remain. The one blocker from the previous verification (CR-01: Route B scope mismatch) was closed by commits `1b6b235` and `5500cd5`. Direct file inspection confirms all four fixes are present in the live codebase at HEAD.

The four SC4 carry-forward UATs are not gaps — they are user-driven captures explicitly marked non-blocking in CONTEXT.md, tracked in `30-UAT.md`, and classified here as human_verification items per the `feedback_uat_must_be_user_driven` memory anchor.

---

_Verified: 2026-05-19T14:00:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Yes — gap closure after initial gaps_found verdict_
