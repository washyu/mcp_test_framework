# Phase 33: Per-bucket skip granularity in `ToolConfig` (999.1) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-26
**Phase:** 33-per-bucket-skip-granularity-in-toolconfig-999-1
**Areas discussed:** Worked example tool choice

---

## Initial gray-area selection

Four gray areas were surfaced. User selected only one for discussion; the other three were deferred to Claude's discretion with explicit defaults recorded in CONTEXT.md (so the user can override during planning if needed).

| Area | Description | Selected for discussion |
|------|-------------|-------------------------|
| Naming: skip_buckets vs alt | `bucket` already used in `_runner.py` / `_reporter.py` for per-tool result aggregation; risk of confusion with new test-bucket field. Alternatives: `skip_checks`, `skip_layers`, `skip_phases`. | |
| Skip + skip_buckets interaction | What happens when an operator sets both `skip: true` AND `skip_buckets: [...]` on the same tool? | |
| --explain bucket-level format | SC#3 says 'grep-able N+5-line block per tool'. Exact rendering shape was open. | |
| Worked example tool choice | Which tool anchors the README + `docs/LIBRARY-MODE.md` worked example (BUCKET-05)? | ✓ |

---

## Worked example tool choice

### Q1: Real homelab-mcp tool vs synthetic placeholder vs test-only tool

| Option | Description | Selected |
|--------|-------------|----------|
| Real homelab-mcp tool (recommended) | Pick a real required-field tool from homelab-mcp (e.g., `create_proxmox_vm`, `deploy_vm`, `ssh_execute_command`). Reads as authentic operator config; drops directly into the existing homelab-mcp `config.example.yaml`. | ✓ |
| Synthetic placeholder (`example_tool`) | Use a fake tool name like `example_create_resource` with a comment that says 'replace with your own required-field tool'. Generic, never stales. | |
| Tiny test-only tool in homelab-mcp | Build a minimal `example_required_field_tool` inside homelab-mcp solely to anchor the docs. | |

**User's choice:** Real homelab-mcp tool
**Notes:** Authenticity over future-proofing; the doc example reads as genuine operator config.

### Q2: Which specific homelab-mcp tool

| Option | Description | Selected |
|--------|-------------|----------|
| `create_proxmox_vm` | Canonical required-field tool — needs name/node/cores/memory/etc. Most operator-recognizable from active homelab-mcp config. | ✓ |
| `ssh_execute_command` | Requires `host` + `command` minimum. Smaller schema, easier doc snippet to read. Less 'dramatic' as a required-field example. | |
| `deploy_vm` | Higher-level orchestration tool, also required-field. Heavier schema. Likely overkill. | |
| Defer to planning | Record 'real required-field tool from homelab-mcp' and let the planner pick. | |

**User's choice:** `create_proxmox_vm`
**Notes:** The schema-vs-empty-args mismatch makes the value proposition obvious in the doc.

### Q3: Snippet depth

| Option | Description | Selected |
|--------|-------------|----------|
| YAML + expected output (recommended) | YAML snippet + `mcp-contracts run --explain` output + pre-run digest slice. ~25–40 lines. | ✓ |
| Just the YAML snippet | One fenced code block + one sentence prose. ~8–12 lines. | |
| YAML + before/after digest only | Snippet + digest line that changed. ~15–20 lines. | |

**User's choice:** YAML + expected output
**Notes:** Operator can verify their config worked without having to run the framework first.

---

## Claude's Discretion

Three areas the user did NOT pick for discussion. Defaults recorded in CONTEXT.md `<decisions>` § Claude's Discretion. Flag during planning if a deviation is needed.

- **Field naming** → keep `skip_buckets` (matches REQUIREMENTS.md BUCKET-01 verbatim); disambiguate naming collision in docs
- **`skip: true` + `skip_buckets: [...]` interaction** → hard-fail at config load via `@model_validator(mode="after")` — redundant config is operator error
- **`--explain` bucket rendering** → extend the existing per-tool block with a single `bucket=<name>: skipped via tools.<name>.skip_buckets` line per skipped bucket (grep-able)

---

## Deferred Ideas

- Renaming the existing `bucket` (per-tool result aggregation) concept in `_runner.py` / `_reporter.py` — out of scope for Phase 33; could be a v1.6 cleanup if docs disambiguation proves insufficient.
- Marker-driven test→bucket inference — one of three options the planner will pick from (markers, explicit dict, name-prefix regex). Not yet selected.
- Codegen for required-field tools (Phase 999.2 in backlog) — pairs naturally with bucket-skip but is its own phase; mention only as a forward reference in BUCKET-05 docs.
