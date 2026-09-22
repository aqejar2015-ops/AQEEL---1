@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python is not in PATH.
    echo Install Python 3.14 64-bit from https://www.python.org/downloads/
    echo Then re-run run_stocks.bat.
    pause
    exit /b 1
)

if not exist .venv (
    echo Virtual environment not found.
    echo Running setup.bat...
    call setup.bat
    if errorlevel 1 (
        exit /b 1
    )
)

call .venv\Scripts\activate.bat
python stocks_main.py
