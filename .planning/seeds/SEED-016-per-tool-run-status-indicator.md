---
id: SEED-016
status: dormant
planted: 2026-05-12
planted_during: Phase 17 (schema-driven-codegen-surface) planning
trigger_when: After SEED-011 hybrid runner with domain UI lands (Phase 18+), OR any milestone touching operator-facing CLI progress / runner output story
scope: Small
---

# SEED-016: Per-tool run status indicator (`Testing [k/N] <Tool Name>`)

## Why This Matters

When `mcp-test-framework run` exercises a server with many tools (homelab-mcp has
~70 tools, often translating to several hundred contract cases), the operator
has no visual feedback about **which tool is currently being tested**. Pytest's
collection summary buries this — even with progress dots streaming under
`--debug`/`--raw`, dots are anonymous and don't tell the operator "we're 47/289
through, currently exercising `list_registered_servers`".

A live per-tool counter formatted like:

```
Testing [1/999] list_registered_servers
Testing [2/999] register_server
Testing [3/999] unregister_server
...
```

gives the operator:
- A clear "we're alive" signal (closes the silent-subprocess gap from SEED-013)
- A domain-language anchor — they see the tool name they care about, not pytest dots
- Implicit progress (`[k/N]`) so they can estimate time remaining
- A fingerprint of WHICH tool just took 20 seconds when a single test hangs

This is the natural extension of the Phase 14 domain-UI contract: the post-run
render already speaks in tool-level rows, so the in-flight render should too.

## When to Surface

**Trigger:** After SEED-011 hybrid runner with domain UI lands (Phase 18+), OR
any milestone touching operator-facing CLI progress / runner output story.

This seed should be presented during `/gsd-new-milestone` when the milestone
scope matches any of:
- Reporter UX work (sister seed: SEED-008)
- Anything touching `_runner.run_pytest_subprocess` or its streaming layer
- Progress-feedback / TTI (time-to-information) work on the operator surface
- A milestone that promotes SEED-013 layer 3 ("domain-language counter from
  streamed pytest output") — this seed is the more specific shape of that layer

Closely related seeds:
- **SEED-013 (progress-feedback-during-run)** — the general "I'm alive" feedback
  seed. SEED-016 is the **specific output shape** for the per-tool case. If
  SEED-013 layer 3 is implemented, SEED-016's format is the canonical render.
  These can be addressed together in a single Phase 16+ plan.
- **SEED-008 (reporter-ux-overhaul)** — parent UX theme.
- **SEED-011 (hybrid-runner-domain-ui)** — established the post-run render
  contract that this seed extends to the in-flight render.

## Scope Estimate

**Small** — a few hours, integrated with a streaming runner.

Implementation sketch (assumes SEED-013 layer 3 streaming infrastructure or
similar exists):

1. Capture pytest stdout in real-time (replace `subprocess.run(..., capture_output=True)`
   with a streaming Popen + line-reader loop in `_runner.run_pytest_subprocess`).
2. Parse pytest's per-test progress (the `test_id` from `pytest -v` output, or
   the parametrize id from each `PASS`/`FAIL`/`SKIP` line) to extract the tool
   name (parametrize ids already encode tool name today — see how Phase 17's
   `gen-sdet-classes` resolves tool names).
3. Maintain a counter `k` and a known-total `N` (already available pre-run via
   `RenderContext.test_plan_count`).
4. Render one line per tool transition: `Testing [{k}/{N}] {tool_name}`,
   overwriting the previous line via `\r` (TTY-only — fall back to newline
   under non-TTY/CI).
5. Honor verbosity ladder: suppress under `-q`, defer to native pytest output
   under `--debug`/`--raw`.

Edge cases to think about:
- A single tool with multiple contract cases — collapse consecutive same-tool
  ticks to one render with a sub-counter (`Testing [12/999] list_registered_servers (3 cases)`),
  or just re-render the same line per case. Both are acceptable; pick whichever
  is cheaper.
- `N` may not be exactly the tool count — it's likely the test-case count.
  Format must clarify: is `[k/N]` "case k of N cases" or "tool k of N tools"?
  Recommended: case-level (`[k/N]` = test cases), tool name annotates which
  tool that case belongs to. This matches operator expectations from CI tools.
- Width budget — long tool names + `[999/999]` prefix can wrap on narrow terms.
  Truncate tool names at the column boundary or break to two lines.

## Breadcrumbs

Related code (verified present 2026-05-12):
- `src/mcp_test_framework/_runner.py` — `run_pytest_subprocess` is the
  current blocking call to wrap with a streaming reader. `RenderContext`
  already carries `test_plan_count`.
- `src/mcp_test_framework/cli.py` — `run` command dispatch; emits header
  line BEFORE the subprocess.

Related decisions:
- Phase 14 CONTEXT D-12 (`-q` / quiet mode) — quiet suppresses header + rows;
  SEED-016 must also suppress the live counter under `-q`.
- Phase 14 CONTEXT D-13 (`--debug`) — debug streams pytest's native output;
  SEED-016 must not double-render.
- Phase 14 CONTEXT D-14 (`--explain` belongs to Phase 16) — same plumbing
  point that SEED-013 mentions; a Phase 16 plan could land all three
  together.

Related seeds:
- SEED-013 (parent — general progress feedback)
- SEED-008 (parent UX theme)
- SEED-011 (post-run render contract this extends)

## Notes

Captured from a Phase 17 planning conversation on 2026-05-12. The user asked
for the indicator after seeing how Phase 17 introduces a per-tool concept
(`gen-sdet-classes` generates one class per tool, registry is per-server with
N tools) — the symmetry between "one file per tool, generated" and "one
status line per tool, in-flight" is intentional.

If SEED-013 gets prioritized first, fold this seed in as the concrete output
shape for its Layer 3. If this seed gets prioritized first, SEED-013 layers
1-2 (basic spinner) can be addressed cheaply alongside.
