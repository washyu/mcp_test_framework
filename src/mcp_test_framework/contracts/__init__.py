"""mcp_test_framework.contracts — pytest-injected contract test surface.

This subpackage contains the 10 contract-test bodies that the framework's
pytest plugin synthesizes into operator test sessions. Operators do not
need to reference this module directly; the library-mode entry point is
a single ini line:

    # operator's pyproject.toml
    [tool.pytest.ini_options]
    mcp_config_file = "./config.yaml"

When `mcp_config_file` is set, the plugin (`mcp_test_framework._plugin`)
reads the YAML, runs the black-box guard, parametrizes the test bodies
in `_tests.py` over `config.tools` (opt-in allowlist semantics), applies
the `mcp_contract` marker, and injects them under the synthetic nodeid
`<mcp-contracts>::test_<name>[<tool>]`.

When `mcp_config_file` is unset, this subpackage is inert — no contract
tests are injected. Operators who installed `mcp-contracts` solely for
`gen-test-classes` see no behavioral change.

There is intentionally NO `register()` API. Phase 27 pivoted away from
the register approach in favor of a pytest-native ini route.
"""
