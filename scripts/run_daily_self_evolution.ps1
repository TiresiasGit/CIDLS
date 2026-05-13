param(
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot)
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRootPath = (Resolve-Path $RepoRoot).Path
$codeCli = "C:\Program Files\Microsoft VS Code\bin\code.cmd"
$agentsPath = Join-Path $repoRootPath "AGENTS.md"
$logDir = Join-Path $repoRootPath "logs\daily_self_evolution"
$promptFilePath = Join-Path $PSScriptRoot "daily_self_evolution_prompt.txt"
$expectedArtifacts = @(
    "project_kanban.html",
    "cidls_platform_overview.html",
    "reports\cidls_pipeline_output\cidls_platform_overview.html",
    "CIDLSパイプラインマインドマップ.html",
    "graph_project_mindmap.html",
    "STORY.html",
    "要求定義書.html",
    "要求仕様書.html",
    "コンセプトスライド.html",
    "scripts\generate_graph_project_mindmap.py",
    "scripts\generate_cidls_platform_overview.py",
    "scripts\generate_commercial_delivery_pack.py",
    "scripts\generate_project_kanban.py",
    "scripts\generate_sw_docs_xlsx.py",
    "reports\commercial_delivery"
)

function Get-ArtifactStatusLines {
    param(
        [string]$RootPath,
        [string[]]$RelativePaths
    )

    $lines = @()
    foreach ($relativePath in $RelativePaths) {
        $fullPath = Join-Path $RootPath $relativePath
        if (Test-Path -LiteralPath $fullPath) {
            $item = Get-Item -LiteralPath $fullPath
            $timestamp = $item.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
            $lines += "- exists  | $relativePath | updated=$timestamp"
            continue
        }

        $lines += "- missing | $relativePath"
    }

    return $lines
}

function Get-LatestLogLines {
    param(
        [string]$DirectoryPath,
        [int]$Count = 3
    )

    if (-not (Test-Path -LiteralPath $DirectoryPath)) {
        return @("- no previous logs")
    }

    $files = @(Get-ChildItem -LiteralPath $DirectoryPath -File -Filter "*.log" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First $Count)

    if ($null -eq $files -or $files.Count -eq 0) {
        return @("- no previous logs")
    }

    return $files | ForEach-Object {
        "- " + $_.Name + " | updated=" + $_.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
    }
}

function New-ExecutionContextReport {
    param(
        [string]$RootPath,
        [string]$ImageFilePath,
        [string]$PromptTextValue,
        [string]$OutputPath,
        [string[]]$ArtifactStatusLines,
        [string[]]$RecentLogLines
    )

    $reportLines = @(
        "# Daily Self Evolution Context",
        "",
        "- generated_at: " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss"),
        "- repo_root: " + $RootPath,
        "- concept_image: " + $ImageFilePath,
        "- base_prompt: " + $PromptTextValue,
        "",
        "## Expected Artifacts",
        $ArtifactStatusLines,
        "",
        "## Recent Logs",
        $RecentLogLines,
        "",
        "## Execution Contract",
        "- Treat the concept image as the source of truth for the target pipeline state.",
        "- Compare current workspace artifacts against the target pipeline and identify the highest-value missing or stale deliverable.",
        "- Make the smallest verified change that increases alignment with the concept image.",
        "- Record follow-up work in generated outputs instead of silently skipping missing deliverables."
    )

    Set-Content -LiteralPath $OutputPath -Encoding UTF8 -Value $reportLines
}

$imageCandidate = Get-ChildItem -LiteralPath $repoRootPath -File -Filter "*.png" |
    Where-Object { $_.Name -like "CIDLS*.png" } |
    Sort-Object Name |
    Select-Object -First 1

if ($null -eq $imageCandidate) {
    throw "Pipeline concept image was not found under repo root: $repoRootPath"
}

$imagePath = $imageCandidate.FullName

if (-not (Test-Path $codeCli)) {
    throw "VS Code CLI was not found: $codeCli"
}

if (-not (Test-Path $agentsPath)) {
    throw "AGENTS.md was not found: $agentsPath"
}

if (-not (Test-Path $promptFilePath)) {
    throw "Prompt file was not found: $promptFilePath"
}

$promptText = (Get-Content -LiteralPath $promptFilePath -Encoding UTF8 -Raw).Trim()
if ([string]::IsNullOrWhiteSpace($promptText)) {
    throw "Prompt file is empty: $promptFilePath"
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$logPath = Join-Path $logDir ("daily_self_evolution_" + $timestamp + ".log")
$contextReportPath = Join-Path $logDir "daily_self_evolution_context_latest.md"
$artifactStatusLines = Get-ArtifactStatusLines -RootPath $repoRootPath -RelativePaths $expectedArtifacts
$recentLogLines = Get-LatestLogLines -DirectoryPath $logDir
New-ExecutionContextReport -RootPath $repoRootPath -ImageFilePath $imagePath -PromptTextValue $promptText -OutputPath $contextReportPath -ArtifactStatusLines $artifactStatusLines -RecentLogLines $recentLogLines

$chatPrompt = @"
$promptText

実行契約:
- 画像を SoT として現況との差分を特定すること。
- 最優先で不足または陳腐化した成果物を 1 件以上改善すること。
- 変更後は検証結果と次の複利改善候補を明示すること。
"@.Trim()

Start-Transcript -Path $logPath -Force | Out-Null
try {
    Write-Host "[START] daily self evolution"
    Write-Host "  repo   : $repoRootPath"
    Write-Host "  image  : $imagePath"
    Write-Host "  prompt : $promptFilePath"
    Write-Host "  ctx    : $contextReportPath"
    Write-Host "  prompt : base prompt + execution contract"
    Write-Host "  model  : available Copilot model + high reasoning"
    Write-Host "  loop   : collect -> compare -> analyze -> execute -> learn"

    # [STEP-1] generate_*.py による成果物自動更新
    $pythonCmd = if ($env:CIDLS_PYTHON) { $env:CIDLS_PYTHON } else { Join-Path $repoRootPath ".venv\Scripts\python.exe" }
    if (Test-Path $pythonCmd) {
        Write-Host "[STEP-1] Running generate_cidls_platform_overview.py --bump-patch"
        & $pythonCmd (Join-Path $PSScriptRoot "generate_cidls_platform_overview.py") --bump-patch
        Write-Host "[STEP-1] Running generate_commercial_delivery_pack.py"
        & $pythonCmd (Join-Path $PSScriptRoot "generate_commercial_delivery_pack.py")
    } else {
        Write-Host "[WARN] python venv not found at $pythonCmd - skipping generate_*.py steps"
    }

    # [STEP-2] VS Code Copilot agent chat
    & $codeCli -r $repoRootPath
    & $codeCli chat --mode agent --reuse-window --add-file $agentsPath --add-file $imagePath --add-file $contextReportPath $chatPrompt

    Write-Host "[OK] chat command dispatched"
}
finally {
    Stop-Transcript | Out-Null
}
