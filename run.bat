@echo off
setlocal

cd /d "%~dp0"

set "VENV_DIR=.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    echo Creating virtual environment...

    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -m venv "%VENV_DIR%"
    ) else (
        python -m venv "%VENV_DIR%"
    )

    if errorlevel 1 exit /b %ERRORLEVEL%

    echo Installing dependencies...
    "%VENV_PYTHON%" -m pip install -r requirements.txt
    if errorlevel 1 exit /b %ERRORLEVEL%
)

echo Starting Syncro Huntress Comparison Tool...
"%VENV_PYTHON%" gui.py %*
exit /b %ERRORLEVEL%
