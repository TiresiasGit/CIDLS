param(
  [int]$MinAgeMinutes = 720,
  [switch]$KillAll,
  [switch]$Quiet
)

$ErrorActionPreference = "Stop"
$targetName = "devrag-windows-x64"
$cutoff = (Get-Date).AddMinutes(-1 * $MinAgeMinutes)
$killed = @()
$skipped = @()

$processes = @(Get-Process -Name $targetName -ErrorAction SilentlyContinue)

foreach ($process in $processes) {
  $shouldKill = $false
  if ($KillAll) {
    $shouldKill = $true
  } elseif ($process.StartTime -lt $cutoff) {
    $shouldKill = $true
  }

  if ($shouldKill) {
    Stop-Process -Id $process.Id -Force
    $killed += [ordered]@{
      id = $process.Id
      start_time = $process.StartTime.ToString("o")
      working_set = $process.WorkingSet64
    }
  } else {
    $skipped += [ordered]@{
      id = $process.Id
      start_time = $process.StartTime.ToString("o")
      working_set = $process.WorkingSet64
    }
  }
}

Start-Sleep -Milliseconds 250
$remaining = @(Get-Process -Name $targetName -ErrorAction SilentlyContinue)

$report = [ordered]@{
  generated_at_utc = [DateTime]::UtcNow.ToString("o")
  process_name = $targetName
  min_age_minutes = $MinAgeMinutes
  kill_all = [bool]$KillAll
  killed_count = $killed.Count
  remaining_count = $remaining.Count
  killed = $killed
  skipped = $skipped
}

if (-not $Quiet) {
  $report | ConvertTo-Json -Depth 5
}
