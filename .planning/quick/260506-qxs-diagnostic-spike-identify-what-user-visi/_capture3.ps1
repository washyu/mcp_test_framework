# Final captures: list contents of the discovered .homelab_mcp dir + update before/after
$ErrorActionPreference = 'Continue'
$RawDir = '.planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw'

$out = "$RawDir/discovered_state_dir.txt"
"=== Contents of C:\Users\washy\.homelab_mcp\ at $(Get-Date -Format o) ===" | Out-File -FilePath $out -Encoding utf8
"NOTE: filenames + sizes + mtimes only -- contents NOT read (some files may contain credentials, registry data, or homelab-mcp source -- all of which are forbidden under the black-box rule)." | Out-File -FilePath $out -Append -Encoding utf8
"" | Out-File -FilePath $out -Append -Encoding utf8
$dir = "$env:USERPROFILE\.homelab_mcp"
if (Test-Path -LiteralPath $dir) {
    Get-ChildItem -LiteralPath $dir -Recurse -Force -ErrorAction SilentlyContinue |
        Select-Object FullName, Length, LastWriteTime, Mode |
        Format-List | Out-File -FilePath $out -Append -Encoding utf8
} else {
    "MISSING (unexpected -- wider_scan.txt found it)" | Out-File -FilePath $out -Append -Encoding utf8
}

# Append discovered dir to before/after retroactively for completeness; relabel
$beforeAddendum = "$RawDir/before.txt"
"" | Out-File -FilePath $beforeAddendum -Append -Encoding utf8
"=== ADDENDUM: $env:USERPROFILE\.homelab_mcp (the underscore variant -- discovered late, captured at $(Get-Date -Format o)) ===" | Out-File -FilePath $beforeAddendum -Append -Encoding utf8
"NOTE: this entry was missing from the original BEFORE candidate list; the live snapshot of its current state is in discovered_state_dir.txt. Both before/after snapshots above showed only the hyphen variant '.homelab-mcp' as ABSENT." | Out-File -FilePath $beforeAddendum -Append -Encoding utf8

$afterAddendum = "$RawDir/after.txt"
"" | Out-File -FilePath $afterAddendum -Append -Encoding utf8
"=== ADDENDUM: $env:USERPROFILE\.homelab_mcp (underscore variant; discovered late) ===" | Out-File -FilePath $afterAddendum -Append -Encoding utf8
"See discovered_state_dir.txt for current contents (PRESENT, modified 2026-04-26)." | Out-File -FilePath $afterAddendum -Append -Encoding utf8

Write-Host "Capture3 complete."
