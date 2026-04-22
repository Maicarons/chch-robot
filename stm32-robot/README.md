# STM32机械臂TCP服务器

通过TCP接收Windows主机的走棋指令，控制机械臂执行动作。

## 硬件要求

### 主控芯片
- **推荐**: STM32F4/F7/H7系列（带以太网MAC）
- **备选**: STM32F1/F3 + ENC28J60/W5500以太网模块

### 网络方案（三选一）

#### 方案1: STM32内置ETH + LwIP（推荐）
- 优点：性能高，无需额外芯片
- 缺点：需要RMII/MII PHY芯片（如LAN8720、DP83848）
- 适用：STM32F4/F7/H7

#### 方案2: W5500硬件TCP/IP芯片
- 优点：简单易用，SPI接口
- 缺点：速度较慢
- 适用：所有STM32

#### 方案3: ENC28J60以太网模块
- 优点：成本低
- 缺点：需要UIP协议栈，RAM占用大
- 适用：资源充足的STM32

### 机械臂驱动
- 步进电机 + 驱动器（如A4988、TMC2208）
- 或舵机（如MG996R、DS3218）
- 夹爪驱动（舵机或电磁铁）

## 文件结构

```
stm32-robot/
├── main.c                  # 主程序
├── robot_tcp_server.h      # TCP服务器头文件
├── robot_tcp_server.c      # TCP服务器实现
├── robot_control.h         # 机械臂控制头文件
├── robot_control.c         # 机械臂控制实现
├── json_parser.h           # JSON解析器头文件
├── json_parser.c           # JSON解析器实现
└── README.md               # 本文档
```

## 编译配置

### CubeMX配置要点

#### 1. 系统时钟
- HSE: 外部晶振（8MHz或25MHz）
- SYSCLK: 根据芯片最大频率设置
- 确保以太网时钟正确配置

#### 2. 以太网（使用LwIP时）
- ETH模式: RMII或MII
- PHY地址: 根据硬件设置（通常0或1）
- LwIP选项:
  - DHCP: 可选（建议静态IP）
  - TCP: 启用
  - TCP_MSS: 1460
  - TCP_SND_BUF: 4 * TCP_MSS

#### 3. USART1（调试输出）
- 波特率: 115200
- 数据位: 8
- 停止位: 1

#### 4. GPIO
- LED指示灯
- 急停按钮（可选）

#### 5. 看门狗
- IWDG: 启用（防止死机）

### 预处理器定义

在`main.h`或编译器选项中添加：

```c
/* 选择网络方案（三选一）*/
#define USE_LWIP        // 使用LwIP协议栈
// #define USE_W5500    // 使用W5500芯片
// #define USE_ENC28J60 // 使用ENC28J60模块

/* 机械臂类型 */
#define ROBOT_TYPE_STEPPER  // 步进电机
// #define ROBOT_TYPE_SERVO // 舵机
```

## 网络配置

### 静态IP配置（推荐）

在`lwipopts.h`或网络初始化代码中：

```c
/* IP地址 */
#define IP_ADDR0    192
#define IP_ADDR1    168
#define IP_ADDR2    1
#define IP_ADDR3    200

/* 子网掩码 */
#define NETMASK0    255
#define NETMASK1    255
#define NETMASK2    255
#define NETMASK3    0

/* 网关 */
#define GW0         192
#define GW1         168
#define GW2         1
#define GW3         1

/* TCP端口 */
#define TCP_PORT    5000
```

### DHCP配置

如果需要动态获取IP，启用LwIP的DHCP功能，并通过串口打印获取的IP地址。

## 通信协议

### TCP连接
- **主机**: Windows (客户端)
- **从机**: STM32 (服务器)
- **端口**: 5000
- **编码**: UTF-8
- **结束符**: `\n` (换行符)

### 指令格式（主机→STM32）

JSON格式，以换行符结尾：

```json
{"cmd":"MOVE","params":{"piece":"R","from_x":100.0,"from_y":100.0,"to_x":150.0,"to_y":100.0,"is_capture":0,"z_height":0.0}}\n
```

**字段说明：**
- `cmd`: 指令类型 ("MOVE", "TEST", "HOME", "STOP", "PING")
- `params`: 参数字段（MOVE指令需要）
  - `piece`: 棋子字符 ('R', 'N', 'B', 'A', 'K', 'C', 'P' 或小写)
  - `from_x`: 起始X坐标（毫米）
  - `from_y`: 起始Y坐标（毫米）
  - `to_x`: 目标X坐标（毫米）
  - `to_y`: 目标Y坐标（毫米）
  - `is_capture`: 是否吃子 (0或1)
  - `z_height`: Z轴高度，0表示使用默认值

### 响应格式（STM32→主机）

```json
{"code":0,"message":"Move completed"}\n
```

**响应码：**
- `0`: 成功
- `1`: 参数错误
- `2`: 执行错误
- `3`: 超时
- `4`: 忙碌

## 机械臂校准

### 坐标系定义
- **原点**: 棋盘左下角
- **X轴**: 水平向右
- **Y轴**: 垂直向前
- **Z轴**: 垂直向上

### Home点位置
修改`robot_control.c`中的宏定义：

```c
#define ROBOT_HOME_X    100.0f   // Home点X
#define ROBOT_HOME_Y    100.0f   // Home点Y
#define ROBOT_HOME_Z    150.0f   // Home点Z
```

### 棋盘尺寸
标准中国象棋棋盘：
- 格子数: 9列 × 10行
- 格子间距: 50mm
- 总尺寸: 450mm × 500mm

## 测试步骤

### 1. 硬件检查
- [ ] 电源正常（通常为12V或24V）
- [ ] 以太网线连接
- [ ] 机械臂接线正确
- [ ] 急停按钮可用

### 2. 串口调试
连接USB转TTL模块到USART1，打开串口助手（115200波特率），观察启动信息：

```
STM32 Robot TCP Server Starting...
Port: 5000
Robot initialized successfully
TCP server started, waiting for connection...
```

### 3. 网络测试
在Windows主机上ping STM32：

```bash
ping 192.168.1.200
```

### 4. TCP连接测试
使用Python测试脚本（在Windows主机）：

```bash
cd G:\GitHub\chch-robot
python robot\tcp_client.py --host 192.168.1.200 --port 5000
```

### 5. 机械臂测试
发送测试指令：

```json
{"cmd":"TEST"}
```

观察机械臂是否按预期运动。

## 故障排查

### 问题1: 无法连接

**可能原因：**
- IP地址配置错误
- 网线未连接
- 防火墙阻止

**解决方法：**
1. 检查STM32串口输出的IP地址
2. 确认网线指示灯亮起
3. 暂时关闭Windows防火墙测试

### 问题2: 机械臂不动作

**可能原因：**
- 电机驱动未供电
- 接线错误
- 限位开关触发

**解决方法：**
1. 检查电机电源
2. 使用万用表检查接线
3. 检查限位开关状态

### 问题3: 运动不准确

**可能原因：**
- 步进电机丢步
- 机械结构松动
- 校准参数错误

**解决方法：**
1. 降低运动速度
2. 紧固机械结构
3. 重新校准坐标

## 性能优化

### 1. 提高响应速度
- 减小TCP缓冲区大小
- 优化JSON解析算法
- 使用DMA传输

### 2. 提高运动精度
- 使用微步驱动（1/16或1/32步）
- 增加编码器反馈
- 闭环控制

### 3. 提高稳定性
- 启用看门狗
- 添加异常处理
- 定期自检

## 安全注意事项

⚠️ **重要警告：**

1. **急停功能**: 必须配备硬件急停按钮
2. **限位保护**: 安装机械限位开关
3. **速度限制**: 初始测试时使用低速
4. **工作区域**: 清理机械臂运动范围内的障碍物
5. **电源保护**: 添加过流保护和保险丝

## 扩展功能

### 未来可以添加：
- [ ] 多段轨迹规划
- [ ] 力反馈控制
- [ ] 视觉定位辅助
- [ ] 无线通信（WiFi/蓝牙）
- [ ] 云端监控界面

## 技术支持

遇到问题请检查：
1. 串口调试输出
2. 网络连接状态
3. 机械臂电源和接线
4. 日志文件

---

**版本**: v1.0  
**日期**: 2026-04-22  
**硬件平台**: STM32F4/F7/H7  
**软件协议**: TCP/JSON
