@echo off
rem CIDLS Daily Self-Evolution Task
rem Runs every day at 10:00 via Windows Task Scheduler
rem Task name: CIDLS_DailyEvolve
rem
rem CU_EVOLVE: CIDLSパイプラインコンセプトイメージ.pngをさらに
rem            CIDLS観点でpngの実現に向けWebから最新のハーネスエンジニアリングを
rem            取り込みさらに反証的複利自己進化させよ

setlocal

rem Working directory = CIDLS project root
cd /d "%~dp0.."

rem Activate uv virtual environment
if not exist ".venv" (
    echo [WARN] .venv not found - running uv sync first
    uv sync
)

rem Log start
echo [%date% %time%] [PROCESS_START] CIDLS daily evolution >> logs\cidls_daily_evolve.log

rem Run the evolution command
rem ANTHROPIC_API_KEY must be set in system environment variables
uv run cidls-compute-use evolve >> logs\cidls_daily_evolve.log 2>&1

if errorlevel 1 (
    echo [%date% %time%] [FAIL] evolution exited with error >> logs\cidls_daily_evolve.log
) else (
    echo [%date% %time%] [SUCC] evolution completed >> logs\cidls_daily_evolve.log
)

echo [%date% %time%] [PROCESS_END] CIDLS daily evolution >> logs\cidls_daily_evolve.log

endlocal
