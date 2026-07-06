# 快速开始

## 环境要求

- Python 3.8+
- Windows 或 Linux 主机
- USB 摄像头或 MJPEG/RTSP 网络摄像头
- 下载到 `Pikafish/` 的 Pikafish 引擎
- 可选：同一局域网内的 STM32 机器人控制器

## 安装依赖

```bash
pip install -r requirements.txt
```

从 Pikafish 官方发布页下载对应平台的二进制文件，放入 `Pikafish/`。如果文件名不同，修改 `config.py` 中的 `ENGINE_PATH`。

## 启动 Web 界面

```bash
python web_simulation/app.py
```

浏览器打开 `http://localhost:5000`。纯软件测试使用 `simulation` 模式，连接 STM32 后使用 `hardware` 模式。

## 启动命令行

```bash
python main.py
python main.py --demo
python main.py --test-camera
python main.py --test-engine
```

## 运行测试

```bash
python -m pytest tests/ -v
```

开发时可运行单个测试文件：

```bash
python -m pytest tests/test_robot_protocol.py -v
python -m pytest tests/test_stabilizer.py -v
```
