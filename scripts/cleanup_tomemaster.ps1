<#
  cleanup_tomemaster.ps1 — pre-start CLEANUP for TomeMaster.

  A restart must mean: kill everything we started, THEN start fresh. The previous
  launcher only killed processes whose command line contained "uvicorn"/"run.py",
  which MISSED the `uvicorn --reload` spawn-worker children (their command line is
  `multiprocessing.spawn`, no "uvicorn" string) — so backend orphans accumulated and
  fought over ports. This script kills the whole process TREE for both servers, then
  frees the ports, so no stale instance survives a restart.

  Shared by Start_TomeMaster.bat and desktop_app.py — one cleanup path for both.
  Safe to run when nothing is running (no-op). Only targets THIS project's servers
  plus whatever is holding the given ports.
#>
param(
    [string]$ProjectRoot = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)),
    [int[]]$Ports = @(8090, 3000),
    [int]$ExcludePid = 0   # caller's own PID (desktop_app.py) — never kill self
)

$ErrorActionPreference = 'SilentlyContinue'
$all = Get-CimInstance Win32_Process

function Get-Descendants($parentId) {
    foreach ($child in ($all | Where-Object { $_.ParentProcessId -eq $parentId })) {
        $child
        Get-Descendants $child.ProcessId
    }
}

$rootNorm = ($ProjectRoot -replace '\\', '/').ToLower()
$targets = @{}

# 1. Root server processes for THIS project:
#    backend  = python running `uvicorn main:app` or `run.py`
#    frontend = node running `next` under this project tree
$roots = $all | Where-Object {
    $cl = $_.CommandLine
    if (-not $cl) { return $false }
    $cln = ($cl -replace '\\', '/').ToLower()
    (($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and ($cln -like '*uvicorn*main:app*' -or $cln -like '*run.py*' -or $cln -like '*desktop_app.py*')) -or
    ($_.Name -eq 'node.exe' -and $cln -like '*next*' -and $cln -like "*$rootNorm*")
}

# 2. Each root PLUS all of its descendants (catches --reload spawn workers, next children)
foreach ($r in $roots) {
    $targets[[int]$r.ProcessId] = $true
    foreach ($d in (Get-Descendants $r.ProcessId)) { $targets[[int]$d.ProcessId] = $true }
}

# 3. Anything still holding our fixed ports (covers orphans whose parent already died)
foreach ($port in $Ports) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
        $owner = [int]$_.OwningProcess
        if ($owner -ne 0) {
            $targets[$owner] = $true
            foreach ($d in (Get-Descendants $owner)) { $targets[[int]$d.ProcessId] = $true }
        }
    }
}

# 4. Kill them (never the caller itself)
foreach ($procId in $targets.Keys) {
    if ($ExcludePid -ne 0 -and $procId -eq $ExcludePid) { continue }
    try { Stop-Process -Id $procId -Force -ErrorAction Stop; Write-Host "  [cleanup] killed PID $procId" } catch {}
}

# 5. Drop the stale port broadcast file
$portFile = Join-Path $ProjectRoot '.sovereign_port'
if (Test-Path $portFile) { Remove-Item $portFile -Force -ErrorAction SilentlyContinue }

Write-Host "[cleanup] TomeMaster pre-start cleanup complete (ports: $($Ports -join ', '))."
