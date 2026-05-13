#Requires -Version 5.1
# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    GeminiCLI Programmer Controller
    GitHub Copilot (orchestrator) -> GeminiCLI (programmer)
.PARAMETER Task
    Task description (English or Japanese)
.PARAMETER WorkDir
    Working directory (default: repository root inferred from this script)
.PARAMETER YoloMode
    Auto-approve all tools (--approval-mode yolo)
.PARAMETER Model
    Model name (default: gemini-2.5-pro)
.PARAMETER CheckOnly
    Check availability only
.OUTPUTS
    ExitCode: 0=success 1=error 2=unavailable(fallback needed)
#>
param(
    [string]$Task = "",
    [string]$WorkDir = "",
    [switch]$YoloMode,
    [string]$Model = "gemini-2.5-pro",
    [switch]$CheckOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $WorkDir) {
    $WorkDir = Split-Path -Parent $PSScriptRoot
}

$LOG_DIR  = Join-Path $WorkDir "logs\gemini_programmer"
$TS_FILE  = Get-Date -Format "yyyyMMdd_HHmmss"
$LOG_FILE = Join-Path $LOG_DIR "gemini_run_${TS_FILE}.log"

function Write-Log {
    param([string]$Level, [string]$Msg)
    $ts   = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[${ts}][${Level}] $Msg"
    Write-Host $line
    if (-not (Test-Path $LOG_DIR)) { New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null }
    Add-Content -Path $LOG_FILE -Value $line -Encoding UTF8
}

# -------------------------------------------------------
# Check GeminiCLI availability
# -------------------------------------------------------
function Test-GeminiAvailable {
    $cmd = Get-Command gemini -ErrorAction SilentlyContinue
    if (-not $cmd) {
        Write-Log "WARN" "gemini not found in PATH. Run: npm install -g @google/gemini-cli"
        return $false
    }

    $ver = & gemini --version 2>&1
    Write-Log "INFO" "gemini version: $ver"

    $hasApiKey   = ($null -ne $env:GEMINI_API_KEY -and $env:GEMINI_API_KEY -ne "")
    $hasOAuth    = Test-Path "$env:USERPROFILE\.gemini\oauth_creds.json"
    $hasCredFile = Test-Path "$env:APPDATA\gemini-cli\credentials.json"

    if (-not $hasApiKey -and -not $hasOAuth -and -not $hasCredFile) {
        Write-Log "WARN" "GeminiCLI: No auth found. Set GEMINI_API_KEY or run: gemini (browser OAuth)"
        Write-Log "INFO" "Run setup: .\scripts\setup_gemini_auth.ps1"
        return $false
    }

    Write-Log "INFO" "GeminiCLI available. apiKey=${hasApiKey} oauth=${hasOAuth}"
    return $true
}

# -------------------------------------------------------
# Invoke GeminiCLI as programmer
# -------------------------------------------------------
function Invoke-GeminiProgrammer {
    param([string]$TaskDesc)

    $ctxFile = Join-Path $WorkDir ".gemini\GEMINI.md"
    $ctx = ""
    if (Test-Path $ctxFile) {
        $ctx = Get-Content $ctxFile -Raw -Encoding UTF8
    }

    $promptBody = "[CIDLS CONTEXT]`n${ctx}`n`n[TASK]`n${TaskDesc}`n`n[RULES]`n- Report diff after changes`n- No fallback/dummy data`n- No pip, no emoji, UTF-8 no BOM"

    $ts2      = Get-Date -Format "yyyyMMdd_HHmmss"
    $tmpFile  = Join-Path $env:TEMP "gemini_task_${ts2}.txt"
    [System.IO.File]::WriteAllText($tmpFile, $promptBody, [System.Text.Encoding]::UTF8)

    $approvalMode = if ($YoloMode) { "yolo" } else { "auto_edit" }
    Write-Log "INFO" "Invoking GeminiCLI: model=${Model} approval=${approvalMode}"
    Write-Log "INFO" "Task(80ch): $($TaskDesc.Substring(0, [Math]::Min(80, $TaskDesc.Length)))"

    Push-Location $WorkDir
    try {
        $promptText = Get-Content $tmpFile -Raw -Encoding UTF8
        & gemini -m $Model --approval-mode $approvalMode -p $promptText
        $ec = $LASTEXITCODE
    } finally {
        Pop-Location
        Remove-Item $tmpFile -ErrorAction SilentlyContinue
    }

    if ($ec -eq 0) {
        Write-Log "INFO" "GeminiCLI completed (exit=0)"
        return 0
    } else {
        Write-Log "ERROR" "GeminiCLI failed (exit=${ec})"
        return 1
    }
}

# -------------------------------------------------------
# Record fallback
# -------------------------------------------------------
function Write-FallbackRecord {
    param([string]$Reason, [string]$TaskDesc)
    $fbLog = Join-Path $WorkDir "logs\gemini_programmer\fallback_record.md"
    if (-not (Test-Path (Split-Path $fbLog))) {
        New-Item -ItemType Directory -Path (Split-Path $fbLog) -Force | Out-Null
    }
    $ts3    = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $short  = $TaskDesc.Substring(0, [Math]::Min(200, $TaskDesc.Length))
    $entry  = "`n## ${ts3} - GeminiCLI Fallback`n`n**Reason**: ${Reason}`n**Task**: ${short}`n**Alt**: GitHub Copilot direct execution`n**Fix**: Set GEMINI_API_KEY or run: gemini (OAuth)`n`n---`n"
    Add-Content -Path $fbLog -Value $entry -Encoding UTF8
    Write-Log "WARN" "Fallback recorded: $fbLog"
}

# -------------------------------------------------------
# Main
# -------------------------------------------------------
Write-Log "INFO" "=== GeminiCLI Programmer Controller v1.0 ==="

if ($CheckOnly) {
    if (Test-GeminiAvailable) {
        Write-Host "GEMINI_AVAILABLE=true"
        exit 0
    } else {
        Write-Host "GEMINI_AVAILABLE=false"
        exit 2
    }
}

if (-not $Task) {
    Write-Log "ERROR" "-Task parameter required"
    exit 1
}

if (Test-GeminiAvailable) {
    Write-Log "INFO" "GeminiCLI programmer mode: running..."
    exit (Invoke-GeminiProgrammer -TaskDesc $Task)
} else {
    Write-Log "WARN" "GeminiCLI unavailable: recording fallback"
    Write-FallbackRecord -Reason "No auth or command not found" -TaskDesc $Task
    Write-Host ""
    Write-Host "=== FALLBACK: GitHub Copilot will execute directly ==="
    Write-Host "Task:"
    Write-Host "----------------------------------------"
    Write-Host $Task
    Write-Host "----------------------------------------"
    exit 2
}
