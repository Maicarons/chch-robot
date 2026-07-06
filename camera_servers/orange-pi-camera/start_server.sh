#!/bin/bash
# 香橙派摄像头服务器快速启动脚本

echo "=========================================="
echo "香橙派摄像头服务器"
echo "=========================================="
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到python3，请先安装Python 3.8+"
    exit 1
fi

echo "✓ Python版本: $(python3 --version)"
echo ""

# 检查依赖是否安装
echo "检查依赖..."
if ! python3 -c "import websockets" 2>/dev/null; then
    echo "⚠️  依赖未安装，正在安装..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败"
        exit 1
    fi
    echo "✓ 依赖安装成功"
else
    echo "✓ 依赖已安装"
fi
echo ""

# 获取本机IP
IP_ADDRESS=$(hostname -I | awk '{print $1}')
if [ -z "$IP_ADDRESS" ]; then
    IP_ADDRESS="0.0.0.0"
fi

echo "=========================================="
echo "网络信息:"
echo "  本机IP: $IP_ADDRESS"
echo "  监听端口: 8765"
echo "  WebSocket地址: ws://$IP_ADDRESS:8765"
echo "=========================================="
echo ""

# 启动服务器
echo "启动摄像头服务器..."
echo "按 Ctrl+C 停止服务器"
echo ""

python3 camera_server.py \
    --host 0.0.0.0 \
    --port 8765 \
    --camera 0 \
    --width 1280 \
    --height 720 \
    --fps 30 \
    --quality 80
