# Milestones — mcp_test_framework

A running log of shipped versions. Each entry summarizes what was delivered; full archives live in `.planning/milestones/v[X.Y]-*.md`.

---

## v1.0 — MVP

**Shipped:** 2026-05-06
**Phases:** 7 (01, 02, 02.1, 03, 04, 04.1, 05)
**Plans:** 22 / 22 complete
**Requirements:** 29 / 29 satisfied
**LOC:** ~3,562 Python (`src/` + `tests/`)
**Commits:** 166
**Timeline:** 2026-05-04 → 2026-05-06 (3 days)

**Delivered:** A `pytest`-runnable test framework that drives one MCP tool end-to-end (schema → call → judge) over stdio against `homelab-mcp`, with `mcp-test-framework run|list-tools|version` CLI; live green at 67 passed, exit 0.

**Key accomplishments:**

1. End-to-end pytest framework — `uv run mcp-test-framework run` produces `67 passed, exit 0` against live `homelab-mcp` (via `uvx`) + Ollama (`qwen3.6:latest` @ `127.0.0.1:11434`)
2. Black-box rule mechanically enforced — `ruff TID251` ban + `tests/conftest.py` `sys.modules` guard + dedicated banned-imports unit test
3. Async stdio MCP client with clean teardown — owner-task + `anyio.Event` lifecycle (Phase 04.1 fix); zero leftover `homelab-mcp.exe` on Windows
4. Ollama judge with qwen3 belt-and-braces — `<think>` strip, `format:json`, `temperature:0`, `keep_alive:30m`, parse-failure fallback preserving `raw_response`; cold-start timeouts wrapped
5. `Judge` Protocol seam shipped in MVP — zero-cost backend swap post-MVP (JUDGE-01)
6. Typer CLI with three commands — `run` (CLI-01), `list-tools` (CLI-02), `version` (CLI-03); SIGINT exit 130 with explicit handler (WR-05); README + `docs/EXTENDING.md`
7. Layered config — `CLI > env > YAML > defaults` via `pydantic-settings[yaml]`, frozen `Config` with custom bare-name nested env source

**Decimal phases (mid-milestone insertions):**

- Phase 02.1: Close Phase 2 verification gaps (config + UAT) — reconciled `uvx homelab-mcp` invocation, ran live UAT, flipped Phase 2 to passed
- Phase 04.1: McpTestClient session-teardown fix — owner-task + `anyio.Event` rewrite resolved `RuntimeError: Attempted to exit cancel scope in a different task`

**Overrides accepted (3 total, all justified):**

- DEF-04-03-A: `list_registered_servers` description fails rubric → resolved by config switch to `list_keyring_credentials` in Phase 5; framework working as designed; upstream description fix tracked for v2
- DEF-04-03-B: `anyio` cancel-scope teardown error → reassigned to and resolved in Phase 04.1
- OPS-03 PARTIAL PASS (Phase 5) → functionally superseded by WR-05 fix + 05-UAT.md test 8 (live SIGINT exit 130 directly observed); override remains in audit trail

**Known deferred items (carried to v2):**

- Upstream `homelab-mcp` `list_registered_servers` description fix (JUDGE/GEN territory)
- Automated cross-platform SIGINT UAT scaffolding (would need `Get-Process`/`pgrep` + programmatic SIGINT delivery helper)
- Open-source pre-flight scrub: homelab IP from README + homelab-specific captures from `.planning/` (only triggers if/when the repo goes public)

**Process gap (documentation hygiene, not a coverage gap):**

- Phase 04.1 missing 04.1-VERIFICATION.md — UAT.md `status:complete` is the load-bearing evidence and is referenced by Phase 5's threat model and 05-UAT.md test 8

**Archives:**
- `.planning/milestones/v1.0-ROADMAP.md` — full phase + plan details
- `.planning/milestones/v1.0-REQUIREMENTS.md` — final state of 29 v1 requirements (all complete)
- `.planning/milestones/v1.0-MILESTONE-AUDIT.md` — pre-close audit report (passed; 29/29 reqs, 7/7 phases, 8/8 flows)

**Tag:** `v1.0`
