@echo off
REM Windows主机网络摄像头配置助手
chcp 65001 >nul

echo ==========================================
echo 网络摄像头配置助手
echo ==========================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo ✓ Python已安装
echo.

REM 获取香橙派IP
set /p ORANGE_PI_IP="请输入香橙派IP地址 (例如 192.168.1.100): "

if "%ORANGE_PI_IP%"=="" (
    echo ❌ IP地址不能为空
    pause
    exit /b 1
)

echo.
echo 正在更新配置文件...
echo.

REM 备份原配置文件
if exist ..\config.py (
    copy ..\config.py ..\config.py.bak >nul
    echo ✓ 已备份配置文件到 config.py.bak
)

REM 使用PowerShell更新配置文件
powershell -Command ^
    "$content = Get-Content '..\config.py' -Raw; ^
     $content = $content -replace 'USE_NETWORK_CAMERA = False', 'USE_NETWORK_CAMERA = True'; ^
     $content = $content -replace 'NETWORK_CAMERA_URL = \"ws://[^\"]+\"', 'NETWORK_CAMERA_URL = \"ws://%ORANGE_PI_IP%:8765\"'; ^
     Set-Content '..\config.py' $content -NoNewline"

if errorlevel 1 (
    echo ❌ 配置文件更新失败
    pause
    exit /b 1
)

echo ✓ 配置文件已更新
echo.
echo ==========================================
echo 配置完成！
echo ==========================================
echo.
echo 香橙派地址: ws://%ORANGE_PI_IP%:8765
echo.
echo 下一步操作:
echo 1. 在香橙派上启动服务器:
echo    cd orange-pi-camera
echo    bash start_server.sh
echo.
echo 2. 在Windows上测试连接:
echo    python orange-pi-camera\test_network_camera.py --mode camera
echo.
echo 3. 运行主程序:
echo    python main.py
echo.
echo ==========================================
echo.

pause
