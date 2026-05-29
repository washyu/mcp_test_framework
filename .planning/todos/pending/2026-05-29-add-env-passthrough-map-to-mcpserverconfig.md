---
created: 2026-05-29T06:09:36.021Z
title: Add env passthrough map to McpServerConfig
area: config
files:
  - src/mcp_test_framework/models.py:58 (McpServerConfig — currently only command + args)
  - src/mcp_test_framework/_isolation.py (env build / strict allowlist + passthrough)
  - src/mcp_test_framework/mcp_client.py (subprocess spawn — where env merges in)
  - docs/EXTENDING.md, docs/LIBRARY-MODE.md (config field reference + host_isolation docs)
---

## Problem

`McpServerConfig` (`src/mcp_test_framework/models.py:58`) exposes only `command`
and `args`. There is no way to declare environment variables for the spawned MCP
subprocess in `config.yaml`. Operators whose server needs env vars to function
must set them in the shell before every run (`$env:PROXMOX_VERIFY_SSL="false"; uv run pytest ...`)
and additionally flip `host_isolation: passthrough` so the strict-mode allowlist
doesn't strip them.

Discovered 2026-05-29 while dogfooding the test-code-author surface against
`homelab-mcp`: `create_proxmox_vm` only succeeds once `PROXMOX_HOST` and
`PROXMOX_VERIFY_SSL` reach the subprocess. The shell-export dance is fragile
(easy to forget, not captured anywhere, not reproducible in CI) and is exactly
the kind of per-run setup `config.yaml` should own.

## Solution

Add a generic `env: dict[str, str]` field to `McpServerConfig` whose contents are
merged into the spawned subprocess environment. Proposed shape:

```yaml
mcp_server:
  command: uv
  args: [run, homelab-mcp]
  env:
    PROXMOX_VERIFY_SSL: "false"
    PROXMOX_HOST: "your-host"
```

Design constraints:

- **MUST stay SUT-agnostic (SEED-022).** A generic `str -> str` map only — NEVER
  Proxmox-specific named fields. The framework knows nothing about the server's
  domain; the operator supplies the data.
- **Compose with `host_isolation`.** Operator-declared env should be injectable in
  BOTH `strict` and `passthrough` modes. Rationale: by listing a var under
  `mcp_server.env` the operator has *explicitly* opted that var in, so it should
  survive the strict-mode allowlist strip rather than being filtered out. This
  means the strict env builder needs to layer `mcp_server.env` on top of (or
  inside) the allowlist result, not before it. Decide precedence vs. an
  inherited same-named var at plan time.
- **Secrets caution.** Document that values land in `config.yaml` in plaintext;
  for credentials, prefer leaving them in the real env + `passthrough` rather
  than committing them. The `env:` map is best for non-secret toggles
  (`*_VERIFY_SSL`, hosts, feature flags).

Pairs conceptually with the Phase 34 (ISOL) host-isolation work — same
subprocess-env codepath in `_isolation.py` / `mcp_client.py`. v1.6 candidate.

## Validation

- Unit: `mcp_server.env` parses; merged map reaches `_build_subprocess_env`.
- Unit: a declared var survives `host_isolation: strict` (not stripped by the
  allowlist).
- Doc: config field reference in EXTENDING.md + LIBRARY-MODE.md host-isolation
  section updated with the secrets caution.
