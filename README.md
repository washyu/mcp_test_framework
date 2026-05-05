# mcp_test_framework

A pytest-based Python framework for testing MCP (Model Context Protocol) servers.

The MVP targets the `homelab-mcp` server over stdio and validates one tool
(`list_registered_servers`) end-to-end through schema validation, an
Ollama-backed description-quality judge, and output conformance checks.

> Full setup, configuration, and usage docs land in Phase 5 (CLI / docs).
> See `.planning/PROJECT.md` and `docs/mcp_test_framework_mvp_spec.md` for the
> authoritative scope and design.
