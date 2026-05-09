# Examples

This directory contains real-world configs for specific MCP servers.
Each file is a complete, runnable `config.yaml` you can copy to your
working directory and pass to `mcp-test-framework run --config <path>`.

## Files

- `homelab-mcp.yaml` — config for the
  [`homelab-mcp`](https://github.com/washyu/homelab-mcp) server. The
  reference example used during development of this framework.

## Naming convention

Files are named after the MCP server they target (lowercase, dashes match
the upstream package name). To add an example for another server, drop a
file named after it here and link it from this README.
