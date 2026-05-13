@echo off
setlocal
cd /d %~dp0..
start "" "%CD%\fixtures\web\ocr_test_target.html"
