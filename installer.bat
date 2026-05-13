@echo off
setlocal

set "CIDLS_ROOT=%~dp0"
if "%CIDLS_ROOT:~-1%"=="\" set "CIDLS_ROOT=%CIDLS_ROOT:~0,-1%"
set "CIDLS_SCRIPT=%CIDLS_ROOT%\scripts\sync_agents_cidls_policy.py"
set "WORKSPACE_DIR=%CD%"

if not exist "%CIDLS_SCRIPT%" (
  echo [ERROR] CIDLS sync script not found: %CIDLS_SCRIPT%
  exit /b 2
)

if not exist "%WORKSPACE_DIR%\logs" mkdir "%WORKSPACE_DIR%\logs"

set "PYTHON_EXE=%WORKSPACE_DIR%\.venv\Scripts\python.exe"
if exist "%PYTHON_EXE%" goto verify_runtime

set "PYTHON_EXE=python"
where python >nul 2>nul
if %errorlevel%==0 goto verify_runtime

set "PYTHON_EXE=py -3"
where py >nul 2>nul
if %errorlevel%==0 goto verify_runtime

echo [ERROR] Python runtime not found in workspace .venv or PATH
exit /b 3

:verify_runtime
%PYTHON_EXE% -c "from pathlib import Path; path = Path(r'%CIDLS_SCRIPT%'); print('[OK] CIDLS runtime ready: ' + str(path.exists()))"
exit /b %errorlevel%
