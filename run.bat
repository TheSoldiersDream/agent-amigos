@echo off
title Agent Amigos Launcher
echo ---------------------------------------------------
echo    AGENT AMIGOS (2025) - QUICK LAUNCHER
echo ---------------------------------------------------
echo.

:: Check if backend venv exists
if not exist "backend\.venv\Scripts\activate" (
    echo [ERROR] Backend not set up. Run install_startup.bat first.
    pause
    exit /b
)

:: Check if frontend node_modules exists
if not exist "frontend\node_modules" (
    echo [ERROR] Frontend not set up. Run install_startup.bat first.
    pause
    exit /b
)

echo Starting Agent Amigos...
echo.

:: [OPTIONAL] Uncomment below to auto-start Ollama (local LLM for Ollie agent)
:: echo Starting Ollama LLM server...
:: tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
:: if %errorlevel% neq 0 (
::     start "Ollama Server" cmd /c "ollama serve"
::     timeout /t 3 /nobreak >nul
:: )

:: Launch backend in a new window
start "Agent Amigos Backend" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate && python agent_init.py"

:: Wait a moment for the backend to start
echo Waiting for backend to initialize...
timeout /t 5 /nobreak >nul

:: Launch frontend in a new window
start "Agent Amigos Frontend" cmd /k "cd /d %~dp0frontend && npm run dev -- --host 127.0.0.1 --port 5173"

echo.
echo ---------------------------------------------------
echo Agent Amigos is running!
echo.
echo Backend: http://127.0.0.1:8080  (check console for actual port)
echo Frontend: http://127.0.0.1:5173
echo.
echo Close this window or press any key to exit.
echo To stop the servers, close their terminal windows.
echo ---------------------------------------------------
pause
