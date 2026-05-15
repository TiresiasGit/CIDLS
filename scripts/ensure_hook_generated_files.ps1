param(
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot)
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-ManagedFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $managedHeader = ':: CIDLS_HOOK_MANAGED'
    if (Test-Path $Path) {
        $existing = Get-Content -Path $Path -Raw -Encoding UTF8
        if ($existing -notmatch [regex]::Escape($managedHeader)) {
            Write-Host "[HOOK] Skip unmanaged file: $Path"
            return
        }
    }

    Set-Content -Path $Path -Value $Content -Encoding Ascii
    Write-Host "[HOOK] Ensured file: $Path"
}

$root = [System.IO.Path]::GetFullPath($RepoRoot)

$installerBat = @'
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
'@

$startBat = @'
:: CIDLS_HOOK_MANAGED
@echo off
setlocal
chcp 65001 > nul
set "ROOT=%~dp0"
pushd "%ROOT%"

call "%ROOT%installer.bat"
if errorlevel 1 (
  echo [ERROR] installer.bat failed.
  popd
  exit /b 1
)

if exist "index.html" (
  echo [INFO] Opening index.html...
  start "" "%ROOT%index.html"
  popd
  exit /b 0
)

if exist "project_kanban.html" (
  echo [INFO] Opening project_kanban.html...
  start "" "%ROOT%project_kanban.html"
  popd
  exit /b 0
)

if exist "scripts\generate_project_kanban.py" (
  echo [INFO] Generating project_kanban.html...
  uv run python scripts\generate_project_kanban.py
  if errorlevel 1 (
    echo [ERROR] project_kanban generation failed.
    popd
    exit /b 1
  )
  if exist "project_kanban.html" start "" "%ROOT%project_kanban.html"
  popd
  exit /b 0
)

echo [OK] Environment is ready. No launch target was found.
popd
exit /b 0
'@

$buildExeBat = @'
:: CIDLS_HOOK_MANAGED
@echo off
setlocal
chcp 65001 > nul
set "ROOT=%~dp0"
pushd "%ROOT%"

call "%ROOT%installer.bat"
if errorlevel 1 (
  echo [ERROR] installer.bat failed.
  popd
  exit /b 1
)

if "%~1"=="" (
  set "TARGET=scripts\generate_cidls_platform_overview.py"
) else (
  set "TARGET=%~1"
)

if "%~2"=="" (
  for %%I in ("%TARGET%") do set "APP_NAME=%%~nI"
) else (
  set "APP_NAME=%~2"
)

if not exist "%TARGET%" (
  echo [ERROR] Target script not found: %TARGET%
  popd
  exit /b 1
)

echo [INFO] Building exe for %TARGET%...
uv tool run pyinstaller --noconfirm --clean --onefile --name "%APP_NAME%" "%TARGET%"
if errorlevel 1 (
  echo [ERROR] exe build failed.
  popd
  exit /b 1
)

echo [OK] Build completed: dist\%APP_NAME%.exe
popd
exit /b 0
'@

Write-ManagedFile -Path (Join-Path $root 'installer.bat') -Content $installerBat
Write-ManagedFile -Path (Join-Path $root 'start.bat') -Content $startBat
Write-ManagedFile -Path (Join-Path $root 'build_exe.bat') -Content $buildExeBat