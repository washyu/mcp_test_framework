# Deferred Items — Phase 999.2

## Pre-existing test failure (out of scope for plan 03)

**Test:** `tests/framework/unit/test_config_example.py::test_config_example_has_three_placeholder_tools`

**Status:** FAILING since plan 05 shipped.

**Root cause:** Plan 05 added Pattern D (`<required_field_tool>`) to `config.example.yaml`, making the tool count 4 instead of 3. The test at line 41-48 asserts exactly 3 placeholder tools (`<safe_read_tool_a>`, `<safe_read_tool_b>`, `<destructive_tool_c>`).

**Fix needed:** Update the test to expect 4 placeholder tools and add `<required_field_tool>` to the expected set. Alternatively, relax to `expected.issubset(set(tools.keys()))`.

**Owner:** Plan 04 or 06 should pick this up as it is directly related to the config.example.yaml changes.

**Discovered:** Plan 03 execution (2026-05-27)
