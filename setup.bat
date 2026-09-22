@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found in PATH.
    echo Install Python 3.14 64-bit and ensure 'Add Python to PATH' is selected.
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
if errorlevel 1 (
    echo Dependency installation failed.
    pause
    exit /b 1
)

echo Setup complete.
echo Next run: run_stocks.bat
pause
