:: CIDLS_HOOK_MANAGED
@echo off
setlocal
chcp 65001 > nul
set "ROOT=%~dp0"
pushd "%ROOT%"

where uv > nul 2>&1
if errorlevel 1 (
  echo [ERROR] uv was not found in PATH.
  popd
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [INFO] Creating virtual environment...
  uv venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create .venv.
    popd
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 (
  echo [ERROR] Failed to activate .venv.
  popd
  exit /b 1
)

if exist "pyproject.toml" (
  echo [INFO] Installing dependencies from pyproject.toml...
  uv sync
  if errorlevel 1 (
    echo [ERROR] uv sync failed.
    popd
    exit /b 1
  )
) else (
  if exist "requirements.txt" (
    echo [INFO] Installing dependencies from requirements.txt...
    uv pip install -r requirements.txt
    if errorlevel 1 (
      echo [ERROR] requirements installation failed.
      popd
      exit /b 1
    )
  ) else (
    echo [INFO] No dependency manifest was found. Environment only was prepared.
  )
)

echo [OK] Environment is ready.
popd
exit /b 0
