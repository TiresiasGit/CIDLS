# setup_devrag.ps1 - 汎用 devrag セットアップスクリプト
# 任意のリポジトリに置いて実行するだけで devrag + VSCode Copilot 統合が完成する。
#
# 実行例:
#   .\setup_devrag.ps1
#   .\setup_devrag.ps1 -RepoRoot "D:\MyProject"
#   .\setup_devrag.ps1 -ProxyUrl "http://proxy.example.com:8080"
#
# パラメータ:
#   -RepoRoot  : 対象リポジトリのルートパス (省略時: このスクリプトのディレクトリ)
#   -ProxyUrl  : プロキシURL (省略時: 直接接続)
#
# ダウンロード先: https://github.com/tomohiro-owada/devrag/releases/latest

param(
    [string]$RepoRoot = $PSScriptRoot,
    [string]$ProxyUrl = "",
    [string]$DeployHooksTo = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- パス定義 ---
$INSTALL_DIR  = "$env:LOCALAPPDATA\devrag"
$BINARY       = "$INSTALL_DIR\devrag.exe"
$CONFIG       = Join-Path $RepoRoot "devrag-config.json"
$MCP_JSON     = Join-Path $RepoRoot ".mcp.json"
$DOWNLOAD_URL = "https://github.com/tomohiro-owada/devrag/releases/download/v1.4.4/devrag-windows-x64.exe.zip"
$ZIP_TEMP     = "$env:TEMP\devrag-windows-x64.exe.zip"

Write-Host "================================================================"
Write-Host " devrag 汎用セットアップ"
Write-Host "  RepoRoot : $RepoRoot"
Write-Host "  Binary   : $BINARY"
Write-Host "  Config   : $CONFIG"
Write-Host "================================================================"
Write-Host ""

# ================================================================
Write-Host "[STEP 1] devrag バイナリのセットアップ"

if (Test-Path $BINARY) {
    $ver = & $BINARY --version 2>&1
    Write-Host "  [OK] 既にインストール済み: $ver"
} else {
    New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null

    if (-not (Test-Path $ZIP_TEMP)) {
        Write-Host "  ダウンロード中..."
        try {
            $iwrParams = @{
                Uri            = $DOWNLOAD_URL
                OutFile        = $ZIP_TEMP
                UseBasicParsing = $true
                TimeoutSec     = 120
            }
            if ($ProxyUrl -ne "") {
                $proxy = New-Object System.Net.WebProxy($ProxyUrl, $true)
                $proxy.Credentials = [System.Net.CredentialCache]::DefaultNetworkCredentials
                $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
                $session.Proxy = $proxy
                $iwrParams["WebSession"] = $session
                Write-Host "    プロキシ: $ProxyUrl"
            }
            Invoke-WebRequest @iwrParams
            Write-Host "  [OK] ダウンロード完了"
        } catch {
            Write-Host ""
            Write-Host "  [WARN] 自動ダウンロード失敗: $_"
            Write-Host ""
            Write-Host "  手動でダウンロードしてください:"
            Write-Host "    1. ブラウザで以下 URL を開く:"
            Write-Host "       $DOWNLOAD_URL"
            Write-Host "    2. ダウンロードしたZIPを以下に保存:"
            Write-Host "       $ZIP_TEMP"
            Write-Host "    3. このスクリプトを再実行"
            Write-Host ""
            Write-Host "  プロキシ環境の場合: .\setup_devrag.ps1 -ProxyUrl 'http://proxy.example.com:8080'"
            exit 1
        }
    } else {
        Write-Host "  [OK] ZIPファイル検出: $ZIP_TEMP"
    }

    Write-Host "  展開中..."
    Expand-Archive -Path $ZIP_TEMP -DestinationPath $INSTALL_DIR -Force
    Remove-Item $ZIP_TEMP -ErrorAction SilentlyContinue

    if (-not (Test-Path $BINARY)) {
        $found = Get-ChildItem $INSTALL_DIR -Filter "devrag.exe" -Recurse | Select-Object -First 1
        if ($found) {
            Move-Item $found.FullName $BINARY -Force
        } else {
            Write-Host "[ERROR] devrag.exe が見つかりません。"
            Get-ChildItem $INSTALL_DIR -Recurse | Select-Object FullName
            exit 1
        }
    }

    $ver = & $BINARY --version 2>&1
    Write-Host "  [OK] インストール完了: $ver"
}

# ================================================================
Write-Host ""
Write-Host "[STEP 2] devrag-config.json の確認・自動生成"

if (Test-Path $CONFIG) {
    Write-Host "  [OK] 既存の設定を使用: $CONFIG"
} else {
    Write-Host "  設定ファイルが見つかりません。リポジトリ構造を検出して自動生成します..."

    # ドキュメントパターンを自動検出
    $patterns = @()
    if (Test-Path (Join-Path $RepoRoot "documents")) { $patterns += "./documents" }
    if (Test-Path (Join-Path $RepoRoot ".github"))   { $patterns += "./.github/**/*.md" }
    foreach ($name in @("AGENTS.md", "CLAUDE.md", "README.md")) {
        if (Test-Path (Join-Path $RepoRoot $name)) { $patterns += "./$name" }
    }
    if ($patterns.Count -eq 0) { $patterns += "./*.md" }

    $configObj = [ordered]@{
        document_patterns = $patterns
        db_path           = "./.devrag/vectors.db"
        chunk_size        = 500
        search_top_k      = 5
        compute           = [ordered]@{ device = "auto"; fallback_to_cpu = $true }
        model             = [ordered]@{ name = "multilingual-e5-small"; dimensions = 384 }
    }
    $configObj | ConvertTo-Json -Depth 5 | Set-Content -Path $CONFIG -Encoding UTF8
    Write-Host "  [OK] 生成完了: $CONFIG"
    Write-Host "       対象パターン: $($patterns -join ', ')"
}

# ================================================================
Write-Host ""
Write-Host "[STEP 3] 初回インデックス構築"
Write-Host "  初回はembeddingモデル(約450MB)を $INSTALL_DIR\models に自動ダウンロード"
Write-Host ""

Set-Location $RepoRoot
& $BINARY list --config $CONFIG
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] list コマンドがエラー終了。手動で確認してください。"
} else {
    Write-Host "[OK] インデックス確認完了"
}

# ================================================================
Write-Host ""
Write-Host "[STEP 4] 動作確認 (RAG検索テスト)"
$q = "フォールバック禁止ルール"
Write-Host "  検索クエリ: '$q'"
$prevEAP = $ErrorActionPreference; $ErrorActionPreference = "SilentlyContinue"
& $BINARY search $q --config $CONFIG --output text 2>&1
$ErrorActionPreference = $prevEAP
Write-Host ""

# ================================================================
Write-Host "[STEP 5] .mcp.json を更新 (devrag-cidls + devrag-local 2サーバー構成)"
# CIDLS(グローバルルール) + ローカル(プロジェクト固有知識) の2サーバー構成
$cidlsRoot   = if ($env:COPILOT_ENH_ROOT -and (Test-Path $env:COPILOT_ENH_ROOT)) { $env:COPILOT_ENH_ROOT } else { $PSScriptRoot }
$cidlsConfig = Join-Path $cidlsRoot "devrag-config.json"
$mcpActual = [ordered]@{
    mcpServers = [ordered]@{
        "devrag-cidls" = [ordered]@{
            type    = "stdio"
            command = $BINARY
            args    = @("--config", $cidlsConfig)
        }
        "devrag-local" = [ordered]@{
            type    = "stdio"
            command = $BINARY
            args    = @("--config", $CONFIG)
        }
    }
}
$mcpActual | ConvertTo-Json -Depth 5 | Set-Content -Path $MCP_JSON -Encoding UTF8
Write-Host "  [OK] devrag-cidls: $cidlsConfig"
Write-Host "  [OK] devrag-local:  $CONFIG"

# ================================================================
Write-Host ""
Write-Host "[STEP 6] 環境変数 COPILOT_ENH_ROOT をユーザースコープに登録"
[System.Environment]::SetEnvironmentVariable('COPILOT_ENH_ROOT', $RepoRoot, 'User')
Write-Host "  [OK] COPILOT_ENH_ROOT=$RepoRoot"

# ================================================================
Write-Host ""
Write-Host "[STEP 7] VSCode User settings.json を現在のパスで更新"
$vsSettings = Join-Path $env:APPDATA "Code\User\settings.json"
$instructionsPath = Join-Path $RepoRoot ".github\copilot-instructions.md"

if (Test-Path $vsSettings) {
    if (Test-Path $instructionsPath) {
        $raw = Get-Content $vsSettings -Raw -Encoding UTF8
        $instructionsJson = $instructionsPath -replace '\\', '\\'
        $newEntry = '"file": "' + $instructionsJson + '"'
        $updated = $raw -replace '"file":\s*"[^"]*copilot-instructions\.md"', $newEntry
        if ($updated -ne $raw) {
            Set-Content -Path $vsSettings -Value $updated -Encoding UTF8
            Write-Host "  [OK] settings.json 更新: $instructionsPath"
        } else {
            # エントリが存在しない場合は追記しない (既存設定を壊さない)
            Write-Host "  [OK] settings.json は既に最新 (または手動追加が必要)"
        }
    } else {
        Write-Host "  [SKIP] .github\copilot-instructions.md が見つかりません: $instructionsPath"
        Write-Host "         ENHANCE.3 の手順に従いファイルを生成してから再実行してください"
    }
} else {
    Write-Host "  [WARN] settings.json 未存在: $vsSettings"
}

# ================================================================
Write-Host ""
Write-Host "[STEP 8] 他リポジトリへの CIDLS hook 展開"
if ($DeployHooksTo -ne "") {
    $srcBase = $PSScriptRoot
    $dstBase = $DeployHooksTo
    Write-Host "  CIDLS ルール -> $dstBase"

    # .github 以下の各サブフォルダをコピー
    $targets = @("hooks", "instructions", "agents", "prompts", "skills")
    foreach ($t in $targets) {
        $src = Join-Path $srcBase ".github\$t"
        $dst = Join-Path $dstBase ".github\$t"
        if (Test-Path $src) {
            New-Item -ItemType Directory -Path $dst -Force | Out-Null
            Copy-Item "$src\*" $dst -Recurse -Force
            Write-Host "  [OK] .github\$t\ -> $dst"
        }
    }

    # copilot-instructions.md をコピー
    $srcInstr = Join-Path $srcBase ".github\copilot-instructions.md"
    $dstGithub = Join-Path $dstBase ".github"
    if (Test-Path $srcInstr) {
        New-Item -ItemType Directory -Path $dstGithub -Force | Out-Null
        Copy-Item $srcInstr $dstGithub -Force
        Write-Host "  [OK] .github\copilot-instructions.md -> $dstGithub"
    }

    # 展開先の .mcp.json を2サーバー構成で生成
    $dstConfig = Join-Path $dstBase "devrag-config.json"
    $dstMcp    = Join-Path $dstBase ".mcp.json"
    $mcpDual = [ordered]@{
        mcpServers = [ordered]@{
            "devrag-cidls" = [ordered]@{
                type    = "stdio"
                command = $BINARY
                args    = @("--config", (Join-Path $srcBase "devrag-config.json"))
            }
            "devrag-local" = [ordered]@{
                type    = "stdio"
                command = $BINARY
                args    = @("--config", $dstConfig)
            }
        }
    }
    $mcpDual | ConvertTo-Json -Depth 5 | Set-Content -Path $dstMcp -Encoding UTF8
    Write-Host "  [OK] .mcp.json 2サーバー構成 (devrag-cidls: CIDLSルール + devrag-local: $dstBase)"

    # setup_devrag.ps1 自体もコピー (展開先でセットアップスクリプトを使えるよう自動展開)
    $srcPs1 = Join-Path $srcBase "setup_devrag.ps1"
    $dstPs1 = Join-Path $dstBase "setup_devrag.ps1"
    if (Test-Path $srcPs1) {
        Copy-Item $srcPs1 $dstPs1 -Force
        Write-Host "  [OK] setup_devrag.ps1 -> $dstBase"
    }

    Write-Host "  [OK] hook 展開完了: $dstBase"
    Write-Host "  次は以下を実行してください:"
    Write-Host "    .\setup_devrag.ps1 -RepoRoot '$dstBase'"
} else {
    Write-Host "  [SKIP] -DeployHooksTo 未指定"
    Write-Host "  他リポジトリへ展開する場合: .\setup_devrag.ps1 -DeployHooksTo 'D:\OtherProject'"
}

# ================================================================
Write-Host ""
Write-Host "================================================================"
Write-Host "[COMPLETE] devrag セットアップ完了"
Write-Host ""
Write-Host "  バイナリ  : $BINARY"
Write-Host "  設定      : $CONFIG"
Write-Host "  MCP設定   : $MCP_JSON"
Write-Host "  RepoRoot  : $RepoRoot"
Write-Host ""
Write-Host "  次の手順:"
Write-Host "    1. VSCode を完全再起動 (File > Exit)"
Write-Host "    2. Copilot チャットで以下が使用可能になります:"
Write-Host "       - search(query: '...') MCP ツール"
Write-Host "       - /devrag-search スラッシュコマンド"
Write-Host "       - devrag-rag スキル"
Write-Host ""
Write-Host "  別プロジェクトへ適用:"
Write-Host "    .\setup_devrag.ps1 -RepoRoot 'D:\OtherProject'"
Write-Host "================================================================"


Write-Host "[STEP 1] devrag バイナリのセットアップ"

if (Test-Path $BINARY) {
    $ver = & $BINARY --version 2>&1
    Write-Host "  [OK] 既にインストール済み: $ver"
} else {
    New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null

    if (-not (Test-Path $ZIP_TEMP)) {
        Write-Host "  ダウンロード中... (プロキシ: $PROXY_URL)"
        try {
            $proxy = New-Object System.Net.WebProxy($PROXY_URL, $true)
            $proxy.Credentials = [System.Net.CredentialCache]::DefaultNetworkCredentials
            $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
            $session.Proxy = $proxy
            Invoke-WebRequest -Uri $DOWNLOAD_URL -OutFile $ZIP_TEMP -WebSession $session -UseBasicParsing -TimeoutSec 120
            Write-Host "  [OK] ダウンロード完了"
        } catch {
            Write-Host ""
            Write-Host "  [WARN] 自動ダウンロード失敗: $_"
            Write-Host ""
            Write-Host "  手動でダウンロードしてください:"
            Write-Host "    1. ブラウザで以下 URL を開く:"
            Write-Host "       $DOWNLOAD_URL"
            Write-Host "    2. ダウンロードしたZIPを以下に保存:"
            Write-Host "       $ZIP_TEMP"
            Write-Host "    3. このスクリプトを再実行 (.\setup_devrag.ps1)"
            Write-Host ""
            Write-Host "  または ZIP を展開して devrag.exe を直接配置:"
            Write-Host "       $BINARY"
            exit 1
        }
    } else {
        Write-Host "  [OK] ZIPファイル検出: $ZIP_TEMP"
    }

    Write-Host "  展開中..."
    Expand-Archive -Path $ZIP_TEMP -DestinationPath $INSTALL_DIR -Force
    Remove-Item $ZIP_TEMP -ErrorAction SilentlyContinue

    if (-not (Test-Path $BINARY)) {
        $found = Get-ChildItem $INSTALL_DIR -Filter "devrag.exe" -Recurse | Select-Object -First 1
        if ($found) {
            Move-Item $found.FullName $BINARY -Force
        } else {
            Write-Host "[ERROR] devrag.exe が見つかりません。"
            Get-ChildItem $INSTALL_DIR -Recurse | Select-Object FullName
            exit 1
        }
    }

    $ver = & $BINARY --version 2>&1
    Write-Host "  [OK] インストール完了: $ver"
}

Write-Host ""
Write-Host "[STEP 2] 初回インデックス構築"
Write-Host "  対象: documents/ + .github/**/*.md + AGENTS.md"
Write-Host "  初回はembeddingモデル(約450MB)を %LOCALAPPDATA%\devrag\models に自動DL"
Write-Host ""

Set-Location $RepoRoot
& $BINARY list --config $CONFIG
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] list コマンドがエラー終了。手動で確認してください。"
} else {
    Write-Host "[OK] インデックス確認完了"
}

Write-Host ""
Write-Host "[STEP 3] 動作確認 (RAG検索テスト)"
Write-Host ""

$q = "フォールバック禁止ルール"
Write-Host "  検索クエリ: '$q'"
$prevEAP = $ErrorActionPreference; $ErrorActionPreference = "SilentlyContinue"
& $BINARY search $q --config $CONFIG --output text 2>&1
$ErrorActionPreference = $prevEAP
Write-Host ""

Write-Host "================================================================"
Write-Host "[COMPLETE] devrag セットアップ完了"
Write-Host ""
Write-Host "  バイナリ: $BINARY"
Write-Host "  設定:     $CONFIG"
Write-Host "  MCP設定:  $MCP_JSON"
Write-Host ""

# .mcp.json に正しい絶対パスを自動書き込み (devrag起動に必要)
Write-Host "[STEP 4] .mcp.json を現在のパスで更新"
$mcpContent = @"
{
  "mcpServers": {
    "devrag": {
      "type": "stdio",
      "command": "$($BINARY -replace '\\', '\\\\')",
      "args": ["--config", "$($CONFIG -replace '\\', '\\\\')"]  
    }
  }
}
"@
# バックスラッシュルJSONエスケープはヒアドキュメント内のエスケープ、実際に書き込む時は単純な JSON とする
$mcpActual = [ordered]@{
    mcpServers = [ordered]@{
        devrag = [ordered]@{
            type    = "stdio"
            command = $BINARY
            args    = @("--config", $CONFIG)
        }
    }
}
$mcpActual | ConvertTo-Json -Depth 5 | Set-Content -Path $MCP_JSON -Encoding UTF8
Write-Host "  [OK] $MCP_JSON を更新しました"

# 環境変数 COPILOT_ENH_ROOT をユーザースコープに登録 (hooks が参照)
[System.Environment]::SetEnvironmentVariable('COPILOT_ENH_ROOT', $SCRIPT_ROOT, 'User')
Write-Host "  [OK] 環境変数 COPILOT_ENH_ROOT=$SCRIPT_ROOT をユーザー環境に登録"

# VSCode User settings.json の codeGeneration.instructions パスを動的更新
Write-Host ""
Write-Host "[STEP 5] VSCode User settings.json を現在のパスで更新"
$vsSettings = Join-Path $env:APPDATA "Code\User\settings.json"
if (Test-Path $vsSettings) {
    $raw = Get-Content $vsSettings -Raw -Encoding UTF8
    # JSON内のバックスラッシュは1個の \ を \\ で表現する (二重エスケープ禁止)
    $instructionsPath = Join-Path $SCRIPT_ROOT ".github\copilot-instructions.md"
    $instructionsJson = $instructionsPath -replace '\\', '\\'   # 1\ -> \\  (JSON標準)
    $newEntry = '"file": "' + $instructionsJson + '"'
    $updated = $raw -replace '"file":\s*"[^"]*copilot-instructions\.md"', $newEntry
    if ($updated -ne $raw) {
        Set-Content -Path $vsSettings -Value $updated -Encoding UTF8
        Write-Host "  [OK] settings.json 更新: $instructionsPath"
    } else {
        Write-Host "  [OK] settings.json は既に最新"
    }
} else {
    Write-Host "  [WARN] settings.json 未存在: $vsSettings"
}

Write-Host ""
Write-Host "  次の手順:"
Write-Host "    1. VSCode を完全再起動 (File > Exit)"
Write-Host "    2. Copilot チャットで以下が使用可能になります:"
Write-Host "       - search(query: '...') MCP ツール"
Write-Host "       - /devrag-search スラッシュコマンド"
Write-Host "       - devrag-rag スキル"
Write-Host "================================================================"
