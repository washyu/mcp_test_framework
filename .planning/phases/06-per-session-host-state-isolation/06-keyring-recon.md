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
