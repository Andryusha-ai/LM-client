@echo off
title Build LM-client

cd /d D:\Project_LM-client

call .venv\Scripts\activate

echo.
echo ==========================
echo Cleaning...
echo ==========================

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__

echo.
echo ==========================
echo Building...
echo ==========================

pyinstaller ^
--noconfirm ^
--windowed ^
--name LM-client ^
Assistant.py

echo.
echo ==========================
echo Done!
echo ==========================

pause