/**
 * STM32机械臂TCP服务器 - 主程序
 * 
 * 功能:
 * 1. 通过以太网接收Windows主机的走棋指令
 * 2. 解析JSON格式的指令
 * 3. 控制机械臂执行动作
 * 4. 返回执行状态
 * 
 * 硬件要求:
 * - STM32F4/F7/H7系列（带以太网MAC）
 * - 或使用ENC28J60等SPI以太网模块
 * - 机械臂驱动接口（步进电机/舵机）
 */

#include "main.h"
#include "robot_tcp_server.h"
#include "robot_control.h"
#include "json_parser.h"
#include <stdio.h>
#include <string.h>

/* 私有定义 ---------------------------------------------------------------*/
#define TCP_SERVER_PORT       5000
#define RX_BUFFER_SIZE        512
#define TX_BUFFER_SIZE        256

/* 私有变量 ---------------------------------------------------------------*/
static uint8_t rx_buffer[RX_BUFFER_SIZE];
static uint8_t tx_buffer[TX_BUFFER_SIZE];
static RobotCommand_t current_command;

/* 函数原型 ---------------------------------------------------------------*/
static void System_Init(void);
static void Process_Command(const char* json_str);
static void Send_Response(uint8_t code, const char* message);

/**
 * @brief  主函数
 * @retval int
 */
int main(void)
{
    /* 系统初始化 */
    System_Init();
    
    printf("STM32 Robot TCP Server Starting...\r\n");
    printf("Port: %d\r\n", TCP_SERVER_PORT);
    
    /* 初始化机械臂 */
    if (Robot_Init() != ROBOT_OK) {
        printf("ERROR: Robot initialization failed!\r\n");
        Error_Handler();
    }
    printf("Robot initialized successfully\r\n");
    
    /* 初始化TCP服务器 */
    if (TCP_Server_Init(TCP_SERVER_PORT) != TCP_OK) {
        printf("ERROR: TCP server initialization failed!\r\n");
        Error_Handler();
    }
    printf("TCP server started, waiting for connection...\r\n");
    
    /* 主循环 */
    while (1)
    {
        /* 等待客户端连接 */
        if (TCP_Server_WaitForClient(100) == TCP_OK) {
            printf("Client connected\r\n");
            
            /* 处理客户端请求 */
            while (TCP_Server_IsConnected()) {
                /* 接收数据 */
                int len = TCP_Server_Receive(rx_buffer, RX_BUFFER_SIZE, 1000);
                
                if (len > 0) {
                    rx_buffer[len] = '\0';
                    printf("Received: %s\r\n", (char*)rx_buffer);
                    
                    /* 解析并处理指令 */
                    Process_Command((const char*)rx_buffer);
                }
                else if (len < 0) {
                    printf("Connection error\r\n");
                    break;
                }
                
                /* 看门狗喂狗 */
                HAL_IWDG_Refresh(&hiwdg);
            }
            
            printf("Client disconnected\r\n");
        }
        
        /* 看门狗喂狗 */
        HAL_IWDG_Refresh(&hiwdg);
    }
}

/**
 * @brief  系统初始化
 * @retval None
 */
static void System_Init(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_USART1_UART_Init();  // 用于调试输出
    MX_ETH_Init();           // 以太网初始化
    
    /* 初始化看门狗 */
    MX_IWDG_Init();
}

/**
 * @brief  处理接收到的指令
 * @param  json_str: JSON格式指令字符串
 * @retval None
 */
static void Process_Command(const char* json_str)
{
    CommandResult_t result;
    
    /* 解析JSON */
    if (JSON_ParseCommand(json_str, &current_command) != JSON_OK) {
        Send_Response(1, "Invalid JSON format");
        return;
    }
    
    /* 根据指令类型执行 */
    switch (current_command.type) {
        case CMD_MOVE_PIECE:
            printf("MOVE: piece=%c from(%.1f,%.1f) to(%.1f,%.1f) capture=%d\r\n",
                   current_command.params.move.piece_char,
                   current_command.params.move.from_x,
                   current_command.params.move.from_y,
                   current_command.params.move.to_x,
                   current_command.params.move.to_y,
                   current_command.params.move.is_capture);
            
            /* 执行移动 */
            result = Robot_MovePiece(
                current_command.params.move.piece_char,
                current_command.params.move.from_x,
                current_command.params.move.from_y,
                current_command.params.move.to_x,
                current_command.params.move.to_y,
                current_command.params.move.is_capture,
                current_command.params.move.z_height
            );
            
            if (result == ROBOT_OK) {
                Send_Response(0, "Move completed");
            } else {
                Send_Response(2, "Move execution failed");
            }
            break;
            
        case CMD_TEST:
            printf("TEST sequence\r\n");
            result = Robot_TestSequence();
            
            if (result == ROBOT_OK) {
                Send_Response(0, "Test completed");
            } else {
                Send_Response(2, "Test failed");
            }
            break;
            
        case CMD_HOME:
            printf("HOME position\r\n");
            result = Robot_GoHome();
            
            if (result == ROBOT_OK) {
                Send_Response(0, "Home position reached");
            } else {
                Send_Response(2, "Failed to reach home");
            }
            break;
            
        case CMD_STOP:
            printf("EMERGENCY STOP!\r\n");
            Robot_EmergencyStop();
            Send_Response(0, "Emergency stop activated");
            break;
            
        case CMD_PING:
            Send_Response(0, "PONG");
            break;
            
        default:
            Send_Response(1, "Unknown command");
            break;
    }
}

/**
 * @brief  发送响应
 * @param  code: 响应码 (0=成功, 1=参数错误, 2=执行错误)
 * @param  message: 响应消息
 * @retval None
 */
static void Send_Response(uint8_t code, const char* message)
{
    /* 构建JSON响应 */
    sprintf((char*)tx_buffer, "{\"code\":%d,\"message\":\"%s\"}\n", code, message);
    
    printf("Response: %s", (char*)tx_buffer);
    
    /* 发送响应 */
    TCP_Server_Send(tx_buffer, strlen((char*)tx_buffer));
}

/**
 * @brief  错误处理
 * @retval None
 */
void Error_Handler(void)
{
    printf("FATAL ERROR! System halted.\r\n");
    
    /* LED闪烁指示错误 */
    while (1) {
        HAL_GPIO_TogglePin(LED_ERROR_GPIO_Port, LED_ERROR_Pin);
        HAL_Delay(200);
    }
}

#ifdef USE_FULL_ASSERT
void assert_failed(uint8_t *file, uint32_t line)
{
    printf("Assertion failed: file %s on line %lu\r\n", file, line);
}
#endif
