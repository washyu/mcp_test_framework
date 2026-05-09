# Error message style guide

Operator-facing error messages in `mcp-test-framework` follow four rules.
This guide is the citation target for every rewritten error site (PERSONA-03)
and the canonical source for the SAFE-03 / SAFE-06 reference messages that
downstream config-safety work will implement verbatim.

## Rules

1. **Operator terms only.** No spec IDs, no internal jargon, no
   `Phase N` / `Plan N-N` / `TOOLCFG-`/`D-`/`CD-` / file:line references.
   The operator does not have your planning artefacts.
2. **Name the actionable next step inline.** Every error ends with a
   `next: <action verb> <command-or-instruction>` line. The verb must
   be imperative (`run`, `check`, `update`, `verify`).
3. **One-line summary + multi-line detail block.** Not a wall of text.
   Format:

       <summary>

       <detail line 1>
       <detail line 2>
       ...

       next: <action> <instruction>

4. **Preserve exit codes.** Don't change behaviour, only words. The
   table below records the contract.

| Error class                              | Exit code |
|------------------------------------------|-----------|
| Config not found / typo'd path           | 2         |
| Config schema mismatch / version error   | 2         |
| MCP server command not on PATH           | 2         |
| MCP server fails handshake               | 2         |
| Judge endpoint unreachable               | 2         |
| Test failure                             | 1         |
| All pass                                 | 0         |
| SIGINT (Ctrl+C)                          | 130       |

## Reference messages (locked for downstream phases)

The following messages are LOCKED in this style guide. Downstream
implementations copy them verbatim — copy exactly, do not reword.

### SAFE-03 — no config found, framework refuses to run

    no config file found: ./config.yaml

    the framework refuses to run without a config file because it would
    otherwise call every tool the server advertises -- including any
    destructive ones. you must explicitly opt in to which tools run.

    next: run `mcp-test-framework config-init -o config.yaml` to generate
          a starter config, then edit it to enable the tools you want to test

### SAFE-06 — config uses an older schema version

    config file uses an older format: <path>

    this release of mcp-test-framework expects schema version 2 (opt-in
    tool selection); your config is version 1 (opt-out). the difference
    matters: in v1 a tool with no entry runs by default, in v2 it skips
    by default.

    your existing per-tool settings (`call_arguments`, `judges`,
    `skip_reason`) port forward unchanged -- only the implicit default
    flips. the migration walkthrough at docs/MIGRATION-v1-to-v2.md shows
    the steps.

    next: run `mcp-test-framework config-init -o config.yaml.new` to see
          the v2 layout, port your tool entries across, then replace your
          existing config

## Banned strings (manual review checklist)

When rewriting an error message, grep the rewritten output for these
patterns -- any match is a regression:

    Phase \d
    Plan \d-\d
    [A-Z]{2,}-\d{2}      # spec IDs like TOOLCFG-01, ISOL-02, D-03
    \d{6}-[a-z0-9]{3}    # quick-task IDs like 260507-j6i
    src/.*\.py:\d+       # file:line references
    \(.*\.md\)           # parenthetical file references inside the message
