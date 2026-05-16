"""mcp_test_framework.contracts -- Phase 27 lands register() here.

Phase 26 ships this as an empty subpackage stub so PEP 561-driven type
resolution finds `mcp_test_framework.contracts` from an installed wheel
without "missing stubs" complaints. Phase 27 (LIB-01..LIB-08) fills the
register() API + virtual _ContractsModule injection + contract-test
extraction inside this subpackage.

Per Phase 26 D-13/D-14: NO `register()` import or implementation in v1.4
pre-Phase-27. An operator who imports from this module in the
Phase 26-only milestone window simply finds an empty namespace. Phase 27
ships within the same milestone (v1.4) before any release, so no helpful
runtime ImportError is needed here.
"""
