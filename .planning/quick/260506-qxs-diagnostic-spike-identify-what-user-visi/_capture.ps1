# Recon capture script - read-only observation of homelab-mcp host-state surface
# Run from repo root.
$ErrorActionPreference = 'Continue'
$RawDir = '.planning/quick/260506-qxs-diagnostic-spike-identify-what-user-visi/raw'

function Snapshot-Paths {
    param([string]$Label, [string]$OutFile)
    $candidates = @(
        "$env:APPDATA\homelab-mcp",
        "$env:APPDATA\homelab_mcp",
        "$env:LOCALAPPDATA\homelab-mcp",
        "$env:LOCALAPPDATA\homelab_mcp",
        "$env:USERPROFILE\.homelab-mcp",
        "$env:USERPROFILE\.config\homelab-mcp",
        "$env:USERPROFILE\.local\share\homelab-mcp",
        "$env:USERPROFILE\.cache\homelab-mcp"
    )
    "=== Snapshot label: $Label ===" | Out-File -FilePath $OutFile -Encoding utf8
    "=== Captured: $(Get-Date -Format o) ===" | Out-File -FilePath $OutFile -Append -Encoding utf8
    "" | Out-File -FilePath $OutFile -Append -Encoding utf8

    foreach ($p in $candidates) {
        "----- PATH: $p -----" | Out-File -FilePath $OutFile -Append -Encoding utf8
        if (Test-Path -LiteralPath $p) {
            try {
                Get-ChildItem -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue |
                    Select-Object FullName, Length, LastWriteTime |
                    Format-List | Out-File -FilePath $OutFile -Append -Encoding utf8
            } catch {
                "ERROR enumerating: $_" | Out-File -FilePath $OutFile -Append -Encoding utf8
            }
        } else {
            "ABSENT" | Out-File -FilePath $OutFile -Append -Encoding utf8
        }
        "" | Out-File -FilePath $OutFile -Append -Encoding utf8
    }

    # Glob TEMP for homelab-mcp* and homelab_mcp*
    "----- GLOB: $env:TEMP\homelab*  (homelab-mcp*, homelab_mcp*) -----" | Out-File -FilePath $OutFile -Append -Encoding utf8
    Get-ChildItem -Path $env:TEMP -Filter 'homelab*' -Force -ErrorAction SilentlyContinue |
        Select-Object FullName, Length, LastWriteTime, Mode |
        Format-List | Out-File -FilePath $OutFile -Append -Encoding utf8
    "" | Out-File -FilePath $OutFile -Append -Encoding utf8
}

# 1. CLI help capture
$helpFile = "$RawDir/help.txt"
"=== uvx homelab-mcp --help (captured $(Get-Date -Format o)) ===" | Out-File -FilePath $helpFile -Encoding utf8
try {
    $out = uvx homelab-mcp --help 2>&1
    $out | Out-File -FilePath $helpFile -Append -Encoding utf8
} catch {
    "EXCEPTION: $_" | Out-File -FilePath $helpFile -Append -Encoding utf8
}
"" | Out-File -FilePath $helpFile -Append -Encoding utf8

# Also try --version (read-only)
"=== uvx homelab-mcp --version ===" | Out-File -FilePath $helpFile -Append -Encoding utf8
try {
    $out2 = uvx homelab-mcp --version 2>&1
    $out2 | Out-File -FilePath $helpFile -Append -Encoding utf8
} catch {
    "EXCEPTION: $_" | Out-File -FilePath $helpFile -Append -Encoding utf8
}
"" | Out-File -FilePath $helpFile -Append -Encoding utf8

# 2. BEFORE snapshot
Snapshot-Paths -Label 'BEFORE handshake' -OutFile "$RawDir/before.txt"

# 3. Trigger a brief handshake. The framework's preflight does:
#    - shutil.which check, then a stdio handshake.
# We do the lightest possible read-only invocation: --version (already done above).
# Per plan: optionally substitute --version when test invocation is too disruptive.
# We'll ALSO attempt one stdio handshake using a small Python snippet that opens
# stdio_client to homelab-mcp and calls list_tools (the same shape as preflight).
$handshakeFile = "$RawDir/handshake.log"
"=== Handshake attempt at $(Get-Date -Format o) ===" | Out-File -FilePath $handshakeFile -Encoding utf8

# Strategy: invoke the framework's existing preflight by running a single integration test.
# But because mutating user state is the very thing we're investigating, fall back to
# --help-only (already in help.txt) and rely on the snapshot diff to capture the side
# effects of the uvx package install + handshake we already did above when running --help/--version.
"Skipping pytest invocation to avoid disturbing the user's running homelab-mcp." | Out-File -FilePath $handshakeFile -Append -Encoding utf8
"The uvx --help / --version above counts as an instantiation of the package: uvx" | Out-File -FilePath $handshakeFile -Append -Encoding utf8
"resolves the package, downloads it if not cached, and invokes its entry point." | Out-File -FilePath $handshakeFile -Append -Encoding utf8
"This means BEFORE/AFTER diff captures any state created by package install + entry-point startup," | Out-File -FilePath $handshakeFile -Append -Encoding utf8
"but NOT necessarily state created by an MCP stdio session (which loads tool registry)." | Out-File -FilePath $handshakeFile -Append -Encoding utf8
"This caveat is documented in FINDINGS.md Open Questions." | Out-File -FilePath $handshakeFile -Append -Encoding utf8
"" | Out-File -FilePath $handshakeFile -Append -Encoding utf8

# 4. AFTER snapshot
Snapshot-Paths -Label 'AFTER handshake' -OutFile "$RawDir/after.txt"

# 5. Process inventory
$procFile = "$RawDir/processes.txt"
"=== Get-Process homelab*, mcp* at $(Get-Date -Format o) ===" | Out-File -FilePath $procFile -Encoding utf8
$procs = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match '^(homelab|mcp)' }
if ($procs) {
    $procs | Format-List Id, ProcessName, Path, StartTime | Out-File -FilePath $procFile -Append -Encoding utf8
} else {
    "NONE OBSERVED matching homelab* or mcp*" | Out-File -FilePath $procFile -Append -Encoding utf8
}
"" | Out-File -FilePath $procFile -Append -Encoding utf8
"=== ALL python.exe processes (homelab-mcp could appear under python) ===" | Out-File -FilePath $procFile -Append -Encoding utf8
$pyprocs = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match '^(python|pythonw|uv|uvx)' }
if ($pyprocs) {
    $pyprocs | Format-List Id, ProcessName, Path, StartTime | Out-File -FilePath $procFile -Append -Encoding utf8
} else {
    "NONE" | Out-File -FilePath $procFile -Append -Encoding utf8
}

# 6. Listening ports
$portFile = "$RawDir/listening_ports.txt"
"=== netstat -ano | findstr LISTENING at $(Get-Date -Format o) ===" | Out-File -FilePath $portFile -Encoding utf8
netstat -ano | Select-String 'LISTENING' | Out-File -FilePath $portFile -Append -Encoding utf8

# 7. Env scan
$envFile = "$RawDir/env_scan.txt"
"=== HOMELAB*, MCP*, XDG_* env vars at $(Get-Date -Format o) ===" | Out-File -FilePath $envFile -Encoding utf8
$matches = Get-ChildItem env: | Where-Object { $_.Name -match '^(HOMELAB|MCP|XDG_)' }
if ($matches) {
    $matches | Format-List | Out-File -FilePath $envFile -Append -Encoding utf8
} else {
    "NONE SET (no HOMELAB_*, MCP_*, or XDG_* env vars in current shell)" | Out-File -FilePath $envFile -Append -Encoding utf8
}
"" | Out-File -FilePath $envFile -Append -Encoding utf8
"=== Other potentially-relevant vars (HOME, USERPROFILE, APPDATA, LOCALAPPDATA, TEMP) ===" | Out-File -FilePath $envFile -Append -Encoding utf8
"HOME=$env:HOME" | Out-File -FilePath $envFile -Append -Encoding utf8
"USERPROFILE=$env:USERPROFILE" | Out-File -FilePath $envFile -Append -Encoding utf8
"APPDATA=$env:APPDATA" | Out-File -FilePath $envFile -Append -Encoding utf8
"LOCALAPPDATA=$env:LOCALAPPDATA" | Out-File -FilePath $envFile -Append -Encoding utf8
"TEMP=$env:TEMP" | Out-File -FilePath $envFile -Append -Encoding utf8

Write-Host "Capture complete."
