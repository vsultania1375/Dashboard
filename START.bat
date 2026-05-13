@echo off
title Service Analysis Dashboard
color 0A

echo.
echo  ================================================
echo   Service Analysis Dashboard v2.0
echo   PAN India Alarm System Intelligence Platform
echo  ================================================
echo.

:: Check Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Docker Desktop is not running!
    echo.
    echo  Please:
    echo  1. Open Docker Desktop from your Start Menu
    echo  2. Wait for the whale icon to stop animating
    echo  3. Run this file again
    echo.
    pause
    exit /b 1
)

echo  [OK] Docker is running
echo.
echo  Starting all services (database + backend + frontend)...
echo  This may take 2-3 minutes on first run while Docker downloads components.
echo.

cd /d "%~dp0"
docker-compose up -d --build

if errorlevel 1 (
    echo.
    echo  [ERROR] Something went wrong. See error above.
    echo  Common fix: Check if port 80 is free.
    pause
    exit /b 1
)

echo.
echo  Waiting for database to be ready...
timeout /t 10 /nobreak >nul

echo.
echo  ================================================
echo   Dashboard is ready!
echo.
echo   Open your browser and go to:
echo   http://localhost
echo.
echo   Login: admin / Admin@1234
echo   (You will be asked to change password)
echo  ================================================
echo.
echo  Press any key to open the browser automatically...
pause >nul
start http://localhost

echo.
echo  Dashboard is running. This window must stay open.
echo  Press Ctrl+C to stop the dashboard.
echo.
docker-compose logs -f backend
