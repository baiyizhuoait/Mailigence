# ============================================================================
# Mailigence - stop the backend and frontend (optionally the database too)
#
# Usage: .\stop.ps1             stop backend + frontend
#        .\stop.ps1 -StopDb     also stop the bundled PostgreSQL server
# ============================================================================
param([switch]$StopDb)

$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Get-PortOwnerPids([int]$Port) {
    $owners = @()
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($conn) { $owners += $conn.OwningProcess }
    if (-not $owners) {
        # Get-NetTCPConnection has been seen returning nothing for a port that is
        # genuinely accepting connections, which would make this script quietly
        # stop nothing. netstat reads the same table without the CIM dependency.
        $owners += netstat -ano | Select-String ":$Port\s+\S+\s+LISTENING\s+(\d+)" | ForEach-Object { [int]$_.Matches[0].Groups[1].Value }
    }
    $owners | Sort-Object -Unique
}

function Stop-PortProcess([int]$Port, [string]$Name) {
    $owners = @(Get-PortOwnerPids -Port $Port)
    if (-not $owners) {
        Write-Host "$Name not running on port $Port"
        return
    }
    foreach ($procId in $owners) {
        try {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            Write-Host "Stopped $Name (PID $procId, port $Port)"
        } catch { }
    }
}

Stop-PortProcess 8000 'Backend'
Stop-PortProcess 5173 'Frontend'

if ($StopDb) {
    $PgCtl = Join-Path $Root '.pginstall\pgsql\bin\pg_ctl.exe'
    $PgData = Join-Path $Root '.pginstall\pgdata'
    if (Test-Path $PgCtl) {
        Write-Host "Stopping PostgreSQL..."
        & $PgCtl -D $PgData stop -m fast | Out-Null
        Write-Host "PostgreSQL stopped"
    }
}

Write-Host "Done."
