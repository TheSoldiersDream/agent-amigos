@echo off
echo ========================================
echo   Agent Amigos - Chrome Launcher
echo ========================================
echo.
echo This opens Chrome with remote debugging enabled.
echo Log into Facebook ONCE, then the agent can control it!
echo.
echo NOTE: Close any existing Chrome windows first.
echo.

REM Kill existing Chrome
taskkill /F /IM chrome.exe 2>nul
timeout /t 2 /nobreak >nul

REM Start Chrome with debugging and your profile
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\Google\Chrome\User Data" --profile-directory=Default --start-maximized https://www.facebook.com

echo.
echo Chrome started with debugging on port 9222
echo You can now use Agent Amigos social media tools!
echo.
echo Keep this Chrome window open while using the agent.
echo.
pause
