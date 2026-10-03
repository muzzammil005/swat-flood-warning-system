@echo off
echo ============================================================
echo   Starting Swat Flood Warning System (Full Stack)
echo ============================================================
echo.

set PATH=C:\Users\%USERNAME%\AppData\Local\Programs\DockerDesktop\resources\bin;%PATH%

echo Checking Docker daemon...
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Docker daemon is not responding yet.
    echo Please make sure Docker Desktop is open and finished starting.
    echo.
    echo If this is your first time, make sure you ran enable_docker_prerequisites.bat
    echo as Administrator and restarted your PC.
    echo.
    pause
    exit /b 1
)

echo Building and starting containers: Postgres (PostGIS), Redis, FastAPI backend, Next.js frontend...
docker compose up --build -d

echo.
echo Waiting for backend and frontend to initialize...
timeout /t 15 /nobreak >nul

echo.
echo Opening Web Dashboard: http://localhost:3000
start http://localhost:3000

echo Opening API Docs: http://localhost:8000/docs
start http://localhost:8000/docs

echo.
echo ============================================================
echo Full project is running!
echo - Web Dashboard:  http://localhost:3000
echo - Backend API:    http://localhost:8000
echo - API Docs:       http://localhost:8000/docs
echo ============================================================
echo.
pause
