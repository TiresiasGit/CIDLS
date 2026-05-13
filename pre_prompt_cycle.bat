@echo off
setlocal

set "CIDLS_ROOT=%~dp0"
if "%CIDLS_ROOT:~-1%"=="\" set "CIDLS_ROOT=%CIDLS_ROOT:~0,-1%"
set "CIDLS_SCRIPT=%CIDLS_ROOT%\scripts\sync_agents_cidls_policy.py"
set "RUNTIME_STATE_SCRIPT=%CIDLS_ROOT%\scripts\sync_runtime_state.py"
set "WORKSPACE_DIR=%CIDLS_WORKSPACE_DIR%"
if not defined WORKSPACE_DIR set "WORKSPACE_DIR=%CD%"
set "WORKSPACE_AGENTS=%WORKSPACE_DIR%\AGENTS.md"
set "CIDLS_TASKS_FILE=%CIDLS_ROOT%\project_kanban.html"
set "SYNC_REPORT_PATH=%WORKSPACE_DIR%\logs\cidls_agents_sync_report.json"

if not exist "%CIDLS_SCRIPT%" (
  echo [ERROR] CIDLS sync script not found: %CIDLS_SCRIPT%
  exit /b 2
)

if not exist "%RUNTIME_STATE_SCRIPT%" (
  echo [ERROR] Runtime state sync script not found: %RUNTIME_STATE_SCRIPT%
  exit /b 2
)

if not exist "%WORKSPACE_DIR%\logs" mkdir "%WORKSPACE_DIR%\logs"

set "PYTHON_EXE=%WORKSPACE_DIR%\.venv\Scripts\python.exe"
if exist "%PYTHON_EXE%" goto run_sync

set "PYTHON_EXE=python"
where python >nul 2>nul
if %errorlevel%==0 goto run_sync

set "PYTHON_EXE=py -3"
where py >nul 2>nul
if %errorlevel%==0 goto run_sync

echo [ERROR] Python runtime not found. Run cmd /c "%CIDLS_ROOT%\installer.bat"
exit /b 3

:run_sync
set "AGENTS_MD_PATH=%WORKSPACE_AGENTS%"
set "CIDLS_TASKS_FILE=%CIDLS_TASKS_FILE%"
set "SYNC_REPORT_PATH=%SYNC_REPORT_PATH%"

%PYTHON_EXE% "%CIDLS_SCRIPT%"
if errorlevel 1 exit /b %errorlevel%

%PYTHON_EXE% "%RUNTIME_STATE_SCRIPT%"
exit /b %errorlevel%
