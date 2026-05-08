---
phase: 260506-qxs-diagnostic-spike
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md
autonomous: true
requirements:
  - SPIKE-ISO-01  # observe homelab-mcp host-state surface as a black box
  - SPIKE-ISO-02  # enumerate isolation knobs (env vars, CLI flags) reachable without source access
  - SPIKE-ISO-03  # recommend an isolation strategy with evidence + effort estimate for v1.1

must_haves:
  truths:
    - "FINDINGS.md exists at the deliverable path and contains all five required sections"
    - "Section 1 lists concrete file/dir/socket/process paths observed (not speculation)"
    - "Section 2 documents env vars and CLI flags with the exact command output / dir listing that proved them"
    - "Section 3 picks ONE strategy from {env-var override, CLI flag, cwd, container} with rationale tied to sections 1+2"
    - "Section 4 gives a rough hours/days effort estimate for the v1.1 implementation"
    - "Section 5 lists open questions that could not be answered without violating the black-box rule"
    - "No source files in src/ are modified; no homelab-mcp source is read"
  artifacts:
    - path: ".planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md"
      provides: "Recon report with state inventory, isolation knobs, recommendation, effort, open questions"
      contains: "## State homelab-mcp creates/mutates"
    - path: ".planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/"
      provides: "Raw evidence captures (help output, dir listings, snapshot diffs) referenced by FINDINGS.md"
      min_lines: 0
  key_links:
    - from: "FINDINGS.md §3 Recommended isolation strategy"
      to: "FINDINGS.md §1 State inventory + §2 Isolation knobs"
      via: "explicit citations of which paths/flags drive the recommendation"
      pattern: "see §[12]"
    - from: "FINDINGS.md §1 State inventory"
      to: "raw/ evidence files"
      via: "referenced filenames (e.g. raw/help.txt, raw/before.txt, raw/after.txt)"
      pattern: "raw/"
---

<objective>
Diagnostic spike: identify what user-visible state `homelab-mcp` touches when launched as a subprocess by the test framework, and recommend an isolation strategy for v1.1.

Purpose: The framework currently breaks the user's daily use of `homelab-mcp` because test runs appear to mutate shared host state (registry, sockets, processes). v1.1 has a hard requirement that test runs MUST NOT mutate user-visible state. Before designing the v1.1 fix, we need an evidence-based picture of *what* state is actually touched and *which knobs* are reachable from outside the black box.

Output: A single recon report `FINDINGS.md` with five required sections (state inventory, isolation knobs, recommended strategy, effort estimate, open questions), backed by raw evidence captures in a `raw/` subdirectory. No production code changes. Implementation belongs to v1.1 per `.planning/todos/pending/2026-05-07-v1-1-isolate-test-runs-from-user-state.md`.

Time-box: 30 minutes wall-clock. Two atomic tasks: (1) observe and capture, (2) synthesize report.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/todos/pending/2026-05-07-v1-1-isolate-test-runs-from-user-state.md
@docs/mcp_test_framework_mvp_spec.md
@src/mcp_test_framework/mcp_client.py
@src/mcp_test_framework/fixtures.py

<black_box_rule>
Hard rule from CLAUDE.md: the framework treats `homelab-mcp` as a BLACK BOX.
- DO NOT read, grep, or import from `homelab-mcp`'s source code, its installed package files, or its repository.
- DO NOT inspect the contents of its Python source files even if they're discoverable on disk via `pip show homelab-mcp` etc.
- ALLOWED signals (external observation only):
  * `homelab-mcp --help` (and any subcommand `--help`) output for documented CLI flags
  * Public PyPI listing / README of the `homelab-mcp` package (web fetch is acceptable; reading the local source tree is NOT)
  * Inspecting user-visible directories on the host: `~/.config/homelab-mcp/`, `~/.local/share/homelab-mcp/`, `~/.cache/homelab-mcp/`, `$XDG_CONFIG_HOME`, `$XDG_DATA_HOME`, `%APPDATA%`, `%LOCALAPPDATA%`, `~/.homelab-mcp/`, `/tmp/homelab-mcp*`
  * Snapshot-diff: list state dirs BEFORE running `homelab-mcp --help` (or a brief stdio handshake), list AFTER, diff
  * Process / socket inventory after a brief launch: `Get-Process homelab*`, `netstat -ano | findstr LISTENING`, lock-file/PID-file presence in standard dirs
  * The framework's own ROADMAP / PROJECT / spec / todo for any documented isolation knobs
- If a question can only be answered by reading homelab-mcp source, record it in FINDINGS.md §5 "Open questions" instead.
</black_box_rule>

<observation_environment>
- Platform: Windows 11, PowerShell as primary shell (use `$env:VAR` not `$VAR`, `$null` not `/dev/null`).
- POSIX equivalents are also relevant because v1.1 will run on Linux/macOS — when documenting candidate state paths, list BOTH Windows (`%APPDATA%\homelab-mcp`, `%LOCALAPPDATA%\homelab-mcp`) AND POSIX (`~/.config/homelab-mcp`, `~/.local/share/homelab-mcp`) so the v1.1 isolation design covers all targets.
- The user has a real `homelab-mcp` instance in active use. Do NOT issue commands that would tear it down, restart it, or mutate its registry. `--help` and a brief stdio handshake (which `_preflight` already does on every test run) are safe; anything that writes is not.
</observation_environment>

<known_unknowns>
From the originating todo, the leading hypotheses are:
- Config / data dirs: `~/.config/homelab-mcp/`, `$XDG_CONFIG_HOME`, `$XDG_DATA_HOME`
- Lock / PID files in shared locations
- A registry / database file (likely, given `list_registered_servers` exists)
- Network sockets, named pipes, or daemon processes
- CWD-relative writes

The spike's job is to confirm or refute each hypothesis with concrete evidence.
</known_unknowns>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Observe and capture homelab-mcp host-state surface</name>
  <files>
    .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/help.txt
    .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/before.txt
    .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/after.txt
    .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/processes.txt
    .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/listening_ports.txt
    .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/env_scan.txt
  </files>
  <action>
Capture external evidence of what state `homelab-mcp` touches. RECON ONLY — observation, no mutation, no source reads.

Create `raw/` under the deliverable directory and write these capture files:

1. **`raw/help.txt`** — top-level CLI help and any obvious subcommand help.
   ```powershell
   homelab-mcp --help 2>&1 | Tee-Object -FilePath "<raw>/help.txt"
   # If --help reveals subcommands, capture each: e.g. `homelab-mcp run --help`, `homelab-mcp serve --help`.
   # Append each to help.txt with a clear header line: `=== homelab-mcp <subcmd> --help ===`.
   ```
   Scan output for any of: `--config`, `--config-dir`, `--data-dir`, `--state-dir`, `--cache-dir`, `--registry`, `--socket`, `--pid-file`, `--workdir`, `--profile`, `--no-state`, `--ephemeral`. Note environment variables mentioned in help text (e.g. `HOMELAB_MCP_HOME`, `HOMELAB_MCP_CONFIG`).

2. **`raw/before.txt`** — snapshot of candidate state directories BEFORE any handshake.
   Capture (recursive ls with size+mtime) for each path that exists; record "ABSENT" for ones that don't:
   - `$env:APPDATA\homelab-mcp\` and `$env:APPDATA\homelab_mcp\`
   - `$env:LOCALAPPDATA\homelab-mcp\` and `$env:LOCALAPPDATA\homelab_mcp\`
   - `$env:USERPROFILE\.homelab-mcp\` and `$env:USERPROFILE\.config\homelab-mcp\`
   - `$env:USERPROFILE\.local\share\homelab-mcp\`
   - `$env:USERPROFILE\.cache\homelab-mcp\`
   - `$env:TEMP\homelab-mcp*` and `$env:TEMP\homelab_mcp*` (glob)
   Use `Get-ChildItem -Recurse -Force -ErrorAction SilentlyContinue` and `Format-List FullName, Length, LastWriteTime`. Tee to `raw/before.txt`.

3. **Trigger one brief handshake** — run the framework's existing preflight path (which already opens an `McpTestClient` and calls `list_tools` then closes it). Easiest invocation:
   ```powershell
   uv run pytest tests/unit/ -q  # NO — this skips preflight (see fixtures.py _session_needs_preflight)
   # Instead, run any single integration test or just the preflight gate directly:
   uv run pytest tests/test_homelab_list_registered_servers.py -q -x --co  # collection-only doesn't trigger preflight
   # The right command: run a single integration test once:
   uv run pytest tests/test_homelab_list_registered_servers.py::<first_test_name> -q -x 2>&1 | Tee-Object -FilePath "<raw>/handshake.log"
   ```
   If unsure which test is cheapest, list with `--co` first, pick the first integration test, run it. If it fails for unrelated reasons that's fine — preflight + one stdio handshake is what we need. If even that is too disruptive (the user's real homelab-mcp is in active use), substitute a single direct invocation: `homelab-mcp --version 2>&1 | Out-File "<raw>/handshake.log"` — note in FINDINGS.md §5 that the snapshot may understate state mutations because we did not exercise `list_tools`.

4. **`raw/after.txt`** — repeat the exact same dir scan as step 2, AFTER the handshake. Same command, different output file.

5. **`raw/processes.txt`** — `Get-Process homelab*, mcp* | Format-List Id, ProcessName, Path, StartTime` immediately after the handshake. Capture even if empty.

6. **`raw/listening_ports.txt`** — `netstat -ano | Select-String "LISTENING"` and grep results for any PIDs from step 5. Tee full output.

7. **`raw/env_scan.txt`** — list any currently-set environment variables matching the patterns `HOMELAB*`, `MCP*`, `XDG_*`:
   ```powershell
   Get-ChildItem env: | Where-Object { $_.Name -match '^(HOMELAB|MCP|XDG_)' } | Format-List | Tee-Object -FilePath "<raw>/env_scan.txt"
   ```

CRITICAL constraints:
- Use the Bash tool with PowerShell syntax (Windows env per CLAUDE.md). Pipe each capture through `Tee-Object` so output ends up on disk AND visible in tool output.
- DO NOT `Get-Content` / `cat` / `Read` any file under the installed `homelab-mcp` package (e.g. `site-packages/homelab_mcp/...`) — that violates the black-box rule. State files (JSON, SQLite, YAML) inside user dirs ARE fair game because they are user-visible artifacts, not source.
- DO NOT run anything that would mutate the user's running homelab-mcp (no `homelab-mcp register ...`, no `homelab-mcp serve --restart`, no killing processes by name). Read-only observation only.
- If any capture step errors out, capture the error to its file and proceed — partial evidence is still evidence; FINDINGS.md §5 records gaps.

Time budget: ~12 minutes. If a step takes >3 minutes, capture what you have and move on.
  </action>
  <verify>
    <automated>test -f .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/help.txt && test -f .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/before.txt && test -f .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/after.txt && test -f .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/processes.txt && test -f .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/listening_ports.txt && test -f .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/env_scan.txt && echo OK</automated>
  </verify>
  <done>All six raw/*.txt capture files exist. before.txt and after.txt cover the same set of candidate paths so a diff is meaningful. help.txt contains the CLI's actual `--help` output (or a clearly-labeled error line if the command failed). No file under the installed homelab-mcp package was opened during this task.</done>
</task>

<task type="auto">
  <name>Task 2: Synthesize FINDINGS.md from captured evidence</name>
  <files>
    .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md
  </files>
  <action>
Synthesize the recon report from the raw captures produced in Task 1. Structure (all five sections REQUIRED):

```markdown
# Diagnostic Spike — homelab-mcp Host-State Surface (RECON)

**Date:** 2026-05-06
**Scope:** Identify user-visible state homelab-mcp touches when spawned as a subprocess by `mcp_test_framework`. Recommend isolation strategy for v1.1.
**Method:** Black-box external observation — CLI `--help`, dir snapshot diff, process/port inventory, env scan. No source reads.

---

## 1. State homelab-mcp creates/mutates

Concrete inventory from before/after dir snapshots, process list, and listening-port inventory. Cite the raw file each row comes from.

| Kind | Path / Identifier | Observed when | Evidence (raw/*) |
|------|-------------------|---------------|------------------|
| config dir | `<path or ABSENT>` | before / after / both | raw/before.txt, raw/after.txt |
| data / registry file | `<path>` | <state> | raw/<file> |
| lock / PID file | `<path or NONE OBSERVED>` | <state> | raw/<file> |
| process | `homelab-mcp` PID `<n>`, started `<t>` | after handshake | raw/processes.txt |
| listening socket | `<host:port or NONE>` | after handshake | raw/listening_ports.txt |
| cwd-relative writes | `<path or NONE OBSERVED>` | <state> | <evidence> |

Below the table, list any new/modified entries that appeared between before.txt and after.txt — these are the *active* mutations a single handshake causes. Bold any path that is also user-visible (i.e. used by the user's real homelab-mcp).

If no mutations were observed, say so explicitly and note that this is the strongest available evidence under the black-box constraint — the absence of file-level mutation does NOT rule out in-memory or daemon-state effects (record those in §5).

## 2. Isolation knobs available

### CLI flags (from `raw/help.txt`)

| Flag | Purpose (from help text) | Confidence |
|------|--------------------------|------------|
| `<flag>` | <text> | direct quote / inferred |

If no isolation flags exist, state that and quote the relevant section of help.txt.

### Environment variables

Two sources:
- (a) Variables explicitly named in `--help` output (cite line).
- (b) Variables that XDG-respecting Python apps conventionally honor: `HOME`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME`, `APPDATA`, `LOCALAPPDATA`, `TEMP`. For each, cite which §1 path it would redirect.

| Env var | Source (help / convention) | Path it would redirect | Confidence |
|---------|---------------------------|------------------------|------------|

### Currently-set HOMELAB_* / MCP_* env vars

Quote `raw/env_scan.txt`. If non-empty, the user's existing config is partly env-driven and that's already a hint about the isolation knob.

## 3. Recommended isolation strategy

Pick ONE primary strategy from {env-var override, CLI flag, cwd-redirect, container}. Rationale must cite §1 (what state must be redirected) and §2 (which knobs reach it).

**Recommendation:** `<strategy>`

**Rationale:**
- <bullet citing §1 and §2 evidence>
- <bullet on why lighter strategies are insufficient or why a heavier strategy is unwarranted>
- <bullet on the implementation seam: which file in src/mcp_test_framework/ owns the change (mcp_client.py vs fixtures.py — see seam discussion in the originating todo)>

**Fallback strategy** (if primary turns out to be insufficient during v1.1 implementation): `<second choice>` — what evidence would trigger the fallback.

**Out of scope for v1.1:** container/VM isolation. Document only the trigger condition that would escalate to it.

## 4. Effort estimate

Rough hours/days for the v1.1 implementation, broken down:
- Plumb env/flag through `Config` (config.py): <estimate>
- Wire isolation into `mcp_client.py` subprocess spawn (or fixture-level tempdir + env override): <estimate>
- Session-scoped tempdir lifecycle in `fixtures.py` (create before mcp_client, teardown after): <estimate>
- New tests (assert post-test: target paths under tmpdir contain artifacts; user paths unchanged): <estimate>
- Cross-platform validation (POSIX + Windows): <estimate>

Single-line total: `~<N> hours` or `~<N> days`. Calibrate to the existing v1.0 phase sizes — v1.0 phases averaged X hours each (cite if you can find it in PROJECT.md / MILESTONES.md; otherwise estimate from first principles and label as such).

## 5. Open questions

Bullet list of things this spike could NOT answer without violating the black-box rule. For each, state what evidence WOULD answer it and how (e.g. "ask the user", "wait for v1.1 implementation to surface it empirically", "out-of-band check homelab-mcp's PyPI README").

Required candidates to consider (drop any that §1+§2 actually answered):
- Does homelab-mcp respect XDG vars on Windows, or only on POSIX?
- Is there a daemon / shared lock outside the user filesystem (mDNS, Unix socket in /tmp, Windows named pipe)?
- Does `list_registered_servers` read from disk or in-memory state mutated by an out-of-process daemon?
- Is `--help` output complete, or are there hidden flags (e.g. `--debug-config`)?
- Does the test framework's preflight handshake actually trigger any registry writes, or only reads?

---

**Raw evidence:** see `raw/` subdirectory.
```

Hard requirements:
- Every claim in §1 cites a specific raw/*.txt file.
- §3's recommendation cites both §1 (what to isolate) and §2 (how).
- §4 produces a concrete number (range OK), not "TBD".
- §5 has at least 2 bullets; "no open questions" is almost certainly wrong under the black-box constraint.
- DO NOT propose any code edits to `src/`. The plan deliverable is the report only.

Time budget: ~15 minutes including reading back through the raw captures.
  </action>
  <verify>
    <automated>test -f .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md && grep -c "^## " .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md | awk '$1>=5{exit 0} {exit 1}' && grep -q "State homelab-mcp" .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md && grep -q "Isolation knobs" .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md && grep -q "Recommended isolation" .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md && grep -q "Effort estimate" .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md && grep -q "Open questions" .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md && grep -q "raw/" .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md && echo OK</automated>
  </verify>
  <done>FINDINGS.md exists with all five required H2 sections present (state inventory, isolation knobs, recommended strategy, effort estimate, open questions). Section 1 cites raw/*.txt evidence files by name. Section 3 names exactly one primary strategy from the allowed set. Section 4 has a numeric estimate. Section 5 has at least two open questions. No files under src/ have been modified.</done>
</task>

</tasks>

<verification>
Phase-level checks (run after both tasks):

1. **Deliverable exists and is well-formed:**
   ```bash
   test -f .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md
   ```

2. **All five required sections present** (H2 headings):
   ```bash
   grep -E "^## (State homelab-mcp|Isolation knobs|Recommended isolation|Effort estimate|Open questions)" \
     .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/FINDINGS.md | wc -l
   # Expect: 5
   ```

3. **Raw evidence directory populated:**
   ```bash
   ls .planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw/ | wc -l
   # Expect: >= 6
   ```

4. **No src/ modifications** (the spike is recon-only):
   ```bash
   git status --porcelain src/ | wc -l
   # Expect: 0
   ```

5. **Black-box rule honored** — manual review: confirm no homelab-mcp source files were opened during the session. The task descriptions explicitly forbid it; verify by reading back the conversation if any doubt.
</verification>

<success_criteria>
- `FINDINGS.md` exists at the deliverable path with all five required sections.
- §1 (state inventory) cites concrete paths and raw evidence files; nothing in §1 is speculation.
- §2 (isolation knobs) lists CLI flags from `--help` output (or explicitly states none exist) AND env vars (named or conventional).
- §3 (recommendation) picks exactly one primary strategy and cites §1+§2 in its rationale.
- §4 (effort) gives a numeric estimate.
- §5 (open questions) lists at least two questions that could not be answered under the black-box rule.
- `raw/` subdirectory contains the six capture files from Task 1.
- `git status src/` is clean — no production code changes.
- Total wall-clock under 30 minutes.
</success_criteria>

<output>
After completion, create `.planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/260506-qxs-01-SUMMARY.md` linking to FINDINGS.md and noting any deviations from the plan (e.g. capture steps that errored).
</output>
