<#
.SYNOPSIS
    GeminiCLI 認証セットアップスクリプト

.DESCRIPTION
    方法A: GEMINI_API_KEY (Google AI Studio) を設定する
    方法B: OAuth ブラウザ認証を実施する
#>

Write-Host "=== GeminiCLI 認証セットアップ ==="
Write-Host ""
Write-Host "方法A: GEMINI_API_KEY 設定 (推奨: CI/CD環境でも使用可)"
Write-Host "  1. https://aistudio.google.com/app/apikey でAPIキーを取得"
Write-Host "  2. 以下を実行 (PowerShellプロファイルに永続化):"
Write-Host '     [System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY","YOUR_KEY","User")'
Write-Host ""
Write-Host "方法B: Googleアカウント OAuth認証 (ブラウザ不要の場合は方法Aを選択)"
Write-Host "  以下を実行するとブラウザが開きます:"
Write-Host "     gemini"
Write-Host ""

$choice = Read-Host "どちらを使用しますか? [A/B]"
if ($choice -eq "A" -or $choice -eq "a") {
    $key = Read-Host "GEMINI_API_KEY を入力してください"
    if ($key) {
        [System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", $key, "User")
        $env:GEMINI_API_KEY = $key
        Write-Host "GEMINI_API_KEY を設定しました (User スコープ - 再起動不要)"
        & gemini -p "こんにちは。1文で自己紹介してください。" -m "gemini-2.5-pro" 2>&1
    } else {
        Write-Host "キーが空です。スキップします。"
    }
} elseif ($choice -eq "B" -or $choice -eq "b") {
    Write-Host "ブラウザ認証を開始します。gemini を起動してください..."
    Start-Process "gemini"
} else {
    Write-Host "スキップしました。後で実行してください。"
}
