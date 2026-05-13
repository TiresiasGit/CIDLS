@echo off
setlocal EnableExtensions

set "CIDLS_REPO=%~dp0.."
for %%I in ("%CIDLS_REPO%") do set "CIDLS_REPO=%%~fI"

if "%CODEX_HOME%"=="" set "CODEX_HOME=%USERPROFILE%\.codex"
if "%CLAUDE_COWORK_COMMAND%"=="" set "CLAUDE_COWORK_COMMAND=claude"

cd /d "%CIDLS_REPO%" || exit /b 2

if exist "%CIDLS_REPO%\pre_prompt_cycle.bat" (
  call "%CIDLS_REPO%\pre_prompt_cycle.bat"
  if errorlevel 1 (
    if exist "%CIDLS_REPO%\installer.bat" (
      call "%CIDLS_REPO%\installer.bat" || exit /b 3
      call "%CIDLS_REPO%\pre_prompt_cycle.bat" || exit /b 4
    ) else (
      exit /b 5
    )
  )
)

set "CLAUDE_COWORK_PROMPT=AGENTS.md、project_kanban.html、reports\commercial_delivery\商用請負納品文書パック_2026-05-06.xlsx、STORY.html、テスト結果を読み、ClaudeCowork収束係として未処理タスク、水平展開漏れ、商用請負納品物の抜け漏れをレビューし、project_kanban.htmlへ反映すべき具体タスクだけを出力せよ。"

%CLAUDE_COWORK_COMMAND% "%CLAUDE_COWORK_PROMPT%"
exit /b %ERRORLEVEL%
