@echo off
setlocal
REM Setup script for Windows. Creates an isolated venv and installs dependencies.
REM It does NOT modify the user's existing Python installation.

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found in PATH.
    echo Install Python 3.14 64-bit from https://www.python.org/downloads/
    echo Then rerun setup.bat.
    pause
    exit /b 1
)

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Setup complete.
echo To start the app: run.bat
pause
