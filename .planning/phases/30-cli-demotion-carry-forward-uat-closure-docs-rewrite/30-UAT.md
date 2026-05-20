---
status: partial
phase: 30-cli-demotion-carry-forward-uat-closure-docs-rewrite
source: [30-CONTEXT.md, 30-VERIFICATION.md]
started: 2026-05-17T00:00:00Z
updated: 2026-05-19T00:00:00Z
---

## About this document

This is a CAPTURE PROTOCOL document. The four UATs below are user-driven
acceptance checks — they verify what the operator perceives when running
actual commands against a live stack, not whether a specific code path fires.
Per memory `feedback_uat_must_be_user_driven`, no agent executes these UATs;
the operator runs them in a follow-up session and pastes evidence here.

Phase 30 VERIFICATION.md does NOT block on UAT closure. These are carry-forward
live-UAT items from v1.2 and v1.3 close that require Proxmox keyring access,
live homelab-mcp reachable via `uvx`, and Ollama reachable at `127.0.0.1:11434`.
Phase 30 closes in the current release cycle regardless of UAT status; UAT
execution is tracked separately.

Closing a UAT means: run the listed commands against a live stack, paste the
output into the Evidence block, check off each Pass criteria box that holds,
flip the Status line to `[x] pass` (or `[x] fail` / `[x] blocked` as
appropriate), and update the Summary block counts at the bottom.

These are user intent checks. The operator is the judge. Pass means the
operator perceives a PASS, not that a specific assertion fired.

## Tests

### UAT-1: README test-code-scenarios PASS-sample re-capture

**Background:** README §"test-code scenarios" still shows pre-Phase-24 FAIL output for the Proxmox VM lifecycle scenario. Phase 24 shipped the `exclude_unset=True` fix; the snapshot needs re-capture against live Proxmox + homelab-mcp.

**Carried from:** Phase 24 Plan 24-02 Task 3a/3b — deferred at Plan 24-02 close (live-uat row in STATE.md Deferred Items).

**Pre-reqs:**
- Operator shell with Proxmox keyring access (agent's PowerShell session cannot reach the keyring per STATE.md deferred-items)
- `MCPTF_DOGFOOD_PROXMOX_HOST=192.168.10.20` set
- `homelab-mcp` reachable via `uvx`
- Ollama reachable for any contract pass (separate run; UAT-1 is test-code only, no judges)

**Commands:**
```powershell
$env:MCPTF_DOGFOOD_PROXMOX_HOST = "192.168.10.20"
uv run mcp-contracts run --test-code --config config.yaml
```

**Expected observable outcome:** All test-code scenarios pass; output shape matches the README §"test-code scenarios" snapshot format with PASS rows instead of FAIL.

**Pass criteria:**
- [ ] No `ToolCallError` from upstream homelab-mcp `inputSchema` bug surfaces (Phase 24 fix holds)
- [ ] Output matches README §"test-code scenarios" snapshot shape (headers, per-tool rows, summary)
- [ ] Re-snapshot pasted verbatim into README §"test-code scenarios", replacing the pre-Phase-24 FAIL block
- [ ] The HTML sentinel comment at README §"test-code scenarios" (`<!-- noqa: sdet-rename-shim — ... -->` if present) is removed once the snapshot is current

**Evidence (paste here after running):**
```
<paste stdout / screenshot reference / file snapshot here>
```

**Status:** [ ] pending / [ ] pass / [ ] fail / [ ] blocked
**Notes:**

---

### UAT-2: Phase 17 SC1 — `gen-test-classes` at ~70-tool scale + pyright clean

**Background:** Phase 17 codegen target was ~70 tools. Live UAT was deferred at v1.3 close; needs live homelab-mcp to enumerate the full tool surface and pyright run on the generated output.

**Carried from:** Phase 17 17-VERIFICATION.md `human_needed` row (STATE.md "Acknowledged at v1.3 milestone close").

**Pre-reqs:**
- `homelab-mcp` runnable via `uvx`, exposing ~70 tools
- `pyright` installed (dev dep)
- A `config.yaml` with `test_code.generated_root` set to a writable path

**Notes on output shape:**
- The slug is derived from the live server's `serverInfo.name` via `server_slug()` ([src/mcp_test_framework/test_code/_slugs.py:24](src/mcp_test_framework/test_code/_slugs.py:24)) — lowercase, non-alphanumerics → underscore, runs collapsed. For `homelab-mcp` this resolves to `homelab_mcp`.
- `gen-test-classes` writes one file per tool named after the tool itself (`<tool_name>.py`), NOT `test_<tool_name>.py`. The original glob in this protocol was wrong (would always match zero); use `*.py` or rely on the operator-mode tally printed by the command itself.
- The framework's *library* code lives at `src/mcp_test_framework/test_code/` (Phase 25 SDET→test_code rename). The codegen *output* lives at `tests/test_code/_generated/<slug>/`. Same `test_code` name, two different roles — known operator-vs-dev confusion source, candidate doc nit.

**Commands:**
```bash
uv run mcp-contracts gen-test-classes --config config.yaml
uv run pyright <test_code.generated_root>/<server_slug>/
# Concrete for homelab-mcp:
#   uv run pyright tests/test_code/_generated/homelab_mcp/
```

**Expected observable outcome:** `gen-test-classes` writes one typed Pydantic Params + Response pair per advertised tool (one `.py` per tool); `pyright` reports zero errors / zero warnings.

**Pass criteria:**
- [x] Generated `.py` file count matches live tool count (use `Get-ChildItem <path> -Recurse -Filter '*.py' | Measure-Object` on PowerShell or `find <path> -name '*.py' | wc -l` on POSIX; subtract 1 for the `__init__.py` if present)
- [x] `pyright` exit code 0
- [x] No `# type: ignore` or `# pyright: ignore` lines in generated code

**Evidence (paste here after running):**
```
Slug observed:           homelab_mcp
Generated path:          tests/test_code/_generated/homelab_mcp/
Generated file count:    59 .py files (58 tools + 1 __init__.py) — matches the 58 tools enabled in config.yaml
pyright result:          0 errors, 0 warnings
type-ignore scrub:       no `# type: ignore` / `# pyright: ignore` lines in generated code

Operator note: confusion observed between src/mcp_test_framework/test_code/ (framework library) and tests/test_code/_generated/<slug>/ (codegen output). Pyright was initially run against the wrong directory. Doc nit captured.
```

**Status:** [ ] pending / [x] pass / [ ] fail / [ ] blocked
**Notes:** Closed 2026-05-19. Tool count 58 vs the ~70 Phase 17 estimate reflects the operator's `config.yaml` allowlist size, not a homelab-mcp regression — the server advertises ~70; only 58 are opted in. UAT closes against the configured allowlist scope.

---

### UAT-3: v1.2 Phase 13 v2 config + migration walkthrough — library-mode example

**Background:** Phase 13 v1→v2 schema migration; live UAT was deferred at v1.2 close. Phase 30 closes it by demonstrating the migration walkthrough using the library-mode `mcp_config_file` ini route.

**Carried from:** Phase 13 13-VERIFICATION.md `human_needed` row.

**Pre-reqs:**
- A v1-schema `config.yaml` to migrate (legacy fixture or hand-crafted)
- pyproject.toml with `[tool.pytest.ini_options] mcp_config_file = "./config.yaml"` set

**Commands:**
```bash
# Start with v1-schema config; observe migration error
uv run pytest --collect-only

# Apply the migration per docs/MIGRATION-v1-to-v2.md
uv run mcp-contracts config-init -o config.yaml.new

# Compare new vs old; merge by hand or replace
uv run pytest --collect-only
```

**Expected observable outcome:** First `pytest --collect-only` emits a fail-loud v1→v2 migration error naming `version: 1` and pointing at the migration doc; second `pytest --collect-only` succeeds and shows injected contract tests.

**Pass criteria:**
- [ ] Migration error names the schema version field
- [ ] Migration error references `mcp-contracts config-init` as the next step
- [ ] After migration, contract tests collect under `<mcp-contracts>::test_*[*]` nodeids
- [ ] No `MCPTF_CONFIG_FILE` env var set during the walkthrough (proves library-mode is the documented route)

**Evidence (paste here after running):**
```
<paste stdout / screenshot reference / file snapshot here>
```

**Status:** [ ] pending / [ ] pass / [ ] fail / [ ] blocked
**Notes:**

---

### UAT-4: v1.2 Phase 14 live-smoke + visual domain UI under both CLI and library modes

**Background:** Phase 14 hybrid runner + visual domain UI; live UAT deferred at v1.2 close. Phase 30 closes it by capturing the domain UI output under BOTH CLI mode (`mcp-contracts run`) and library mode (`pytest --mcp-domain-ui=force`) and confirming visual parity.

**Carried from:** Phase 14 14-VERIFICATION.md `human_needed` row.

**Pre-reqs:**
- Live homelab-mcp + Ollama reachable
- `config.yaml` with at least 2-3 enabled tools

**Commands:**
```powershell
# CLI mode (PowerShell — Windows-first dev environment per CLAUDE.md)
uv run mcp-contracts run --config config.yaml *>&1 | Tee-Object -FilePath cli_output.txt

# Library mode (force the reporter even in non-TTY contexts)
uv run pytest -o "mcp_config_file=./config.yaml" --mcp-domain-ui=force *>&1 | Tee-Object -FilePath lib_output.txt

# Visual diff
Compare-Object (Get-Content cli_output.txt) (Get-Content lib_output.txt)
```

Or POSIX equivalent:
```bash
uv run mcp-contracts run --config config.yaml > cli_output.txt 2>&1
uv run pytest -o "mcp_config_file=./config.yaml" --mcp-domain-ui=force > lib_output.txt 2>&1
diff -u cli_output.txt lib_output.txt
```

**Expected observable outcome:**
- Both outputs show the MCP domain UI header / per-tool rows / `Result:` summary
- CLI mode wraps pytest's native output (none visible by default)
- Library mode emits domain UI ADDITIVE to pytest's native output (per Phase 29 reporter design)
- Per-tool rows + summary line agree between the two runs (same tools, same outcomes)

**Pass criteria:**
- [ ] CLI mode shows the domain UI without pytest framing
- [ ] Library mode shows BOTH pytest native output AND the domain UI
- [ ] Per-tool verdicts (PASS / FAIL / SKIP) match across both routes
- [ ] `Result:` summary line agrees (same PASS / FAIL / SKIP counts) between the two

**Evidence (paste here after running):**
```
<paste stdout / screenshot reference / file snapshot here>
```

**Status:** [ ] pending / [ ] pass / [ ] fail / [ ] blocked
**Notes:**

---

## Summary

total: 4
passed: 1
issues: 0
pending: 3
skipped: 0
blocked: 0
