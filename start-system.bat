@echo off
chcp 65001 >nul
cls

echo =====================================
echo Rebar System Startup Script
echo =====================================
echo.

set "PROJECT_DIR=%~dp0"

:: 1. Check and Start MinIO Service
echo 1. Checking MinIO Service...
tasklist | find /i "minio.exe" >nul
if %ERRORLEVEL% == 1 (
    if exist "D:\tool\minio.exe" (
        echo    Starting MinIO service...
        start "MinIO" /B "D:\tool\minio.exe" server D:\minio-data
        timeout /t 5 >nul
        echo    MinIO service started.
    ) else (
        echo    [WARNING] MinIO not found at D:\tool\minio.exe
    )
) else (
    echo    MinIO is already running.
)
echo.

:: 2. Start Backend Service
echo 2. Starting Python Backend...
if exist "%PROJECT_DIR%.venv\Scripts\activate.bat" (
    echo    Venv found. Installing deps and starting...
    start "Rebar Backend" cmd /k "cd /d %PROJECT_DIR% && call .venv\Scripts\activate.bat && pip install -r requirements.txt -q && python app.py"
) else (
    echo    [WARNING] No .venv. Using global python...
    start "Rebar Backend" cmd /k "cd /d %PROJECT_DIR% && pip install -r requirements.txt -q && python app.py"
)
echo    Backend: http://localhost:5000
echo.

:: 3. Start Frontend Service
echo 3. Starting Frontend...
if exist "%PROJECT_DIR%frontend\package.json" (
    start "Rebar Frontend" cmd /k "cd /d %PROJECT_DIR%frontend && npm run dev"
    echo    Frontend: http://localhost:5173
) else (
    echo    [ERROR] frontend\package.json not found!
)
echo.

echo =====================================
echo All services starting. Check each window.
echo =====================================
pause >nul
