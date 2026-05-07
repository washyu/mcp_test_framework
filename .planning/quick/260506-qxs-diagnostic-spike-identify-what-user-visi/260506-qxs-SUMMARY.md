---
phase: 260506-qxs-diagnostic-spike
plan: 01
type: quick
duration_minutes: 25
completed: 2026-05-06
tasks_completed: 2
files_created:
  - .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md
  - .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/help.txt
  - .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/before.txt
  - .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/after.txt
  - .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/processes.txt
  - .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/listening_ports.txt
  - .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/env_scan.txt
  - .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/handshake.log
  - .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/wider_scan.txt
  - .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/keyring.txt
  - .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/discovered_state_dir.txt
files_modified:
  - (none in src/ — recon-only spike)
commits:
  - 9451832  # chore(260506-qxs-01): capture homelab-mcp host-state recon evidence
  - 358f262  # docs(260506-qxs-02): synthesize FINDINGS.md from recon evidence
requirements:
  - SPIKE-ISO-01
  - SPIKE-ISO-02
  - SPIKE-ISO-03
---

# 260506-qxs Diagnostic Spike — homelab-mcp Host-State Surface Summary

**One-liner:** Black-box recon found homelab-mcp persists user state in `~/.homelab_mcp/{credential_registry.json,known_hosts,migration_state.json}` plus ~20 Windows Credential Manager entries; recommended v1.1 isolation: per-session tempdir + `HOME`/`USERPROFILE` env override on the spawned subprocess (~11 h effort, MEDIUM confidence).

**Deliverable:** [FINDINGS.md](./FINDINGS.md) with five required sections (state inventory, isolation knobs, recommended strategy, effort estimate, open questions). Raw evidence in [`raw/`](./raw/).

## What this spike answered

1. **Where does homelab-mcp keep user state?** `~/.homelab_mcp/` (root-of-home, underscore variant — *not* the XDG path the originating todo hypothesized) for 3 files totaling ~8 KB, plus the OS keyring for ~20 SSH/Proxmox credentials.
2. **What knobs can the framework reach as a black-box client?** No `--config`/`--data-dir`/`--state-dir` CLI flag exists (confirmed via `--help` for both top-level and `credentials` subcommand). Only the OS-level `HOME`/`USERPROFILE` env vars look like a reliable redirection point; XDG vars are unlikely to be honored given the non-XDG dir layout.
3. **What's the v1.1 implementation plan?** ~11 hours across 1–2 working days. Patch lives at `mcp_client.py:143` and `fixtures.py:208` where `StdioServerParameters` is built — pass an `env=` dict containing the tempdir-overriding `HOME`/`USERPROFILE` plus a passthrough allowlist. New session-scoped `_isolated_home` fixture owns the `tempfile.TemporaryDirectory`.

## What it could NOT answer (under the black-box rule)

The biggest residual risk: **does `list_registered_servers` touch the OS keyring?** If yes, `HOME` redirect alone won't isolate test runs — we'd need `PYTHON_KEYRING_BACKEND=keyring.backends.null.Null` layered on top. This is FINDINGS.md §5 question #2; the cheap way to answer it is `cmdkey /list | findstr homelab` before/after a real pytest run on isolation-equipped infrastructure (which is itself a v1.1 deliverable). Six other open questions are listed in §5 — most self-resolve once v1.1 ships.

## Deviations from plan

- **Discovery delta:** the BEFORE candidate path list (`raw/before.txt`) only enumerated `~/.homelab-mcp` (hyphen), `~/.config/homelab-mcp` (XDG hyphen), and Windows-AppData hyphen variants. The actual path is `~/.homelab_mcp` (root-of-home, **underscore**), found via a follow-up `Get-ChildItem -Filter '*homelab*' -Recurse -Depth 3` over `$env:USERPROFILE` (`raw/wider_scan.txt`). Addenda were appended to before.txt and after.txt linking to `raw/discovered_state_dir.txt` for the live snapshot. **No re-snapshot was performed** because the file mtimes (2026-05-04, 2026-04-26) predate the spike — the existing artifacts are user-state, not spike-induced. Documented in FINDINGS.md §1 "Discovery delta vs original candidate list" and §5 question #5.
- **Handshake substitution:** the plan permitted substituting `homelab-mcp --version` for the framework's full `pytest` invocation if the latter risked disturbing the user's running daemon. Used. Captured in `raw/handshake.log`. Consequence: file-level mutation evidence in `before.txt` vs `after.txt` is necessarily empty; the recommendation in §3 leans on the static state-surface evidence (`raw/discovered_state_dir.txt`, `raw/keyring.txt`) rather than handshake-induced deltas. Open question §5 #5 covers this.
- **Two extra raw captures added beyond the six required:** `raw/wider_scan.txt` (depth-3 USERPROFILE glob — discovered the underscore variant) and `raw/keyring.txt` (`cmdkey /list` filtered to `homelab`/`mcp` — discovered the keyring surface). Without these, the recommendation would have been built on an incomplete state inventory.
- **Helper scripts captured under version control:** `_capture.ps1`, `_capture2.ps1`, `_capture3.ps1` are committed alongside the raw evidence so the snapshot is reproducible (a future v1.1 implementer can re-run them to compare a tempdir-isolated invocation against the user's home-dir baseline). They are NOT framework code and live under `.planning/quick/...`, not `src/`.

## Constraint compliance

- **Black-box rule (CLAUDE.md):** No source files under any homelab-mcp install location were opened. Only filename + size + mtime listings of `~/.homelab_mcp/` (which is user-state, not source) were captured. CLI `--help` and `--version` are documented external surfaces.
- **Read-only observation:** The only commands that *could* have mutated state were `uvx homelab-mcp --help` and `uvx homelab-mcp --version`. Both are documented as meta-only by argparse convention; neither created or modified any file under `~/.homelab_mcp/` (mtimes there predate the spike). No `homelab-mcp credentials add/remove/link/unlink` was issued.
- **No src/ modifications:** confirmed via `git status --porcelain src/` post-task — nothing changed.
- **Time budget:** ~25 minutes wall-clock, under the 30-minute cap.

## Self-Check: PASSED

- `FINDINGS.md` exists at `.planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md` (18,892 bytes) — confirmed via `ls -la`.
- All five required H2 sections present — confirmed via `grep -c '^## '` returning `5`.
- All raw/ evidence files exist (8 capture files: help.txt, before.txt, after.txt, processes.txt, listening_ports.txt, env_scan.txt, handshake.log + 3 follow-up: wider_scan.txt, keyring.txt, discovered_state_dir.txt) — confirmed via `Get-ChildItem`.
- Both task commits exist:
  - `9451832` chore(260506-qxs-01) — confirmed via `git log --oneline | head`.
  - `358f262` docs(260506-qxs-02) — confirmed via `git log --oneline | head`.
- No files under `src/` modified — `git status --porcelain src/` returns empty.

## Pointer for v1.1 planner

Start from FINDINGS.md §3 (recommended strategy) and §4 (effort breakdown). The first v1.1 task should be the §5 question #2 verification (does `list_registered_servers` touch the keyring?) — that determines whether the implementation needs the keyring-backend fallback or just the `HOME`/`USERPROFILE` override.
