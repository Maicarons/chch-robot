# 📷 网络摄像头系统 - 快速开始

## 🎯 功能概述

实现了基于WebSocket的分布式摄像头系统，支持香橙派(Linux)到Windows主机的图像传输。

**架构：**
```
香橙派(摄像头) → WebSocket → Windows主机(AI识别) → STM32机械臂
```

## ⚡ 5分钟快速上手

### 步骤1️⃣：香橙派端（Linux）

```bash
# SSH连接到香橙派
ssh pi@192.168.1.100

# 进入项目目录
cd ~/chch-robot/orange-pi-camera

# 安装依赖
pip install -r requirements.txt

# 启动服务器
bash start_server.sh
```

**输出示例：**
```
==========================================
香橙派摄像头服务器
==========================================

✓ Python版本: Python 3.9.2

✓ 依赖已安装

==========================================
网络信息:
  本机IP: 192.168.1.100
  监听端口: 8765
  WebSocket地址: ws://192.168.1.100:8765
==========================================

启动摄像头服务器...
按 Ctrl+C 停止服务器
```

### 步骤2️⃣：Windows主机端

```bash
# 运行配置助手
cd orange-pi-camera
configure_windows.bat

# 输入香橙派IP地址
请输入香橙派IP地址 (例如 192.168.1.100): 192.168.1.100
```

**输出示例：**
```
==========================================
网络摄像头配置助手
==========================================

✓ Python已安装

正在更新配置文件...

✓ 已备份配置文件到 config.py.bak
✓ 配置文件已更新

==========================================
配置完成！
==========================================

香橙派地址: ws://192.168.1.100:8765
```

### 步骤3️⃣：测试连接

```bash
# 测试摄像头
python test_network_camera.py --mode camera

# 测试棋盘识别
python test_network_camera.py --mode recognition
```

### 步骤4️⃣：运行主程序

```bash
cd ..
python main.py
```

## 📋 系统要求

### 香橙派端
- ✅ Python 3.8+
- ✅ OpenCV 4.5+
- ✅ USB摄像头或CSI摄像头
- ✅ 有线网络连接（推荐）

### Windows主机
- ✅ Python 3.8+
- ✅ OpenCV 4.5+
- ✅ websockets 12.0+
- ✅ 千兆以太网（推荐）

## 🔧 常用命令

### 香橙派端

```bash
# 启动服务器（默认参数）
bash start_server.sh

# 自定义参数
python camera_server.py --width 1280 --height 720 --fps 30 --quality 80

# 查看帮助
python camera_server.py --help
```

### Windows端

```bash
# 运行配置助手
configure_windows.bat

# 测试摄像头
python test_network_camera.py --mode camera

# 测试棋盘识别
python test_network_camera.py --mode recognition

# 验证安装
python verify_installation.py
```

## ⚙️ 配置选项

### 香橙派端参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--host` | 0.0.0.0 | 监听地址 |
| `--port` | 8765 | 监听端口 |
| `--camera` | 0 | 摄像头索引 |
| `--width` | 1280 | 图像宽度 |
| `--height` | 720 | 图像高度 |
| `--fps` | 30 | 帧率 |
| `--quality` | 80 | JPEG质量(1-100) |

### Windows端配置

编辑 `config.py`：

```python
# 启用网络摄像头
USE_NETWORK_CAMERA = True

# 设置香橙派地址
NETWORK_CAMERA_URL = "ws://192.168.1.100:8765"
```

## 🚀 性能调优

### 高性能模式（推荐）

**香橙派：**
```bash
python camera_server.py --width 1280 --height 720 --fps 30 --quality 80
```

**性能指标：**
- 延迟：80-120ms
- 帧率：20-25fps
- 带宽：5-8Mbps

### 低带宽模式

**香橙派：**
```bash
python camera_server.py --width 640 --height 480 --fps 15 --quality 60
```

**性能指标：**
- 延迟：40-80ms
- 帧率：12-14fps
- 带宽：1-2Mbps

## ❓ 常见问题

### Q1: 连接失败怎么办？

**检查清单：**
1. ✅ 确认香橙派服务器已启动
2. ✅ 确认IP地址正确
3. ✅ 测试网络连通性：`ping 192.168.1.100`
4. ✅ 检查防火墙设置

**解决方案：**
```bash
# 香橙派端检查
netstat -tuln | grep 8765

# Windows端测试
telnet 192.168.1.100 8765
```

### Q2: 图像延迟高？

**优化方法：**
1. 降低JPEG质量：`--quality 60`
2. 降低分辨率：`--width 640 --height 480`
3. 使用有线网络（避免WiFi）

### Q3: 频繁断连？

**解决方法：**
1. 检查网络稳定性
2. 降低推流频率
3. 检查香橙派CPU负载

## 📚 详细文档

- [README.md](README.md) - 快速开始
- [USAGE.md](USAGE.md) - 详细使用指南
- [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) - 项目总览
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - 实施总结

## 🔍 故障排查工具

```bash
# 运行完整验证
python verify_installation.py

# 查看详细日志
python camera_server.py 2>&1 | tee server.log
```

## 🛡️ 安全提示

⚠️ **警告：** 当前实现未加密，仅适用于可信局域网！

- ✅ 在专用VLAN中使用
- ✅ 限制访问IP范围
- ❌ 不要暴露在公网

## 📞 技术支持

遇到问题？

1. 查看 [USAGE.md](USAGE.md) 故障排查章节
2. 运行 `verify_installation.py` 诊断
3. 检查日志输出

## 🎉 成功标志

当你看到以下输出时，表示系统正常工作：

**香橙派端：**
```
INFO: 客户端连接: 12345, 当前客户端数: 1
INFO: 开始推流: 间隔=0.1s
```

**Windows端：**
```
✅ 网络摄像头已连接
✅ 识别成功: 32 个棋子
```

---

**版本**: v1.0  
**更新日期**: 2026-04-22  
**许可证**: 与主项目相同
