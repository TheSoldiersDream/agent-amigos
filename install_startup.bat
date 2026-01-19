@echo off
title Agent Amigos Installer
echo ---------------------------------------------------
echo    AGENT AMIGOS (2025) - ARCHITECTURE SETUP
echo ---------------------------------------------------
echo.

:: 0. Prerequisite Check
echo [0/4] Checking Prerequisites...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please run 'setup_prerequisites.bat' first, then restart your terminal.
    pause
    exit /b
)

call npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH.
    echo Please run 'setup_prerequisites.bat' first, then restart your terminal.
    pause
    exit /b
)

echo Prerequisites found. Proceeding...
echo.

:: 1. Backend Setup
echo [1/4] Setting up Backend (Python)...
cd backend
if not exist ".venv" (
    python -m venv .venv
)
call .venv\Scripts\activate
pip install -r requirements.txt
cd ..

:: 2. Frontend Setup
echo [2/4] Setting up Frontend (Node/Electron)...
cd frontend
if not exist "node_modules" (
    call npm install
)
cd ..

:: 3. Startup
echo [3/4] Setup Complete.
echo.
echo [4/4] Launching Agent Amigos...
echo.

:: [OPTIONAL] Uncomment below to auto-start Ollama (local LLM for Ollie agent)
:: echo Starting Ollama LLM server...
:: tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
:: if %errorlevel% neq 0 (
::     start "Ollama Server" cmd /c "ollama serve"
::     timeout /t 3 /nobreak >nul
:: )

:: Launch backend in a new window
start "Agent Amigos Backend" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate && set LLM_API_BASE=http://127.0.0.1:11434/v1 && set LLM_MODEL=llama3.2 && python agent_init.py"

:: Wait a moment for the backend to start
echo Waiting for backend to initialize...
timeout /t 5 /nobreak >nul

:: Launch frontend in a new window
start "Agent Amigos Frontend" cmd /k "cd /d %~dp0frontend && npm run dev -- --host 127.0.0.1 --port 5173"

echo.
echo ---------------------------------------------------
echo Agent Amigos is starting!
echo.
echo Backend: http://127.0.0.1:8080  (check console for actual port)
echo Frontend: http://127.0.0.1:5173
echo.
echo Close this window when done, or press Ctrl+C in the
echo backend/frontend windows to stop the servers.
echo ---------------------------------------------------
pause
