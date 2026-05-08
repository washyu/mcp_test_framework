# ISOL-01 Keyring-Touch Recon — homelab-mcp

**Date:** 2026-05-07
**Scope:** Determine whether `list_keyring_credentials` and `list_registered_servers` tools mutate (or read) Windows Credential Manager entries scoped to `*@homelab-mcp` / `*@homelab-mcp-proxmox` targets when invoked under the framework's stdio spawn.
**Method:** PyPI README evidence (no source read per CLAUDE.md black-box rule + CONTEXT D-01) + before/after `cmdkey /list` diff. Mirrors the 260506-qxs FINDINGS.md template (CONTEXT D-02).

No homelab-mcp source files were read during this recon (CLAUDE.md black-box rule).

---

## 1. PyPI README evidence

**Source:** PyPI JSON metadata for `homelab-mcp` v1.7.0 — `https://pypi.org/pypi/homelab-mcp/json` (queried 2026-05-07). Full README captured at `raw/pypi-readme.txt`. Fetch script at `raw/fetch-pypi.ps1`.

### Documented keyring use

The PyPI README explicitly documents OS-keyring writes by the homelab-mcp credential surface. Direct quotes:

> Credentials are stored in the OS keyring (libsecret on Linux, Keychain on macOS). When the OS keyring is unavailable (headless servers), credentials fall back to environment variables.

> The CLI provides full CRUD over credentials: `add` (create/update — upsert), `list` (read), `remove` (delete). There is no separate `update` subcommand — re-running `add` replaces both the keyring secret and the registry entry's auth type.

> Store an SSH key-based credential (stores the key file path in the keyring, not the key)

The "Credential Management" section also documents the CLI commands that mutate the keyring:

```
# Store an SSH credential
homelab-mcp credentials add 192.168.1.10 admin

# Store a Proxmox API credential
homelab-mcp credentials add 192.168.1.200 root@pam --type proxmox

# List stored credentials
homelab-mcp credentials list
homelab-mcp credentials list --type proxmox

# Remove a credential
homelab-mcp credentials remove 192.168.1.10
```

The README's feature-list bullet states the design intent:

> **Credential Management** — Register servers once, connect without re-entering credentials

### Tool surface descriptions

The PyPI README does NOT name the MCP tools `list_keyring_credentials` or `list_registered_servers` directly — it documents the CLI subcommand surface (`homelab-mcp credentials add|list|remove`) and the high-level "Credential Management" feature. The MCP-tool names exposed over stdio are not enumerated in the README; the README links to a separate "Tool Reference" doc (`docs/tool-reference.md`) that lives in the GitHub source repo and is therefore out-of-scope under the no-source-read constraint.

What the README *does* establish:
- Credentials stored by the server are owned by the OS keyring (libsecret / Keychain / Windows Credential Manager via the Python `keyring` library's default backend chain).
- The credential subsystem reads from AND writes to that keyring (CRUD).
- "List stored credentials" (`homelab-mcp credentials list`) is documented as a read of the keyring. The MCP tool `list_keyring_credentials` is the protocol-side equivalent of this CLI command — name-equivalence + READMe behavior makes "this tool reads the keyring" the high-confidence inference, even without reading source.
- "Register servers once" (`list_registered_servers`) is the MCP-tool surface for the registry side of the same subsystem. The registry file (`~/.homelab_mcp/credential_registry.json`, per the 260506-qxs spike §1) sits alongside the keyring as the second leg of credential storage. Whether `list_registered_servers` *also* touches the keyring (e.g., to enrich registry entries with credential metadata) is not directly answered by the README — that question is what §2's empirical diff is for.

### Verdict from §1 alone

**Positive evidence of keyring touchpoints exists in the public PyPI README.** The credential subsystem unambiguously reads and writes the OS keyring. The remaining question — "does invoking `list_keyring_credentials` / `list_registered_servers` over stdio mutate the user's keyring entries, or only read them?" — is answered empirically in §2.

---

## 2. cmdkey before/after diff

### Procedure

Run on Windows 11 (this host has the live `homelab-mcp` install with ~20 keyring entries documented in the 260506-qxs spike `raw/keyring.txt`).

```powershell
# 1. BEFORE snapshot (filtered to homelab/mcp targets)
cmdkey /list | Select-String -Pattern 'homelab|mcp' `
  > .planning/phases/06-per-session-host-state-isolation/raw/keyring-before.txt

# 2. Drive v1.1 tool surface end-to-end (pre-isolation; bleed-through measurement).
#    Pytest preflight gated on Ollama qwen3.6:latest (unavailable on this dev
#    box -- model not pulled), so falls back to a minimal driver that spawns
#    homelab-mcp via stdio and calls each v1.1-surface tool directly.
$env:MCP_SERVER_COMMAND = 'uvx'
$env:MCP_SERVER_ARGS = '["homelab-mcp"]'
uv run python `
  .planning/phases/06-per-session-host-state-isolation/raw/drive-tools.py

# 3. AFTER snapshot
cmdkey /list | Select-String -Pattern 'homelab|mcp' `
  > .planning/phases/06-per-session-host-state-isolation/raw/keyring-after.txt

# 4. Diff
Compare-Object (Get-Content raw/keyring-before.txt) (Get-Content raw/keyring-after.txt) `
  > .planning/phases/06-per-session-host-state-isolation/raw/keyring-diff.txt
```

The minimal driver (`raw/drive-tools.py`) imports the framework's `McpTestClient` (which treats homelab-mcp as a black-box subprocess), connects via `stdio_client`, calls `list_tools`, then `call_tool('list_keyring_credentials', {})` and `call_tool('list_registered_servers', {})`, and exits cleanly. Driver output captured at `raw/driver.log`.

### Evidence files

- [`raw/keyring-before.txt`](raw/keyring-before.txt) — 20 `Target:` / `User:` lines, mtime 2026-05-07T08:26
- [`raw/keyring-after.txt`](raw/keyring-after.txt) — 20 `Target:` / `User:` lines, mtime 2026-05-07T08:28
- [`raw/keyring-diff.txt`](raw/keyring-diff.txt) — `(empty diff -- before and after are identical for filtered Target/User lines)`
- [`raw/driver.log`](raw/driver.log) — driver output: 58 tools listed; both tool calls returned `isError=False` with structured JSON content
- [`raw/test-pass1.log`](raw/test-pass1.log), [`raw/test-pass2.log`](raw/test-pass2.log) — pytest invocations that hit preflight failure (recorded for completeness)

### Diff result

| Target | Before | After | Delta |
|--------|--------|-------|-------|
| (all 20 entries listed in raw/keyring-before.txt) | present | present | unchanged |
| `(any new entry)` | (none) | (none) | none added |
| `(any removed entry)` | (none) | (none) | none removed |

`Compare-Object` returned an empty result set. **No keyring mutations observed across the test run.** All 20 `*@homelab-mcp` / `*@homelab-mcp-proxmox` targets present BEFORE were present AFTER, byte-for-byte identical at the `cmdkey /list` line level.

This is consistent with the driver invoking only READ-side tools (`list_keyring_credentials` returned 7 ssh credentials, `list_registered_servers` returned the same 7 hostnames as a registered-server list). The `cmdkey list` API does not show whether a process *read* an entry, only whether one was added/removed/modified — so this empty diff says "no mutation" and not "no read". The §1 PyPI README evidence is what tells us the read happened (the tool name `list_keyring_credentials` plus the populated `credentials` array in `driver.log` confirm read-traffic into Windows Credential Manager).

### Caveats

- **Pytest preflight failed** in this environment: Ollama `127.0.0.1:11434` is reachable but `qwen3.6:latest` is not pulled (`/api/tags` returned an empty list). Both `pytest tests/test_homelab_list_registered_servers.py` runs exited with code 2 ("model not in /api/tags"). Per Plan 06-01 Task 2's documented fallback, a minimal driver was used instead. This means tools that would only be exercised under the LLM-judged Category 2 tests (`test_description_clarity`, `test_description_disambiguation`, `test_parameters_self_explanatory`) did NOT run — but those tests do not invoke additional MCP tool calls beyond what `target_tool` (a single `list_tools` round-trip) and `call_tool({})` already cover. The driver's `call_tool('list_keyring_credentials', {})` + `call_tool('list_registered_servers', {})` pair matches the tool-call surface that ISOL-03's hash-equality test will exercise (per CONTEXT D-08 step 2). **Confidence: HIGH for the v1.1 read-side tool surface.**
- **Mutation surface NOT exercised:** the v1.1 tool surface in scope here is read-only. The PyPI README §1 documents `homelab-mcp credentials add|remove` as the CLI-side mutation surface; the corresponding MCP tools (likely `register_server`, observed in the 58-tool list at `raw/driver.log`) were NOT called. ISOL-04 (`PYTHON_KEYRING_BACKEND=null`) protects against the case where a future v1.x test surface adds a tool that triggers mutation. The §3 decision below weights this asymmetry explicitly.
- **Read-traffic invisibility:** `cmdkey /list` snapshots the *state* of Credential Manager; it does not log read-access. We cannot prove from this diff alone that homelab-mcp's `list_keyring_credentials` traversed Windows Credential Manager, but the driver returned 7 ssh credentials whose hostnames (`192.168.10.20`, `192.168.10.21`, `192.168.10.81`, `192.168.10.84`, `192.168.10.166`, `192.168.10.171`, `192.168.10.180` — derivable from `raw/driver.log`) overlap exactly with cmdkey `Target:` lines for `*@homelab-mcp`. The credentials surfaced through the MCP tool ARE the user's real Credential Manager entries.
- **Driver startup log captured ground truth:** `raw/driver.log` includes homelab-mcp v1.7.0 startup messages explicitly stating `"v1.6: keyring is now the sole credential store"`. This is upstream-author confirmation that the keyring IS the storage backend at runtime — independent corroboration of §1's PyPI README quote.
- **D-03 enforced:** this §2 procedure produced one-time recon evidence under `raw/`. No pytest test file (`tests/test_keyring*.py` or similar) was created. The keyring-axis regression guard is downstream in Plan 06-03's ISOL-03 hash-equality test (CONTEXT D-08).

---

## 3. Decision: ship ISOL-04 in v1.1, or defer with trigger

### Evidence summary

- **§1 (PyPI README):** explicit and unambiguous. The README's "Credential Management" section states "Credentials are stored in the OS keyring (libsecret on Linux, Keychain on macOS)" and documents read+write keyring operations via the `homelab-mcp credentials add|list|remove` CLI. Independent corroboration came from the driver run, which captured a homelab-mcp v1.7.0 startup banner: `"v1.6: keyring is now the sole credential store"` (raw/driver.log). The MCP-tool name `list_keyring_credentials` itself names the keyring as the data source.
- **§2 (cmdkey diff):** empty. The v1.1 read-only tool surface (`list_keyring_credentials` + `list_registered_servers`) did not mutate Windows Credential Manager state across one full session. This proves the *current* read-only surface is non-mutating but does not bound future tool additions.
- **Yes/no:** YES, the framework's tool surface touches the OS keyring — for reads today (§1 + driver.log), with a documented mutation surface (`credentials add|remove`, the registered-server `register_server` tool exposed in driver.log's tool list) one tool addition away from being live in any test that exercises the credential-add MCP tool transitively.

### Decision

**SHIP: ISOL-04**

Rationale: §1 produced positive evidence that the OS keyring is THE credential store at runtime (upstream-author confirmation in the v1.7.0 startup banner). Even though §2's empty cmdkey diff shows the *current* v1.1 read-only surface is non-mutating, the cost of injecting `PYTHON_KEYRING_BACKEND=keyring.backends.null.Null` into `_build_isolated_env` is one extra dict entry (zero runtime cost, zero API surface) versus the cost of forgetting it the first time a test exercises a mutation tool (a real keyring entry written to the developer's Credential Manager and then never cleaned up). Defense-in-depth: ISOL-02's `HOME` redirect protects the registry file, ISOL-04's null-keyring-backend protects the OS keyring; the two together make the spawned subprocess fully sandboxed against the credential surface §1 documents.

### Trigger to re-open (only if DEFER)

(N/A — shipping in v1.1.)

### Plan 06-02 consequence

Plan 06-02 MUST add `PYTHON_KEYRING_BACKEND=keyring.backends.null.Null` to the `_build_isolated_env` return dict.

The recommended placement (per PATTERNS.md `_isolation.py` shape): a fourth module-level constant alongside `_PASSTHROUGH_ALLOWLIST`, `_MCP_PREFIX`, and `_HOME_OVERRIDES`:

```python
# ISOL-04: force the Python keyring library into a no-op backend so the
# spawned subprocess CANNOT read or write the user's real OS keyring
# (libsecret/Keychain/Windows Credential Manager). Decision recorded in
# .planning/phases/06-.../06-keyring-recon.md §3 (SHIP: ISOL-04).
_KEYRING_BACKEND_OVERRIDE: dict[str, str] = {
    "PYTHON_KEYRING_BACKEND": "keyring.backends.null.Null",
}
```

Caveat for Plan 06-02 implementer: this only short-circuits the Python `keyring` library's backend chain. If homelab-mcp's credential code ever bypasses `keyring` and calls Win32 `CredWrite` / libsecret directly via `ctypes`, the env var has no effect. The §1 evidence ("Credentials are stored in the OS keyring (libsecret on Linux, Keychain on macOS)") + the v1.7.0 startup banner ("keyring is now the sole credential store") strongly suggest the standard `keyring` library is the path — direct Win32/libsecret calls would be unusual and would also break the documented "headless servers fall back to environment variables" behavior. See §5 Q1 for the residual uncertainty.

---

## 5. Open questions

1. **Q1: Does `cmdkey` capture the same keyring entries that the Python `keyring` library would write/read?** `PYTHON_KEYRING_BACKEND=keyring.backends.null.Null` only short-circuits the Python `keyring` library's backend chain. If homelab-mcp's credential code ever bypasses `keyring` and calls Win32 `CredWrite` (Windows) or libsecret (Linux) directly via `ctypes`, the env var has no effect and the cmdkey-axis ISOL-03 hash-equality test would still pass under isolation while the user's real keyring gets mutated. The §1 PyPI README evidence ("Credentials are stored in the OS keyring (libsecret on Linux, Keychain on macOS). When the OS keyring is unavailable (headless servers), credentials fall back to environment variables.") strongly implies the standard `keyring` library is the path — that fallback semantics is exactly what `keyring` provides. **What would answer it definitively:** snapshot `cmdkey /list` before/after a test that DOES write a credential under isolation; if the user's real cmdkey output gains a new `Target:` line, the env var was bypassed. Tracked for Plan 06-03's ISOL-03 design — see "Caveats from §2 that affect ISOL-03" in 06-01-SUMMARY.md.

2. **Q2 (carried forward from 260506-qxs FINDINGS §5 Q3): `MCP_CONNECTION_NONBLOCKING` semantics — propagate or strip?** Currently set in user env (`raw/env_scan.txt` from the spike). Disposition per CONTEXT CD-03: passing through under the `MCP_*` allowlist by default; flip to strip if it causes flakiness during ISOL-01 recon. **Status from this recon:** the driver's MCP handshake completed cleanly with `MCP_CONNECTION_NONBLOCKING=true` set in the parent env (passthrough behavior, since the driver did not yet implement the ISOL-02 allowlist) — no observed flakiness. Default disposition (`MCP_*` allowlist passthrough) holds; no strip needed for v1.1.

3. **Q3 (new, surfaced during Task 2):** the upstream startup banner `"v1.6: keyring is now the sole credential store"` (`raw/driver.log` line "Dropped legacy ssh_credentials table") implies an EARLIER homelab-mcp version stored credentials in a SQLite DB inside `~/.homelab_mcp/`. ISOL-03's hash list (`credential_registry.json`, `known_hosts`, `migration_state.json`, per CONTEXT D-08) does NOT cover any `*.db` file. Is there a stale `.db` file in `~/.homelab_mcp/` that could be mutated by a future homelab-mcp version that re-introduces DB-backed credentials, and if so should ISOL-03's file list expand to cover it? **What would answer it:** `dir %USERPROFILE%\.homelab_mcp\` → look for `.db` artifacts. Tracked for Plan 06-03's test-design pass — likely additive (one more file in the hash list, behind a "if exists" guard).

4. **Q4 (new, surfaced during Task 2):** the driver's `list_tools()` returned 58 tools (raw/driver.log), including credential-mutation candidates like `register_server`, `decommission_device`, `purge_devices`, `update_device_config`. The v1.1 test surface only exercises 2 of these (`list_keyring_credentials`, `list_registered_servers`), but ISOL-04's null-keyring backend protects the WHOLE surface — including any tool that incidentally writes a credential. Should Plan 06-03's ISOL-03 test exercise a wider tool fan-out to surface mutation more aggressively? **What would answer it:** review of the 58-tool list against "which tools document keyring or credential side-effects". Out of scope for Plan 06-01 (recon, not test design); referenced for Plan 06-03 (test design + scope).

5. **Q5 (new, surfaced during Task 2):** the homelab-mcp startup also emitted `"Dropped legacy drift_baselines table (v1.7: sitemap is now the single source of truth for drift)"`. This is upstream behavior unrelated to keyring isolation, but it implies homelab-mcp may run *destructive schema migrations* on subprocess start — a behavior that ISOL-02's `HOME` redirect should already neutralize (the redirected tempdir won't have a legacy table to drop) but worth flagging as a behavior the v1.1 surface inherits. **What would answer it:** post-Plan 06-02 verification that subsequent test-run boots do NOT emit "Dropped legacy ..." messages, confirming the migration doesn't re-trigger from the tempdir each session. Tracked as a Plan 06-03 verification-pass observation.
