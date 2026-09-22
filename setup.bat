@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found in PATH. Install Python 3.14 and enable Add Python to PATH.
    pause
    exit /b 1
)
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Dependency installation failed. See the message above.
    pause
    exit /b 1
)
echo Setup complete. You can now double-click run.bat.
pause
