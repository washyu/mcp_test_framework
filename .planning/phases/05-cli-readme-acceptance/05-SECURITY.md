---
phase: 05
slug: cli-readme-acceptance
status: verified
threats_open: 0
threats_total: 23
threats_closed: 23
asvs_level: 1
created: 2026-05-07
verified: 2026-05-07
---

# Phase 05 — Security

> Per-phase security contract for the `cli-readme-acceptance` phase. Threat register consolidated from
> the five plan-level `<threat_model>` blocks (Plans 05-01..05-05). All threats have an explicit
> disposition (mitigate / accept) with documented evidence; `threats_open: 0`.

---

## Trust Boundaries

Aggregated across all five plans:

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| User shell → CLI | Untrusted argv (`--config PATH`, `--json`, pytest flags after `--`) | Path strings, boolean flags, opaque pytest argv |
| CLI → filesystem | `_load_config` reads `--config` path as `Path` (no eval, no glob expansion) | YAML overlay file contents |
| CLI → `os.environ` | `_load_config` writes `MCPTF_CONFIG_FILE` (process-local) | Path string |
| CLI → `pytest.main()` | `run` forwards unsanitized argv-suffix to pytest's own parser | pytest argv |
| CLI → MCP subprocess (homelab-mcp) | `stdio_client` launches `cfg.mcp_server.command` from owner-controlled config | Subprocess command + args |
| MCP subprocess → CLI stdout | Tool definitions flow through `Tool.model_validate` (mcp SDK Pydantic guard) before formatters | name, description, inputSchema, outputSchema |
| Live Ollama HTTP endpoint → CLI | Plan 05 SC#1 path; `httpx.Timeout` from Phase 3 | JSON judge response |
| Repo file (README.md, EXTENDING.md) → Reader | Static markdown; framework does not eval | Documentation text |
| Human Ctrl+C → Python interpreter | OS delivers SIGINT to foreground process | Signal |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-05-01-01 | Tampering | `_load_config` (cli.py:80) | mitigate | `path.is_file()` pre-flight rejects missing paths with exit 2; `pydantic-settings` + `yaml.safe_load` semantics — no arbitrary code execution. **Hardened by WR-02 fix (commit `ba81b3c`):** env var is popped on `Config()` failure so a stale `MCPTF_CONFIG_FILE` cannot leak across invocations. | closed |
| T-05-01-02 | Information Disclosure | `version` command | accept | Version string is public information (already in `pyproject.toml` and git history). | closed |
| T-05-01-03 | Denial of Service | `Config()` instantiation | accept | A malformed YAML overlay raises `ValidationError` and exits non-zero immediately; no resource exhaustion possible from a single `Config()` call. | closed |
| T-05-01-04 | Elevation of Privilege | `[project.scripts]` shim | accept | Shim runs with the user's own privileges; no setuid / elevation. | closed |
| T-05-01-05 | Repudiation | CLI invocation | accept | No audit-log requirement for MVP; pytest's stdout/stderr is sufficient. | closed |
| T-05-02-01 | Tampering | `pytest_args` forwarding (cli.py `run`) | accept | `--` forwarding is the explicit feature; user is the sole consumer of their own CLI. No privilege boundary crossed. | closed |
| T-05-02-02 | Denial of Service | `pytest.main()` | accept | Hangs are bounded by underlying SDK timeouts (`asyncio.timeout` in `McpTestClient`, `httpx.Timeout` in `OllamaJudge`); `run` deliberately adds no wall-clock cap (pytest convention: user kills it). | closed |
| T-05-02-03 | Information Disclosure | `_load_config` `ValidationError` | accept | Pydantic error messages may include field values; for a developer CLI on a developer machine, this is the desired diagnostic surface (CONTEXT.md Discretion bullet 2). | closed |
| T-05-02-04 | Repudiation (OPS-03) | `run` SIGINT teardown | mitigate | pytest's own SIGINT handler invokes finalizers; the `mcp_client` fixture's `AsyncExitStack` (Phase 04.1) unwinds in the same task that did `__aenter__`; `stdio_client._terminate_process_tree` reaps the subprocess. Verified by `tests/smoke/test_smoke_homelab_mcp.py` regression smoke and 05-UAT.md test 7. | closed |
| T-05-02-05 | Elevation of Privilege | `run` | accept | `run` adds no privilege escalation — runs pytest as the same user with the same env. | closed |
| T-05-03-01 | Tampering | `cfg.mcp_server.command` | accept | Owner-controlled config (env / YAML / .env). Trust model parity with `bash -c "$X"`; pydantic-settings does not eval the value. | closed |
| T-05-03-02 | Information Disclosure | `_format_tools_text` / `_format_tools_json` output | accept | Tool descriptions and schemas are intended to be displayed — they are the literal point of `list-tools`. No PII or secrets flow through this path. | closed |
| T-05-03-03 | Denial of Service | MCP subprocess hang | mitigate | `McpTestClient.list_tools()` wraps `session.list_tools()` in `asyncio.timeout(self._timeout_seconds)` (default 30s) at `mcp_client.py:189`. A hanging subprocess raises `TimeoutError`. | closed |
| T-05-03-04 | Repudiation (OPS-03) | Ctrl+C subprocess teardown on `list-tools` | mitigate | `asyncio.Runner` + `AsyncExitStack`-owned `McpTestClient` (cli.py:163, 197): KeyboardInterrupt unwinds the runner's task → `__aexit__` runs in the same task that did `__aenter__` → `stdio_client._terminate_process_tree` (mcp SDK) sends SIGTERM then SIGKILL on a 2.0s timer (Job Object on Windows). **Hardened by WR-05 fix (commit `deaf6b3`):** explicit `try/except KeyboardInterrupt → typer.Exit(code=130)` enforces the docstring's exit-code-130 guarantee. **Directly verified** by 05-UAT.md test 8 (live SIGINT → exit 130, clean stderr, no zombie subprocess). | closed |
| T-05-03-05 | Tampering | JSON output non-serializable schema content | accept | **Disposition rationale revised by WR-04 fix (commit `0b86565`):** the original plan accepted lossy stringification via `json.dumps(..., default=str)`. Code review (REVIEW.md WR-04) recategorized this as masking a real spec violation — MCP `inputSchema`/`outputSchema` MUST be JSON-serializable by contract. `default=str` was dropped; non-serializable content now raises `TypeError`. The new accepted-risk rationale is "fail loud on contract violation" (a strict-typing improvement, not a security regression). | closed |
| T-05-03-06 | Pitfall 4 (Windows ProactorEventLoop) | `asyncio.Runner` on Windows | mitigate | Python 3.14 default event loop on Windows is `ProactorEventLoop` (required for `stdio_client` subprocess support). `asyncio.Runner()` honors the platform default. Verified via Phase 04.1 same-task pattern shipped on Win11 and confirmed by 05-UAT.md tests 5/7/8 (live homelab-mcp on Windows). | closed |
| T-05-04-01 | Information Disclosure | README env-var table | accept | Default values shown (e.g., `http://127.0.0.1:11434`) reveal homelab topology. Repo is private; the IP is non-routable RFC1918 space. **Open-source pre-flight TODO:** replace homelab IP with a placeholder before any public publication. | closed |
| T-05-04-02 | Tampering | EXTENDING.md code samples | accept | Samples are illustrative; the user implements them in their own tree. Framework does not eval markdown. | closed |
| T-05-04-03 | Spoofing | EXTENDING.md OpenAIJudge example | accept | The example shows `api_key="..."` placeholder; users wire their own secret loading. | closed |
| T-05-05-01 | Repudiation | Live UAT capture authenticity | mitigate | Walkthrough doc (05-05-ACCEPTANCE-WALKTHROUGH.md) includes verbatim stdout/stderr captures with exit codes; 05-UAT.md cross-references against the captured behavior. | closed |
| T-05-05-02 | Denial of Service | Live homelab-mcp subprocess hang | mitigate | Same control as T-05-03-03 (`asyncio.timeout(30s)` in `McpTestClient.list_tools`). | closed |
| T-05-05-03 | OPS-03 (Pitfall 1 regression) | `asyncio.Runner` + `AsyncExitStack` lifecycle | mitigate | Original 05-05 verdict was PARTIAL PASS (SIGINT couldn't land mid-run on warm uvx cache). After WR-05 added an explicit `KeyboardInterrupt` handler, 05-UAT.md test 8 directly observed exit 130 + clean teardown — partial-pass upgraded to full pass. | closed |
| T-05-05-04 | Information Disclosure | Captured stdout in walkthrough doc | accept | Local-dev-machine output; `.planning/` is private to the repo. **Open-source pre-flight TODO:** scrub homelab-specific details before publishing. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-05-01 | T-05-01-02 | Version string is public information (`pyproject.toml`, git history). | Phase 05 plan author + UAT verifier | 2026-05-07 |
| AR-05-02 | T-05-01-03 | Malformed YAML raises `ValidationError` and exits immediately; no resource exhaustion vector. | Phase 05 plan author + UAT verifier | 2026-05-07 |
| AR-05-03 | T-05-01-04 | Console-script shim runs at user privilege; no setuid escalation. | Phase 05 plan author + UAT verifier | 2026-05-07 |
| AR-05-04 | T-05-01-05 | MVP scope: pytest stdout/stderr replaces dedicated audit log. | Phase 05 plan author + UAT verifier | 2026-05-07 |
| AR-05-05 | T-05-02-01 | `--` forwarding to pytest is the explicit feature; user is sole consumer. | Phase 05 plan author + UAT verifier | 2026-05-07 |
| AR-05-06 | T-05-02-02 | pytest convention: user-killed runs; SDK-level timeouts bound any hang. | Phase 05 plan author + UAT verifier | 2026-05-07 |
| AR-05-07 | T-05-02-03 | Developer-CLI surface; Pydantic error verbosity is desired diagnostic. | Phase 05 plan author + UAT verifier | 2026-05-07 |
| AR-05-08 | T-05-02-05 | Same-user execution; no privilege boundary in `run`. | Phase 05 plan author + UAT verifier | 2026-05-07 |
| AR-05-09 | T-05-03-01 | `cfg.mcp_server.command` is owner-controlled config; trust parity with `bash -c "$X"`. | Phase 05 plan author + UAT verifier | 2026-05-07 |
| AR-05-10 | T-05-03-02 | Tool descriptions and schemas are the intended display payload of `list-tools`. | Phase 05 plan author + UAT verifier | 2026-05-07 |
| AR-05-11 | T-05-03-05 | Revised by WR-04: non-serializable schema content now raises `TypeError` (fail loud on MCP contract violation). | Code review WR-04 fix | 2026-05-07 |
| AR-05-12 | T-05-04-01 | Repo currently private; RFC1918 IP. Open-source pre-flight TODO before publication. | Phase 05 plan author + UAT verifier | 2026-05-07 |
| AR-05-13 | T-05-04-02 | Markdown is not evaluated; users own their own integration trust. | Phase 05 plan author + UAT verifier | 2026-05-07 |
| AR-05-14 | T-05-04-03 | Placeholder `api_key` in code sample; users wire their own secrets. | Phase 05 plan author + UAT verifier | 2026-05-07 |
| AR-05-15 | T-05-05-04 | `.planning/` is private; open-source pre-flight TODO before publication. | Phase 05 plan author + UAT verifier | 2026-05-07 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-05-07 | 23 | 23 | 0 | /gsd-secure-phase 05 (orchestrator, State B initial creation) |

### Audit Notes (2026-05-07)

- **Source:** Threat register consolidated from the five `<threat_model>` blocks in `05-{01..05}-PLAN.md`. No `## Threat Flags` entries surfaced in any SUMMARY.md (no execution-time threat surprises).
- **Code-review fix interactions** (commits `f15de64..deaf6b3` from `/gsd-code-review-fix 05`):
  - **WR-01** (`pytest_args: list[str] | None`): no threat-register impact (typing correction only).
  - **WR-02** (`_load_config` env-var pop on failure): hardens T-05-01-01 — eliminates the cross-invocation env-var leak that the original plan only documented as intentional behavior.
  - **WR-03** (direct `outputSchema` attribute access): no threat-register impact (asymmetry removal; both fields already on `Tool`).
  - **WR-04** (drop `default=str`): revises T-05-03-05 rationale from "lossy JSON acceptable" to "fail loud on MCP contract violation." Net security posture improves (no silent contract violation).
  - **WR-05** (explicit `KeyboardInterrupt → typer.Exit(130)`): hardens T-05-03-04 — the SIGINT exit-code guarantee was previously a docstring claim; it is now syntactically enforced and directly UAT-verified (05-UAT test 8).
- **OPS-03 verdict upgrade:** Phase 05's earlier acceptance walkthrough (05-05-SUMMARY) recorded T-05-05-03 as PARTIAL PASS due to interrupt-window narrowness on the warm uvx cache. The WR-05 fix + 05-UAT.md test 8 supersede that with a directly-observed SIGINT → exit 130 + empty `Get-Process homelab-mcp`.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept)
- [x] Accepted risks documented in Accepted Risks Log (15 entries)
- [x] `threats_open: 0` confirmed (23/23 closed)
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-05-07
