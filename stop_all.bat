@echo off
REM Stop every HR assistant service started by start_all.bat
setlocal
for %%T in (HR-Employee-9090 HR-Leave-9091 HR-PolicyRAG-8001 HR-Orchestrator-8000 HR-Frontend-8501) do (
    taskkill /FI "WINDOWTITLE eq %%T*" /T /F >nul 2>&1
)
REM Anything still listening on the service ports
for %%P in (9090 9091 8001 8000 8501) do (
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr /R /C:":%%P .*LISTENING"') do taskkill /PID %%A /T /F >nul 2>&1
)
echo All HR assistant services stopped.
timeout /t 3
