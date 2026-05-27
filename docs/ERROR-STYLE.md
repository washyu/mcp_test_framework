# Error message style guide

Operator-facing error messages in `mcp-contracts` follow four rules.
This guide is the citation target for every rewritten error site and the
canonical source for the missing-config and schema-mismatch reference
messages that the config-safety code implements verbatim.

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

### No config found, framework refuses to run

    no config file found: ./config.yaml

    the framework refuses to run without a config file because it would
    otherwise call every tool the server advertises -- including any
    destructive ones. you must explicitly opt in to which tools run.

    next: run `mcp-contracts config-init -o config.yaml` to generate
          a starter config, then edit it to enable the tools you want to test

### Config uses an older schema version

    unsupported config version <version>

    this build supports schema version 2.
    your config declares version <version>, which is no longer accepted.

    next: run `mcp-contracts config-init -o config.yaml` to generate a
          current scaffold

### skip and skip_buckets are both set

    skip=true and skip_buckets are mutually exclusive

    skip=true is whole-tool: every bucket is already skipped.
    layering skip_buckets on top is redundant intent and the framework
    will not silently pick which lever wins.

    next: keep skip=true to disable every bucket, OR remove skip and
          use skip_buckets alone to disable named buckets.

### host_isolation literal_error

Trigger: operator sets `host_isolation: <unknown>` in `config.yaml` where
`<unknown>` is neither `strict` nor `passthrough`. Source: the
`(literal_error, ('host_isolation',))` branch in
`_emit_operator_error_for_validation` (cli error mapper). Pinned by
`tests/framework/unit/test_error_style.py::test_error_style_host_isolation_literal_rejection`.

    unknown host_isolation mode: '<bad_value>'

    host_isolation accepts only 'strict' or 'passthrough'.
    strict (default) isolates the spawned MCP subprocess from your host
    credentials and HOME;
    passthrough hands the operator's full env to the subprocess (xdist
    clamped to 1 worker).

    next: set `host_isolation: strict` or `host_isolation: passthrough`
          in your config.yaml; see docs/LIBRARY-MODE.md §host-isolation
          for the trade-off

## Banned strings (manual review checklist)

When rewriting an error message, grep the rewritten output for these
patterns -- any match is a regression:

    Phase \d
    Plan \d-\d
    [A-Z]{2,}-\d{2}      # spec IDs like TOOLCFG-01, ISOL-02, D-03
    \d{6}-[a-z0-9]{3}    # quick-task IDs like 260507-j6i
    src/.*\.py:\d+       # file:line references
    \(.*\.md\)           # parenthetical file references inside the message
