@echo off
REM ==========================================================
REM  Start the whole HR assistant, each service in its own window
REM    Employee service   http://localhost:9090
REM    Leave service      http://localhost:9091
REM    Policy RAG         http://localhost:8001
REM    Orchestrator       http://localhost:8000   (API docs: /docs)
REM    Frontend           http://localhost:8501
REM  Stop everything with stop_all.bat
REM ==========================================================
setlocal
cd /d "%~dp0"
set "ROOT=%CD%"
set "PY=python"
if exist "%ROOT%\.venv\Scripts\python.exe" set "PY=%ROOT%\.venv\Scripts\python.exe"

if exist "%ROOT%\policy_rag_service\data\vectorstore" goto indexed
echo Policy index not found - indexing policy PDFs first ...
pushd "%ROOT%\policy_rag_service"
"%PY%" main.py ingest
popd
:indexed

echo Starting backend services ...
start "HR-Employee-9090" /D "%ROOT%\employee_retreival_system" cmd /k ""%PY%" app.py --port 9090"
start "HR-Leave-9091" /D "%ROOT%\leave_management_system" cmd /k ""%PY%" app.py --port 9091"
start "HR-PolicyRAG-8001" /D "%ROOT%\policy_rag_service" cmd /k ""%PY%" main.py serve"

echo Waiting for backends to start ...
timeout /t 8 /nobreak >nul

echo Starting orchestrator ...
start "HR-Orchestrator-8000" /D "%ROOT%" cmd /k ""%PY%" -m uvicorn app.main:app --port 8000"
timeout /t 4 /nobreak >nul

echo Starting frontend ...
start "HR-Frontend-8501" /D "%ROOT%\frontend" cmd /k ""%PY%" -m streamlit run home.py --server.port 8501"

echo.
echo All services launched.
echo   Frontend      http://localhost:8501
echo   Orchestrator  http://localhost:8000/docs
echo   Health check  http://localhost:8000/health
echo.
echo Run stop_all.bat to stop everything.
timeout /t 10
