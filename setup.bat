@echo off
REM ==========================================================
REM  One-time setup: virtual env, dependencies, .env, policy index
REM  Usage: double-click setup.bat (or run it from this folder)
REM ==========================================================
setlocal
cd /d "%~dp0"
set "ROOT=%CD%"
set "PY=%ROOT%\.venv\Scripts\python.exe"

if exist "%PY%" goto venv_ready
echo [1/4] Creating virtual environment in .venv ...
py -3 -m venv .venv 2>nul
if not exist "%PY%" python -m venv .venv
if not exist "%PY%" (
    echo ERROR: Could not create a virtual environment. Install Python 3.10+ and try again.
    pause
    exit /b 1
)
:venv_ready

echo [2/4] Installing dependencies - this can take a few minutes ...
"%PY%" -m pip install --upgrade pip
"%PY%" -m pip install -r requirements.txt -r employee_retreival_system\requirements.txt -r leave_management_system\requirements.txt -r policy_rag_service\requirements.txt streamlit requests
if errorlevel 1 (
    echo ERROR: Dependency installation failed. See the messages above.
    pause
    exit /b 1
)

echo [3/4] Checking LLM configuration ...
if not exist "policy_rag_service\.env" (
    copy /Y "policy_rag_service\.env.example" "policy_rag_service\.env" >nul
    echo   Created policy_rag_service\.env from .env.example
    echo   ACTION NEEDED: open policy_rag_service\.env and set LLM_API_KEY to your group key.
)
if not exist "policy_rag_service\certs\vm06-ca.crt" (
    echo   ACTION NEEDED: copy the CA certificate to policy_rag_service\certs\vm06-ca.crt
)

echo [4/4] Indexing policy PDFs ...
pushd policy_rag_service
"%PY%" main.py ingest
popd

echo.
echo Setup complete. Run start_all.bat to start the HR assistant.
pause
