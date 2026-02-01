@echo off
setlocal enabledelayedexpansion
REM Setup: create venv (if missing), install deps, then run the app with uvicorn.

cd /d "%~dp0"

set "VENV_DIR=.venv"
set "VENV_SCRIPTS=%VENV_DIR%\Scripts"
set "VENV_PYTHON=%VENV_SCRIPTS%\python.exe"
set "VENV_PIP=%VENV_SCRIPTS%\pip.exe"
set "VENV_UVICORN=%VENV_SCRIPTS%\uvicorn.exe"

REM Find Python for creating venv: try PYTHON env, python, python3, py -3
set "PYTHON_CMD="
if defined PYTHON (
  set "PYTHON_CMD=%PYTHON%"
  goto have_python
)
where python >nul 2>&1 && (set "PYTHON_CMD=python" & goto have_python)
where python3 >nul 2>&1 && (set "PYTHON_CMD=python3" & goto have_python)
where py >nul 2>&1 && (set "PYTHON_CMD=py -3" & goto have_python)
goto no_python

:have_python
if not exist "%VENV_DIR%" (
  echo ==^> Creating virtual environment in %VENV_DIR%
  %PYTHON_CMD% -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo Failed to create venv with %PYTHON_CMD%
    exit /b 1
  )
) else (
  echo ==^> Using existing virtual environment %VENV_DIR%
)

REM Install dependencies - try venv pip first, fall back to python -m pip
echo ==^> Installing dependencies
set "PIP_CMD="
if exist "%VENV_PIP%" (
  set "PIP_CMD=%VENV_PIP%"
) else (
  set "PIP_CMD=%VENV_PYTHON% -m pip"
)

%PIP_CMD% install -q -r requirements.txt
if errorlevel 1 (
  echo pip install failed, trying python -m pip...
  "%VENV_PYTHON%" -m pip install -q -r requirements.txt
  if errorlevel 1 (
    echo Failed to install dependencies
    exit /b 1
  )
)

REM Start uvicorn - use uvicorn.exe or python -m uvicorn
echo ==^> Starting uvicorn
if exist "%VENV_UVICORN%" (
  "%VENV_UVICORN%" app.main:app --reload --host 0.0.0.0 --port 8000
) else (
  "%VENV_PYTHON%" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
)

exit /b 0

:no_python
echo No Python found. Please install Python and ensure python, python3, or py is in PATH.
exit /b 1
