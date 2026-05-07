# Drive the v1.1 tool surface end-to-end WITHOUT isolation.
# This is intentionally pre-isolation (the bleed-through measurement that
# Plan 06-02 will fix). MCP_SERVER_COMMAND=uvx + MCP_SERVER_ARGS routes to
# the PyPI-cached homelab-mcp install per config.example.yaml's "default
# invocation uses uvx for zero-install" pattern.

$env:MCP_SERVER_COMMAND = 'uvx'
$env:MCP_SERVER_ARGS = '["homelab-mcp"]'

# v1.1 surface defaults to list_keyring_credentials per config.example.yaml.
# Run that target tool's full suite, then run a second pass for
# list_registered_servers so we exercise BOTH tool calls captured in
# 06-CONTEXT.md "ISOL-03 verification (D-08 step 2)".

Write-Host "=== PASS 1: target = list_keyring_credentials ==="
$env:TARGET_TOOL_NAME = 'list_keyring_credentials'
uv run pytest tests/test_homelab_list_registered_servers.py -v --tb=short -k 'test_target_tool_exists or test_empty_args_call_returns_non_error' 2>&1 | Tee-Object -FilePath '.planning/phases/06-per-session-host-state-isolation/raw/test-pass1.log'
$pass1Exit = $LASTEXITCODE
Write-Host "PASS 1 exit code: $pass1Exit"

Write-Host ""
Write-Host "=== PASS 2: target = list_registered_servers ==="
$env:TARGET_TOOL_NAME = 'list_registered_servers'
uv run pytest tests/test_homelab_list_registered_servers.py -v --tb=short -k 'test_target_tool_exists or test_empty_args_call_returns_non_error' 2>&1 | Tee-Object -FilePath '.planning/phases/06-per-session-host-state-isolation/raw/test-pass2.log'
$pass2Exit = $LASTEXITCODE
Write-Host "PASS 2 exit code: $pass2Exit"

Write-Host ""
Write-Host "=== Summary ==="
Write-Host "PASS 1 (list_keyring_credentials): exit $pass1Exit"
Write-Host "PASS 2 (list_registered_servers): exit $pass2Exit"
