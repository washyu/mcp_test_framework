---
phase: 05-cli-readme-acceptance
verified: 2026-05-06T22:00:00Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 1
overrides:
  - must_have: "KeyboardInterrupt cleanly tears down MCP subprocess (no zombie homelab-mcp on Windows) — SC#4 / OPS-03"
    reason: "PARTIAL PASS accepted by user during execution. Natural-exit teardown of `list-tools` directly verified clean (`Get-Process homelab-mcp` empty after exit). SIGINT path could not be UAT-tested directly because the warm `uvx` cache returned the full tool list in <1s, narrower than the Ctrl+C delivery window. SIGINT coverage carried by (1) shared `asyncio.Runner` + `AsyncExitStack`-owned McpTestClient lifecycle with the natural-exit case (both unwind through the same `__aexit__` on the same task), (2) Phase 04.1 fixture-side teardown evidence (`tests/smoke/test_mcp_client_teardown_regression.py` + 04.1-01-SUMMARY.md), (3) CONTEXT.md `<deferred>` already tracks automated cross-platform SIGINT UAT as the durable closure path. Documented in 05-05-SUMMARY.md `Decisions Made` and 05-05-ACCEPTANCE-WALKTHROUGH.md `## OPS-03 (SC#4)`."
    accepted_by: "washyu"
    accepted_at: "2026-05-06T00:00:00Z"
---

# Phase 5: CLI, README & Acceptance Verification Report

**Phase Goal:** Users can install, configure, and run the framework against `homelab-mcp` via the `mcp-test-framework` CLI from a clean checkout, with all 6 spec acceptance criteria observable.

**Verified:** 2026-05-06T22:00:00Z
**Status:** passed (with 1 override applied)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| #   | Truth (Success Criterion)                                                                                              | Status                | Evidence                                                                                                                                                                                                                          |
| --- | ---------------------------------------------------------------------------------------------------------------------- | --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | SC#1 — `run` resolves config + invokes `pytest.main` + exits with pytest's exit code (CLI-01)                          | VERIFIED              | `src/mcp_test_framework/cli.py:86-119` shows `run` calls `_load_config(config)` then `raise typer.Exit(code=pytest.main(["tests", *forwarded]))` with no try/except wrap. Walkthrough captured `run-exit=0` against live homelab-mcp + Ollama (67 passed, 5 deselected, 22.02s). My re-verify: `uv run mcp-test-framework run -- --collect-only -q` exits 0; bad `--config` path exits 2. |
| 2   | SC#2 — `list-tools` connects via stdio + prints tools (CLI-02), no pytest, no Ollama                                   | VERIFIED              | `cli.py:122-155` `list_tools` uses `asyncio.Runner` + `_list_tools_async` (AsyncExitStack-owned `McpTestClient`); no pytest import in this path; no Ollama call. Walkthrough captured 58 tools printed alphabetically (text mode, exit=0) and parsed JSON via `ConvertFrom-Json` with the four required keys. My re-verify: `uv run mcp-test-framework --help` lists `list-tools`. |
| 3   | SC#3 — `version` prints package version (CLI-03)                                                                       | VERIFIED              | `cli.py:158-165` reads `metadata.version("mvp-test-framework")` with `__version__` fallback. My re-verify: `uv run mcp-test-framework version` prints `0.1.0` (exit 0). Walkthrough captured `version-exit=0`. |
| 4   | SC#4 — KeyboardInterrupt cleanly tears down MCP subprocess (no zombie `homelab-mcp.exe`) (OPS-03)                      | PASSED (override)     | Override: PARTIAL PASS accepted by washyu on 2026-05-06. Natural-exit teardown verified clean (`Get-Process homelab-mcp` empty after `list-tools` exits). SIGINT path inferred from shared code path (asyncio.Runner + AsyncExitStack on a single task) + Phase 04.1 fixture-side teardown evidence. See `05-05-ACCEPTANCE-WALKTHROUGH.md` `## OPS-03 (SC#4)` and `05-05-SUMMARY.md` for full evidence trail. |
| 5   | SC#5 — README explains setup, configuration (precedence), run instructions, Windows troubleshooting (DOCS-01)          | VERIFIED              | `README.md` (146 lines) has all 9 H2 sections (`## Prerequisites`, `## Setup`, `## Commands`, `## Configuration`, `## Sample green run`, `## Troubleshooting (Windows)`, `## Further reading`). Precedence sentence `CLI flag > env var > .env > YAML overlay > default` present at L68. Windows troubleshooting includes `taskkill /F /IM homelab-mcp.exe` at L130. Env-var table at L70-80 covers all 8 env vars + `MCPTF_CONFIG_FILE`. |
| 6   | SC#6 — Clean clone → `uv sync` → `run` → standard pytest output + exit 0                                              | VERIFIED              | Walkthrough captured `uv-sync-exit=0` and `run-exit=0` with 67 passed against live homelab-mcp + Ollama on Win11. README `## Sample green run` (L88-107) contains the real captured 13-line excerpt with `passed in 22.02s`. The `<!-- TODO Plan 05 -->` placeholder is gone (verified by Grep: 0 matches). |

**Score:** 6/6 truths verified (1 via override)

### Required Artifacts

| Artifact                                                                                | Expected                                                                          | Status     | Details                                                                                                                                                                                                       |
| --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/mcp_test_framework/cli.py`                                                         | Typer `app` + `_load_config` + `run` + `list_tools` + `version` + 3 helpers       | VERIFIED   | 233 lines. Module imports cleanly. All 3 `@app.command(...)` definitions present. `asyncio.Runner` + `AsyncExitStack` pattern matches plan. No `asyncio.run()`, no `asyncio.Future`/`asyncio.Event`/`owner_task`, no `import rich`, no `except KeyboardInterrupt`, no `import pytest` at module scope (function-local in `run` only).            |
| `pyproject.toml`                                                                        | `[project.scripts] mcp-test-framework = "mcp_test_framework.cli:app"` uncommented | VERIFIED   | L18-22 active and uncommented. `uv run mcp-test-framework version` resolves the entry point and prints `0.1.0`.                                                                                                |
| `README.md`                                                                             | ≥100 lines, 9 H2 sections, env table, precedence sentence, Windows troubleshooting, sample green-run with real `passed in` excerpt | VERIFIED   | 146 lines, all H2 sections present, all 8 env vars + `MCPTF_CONFIG_FILE` documented, `passed in 22.02s` excerpt captured at L88-107, `TODO Plan 05` marker absent.                                              |
| `docs/EXTENDING.md`                                                                     | ≥60 lines, 2 H2 recipes (rubric subclass + Judge Protocol override)               | VERIFIED   | 121 lines. Both H2 sections present with copy-pasteable code samples. `runtime_checkable` caveat documented at L66-71. `score >= 4` mentioned at L57. No `import rich`. |
| `.env.example` / `config.example.yaml`                                                  | Synced env-var documentation (no Phase 5 schema additions)                       | VERIFIED   | `.env.example` ships 8 env vars + commented `MCPTF_CONFIG_FILE`. Sync-check artifact `05-04-SYNC-CHECK.txt` exists with no `MISSING:` lines. Note: `TARGET_TOOL_NAME` was changed from `list_registered_servers` to `list_keyring_credentials` (intentional; documented).                  |
| `.planning/phases/05-cli-readme-acceptance/05-05-ACCEPTANCE-WALKTHROUGH.md`             | Verbatim capture of all 6 SCs with exit codes + final summary table              | VERIFIED   | 356 lines. H2 sections for SC#1/SC#6, SC#2, SC#3, SC#5, OPS-03 (SC#4), final summary all present. Verbatim exit-code captures (`run-exit=0`, `list-tools-text-exit=0`, `list-tools-json-exit=0`, `version-exit=0`) confirmed. OPS-03 section honestly records PARTIAL with evidence trail. |

### Key Link Verification

| From                                  | To                                            | Via                                                       | Status   | Details                                                                                                                                  |
| ------------------------------------- | --------------------------------------------- | --------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `pyproject.toml [project.scripts]`    | `mcp_test_framework.cli:app`                  | console-script entry point                                | WIRED    | Active L22; `uv run mcp-test-framework version` resolves and prints `0.1.0`.                                                              |
| `cli.py run()`                        | `pytest.main(["tests", *forwarded])`          | direct call, no try/except wrap (D-cli-flags-3)           | WIRED    | `cli.py:119` `raise typer.Exit(code=pytest.main(["tests", *forwarded]))`. No `try:` within 5 lines preceding `pytest.main` (verified manually). |
| `cli.py list_tools()`                 | `asyncio.Runner.run(_list_tools_async(cfg))`  | single-task event-loop ownership                          | WIRED    | `cli.py:150-151`. No `asyncio.run(` (verified by grep). |
| `cli.py _list_tools_async()`          | `McpTestClient.__aenter__/__aexit__`          | AsyncExitStack-owned single-task lifecycle                | WIRED    | `cli.py:177-184` uses `async with AsyncExitStack() as stack: client = await stack.enter_async_context(McpTestClient(...))`. |
| `cli.py version()`                    | `metadata.version("mvp-test-framework")`      | stdlib distribution-name lookup                           | WIRED    | `cli.py:162`. Live verified: returns `0.1.0`. |
| `cli.py _load_config()`               | `os.environ["MCPTF_CONFIG_FILE"] = str(path)` + `Config()` | env-var seam → Pydantic-settings YAML overlay     | WIRED    | `cli.py:72-77`. `--config /nonexistent.yaml` exits 2 with the documented stderr line (re-verified). Note: WR-02 in 05-REVIEW.md flags env-var leak as a quality concern, advisory only. |
| `README.md ## Configuration`          | `.env.example` (env-var table sync)           | manual sync verified by 05-04-SYNC-CHECK.txt              | WIRED    | All 8 env vars from `.env.example` + `MCPTF_CONFIG_FILE` appear in README table. No `MISSING:` in sync artifact. |
| `README.md ## Further reading`        | `docs/EXTENDING.md`                           | markdown link                                             | WIRED    | `README.md:145` `- [`docs/EXTENDING.md`](docs/EXTENDING.md) -- add a new rubric, swap the judge backend`. |
| `docs/EXTENDING.md`                   | `judge_protocol.py` + `rubrics.py`            | code-sample imports + path mention                        | WIRED    | `from mcp_test_framework.judge_protocol import Judge` (L77), `from mcp_test_framework.rubrics import Rubric` (L27); `judge_protocol.py` and `rubrics.py` both referenced by name. |

### Data-Flow Trace (Level 4)

The CLI commands operate on dynamic data sourced from the live MCP server and a real config object, not hardcoded stubs.

| Artifact                       | Data Variable           | Source                                                                                          | Produces Real Data | Status    |
| ------------------------------ | ----------------------- | ----------------------------------------------------------------------------------------------- | ------------------ | --------- |
| `cli.py list_tools` (text/JSON) | `tools: list[Tool]`     | `await client.list_tools()` → MCP `session.list_tools()` over stdio_client subprocess pipe      | YES                | FLOWING   |
| `cli.py run` exit code         | `pytest.main(...)`      | pytest's collected tests under `tests/`; live UAT shows 67 passed against live homelab-mcp     | YES                | FLOWING   |
| `cli.py version`               | `v = metadata.version(...)` | importlib.metadata reading the installed distribution                                       | YES                | FLOWING   |
| `cli.py _load_config`          | `Config()` instance     | pydantic-settings: env vars > `.env` > `MCPTF_CONFIG_FILE` YAML > Pydantic defaults             | YES                | FLOWING   |

### Behavioral Spot-Checks

I executed live spot-checks during verification (not relying solely on the walkthrough capture):

| Behavior                                            | Command                                                          | Result                                                | Status |
| --------------------------------------------------- | ---------------------------------------------------------------- | ----------------------------------------------------- | ------ |
| `version` resolves entry point + prints version     | `uv run mcp-test-framework version`                              | stdout: `0.1.0`, exit=0                                | PASS   |
| `--help` shows all 3 subcommands                    | `uv run mcp-test-framework --help`                               | Lists `run`, `list-tools`, `version` with descriptions | PASS   |
| Bad `--config` path exits 2 with stderr message     | `uv run mcp-test-framework run --config /nonexistent.yaml`       | stderr: `error: --config path not found: ...`, exit=2 | PASS   |
| `run` forwards args to pytest collect-only          | `uv run mcp-test-framework run -- --collect-only -q`             | `67/72 tests collected (5 deselected) in 0.03s`, exit=0 | PASS  |

### Requirements Coverage

| Requirement | Source Plan(s)                | Description                                                                                                                                | Status      | Evidence                                                                                                                                                              |
| ----------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CLI-01      | 05-02, 05-05                  | `mcp-test-framework run [...]` resolves config, invokes pytest.main(), exits with pytest's exit code                                       | SATISFIED   | SC#1 verified live; `cli.py:86-119` implements the contract. Re-verified `--collect-only -q` exits 0.                                                                  |
| CLI-02      | 05-03, 05-05                  | `mcp-test-framework list-tools [...]` connects via stdio, prints tools, no pytest, no Ollama                                              | SATISFIED   | SC#2 verified live (58 tools text + JSON); `cli.py:122-155` does not import pytest or Ollama in this code path.                                                       |
| CLI-03      | 05-01, 05-05                  | `mcp-test-framework version` prints package version                                                                                       | SATISFIED   | SC#3 verified live; my re-verify returns `0.1.0`.                                                                                                                      |
| OPS-03      | 05-02, 05-03, 05-05           | KeyboardInterrupt at the CLI level cleanly tears down MCP subprocess (no zombie homelab-mcp.exe)                                          | SATISFIED (override) | Natural-exit teardown verified clean. SIGINT path inferred from shared asyncio.Runner+AsyncExitStack code path with Phase 04.1's already-verified fixture-side teardown. User-accepted PARTIAL PASS. |
| DOCS-01     | 05-04, 05-05                  | README explains setup, configuration (precedence), running tests, Windows troubleshooting                                                  | SATISFIED   | SC#5 verified; `README.md` 146 lines with all required sections; sync-check artifact confirms parity with `.env.example`.                                              |

**No orphaned requirements:** REQUIREMENTS.md maps exactly CLI-01, CLI-02, CLI-03, OPS-03, DOCS-01 to Phase 5 (line 154); all 5 are claimed by Phase 5 plans.

### Anti-Patterns Found

The 05-REVIEW.md report (0 critical, 5 warnings, 4 info) was advisory; none are blockers. I confirm:

| File                              | Line(s)        | Pattern                                                                                       | Severity | Impact                                                                                                                                                |
| --------------------------------- | -------------- | --------------------------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/mcp_test_framework/cli.py`   | 92-95          | `pytest_args: list[str] = typer.Argument(None, ...)` — type contradicts default (WR-01)        | Info     | `or []` rescue at L118 papers over it; runtime is correct. Quality polish, not goal-blocking.                                                          |
| `src/mcp_test_framework/cli.py`   | 72-77          | `_load_config` mutates `os.environ["MCPTF_CONFIG_FILE"]` and never unsets on error (WR-02)    | Warning  | Test isolation hazard if `_load_config` is called repeatedly in-process. Documented in 05-REVIEW; advisory only. Does not affect goal achievement.    |
| `src/mcp_test_framework/cli.py`   | 222-225        | Asymmetric attribute access: `t.inputSchema` vs `getattr(t, "outputSchema", None)` (WR-03)     | Info     | Both are `model_fields` on current SDK; getattr is dead code today.                                                                                    |
| `src/mcp_test_framework/cli.py`   | 229            | `json.dumps(..., default=str)` masks non-serializable schema content (WR-04)                  | Info     | Defensive but loses crash signal on malformed schemas. Not exercised in current SDK.                                                                  |
| `src/mcp_test_framework/cli.py`   | 144-147        | Docstring claims `KeyboardInterrupt → exit 130` but Click standalone_mode may convert to 1 (WR-05) | Warning  | Honesty issue in docstring. Doesn't change runtime; SIGINT teardown still unwinds the AsyncExitStack regardless of final exit code. Note: this dovetails with the OPS-03 override — direct SIGINT verification was deferred. |

**Pertinent absences confirmed:** No `import pytest` at module scope (verified — only function-local in `run`). No `asyncio.run(`. No owner-task scaffolding (`asyncio.Future`/`asyncio.Event`/`owner_task` Python identifiers). No `import rich`. No `try: ... except KeyboardInterrupt`. No explicit `-m` flag. No `# TODO Plan 05` markers in README.

### Human Verification Required

None. The remaining concern (direct SIGINT UAT against the warm-cache `list-tools` path) was already accepted by the user as a PARTIAL PASS during execution and is recorded as an override above. CONTEXT.md `<deferred>` already tracks the durable closure path (automated cross-platform SIGINT scaffolding); raising it here as a fresh `human_needed` would be redundant.

### Gaps Summary

No gaps blocking goal achievement.

The only deviation from the literal 6/6 SC verification is SC#4 (OPS-03 SIGINT path), which is recorded as a PASSED (override) per the user's explicit acceptance during execution. The framework's value proposition was demonstrated end-to-end during acceptance itself: the qwen3.6 judge surfaced a real description-quality gap in `list_registered_servers`'s description with substantive reasoning during SC#6, and the user resolved it with a documented config-only switch (`TARGET_TOOL_NAME=list_keyring_credentials`) plus an upstream homelab-mcp tracking note. That is exactly the failure mode the framework exists to catch.

**Two follow-up items tracked (not blocking):**

1. Upstream homelab-mcp `list_registered_servers` description fails the disambiguation rubric (config-only switch documented; once upstream lands a disambiguation hint, the documented default can be switched back).
2. Automated cross-platform SIGINT UAT scaffolding (already in CONTEXT.md `<deferred>`).

Five 05-REVIEW.md warnings are advisory polish — no blockers to phase goal achievement.

---

_Verified: 2026-05-06T22:00:00Z_
_Verifier: Claude (gsd-verifier)_
