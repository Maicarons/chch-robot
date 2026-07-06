@echo off
chcp 65001 >nul

echo ==========================================
echo Orange Pi camera configuration helper
echo ==========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found. Please install Python 3.8 or newer.
    pause
    exit /b 1
)

set /p ORANGE_PI_IP=Enter Orange Pi IP address:
if "%ORANGE_PI_IP%"=="" (
    echo [ERROR] IP address cannot be empty.
    pause
    exit /b 1
)

echo.
echo Update config.py manually with:
echo USE_IP_CAMERA = True
echo IP_CAMERA_URL = "ws://%ORANGE_PI_IP%:8765"
echo.
echo Next steps:
echo 1. Start server on Orange Pi:
echo    cd camera_servers/orange-pi-camera
echo    bash start_server.sh
echo.
echo 2. Test from Windows:
echo    python camera_servers/orange-pi-camera\test_network_camera.py
echo.
echo 3. Run CH-RO:
echo    python web_simulation/app.py
echo.
pause
