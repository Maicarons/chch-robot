# 机械臂TCP通信协议规范

## 概述

本文档定义了Windows主机与STM32机械臂之间的TCP通信协议。

## 网络架构

```
┌──────────────┐         TCP/IP          ┌──────────────┐
│ Windows主机   │ ◄══════════════════► │ STM32机械臂   │
│ (TCP客户端)   │    Port: 5000         │ (TCP服务器)   │
└──────────────┘                         └──────────────┘
     发送指令                                执行动作
     接收响应                                返回状态
```

## 连接参数

- **协议**: TCP
- **编码**: UTF-8
- **端口**: 5000
- **结束符**: `\n` (换行符, 0x0A)
- **超时**: 10秒（可配置）

## 消息格式

### 请求消息（主机→STM32）

JSON格式，以换行符结尾：

```json
{"cmd":"COMMAND","params":{...}}\n
```

### 响应消息（STM32→主机）

JSON格式，以换行符结尾：

```json
{"code":0,"message":"Success message"}\n
```

## 指令类型

### 1. MOVE - 移动棋子

**请求：**
```json
{
    "cmd": "MOVE",
    "params": {
        "piece": "R",
        "from_x": 100.0,
        "from_y": 100.0,
        "to_x": 150.0,
        "to_y": 100.0,
        "is_capture": 0,
        "z_height": 0.0
    }
}\n
```

**参数字段：**

| 字段 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| piece | string | 是 | 棋子字符 | 'R', 'N', 'B', 'A', 'K', 'C', 'P' (大写=红方, 小写=黑方) |
| from_x | float | 是 | 起始X坐标（毫米） | 100.0 |
| from_y | float | 是 | 起始Y坐标（毫米） | 100.0 |
| to_x | float | 是 | 目标X坐标（毫米） | 150.0 |
| to_y | float | 是 | 目标Y坐标（毫米） | 100.0 |
| is_capture | int | 否 | 是否吃子 (0或1) | 0 |
| z_height | float | 否 | Z轴高度，0表示默认值 | 0.0 |

**响应（成功）：**
```json
{"code":0,"message":"Move completed"}\n
```

**响应（失败）：**
```json
{"code":2,"message":"Move execution failed"}\n
```

---

### 2. TEST - 测试序列

**请求：**
```json
{"cmd":"TEST"}\n
```

**响应（成功）：**
```json
{"code":0,"message":"Test completed"}\n
```

**响应（失败）：**
```json
{"code":2,"message":"Test failed"}\n
```

---

### 3. HOME - 回home点

**请求：**
```json
{"cmd":"HOME"}\n
```

**响应（成功）：**
```json
{"code":0,"message":"Home position reached"}\n
```

**响应（失败）：**
```json
{"code":2,"message":"Failed to reach home"}\n
```

---

### 4. STOP - 急停

**请求：**
```json
{"cmd":"STOP"}\n
```

**响应：**
```json
{"code":0,"message":"Emergency stop activated"}\n
```

⚠️ **注意**: 急停指令会立即停止所有电机运动！

---

### 5. PING - 心跳检测

**请求：**
```json
{"cmd":"PING"}\n
```

**响应：**
```json
{"code":0,"message":"PONG"}\n
```

## 响应码定义

| 代码 | 含义 | 说明 |
|------|------|------|
| 0 | SUCCESS | 成功执行 |
| 1 | ERROR_PARAM | 参数错误（JSON格式错误、缺少字段等） |
| 2 | ERROR_EXECUTE | 执行错误（机械臂运动失败、超时等） |
| 3 | ERROR_TIMEOUT | 通信超时 |
| 4 | BUSY | 机械臂忙碌，无法接受新指令 |

## 坐标系定义

### 机械臂坐标系

```
         Y (向前)
         ↑
         |
         |
         |___________→ X (向右)
        /
       /
      ↓ Z (向下)
```

- **原点**: 棋盘左下角（可根据实际校准调整）
- **X轴**: 水平向右
- **Y轴**: 垂直向前
- **Z轴**: 垂直向上（正值向上）

### 棋盘尺寸

标准中国象棋棋盘：
- **列数**: 9列（0-8）
- **行数**: 10行（0-9）
- **格子间距**: 50mm
- **总宽度**: 450mm (9 × 50)
- **总高度**: 500mm (10 × 50)

### Home点位置

默认Home点坐标（可在`robot_control.c`中修改）：
- **X**: 100mm
- **Y**: 100mm
- **Z**: 150mm

## 使用示例

### Python示例

```python
from robot import RobotTCPClient

# 创建客户端
client = RobotTCPClient(host="192.168.1.200", port=5000)

# 连接
if client.connect():
    print("连接成功")
    
    # 移动棋子
    success, msg = client.move_piece(
        piece_char='R',
        from_x=100.0,
        from_y=100.0,
        to_x=150.0,
        to_y=100.0,
        is_capture=False
    )
    
    if success:
        print(f"移动成功: {msg}")
    else:
        print(f"移动失败: {msg}")
    
    # 断开连接
    client.disconnect()
```

### C语言示例（STM32端）

```c
// 在main.c中已实现，无需额外代码
// 接收到的JSON会自动解析并执行
```

## 错误处理

### 主机端错误处理

```python
try:
    success, msg = client.move_piece(...)
    if not success:
        # 尝试重连
        client.reconnect()
        # 重试指令
        success, msg = client.move_piece(...)
except Exception as e:
    print(f"通信错误: {e}")
```

### STM32端错误处理

```c
// 在Process_Command函数中
if (result != ROBOT_OK) {
    Send_Response(2, "Move execution failed");
    // 记录错误日志
    // 可选：回到安全位置
}
```

## 性能指标

### 典型延迟

| 操作 | 延迟 | 说明 |
|------|------|------|
| TCP连接建立 | 10-50ms | 取决于网络状况 |
| 指令传输 | 5-20ms | JSON序列化+网络传输 |
| 机械臂响应 | 100-500ms | 取决于运动距离 |
| 总延迟 | 115-570ms | 从发送到完成 |

### 吞吐量

- **最大指令频率**: 2-5 Hz（受机械臂速度限制）
- **建议指令间隔**: ≥500ms（避免队列堆积）

## 安全机制

### 1. 看门狗保护

STM32启用独立看门狗（IWDG），如果主循环卡死会自动复位。

### 2. 急停功能

支持硬件急停按钮和软件STOP指令。

### 3. 限位保护

建议在机械臂各轴安装限位开关，防止超程。

### 4. 超时保护

TCP通信设置10秒超时，避免无限等待。

### 5. 忙状态检查

机械臂忙碌时返回code=4，主机应等待后再发送新指令。

## 调试技巧

### 1. 串口监控

连接USB转TTL到STM32的USART1，查看实时日志：

```
Received: {"cmd":"MOVE","params":{"piece":"R",...}}
MOVE: piece=R from(100.0,100.0) to(150.0,100.0) capture=0
Move to (100.0, 100.0, 130.0), distance=30.0
Gripper CLOSE
Move to (150.0, 100.0, 130.0), distance=50.0
Gripper OPEN
Move completed
Response: {"code":0,"message":"Move completed"}
```

### 2. 网络抓包

使用Wireshark捕获TCP数据包，分析通信过程。

### 3. Python测试工具

```bash
python robot/tcp_client.py --host 192.168.1.200 --port 5000
```

## 常见问题

### Q1: 连接被拒绝

**原因**: STM32未启动或IP地址错误  
**解决**: 
1. 检查STM32电源和网线
2. 确认IP地址正确
3. ping测试连通性

### Q2: 指令无响应

**原因**: JSON格式错误或参数缺失  
**解决**: 
1. 检查JSON格式
2. 查看STM32串口输出
3. 验证必填字段

### Q3: 机械臂不动作

**原因**: 电机驱动故障或限位触发  
**解决**: 
1. 检查电机电源
2. 检查限位开关状态
3. 查看错误响应码

## 版本历史

### v1.0 (当前版本)
- ✅ 基础TCP通信
- ✅ JSON指令解析
- ✅ 5种指令类型
- ✅ 错误处理机制

### 计划功能
- ⏳ 指令队列支持
- ⏳ 运动轨迹规划
- ⏳ 实时状态反馈
- ⏳ 固件在线升级

---

**文档版本**: v1.0  
**更新日期**: 2026-04-22  
**维护者**: Development Team
