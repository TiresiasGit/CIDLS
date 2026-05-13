param(
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$TaskName = "CIDLS_Daily_Self_Evolution_1100",
    [string]$StartTime = "11:00"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$runner = Join-Path (Resolve-Path $PSScriptRoot).Path "run_daily_self_evolution.cmd"
if (-not (Test-Path $runner)) {
    throw "ランナーが見つかりません: $runner"
}

& schtasks.exe /Create /TN $TaskName /SC DAILY /ST $StartTime /TR $runner /F /IT /RL LIMITED
if ($LASTEXITCODE -ne 0) {
    throw "schtasks.exe /Create が失敗しました: exit=$LASTEXITCODE"
}

& schtasks.exe /Query /TN $TaskName /V /FO LIST
if ($LASTEXITCODE -ne 0) {
    throw "schtasks.exe /Query が失敗しました: exit=$LASTEXITCODE"
}