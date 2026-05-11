---
id: SEED-013
status: dormant
planted: 2026-05-11
planted_during: Phase 14 (hybrid-runner-with-domain-ui) UAT — Test 3 verbosity-ladder verification
trigger_when: Phase 16 (reporter UX overhaul), OR any milestone touching operator-facing CLI progress / pytest-subprocess wrapper UX
scope: Small
---

# SEED-013: Progress feedback during silent pytest subprocess run

## Why This Matters

Phase 14 made pytest invisible by default — the wrapper runs `pytest` as a child subprocess and renders only the domain UI (header → per-tool rows → summary line) when the subprocess exits. This is the right contract for the operator, but it creates a UX dead spot: while the subprocess is working, the operator sees **nothing** until it finishes.

Surfaced from Phase 14 UAT Test 3 on 2026-05-11. Operator feedback verbatim:

> "the other runs where we only show the result summary is a little jarring because the command seems to hang for a but with no user feedback then we get the output so maybe a spinner with text saying running tests or a status bar would be for users."

Concrete measurements from the live run that exposed it:
- Default `mcp-test-framework run`: ~20 silent seconds before the domain UI dropped (1 FAIL / 8 PASS / 59 SKIP, homelab-mcp, 289 contract cases)
- `-q` is the worst case — no header to anchor on, just silence then a one-line summary
- `--debug` and `--raw` are unaffected because they stream pytest's native progress dots

Operators trained on raw pytest are used to the `.`/`F`/`s` progress markers as a "the process is alive" signal. Phase 14 deliberately suppressed those — but provided no replacement. This is goal-adjacent to RUNNER-04 (verbosity ladder) but was scoped out of Phase 14's plans because nobody had run it against ~290 live tests yet.

## When to Surface

**Trigger:** Phase 16 reporter UX overhaul, OR any milestone touching operator-facing CLI progress / pytest-subprocess wrapper UX.

This seed should be presented during `/gsd-new-milestone` when the milestone scope matches any of:
- Reporter UX work (sister seed: SEED-008)
- Anything touching `_runner.run_pytest_subprocess` or the cli.py `run` command's dispatch
- Performance-perception / TTI (time-to-information) work on the operator surface
- Any milestone that promises "better operator feedback" or "clearer CLI"
- A specific Phase 16 plan that adds `--explain` (mentioned in CONTEXT D-14) — natural place to also add live progress, since both are operator-feedback enhancements

Related artifacts:
- SEED-008 (reporter-ux-overhaul) — parent UX theme; this is one concrete gap inside it
- SEED-011 (hybrid-runner-domain-ui) — Phase 14's parent seed; this is the first piece of unfinished business surfaced after Phase 14 shipped
- ROADMAP.md Phase 16 — "Reporter UX overhaul"

## Scope Estimate

**Small** — a few hours. The seed describes a layered set of options, smallest to largest:

1. **Smallest (~1 hr):** Emit a single `Running 289 contract cases against <server>...` line BEFORE the subprocess.run() call. Replace with the full render output when done. Zero risk to the rendering contract; lands the "I'm alive" signal at minimum cost. Recommended first cut.

2. **Small (~2-4 hrs):** Spawn a background thread that prints a single-line spinner with elapsed time (`\r⠋ Running tests... 12s`) while subprocess.run is blocked; clear the line when output is ready. Skip if stdout is not a TTY (CI compatibility). Adds polish; minimal risk.

3. **Medium (own plan):** Capture pytest stdout in real-time via Popen + line-stream, translate pytest's progress markers (`.`/`F`/`s`) to a domain-language counter (`Tested 47/289 contract cases — 0 failures so far`). Higher effort because it requires reshaping `run_pytest_subprocess` from `subprocess.run` to a streaming Popen loop, and matching pytest's progress output to domain rows. Stays in MCP-domain language — this is the "right" Phase 16-shaped answer. Probably its own plan inside Phase 16 rather than a side fix.

A Phase 16 plan can cherry-pick any layer. Layer 1 alone would already close the UAT finding.

## Breadcrumbs

Related code:
- `src/mcp_test_framework/_runner.py::run_pytest_subprocess` — currently blocks on `subprocess.run(..., capture_output=True)`. Wrap this call with the progress signaling.
- `src/mcp_test_framework/cli.py::run` — sets up the call; could emit the "Running N contract cases..." line here BEFORE delegating, after `_load_config` + `_discover_tools_for_run`.
- `src/mcp_test_framework/_runner.py::RenderContext` — already carries `test_plan_count` (the 289 from header `Test plan: 289 contract cases`), so the count is available pre-run.

Related decisions:
- Phase 14 CONTEXT D-12 (`-q` / quiet mode) — quiet suppresses header + rows, leaves only summary. SEED-013 should respect this: under `-q`, suppress the spinner too, OR show only an elapsed-time clock with no `Running tests…` prefix.
- Phase 14 CONTEXT D-13 (`--debug`) — debug appends raw pytest output. SEED-013 should NOT activate progress feedback under `--debug` because pytest's native dots will stream live anyway.
- Phase 14 CONTEXT D-14 (`--explain` belongs to Phase 16) — natural plumbing point: the same Phase 16 plan that adds `--explain` can add progress feedback.

Related captured items:
- `.planning/phases/14-hybrid-runner-with-domain-ui/14-HUMAN-UAT.md` — gap entry "Operator running `mcp-test-framework run` (default or `-q`) sees progress feedback while the child pytest is working" with severity=minor, candidate_fixes layered as above.

## Notes

This seed deliberately does NOT belong to Phase 14 gap-closure. Phase 14's goal was "operator sees domain UI instead of pytest framing" — that goal IS met. The progress-feedback gap is goal-adjacent (it's about WHEN the operator sees the UI, not WHAT they see). The principled call is to fix Phase 14's true gaps (Windows Unicode crash, stale cache patch path) inside Phase 14, and let progress feedback ride with the broader Phase 16 reporter work.

If Phase 16 gets delayed and operators start hitting this routinely, escalate by promoting the "Smallest" option (Layer 1) to a hotfix plan — it's literally one `typer.echo()` line plus a flush, no behavioral risk.
