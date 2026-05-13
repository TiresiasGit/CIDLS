# setup_daily_task.ps1
# Registers the CIDLS daily self-evolution task in Windows Task Scheduler.
#
# Usage (run as Administrator or current user):
#   .\scripts\setup_daily_task.ps1
#
# The task runs at 10:00 every day and calls cidls_daily_evolve.bat
# which in turn calls: cidls-compute-use evolve
#
# CIDLSパイプラインコンセプトイメージ.pngをさらにCIDLS観点でpngの実現に向け
# Webから最新のハーネスエンジニアリングを取り込みさらに反証的複利自己進化させよ

$TaskName    = "CIDLS_DailyEvolve"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BatchFile   = Join-Path $ProjectRoot "scripts\cidls_daily_evolve.bat"
$LogDir      = Join-Path $ProjectRoot "logs"

# Ensure logs directory exists
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
    Write-Host "[INFO] Created logs directory: $LogDir"
}

# Remove existing task if present (idempotent registration)
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "[INFO] Removed existing task: $TaskName"
}

# Define the action
$Action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$BatchFile`"" `
    -WorkingDirectory $ProjectRoot

# Daily at 10:00
$Trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At "10:00"

# Run as current user, only when logged on
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable:$false `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew

# Register the task
Register-ScheduledTask `
    -TaskName    $TaskName `
    -Action      $Action `
    -Trigger     $Trigger `
    -Settings    $Settings `
    -Description "CIDLS反証的複利自己進化: pngの実現に向けCIDLS観点でWebから最新ハーネスエンジニアリングを取り込みさらに反証的複利自己進化させよ" `
    -RunLevel    Limited `
    -Force

Write-Host "[SUCC] Registered scheduled task: $TaskName"
Write-Host "       Schedule  : Daily at 10:00"
Write-Host "       Batch     : $BatchFile"
Write-Host "       Log       : $LogDir\cidls_daily_evolve.log"
Write-Host ""
Write-Host "IMPORTANT: Set ANTHROPIC_API_KEY in System Environment Variables"
Write-Host "           Control Panel > System > Environment Variables > New"
Write-Host "           Name  : ANTHROPIC_API_KEY"
Write-Host "           Value : <ANTHROPIC_API_KEY_VALUE>"
