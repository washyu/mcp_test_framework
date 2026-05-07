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
