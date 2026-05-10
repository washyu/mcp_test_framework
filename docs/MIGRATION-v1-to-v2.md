# Migrating config from schema v1 -> v2

This release of mcp-test-framework expects schema version 2. v1 configs no
longer load -- the loader refuses with a clear pointer here. This page
walks an existing operator through the port.

## Why this matters

In v1, a tool with no `tools.<name>` entry ran by default -- including any
destructive tools the server advertised. In v2, a tool with no entry skips
by default. You explicitly opt every tool in.

The flip is intentional. Auto-migration would silently keep your old
`call_arguments` while inverting the default behind your back -- the exact
silent-destructive class v2 is built to prevent. So the migration is
manual and the framework refuses to load a v1 file.

## What stays the same

Per-tool fields port forward unchanged: `call_arguments`, `judges`,
`skip_reason`. Top-level `ollama:`, `mcp_server:`, and
`judge_timeout_seconds:` blocks port forward unchanged.

## What changes

- `version: 1` -> `version: 2` (top-level header).
- `target:` block -> DELETE. v2 has no `target` field. Single-tool focus is
  now done via a focus config passed to `--config`
  (e.g. `--config focus-list_tools.yaml`).
- `.env` files no longer override config. If you had any framework config
  in `.env` (`OLLAMA_BASE_URL`, `MCP_SERVER_COMMAND`, etc.), move it into
  your YAML.
- env vars no longer override config. The framework's config sources
  collapse to: YAML + CLI flags.
- Unlisted tools auto-skip. In v1, you skipped destructive tools with
  `tools.<name>.skip: true` entries. In v2, you opt them IN by listing
  them; everything else skips with reason `"not selected in config"`.

## Step-by-step port

1. Run `mcp-test-framework config-init -o config.yaml.new` from your repo
   root. This emits a complete v2 scaffold with every discovered tool
   listed as `skip: true`.
2. Open both your old `config.yaml` and the new `config.yaml.new` side by
   side.
3. For each tool you want to keep testing:
   - Find the tool's block in `config.yaml.new`.
   - Delete the `skip: true` and `skip_reason:` lines.
   - Copy your `call_arguments:` / `judges:` blocks across from the old
     file.
4. Delete the top-level `target:` block from your old config (do not copy
   it into the new file).
5. If you had framework config in `.env`, move it into your new YAML.
6. Replace `config.yaml` with `config.yaml.new`.
7. Re-run `mcp-test-framework run`. The pre-run output will show which
   tools are selected.

## Side-by-side per-tool example

Before (v1):

```yaml
version: 1

target:
  tool_name: null

tools:
  list_servers:
    call_arguments:
      tag: "production"
    judges: ["clarity"]
  delete_database:
    skip: true
    skip_reason: "destructive -- never run against the live cluster"
```

After (v2 -- opt-in equivalent):

```yaml
version: 2

# target: block deleted.

tools:
  list_servers:
    # listed and not skipped -> selected to run.
    call_arguments:
      tag: "production"
    judges: ["clarity"]
  delete_database:
    # still listed-with-skip -> SKIP row with the curated reason.
    skip: true
    skip_reason: "destructive -- never run against the live cluster"
  # Every other tool the server advertises auto-skips with reason
  # "not selected in config". You no longer need an entry per tool.
```

## What about `.env`?

The framework no longer reads `.env` for config values. CI-secret patterns
(API keys for future HTTP-backed judges) still pass through `.env` as a
process-env convention, but the framework's config layer ignores it.

See `.env.example` in the repo root for the supported pattern.
