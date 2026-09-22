@echo off
setlocal
REM Run script for Windows. Starts the app in the isolated venv.

if not exist .venv (
    echo Virtual environment not found.
    echo Run setup.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
python main.py
