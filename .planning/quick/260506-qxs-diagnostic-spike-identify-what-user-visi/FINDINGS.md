# Diagnostic Spike — homelab-mcp Host-State Surface (RECON)

**Date:** 2026-05-06
**Scope:** Identify user-visible state `homelab-mcp` touches when spawned as a subprocess by `mcp_test_framework`. Recommend isolation strategy for v1.1.
**Method:** Black-box external observation — CLI `--help` (top-level + `credentials` subcommand), before/after dir snapshot of conventional state paths, wider USERPROFILE depth-3 `homelab*` glob, process/port inventory, env scan, OS keyring inventory filtered to homelab/mcp targets. No source files read.

---

## 1. State homelab-mcp creates/mutates

### Confirmed user-visible state surface

| Kind | Path / Identifier | Observed when | Evidence (raw/*) |
|------|-------------------|---------------|------------------|
| **registry file** (JSON) | **`%USERPROFILE%\.homelab_mcp\credential_registry.json`** (1940 bytes, mtime 2026-05-04) | already present (user has live install) | `raw/discovered_state_dir.txt`, `raw/wider_scan.txt` |
| **SSH known_hosts** | **`%USERPROFILE%\.homelab_mcp\known_hosts`** (6252 bytes, mtime 2026-05-04) | already present | `raw/discovered_state_dir.txt` |
| **migration state** (JSON) | `%USERPROFILE%\.homelab_mcp\migration_state.json` (136 bytes, mtime 2026-04-26) | already present | `raw/discovered_state_dir.txt` |
| **OS keyring entries** (Windows Credential Manager) | **~20 entries with `target=*@homelab-mcp` or `target=*@homelab-mcp-proxmox`** (e.g. `LegacyGeneric:target=root@192.168.10.20@homelab-mcp`) | already present | `raw/keyring.txt` |
| process | `homelab-mcp` PID 28752 from `C:\Users\washy\projects\mcp_python_server\.venv\Scripts\homelab-mcp.exe`, started 2026-05-06 18:33 | running before the spike | `raw/processes.txt` |
| listening socket | NONE (PID 28752 is not in `LISTENING` set) — confirms stdio-mode operation, no daemon socket | n/a | `raw/listening_ports.txt` |
| cwd-relative writes | NONE OBSERVED in repo working tree post-`uvx homelab-mcp --version` | after handshake | derived from `git status` being clean for tracked paths after captures |

### Mutations observed across before/after handshake

**None at the file level.** `raw/before.txt` vs `raw/after.txt` show identical contents for every conventional candidate path (`%APPDATA%\homelab-mcp`, `%LOCALAPPDATA%\homelab-mcp`, `~/.config/homelab-mcp`, etc.) — all `ABSENT` in both snapshots. The lone existing state dir (`~/.homelab_mcp\` with the underscore variant) was discovered later via the wider scan; its mtimes (2026-05-04, 2026-04-26) predate this spike, so we have no evidence it was *mutated* by our `--version` invocation. See §5 for why this likely understates true mutation pressure.

### Discovery delta vs original candidate list

Hypothesis paths from the originating todo and `<known_unknowns>` named the directory as `~/.config/homelab-mcp` or `~/.homelab-mcp` (XDG / hyphen). The actual path on this host is **`~/.homelab_mcp`** — root-of-home, **underscore variant**. The original BEFORE candidate list (raw/before.txt) missed it; the depth-3 USERPROFILE glob in `raw/wider_scan.txt` caught it. Addenda are appended to before.txt and after.txt linking to `discovered_state_dir.txt`.

### What this means for the framework

The framework's `Config.mcp_server.command` defaults to bare `"homelab-mcp"` (`src/mcp_test_framework/models.py:51`) and `args=[]`. `McpTestClient.__aenter__` does `shutil.which(self._command)` and then hands `StdioServerParameters` to `stdio_client` with no `env=` override. **Result: the spawned subprocess inherits the parent's full environment, including `USERPROFILE`/`HOME`, and therefore reads/writes the SAME `~/.homelab_mcp/credential_registry.json` and the SAME OS keyring entries the user's daily install touches.** That is the bleed-through.

Bonus complication observed in `raw/processes.txt`: the user's running daemon is the *source-venv* install at `mcp_python_server\.venv\Scripts\homelab-mcp.exe`, while `uvx homelab-mcp` resolves to a *PyPI-cached* install at `C:\Users\washy\AppData\Local\uv\cache\archive-v0\VOAyoI199Rl6EAPPV0hE1\Scripts\homelab-mcp` (1.7.0 per `--version`). They are different binaries / different versions / different code paths but share the user-state directory and keyring — so isolation cannot rely on "different install = different state."

## 2. Isolation knobs available

### CLI flags (from `raw/help.txt`)

| Flag | Purpose (from help text) | Confidence |
|------|--------------------------|------------|
| `--http` | Run in HTTP mode instead of stdio mode | direct quote |
| `--host HOST` | HTTP server host (default: 127.0.0.1) | direct quote |
| `--port PORT` | HTTP server port (default: 8080) | direct quote |
| `--no-auth` | Disable API key authentication | direct quote |
| `--api-key API_KEY` | API key for authentication | direct quote |
| `--ssl-cert SSL_CERT` | Path to SSL certificate file (enables HTTPS) | direct quote |
| `--ssl-key SSL_KEY` | Path to SSL private key file | direct quote |
| `--version`, `-h/--help` | meta only | direct quote |
| `credentials` (subcmd) | Manage stored credentials (add/list/remove/link/unlink) | direct quote |

**No isolation flag exists.** There is **no `--config`, `--config-dir`, `--data-dir`, `--state-dir`, `--cache-dir`, `--registry`, `--workdir`, `--profile`, `--no-state`, `--ephemeral`** in the documented top-level surface (raw/help.txt lines 13–22). The only persistence-adjacent options (`--ssl-cert`, `--ssl-key`) take filesystem paths but only for HTTPS material — they don't redirect the registry. The `credentials` subcommand mutates the same keyring; no `--keyring-backend` option is exposed (raw/help.txt lines 43–58).

### Environment variables

**(a) Variables explicitly named in `--help` output:** none. Help text mentions zero env vars.

**(b) Conventional vars XDG-respecting Python apps honor:** even if homelab-mcp respects them on POSIX, the registry path `~/.homelab_mcp/` (root-of-home with underscore) is **not XDG-conformant** — XDG would put it at `$XDG_CONFIG_HOME/homelab-mcp/` (hyphen, under `.config/`). The fact that homelab-mcp invented its own root-of-home path suggests it does **not** use XDG conventions, which means `XDG_CONFIG_HOME=<tmpdir>` would be ignored on this Windows host AND on POSIX.

| Env var | Source (help / convention) | Path it would redirect | Confidence |
|---------|---------------------------|------------------------|------------|
| `HOME` (POSIX) / `USERPROFILE` (Windows) | OS convention — Python's `os.path.expanduser('~')` reads these | `~/.homelab_mcp/credential_registry.json`, `~/.homelab_mcp/known_hosts`, `~/.homelab_mcp/migration_state.json` | **HIGH** — `~/.homelab_mcp/` IS root-of-home, so any code that expands `~` will follow whatever HOME/USERPROFILE we set. This is the redirection lever for all three FILE artifacts in §1. |
| `XDG_CONFIG_HOME` / `XDG_DATA_HOME` / `XDG_CACHE_HOME` | XDG convention | None on this host (homelab-mcp doesn't use XDG) | LOW — non-XDG dir layout per §1 |
| `APPDATA` / `LOCALAPPDATA` | Windows convention | None on this host (homelab-mcp doesn't use these) | LOW — both candidates absent in before/after |
| `MCP_CONNECTION_NONBLOCKING` | currently set in env (`raw/env_scan.txt`) | unknown — not documented in `--help`; appears MCP-protocol-related rather than state-redirecting | UNKNOWN |
| **OS keyring backend** | not env-controllable from outside the source | **none of the above** | **NONE** — keyring entries are owned by Windows Credential Manager (system service, accessed via Win32 API). No `HOME` redirect can move them. See §3 for implications. |

### Currently-set HOMELAB_* / MCP_* env vars

From `raw/env_scan.txt`:

```
MCP_CONNECTION_NONBLOCKING=true
```

That's the only match. No `HOMELAB_*` env vars set. So the user's existing config is **not** env-driven for state location — confirming env-var-based isolation must be set explicitly by the framework, not inferred from the user's existing setup.

## 3. Recommended isolation strategy

**Recommendation:** **per-session tempdir + `HOME`/`USERPROFILE` env override** at the subprocess-spawn boundary in `src/mcp_test_framework/mcp_client.py` (and the parallel spawn in `src/mcp_test_framework/fixtures.py:_owner_task`).

**Rationale:**

- **§1 says the file artifacts live at `~/.homelab_mcp/*`** — root-of-home. Whatever logic homelab-mcp uses to compute that path almost certainly resolves `~` via `os.path.expanduser('~')`, which on Python honors `HOME` first then `USERPROFILE` on Windows. Setting `HOME=<tmpdir>` and `USERPROFILE=<tmpdir>` on the spawned subprocess will redirect the registry, known_hosts, and migration_state writes into the tempdir — without needing a CLI flag homelab-mcp doesn't expose (§2 confirms none exists).
- **§2 confirms no CLI flag and no documented env var can redirect state**, ruling out the "lighter" CLI-flag strategy. The cwd-redirect strategy alone is insufficient because `~/.homelab_mcp/` is not cwd-relative.
- **Implementation seam:** the patch lives in `src/mcp_test_framework/mcp_client.py` where `StdioServerParameters(command=..., args=...)` is built — the `mcp` SDK's `StdioServerParameters` accepts an `env=` parameter that gets passed to `anyio.open_process`. Build the env dict once in the `mcp_client` fixture (`src/mcp_test_framework/fixtures.py:175`), include the tempdir-overriding `HOME`/`USERPROFILE`/`TEMP`/`TMP`/`TMPDIR`, and pass through anything else from `os.environ` that homelab-mcp legitimately needs (e.g. `PATH`, `SYSTEMROOT` on Windows). The session-scoped `tempfile.TemporaryDirectory` is created in a new fixture (or inlined into `mcp_client`) and torn down after the session ends.
- **Container is unwarranted** for v1.1: the file surface is small (3 files in one dir), there's no daemon, no port, no IPC outside stdio, and the keyring problem (see fallback) is not solved by containers without keyring-mocking inside the container anyway.

**Critical caveat — keyring is NOT redirected by `HOME`:** §1 documents ~20 Windows Credential Manager entries with `target=*@homelab-mcp`. These are owned by the OS service, not the filesystem; `HOME=<tmpdir>` does not move them. **If the test suite ever invokes `credentials add/remove` (directly or transitively via tool calls that trigger credential lookup), it will mutate the user's real keyring.** Mitigations to evaluate during v1.1 planning:
  1. Verify the test suite's target tool (`list_registered_servers`) does NOT touch the keyring — it likely only reads `credential_registry.json`. If true, `HOME` redirect is sufficient for v1.1's current test surface.
  2. If keyring access is unavoidable, inject `PYTHON_KEYRING_BACKEND=keyring.backends.null.Null` (or `keyrings.alt.file.PlaintextKeyring` pointing at the tempdir) in the spawned env. The `keyring` library reads this env var at import time. Confirmation requires §5 follow-up.
  3. Worst case: deny network egress to homelab IPs from the test process so even if a credential is read, no harm reaches the real homelab. Out of scope for v1.1 but document.

**Fallback strategy** (if primary turns out to be insufficient during v1.1 implementation): **`PYTHON_KEYRING_BACKEND=keyring.backends.null.Null` + `HOME` override**, layering keyring isolation on top of the tempdir. Trigger: any v1.1 test that exercises a tool that touches credentials (transitively or directly) starts mutating real keyring entries during a green run.

**Out of scope for v1.1:** container/VM isolation. Trigger condition that would escalate to it: (a) homelab-mcp turns out to ignore `HOME` and uses a hard-coded absolute path, (b) the keyring-backend env var is also ignored, (c) tests need to exercise the SSH `known_hosts` flow against real hosts (which would require network isolation, not just filesystem isolation).

## 4. Effort estimate

| Component | Estimate | Notes |
|-----------|----------|-------|
| Plumb tempdir + env-override knobs through `Config` (`config.py`, `models.py`) | **1.5 h** | New optional sub-model `IsolationConfig { isolate: bool=True, extra_env: dict[str,str]={} }`; one alias on `McpServerConfig.env` if we want users to inject more vars. Tests for the bare-name env routing path (already non-trivial — see plan-checker BLOCKER #1 in 01-02-PLAN.md). |
| Wire isolation into the subprocess spawn | **2 h** | Change `StdioServerParameters(command=..., args=...)` callsites in `mcp_client.py:143` and `fixtures.py:208` to include `env={...}`. Build the env dict from a passthrough allowlist (`PATH`, `SYSTEMROOT`, `USERNAME`, `LANG`, …) plus the override (`HOME`, `USERPROFILE`, `TEMP`, `TMP`, `TMPDIR`). Add a comment block citing this FINDINGS.md. |
| Session-scoped tempdir lifecycle in `fixtures.py` | **1.5 h** | New `@pytest_asyncio.fixture(scope="session")` `_isolated_home` that yields a `tempfile.TemporaryDirectory` path; depended on by `mcp_client`. Cleanup automatic via context-manager exit. |
| New tests asserting isolation | **3 h** | Two test classes: (a) post-`mcp_client` session, assert `<tmpdir>/.homelab_mcp/` exists with the 3 expected files (or some subset, since `list_registered_servers` may only touch the registry) AND assert `~/.homelab_mcp/{credential_registry.json,known_hosts,migration_state.json}` mtimes are unchanged from before the run. (b) Process-list assertion that the spawned child's open file handles do not include the user's real registry path (Windows: `handle.exe` from Sysinternals or `Get-Process \| Select-Object -ExpandProperty Modules`; POSIX: `/proc/<pid>/fd/`). |
| Cross-platform validation (POSIX + Windows) | **2 h** | The `HOME` vs `USERPROFILE` discrepancy is the obvious cross-platform pitfall. CI-style smoke run on Linux + Windows; check that `os.path.expanduser('~')` inside the subprocess actually expands to the tempdir under both. |
| Keyring caveat investigation (§3 caveat #1) | **1 h** | Manually trace whether `list_registered_servers` triggers keyring access — observation only, not source-read; either run the existing TEST-05 / TEST-06 suite against the isolated tempdir and check `cmdkey /list` diff, or read the public homelab-mcp PyPI README for documented keyring touchpoints. |

**Total: ~11 hours, spread across 1–2 working days.** Calibration: the v1.0 phases averaged 1–2 day plans (e.g. Phase 04 fixtures landed in two plans of ~1 day each per `.planning/MILESTONES.md`); this fits the same envelope. **Confidence: MEDIUM** — the core HOME-override change is small, but the cross-platform tests and the keyring caveat could double the estimate if the assumptions in §3 don't hold.

## 5. Open questions

1. **Does homelab-mcp respect `HOME`/`USERPROFILE` for `~/.homelab_mcp/` resolution, or does it use a hardcoded absolute path?** This spike confirms the path exists and suggests `os.path.expanduser('~')` is involved, but cannot prove the resolution mechanism without reading source. **What would answer it:** the v1.1 implementation's first integration test — set `HOME=<tmpdir>` on a spawned subprocess, run the suite, then check whether `<tmpdir>/.homelab_mcp/` was created. If it wasn't, the assumption is wrong and we fall back to the keyring-style env-var override pattern OR to the originating-todo's strategy 4 (container).
2. **Does `list_registered_servers` (the v1.0 / v1.1 target tool) read or write the keyring at all?** §1 names ~20 Credential Manager entries; §3 caveat is the largest risk to the recommended strategy. **What would answer it:** snapshot `cmdkey /list | findstr homelab` before and after `pytest tests/test_homelab_list_registered_servers.py` — if no diff appears, the tool is registry-read-only and the keyring is safe. (Could be done in a follow-up spike or as the first task of v1.1.)
3. **Is `MCP_CONNECTION_NONBLOCKING=true` (currently set in the user's env, per `raw/env_scan.txt`) something the framework should propagate to its isolated subprocess, or strip?** Help text doesn't mention it; appears MCP-protocol-related. **What would answer it:** PyPI README of `homelab-mcp` and/or `mcp` SDK documentation (out-of-band doc check, not source read).
4. **Are there hidden CLI flags not documented in `--help` (e.g. `--debug-config`, `--state-dir` reserved for testing)?** **What would answer it:** ask the upstream maintainer of `homelab-mcp` directly OR read the PyPI README. Do NOT solve by reading source.
5. **Does the framework's preflight handshake (`fixtures.py:_preflight`) actually trigger registry writes, or only reads?** `raw/before.txt` vs `raw/after.txt` showed no file-level mutation, but only because we substituted `uvx homelab-mcp --version` for the full pytest invocation (per the plan's degradation-allowed clause and the constraint about not disturbing the user's running daemon). **What would answer it:** rerun the snapshot diff with the framework's actual integration test once v1.1 isolation is in place — that lets us measure mutation pressure against a tempdir without putting the user's real state at risk. This is a self-resolving question once §1's primary recommendation is implemented.
6. **Does `homelab-mcp` write to `cwd` for any operation we didn't trigger (e.g. logs, dumps)?** `git status` post-handshake is clean for tracked paths, but the working directory wasn't a tempdir — could have been written elsewhere on disk. **What would answer it:** spawn into `cwd=<tmpdir2>` and snapshot it post-run. Easy to add to v1.1 isolation tests.
7. **Are there homelab-mcp PIDs that survive past the `stdio_client` AsyncExitStack unwind?** `raw/processes.txt` only captures one snapshot, after the user's pre-existing daemon was already running; we don't know if our `uvx --version` left a child behind. **What would answer it:** v1.1 should include a test that asserts no new homelab-mcp process exists 5s after `mcp_client` fixture teardown — the v1.0 SIGINT scaffold deferred in STATE.md "Deferred Items" is the same problem.

---

**Raw evidence:** see `raw/` subdirectory.
- `raw/help.txt` — top-level + `credentials` subcommand `--help` output
- `raw/before.txt`, `raw/after.txt` — conventional state-dir snapshots (with addenda pointing at the underscore-variant discovery)
- `raw/wider_scan.txt` — depth-3 USERPROFILE glob that uncovered `~/.homelab_mcp/`
- `raw/discovered_state_dir.txt` — contents (filenames + sizes + mtimes only) of `~/.homelab_mcp/`
- `raw/keyring.txt` — `cmdkey /list` filtered to `homelab`/`mcp` targets
- `raw/processes.txt` — running `homelab-mcp`, `python`, `uv`, `uvx` processes at capture time
- `raw/listening_ports.txt` — full LISTENING port inventory (homelab-mcp PID 28752 absent, confirming stdio-only)
- `raw/env_scan.txt` — `HOMELAB_*`, `MCP_*`, `XDG_*` env vars (only `MCP_CONNECTION_NONBLOCKING=true` set)
- `raw/handshake.log` — caveat note explaining why we substituted `uvx --version` for a full pytest run
