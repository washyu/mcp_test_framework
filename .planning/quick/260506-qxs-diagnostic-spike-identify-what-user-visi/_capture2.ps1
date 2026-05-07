# Follow-up captures: credentials subcommand help + wider home-dir homelab* scan.
$ErrorActionPreference = 'Continue'
$RawDir = '.planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw'
$h = "$RawDir/help.txt"

"" | Out-File -FilePath $h -Append -Encoding utf8
"=== uvx homelab-mcp credentials --help ===" | Out-File -FilePath $h -Append -Encoding utf8
(uvx homelab-mcp credentials --help 2>&1) | Out-File -FilePath $h -Append -Encoding utf8

"" | Out-File -FilePath $h -Append -Encoding utf8
"=== uvx homelab-mcp credentials list --help ===" | Out-File -FilePath $h -Append -Encoding utf8
(uvx homelab-mcp credentials list --help 2>&1) | Out-File -FilePath $h -Append -Encoding utf8

# Wider candidate scan: any `homelab*` filename or directory under user profile,
# capped at depth 3 to avoid scanning the entire home directory tree.
$wider = "$RawDir/wider_scan.txt"
"=== Wider scan: USERPROFILE\**\homelab* (depth<=3) at $(Get-Date -Format o) ===" | Out-File -FilePath $wider -Encoding utf8
$found = Get-ChildItem -Path $env:USERPROFILE -Filter 'homelab*' -Recurse -Depth 3 -Force -ErrorAction SilentlyContinue
if ($found) {
    $found | Select-Object FullName, Length, LastWriteTime, Mode | Format-List | Out-File -FilePath $wider -Append -Encoding utf8
} else {
    "NO homelab* files/dirs found within depth 3 of USERPROFILE" | Out-File -FilePath $wider -Append -Encoding utf8
}

"" | Out-File -FilePath $wider -Append -Encoding utf8
"=== Wider scan: USERPROFILE\**\*homelab* (depth<=3, contains 'homelab') at $(Get-Date -Format o) ===" | Out-File -FilePath $wider -Append -Encoding utf8
$found2 = Get-ChildItem -Path $env:USERPROFILE -Filter '*homelab*' -Recurse -Depth 3 -Force -ErrorAction SilentlyContinue
if ($found2) {
    $found2 | Select-Object FullName, Length, LastWriteTime, Mode | Format-List | Out-File -FilePath $wider -Append -Encoding utf8
} else {
    "NO files/dirs containing 'homelab' found within depth 3 of USERPROFILE" | Out-File -FilePath $wider -Append -Encoding utf8
}

# OS keyring inventory: credential manager (read-only listing of generic credentials only)
$kr = "$RawDir/keyring.txt"
"=== Windows Credential Manager (cmdkey /list) at $(Get-Date -Format o) ===" | Out-File -FilePath $kr -Encoding utf8
"NOTE: filtered to lines mentioning 'homelab' or 'mcp' to avoid leaking unrelated creds" | Out-File -FilePath $kr -Append -Encoding utf8
$cmdkeyOut = cmdkey /list 2>&1
$filtered = $cmdkeyOut | Where-Object { $_ -match 'homelab|mcp|MCP' }
if ($filtered) {
    $filtered | Out-File -FilePath $kr -Append -Encoding utf8
} else {
    "NONE: no Windows Credential Manager entries match 'homelab' or 'mcp'." | Out-File -FilePath $kr -Append -Encoding utf8
    "NOTE: this only inspects domain creds; 'generic' creds via Python keyring may use a separate target name format not matched by these substrings." | Out-File -FilePath $kr -Append -Encoding utf8
}

Write-Host "Follow-up capture complete."
