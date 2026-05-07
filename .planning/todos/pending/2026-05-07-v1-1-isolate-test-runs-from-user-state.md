---
created: 2026-05-07T02:22:24.300Z
title: v1.1 hard requirement — isolate test runs from user-visible homelab-mcp state
area: testing
resolves_phase: 6
files:
  - src/mcp_test_framework/mcp_client.py
  - src/mcp_test_framework/fixtures.py
  - src/mcp_test_framework/config.py
---

## Problem

The framework currently spawns `homelab-mcp` as a subprocess for each test session via `stdio_client`. The subprocess appears to be sharing state with the user's real `homelab-mcp` instance — user reported (2026-05-06) that they cannot use homelab-mcp normally because tests bring up an instance, tear it down, and seem to clear any running instance / mutate registry state at the start of the run.

This is a **current usability bug** (the framework breaks the user's daily use of the tool it tests) AND a **v1.1 design constraint**: v1.1 expands to multi-tool testing, which means more spawns, more teardowns, more potential bleed-through. If v1.1 ships without isolation, the problem gets strictly worse.

The framework treats homelab-mcp as a black box (CLAUDE.md rule), so isolation must be achievable via env vars and CLI args — we cannot read or modify homelab-mcp source.

## Solution

**Acceptance criterion for v1.1:** "Test runs MUST NOT mutate any user-visible state on the host. Running the test suite while a real homelab-mcp instance is in use must not affect that instance's registry, config, sockets, or processes."

**Investigation precedes design.** A diagnostic spike (separate todo / `/gsd-quick` task) needs to identify exactly which paths/sockets/processes homelab-mcp touches when launched. Likely candidates:

- Config / data dirs: `~/.config/homelab-mcp/`, `$XDG_CONFIG_HOME`, `$XDG_DATA_HOME`
- Lock / PID files in shared locations
- A registry / database file (likely, given `list_registered_servers` exists)
- Network sockets, named pipes, or daemon processes
- CWD-relative writes

**Isolation strategies, lightest to heaviest:**

1. **Per-session tempdir + env override.** Spawn subprocess with `HOME=<tmpdir>`, `XDG_CONFIG_HOME=<tmpdir>/.config`, `XDG_DATA_HOME=<tmpdir>/.local/share`. Cheapest if homelab-mcp respects XDG. Cleanup via `tempfile.TemporaryDirectory`.
2. **CLI flag if homelab-mcp exposes one.** Run `homelab-mcp --help` to scan for `--config-dir`, `--data-dir`, `--state-dir`, etc. If present, this is the cleanest answer and the most explicit.
3. **Subprocess in a temp working directory.** `cwd=tmpdir` covers tools that read/write relative to CWD. Cheap; combine with strategy 1.
4. **Container or VM.** Heaviest, most reliable, but adds docker/podman as a test dep. **Out of scope for v1.1** — flag if the spike reveals strategies 1–3 are insufficient.

**Implementation seam:** isolation lives in `src/mcp_test_framework/mcp_client.py` (where the subprocess is launched) and `src/mcp_test_framework/fixtures.py` (where the session-scoped lifecycle is defined). The session-scoped tempdir must be created before the `mcp_client` fixture spawns the subprocess and torn down after the fixture exits.

**Anti-pattern to avoid:** Do NOT let v1.1 design absorb "we'll fix isolation later." This is a v1.1 deliverable. The seeds (SEED-003, SEED-004) explicitly depend on v1.1 making good architectural choices; isolation is one of them.

**Cross-references:**
- Related diagnostic spike: kicked off via `/gsd-quick` (separate task) on 2026-05-07
- v1.1 milestone scoping conversation: see chat log 2026-05-06/07
- SEED-004 (stateful tool testing) inherits whatever isolation pattern this work establishes — design it cleanly
