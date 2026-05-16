"""mcp_test_framework.contracts — subpackage stub.

Currently shipped as an empty subpackage so PEP 561-driven type
resolution finds `mcp_test_framework.contracts` from an installed wheel
without "missing stubs" complaints. A future library-mode milestone
fills the register() API + virtual _ContractsModule injection +
contract-test extraction inside this subpackage.

There is intentionally NO `register()` import or implementation here
yet. An operator who imports from this module in the current milestone
window simply finds an empty namespace. The library-mode milestone
ships within the same release before any user-facing wheel publish, so
no helpful runtime ImportError is needed here.
"""
