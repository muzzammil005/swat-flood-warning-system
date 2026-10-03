@echo off
echo ============================================================
echo   Enabling Windows Virtual Machine Platform & WSL for Docker
echo ============================================================
echo.
echo [1/3] Enabling Virtual Machine Platform...
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

echo.
echo [2/3] Enabling Windows Subsystem for Linux...
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

echo.
echo [3/3] Updating WSL...
wsl.exe --update

echo.
echo ============================================================
echo  COMPLETED! 
echo  IMPORTANT: You MUST restart your computer now.
echo.
echo  After restarting:
echo    1. Launch Docker Desktop (it will start cleanly now).
echo    2. Run: docker compose up --build -d
echo    3. Web: http://localhost:3000
echo       API: http://localhost:8000
echo ============================================================
echo.
pause
