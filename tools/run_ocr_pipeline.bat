@echo off
setlocal
cd /d %~dp0..
if not exist .venv (
  uv venv
)
uv sync --extra dev
uv run cidls-ocr-pipeline %*
