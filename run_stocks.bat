@echo off
setlocal
cd /d "%~dp0"
if not exist .venv (
    echo Virtual environment not found. Run setup.bat first.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
python stocks_main.py
