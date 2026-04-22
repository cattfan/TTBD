@echo off
title TikTok Analytics - Starting...
color 0B

echo ============================================
echo    TIKTOK ANALYTICS - KHOI DONG
echo ============================================
echo.

:: Set directory
cd /d "%~dp0"

:: Kiem tra xem moi truong ao (.venv) da duoc tao chua
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Moi truong hoat dong chua duoc thiet lap.
    echo Vui long chay file "setup.bat" de cai dat ban dau truoc nhe!
    echo.
    pause
    exit /b 1
)

:: Kich hoat moi truong ao (.venv)
call .venv\Scripts\activate.bat

echo [OK] Da ket noi moi truong ao.
echo [OK] Khoi dong server...
echo.
echo Dashboard: http://localhost:8000
echo.

:: Open browser
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8000"

:: Start application
python app.py

echo.
echo ============================================
echo    SERVER STOPPED
echo ============================================
pause
