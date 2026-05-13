param(
    [string]$TaskName = "CIDLS-ClaudeCowork-Cycle",
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$CodexHome = $(if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }),
    [string]$ClaudeCommand = $(if ($env:CLAUDE_COWORK_COMMAND) { $env:CLAUDE_COWORK_COMMAND } else { "claude" }),
    [ValidateSet("Hourly", "Daily")]
    [string]$Schedule = "Daily",
    [string]$At = "09:00"
)

$ErrorActionPreference = "Stop"

$resolvedRepo = (Resolve-Path -LiteralPath $RepoRoot).Path
$runner = Join-Path $resolvedRepo "scripts\run_claude_cowork_cycle.cmd"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "ClaudeCowork runner was not found: $runner"
}

$action = New-ScheduledTaskAction `
    -Execute $runner `
    -WorkingDirectory $resolvedRepo

if ($Schedule -eq "Hourly") {
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddMinutes(5) `
        -RepetitionInterval (New-TimeSpan -Hours 1)
} else {
    $trigger = New-ScheduledTaskTrigger -Daily -At $At
}

$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel LeastPrivilege

$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

$task = New-ScheduledTask `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "CIDLS ClaudeCowork収束係レビュー。AGENTS、project_kanban、商用請負Excel、STORY、テスト証跡を確認する。"

$env:CODEX_HOME = $CodexHome
$env:CLAUDE_COWORK_COMMAND = $ClaudeCommand

Register-ScheduledTask `
    -TaskName $TaskName `
    -InputObject $task `
    -Force | Out-Null

[pscustomobject]@{
    ok = $true
    task_name = $TaskName
    repo_root = $resolvedRepo
    codex_home = $CodexHome
    claude_command = $ClaudeCommand
    runner = $runner
    schedule = $Schedule
    at = $At
} | ConvertTo-Json -Depth 4
