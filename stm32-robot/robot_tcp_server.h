/**
 * robot_tcp_server.h - TCP服务器头文件
 */

#ifndef __ROBOT_TCP_SERVER_H
#define __ROBOT_TCP_SERVER_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>

/* 返回码定义 */
typedef enum {
    TCP_OK = 0,
    TCP_ERROR = -1,
    TCP_TIMEOUT = -2,
    TCP_DISCONNECTED = -3
} TCP_Result_t;

/**
 * @brief  初始化TCP服务器
 * @param  port: 监听端口
 * @retval TCP_Result_t
 */
TCP_Result_t TCP_Server_Init(uint16_t port);

/**
 * @brief  等待客户端连接
 * @param  timeout_ms: 超时时间（毫秒）
 * @retval TCP_Result_t
 */
TCP_Result_t TCP_Server_WaitForClient(uint32_t timeout_ms);

/**
 * @brief  检查是否已连接
 * @retval 1=已连接, 0=未连接
 */
int TCP_Server_IsConnected(void);

/**
 * @brief  接收数据
 * @param  buffer: 接收缓冲区
 * @param  max_len: 最大长度
 * @param  timeout_ms: 超时时间（毫秒）
 * @retval 接收字节数，负数表示错误
 */
int TCP_Server_Receive(uint8_t* buffer, uint32_t max_len, uint32_t timeout_ms);

/**
 * @brief  发送数据
 * @param  data: 发送数据
 * @param  len: 数据长度
 * @retval TCP_Result_t
 */
TCP_Result_t TCP_Server_Send(const uint8_t* data, uint32_t len);

/**
 * @brief  断开连接
 * @retval None
 */
void TCP_Server_Disconnect(void);

#ifdef __cplusplus
}
#endif

#endif /* __ROBOT_TCP_SERVER_H */
