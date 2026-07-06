/**
 * robot_tcp_server.c - TCP服务器实现
 * 
 * 注意: 具体实现取决于使用的以太网方案
 * 1. STM32内置ETH + LwIP协议栈
 * 2. ENC28J60 + UIPTCP/IP协议栈
 * 3. W5500硬件TCP/IP芯片
 */

#include "robot_tcp_server.h"
#include "main.h"

/* 根据实际硬件选择以下一种实现 */

/* 方案1: STM32 ETH + LwIP (推荐F4/F7/H7) */
#if defined(USE_LWIP)

#include "lwip/tcp.h"
#include "lwip/netif.h"

static struct tcp_pcb* server_pcb = NULL;
static struct tcp_pcb* client_pcb = NULL;
static uint8_t is_connected = 0;

/**
 * @brief  客户端连接回调
 */
static err_t client_accept_callback(void *arg, struct tcp_pcb *newpcb, err_t err)
{
    if (client_pcb != NULL) {
        tcp_close(client_pcb);
    }
    
    client_pcb = newpcb;
    is_connected = 1;
    
    tcp_arg(client_pcb, NULL);
    tcp_recv(client_pcb, NULL);  // 设置接收回调
    
    return ERR_OK;
}

TCP_Result_t TCP_Server_Init(uint16_t port)
{
    server_pcb = tcp_new();
    if (server_pcb == NULL) {
        return TCP_ERROR;
    }
    
    err_t err = tcp_bind(server_pcb, IP_ADDR_ANY, port);
    if (err != ERR_OK) {
        return TCP_ERROR;
    }
    
    server_pcb = tcp_listen(server_pcb);
    tcp_accept(server_pcb, client_accept_callback);
    
    return TCP_OK;
}

TCP_Result_t TCP_Server_WaitForClient(uint32_t timeout_ms)
{
    uint32_t start = HAL_GetTick();
    
    while (!is_connected) {
        /* LwIP轮询处理 */
        MX_LWIP_Process();
        
        if (HAL_GetTick() - start > timeout_ms) {
            return TCP_TIMEOUT;
        }
        
        HAL_Delay(1);
    }
    
    return TCP_OK;
}

int TCP_Server_IsConnected(void)
{
    return is_connected && (client_pcb != NULL);
}

int TCP_Server_Receive(uint8_t* buffer, uint32_t max_len, uint32_t timeout_ms)
{
    if (!is_connected || client_pcb == NULL) {
        return TCP_DISCONNECTED;
    }
    
    /* 这里需要根据实际的LwIP接收回调实现 */
    /* 简化示例，实际需要环形缓冲区和回调机制 */
    return 0;  // TODO: 实现实际接收逻辑
}

TCP_Result_t TCP_Server_Send(const uint8_t* data, uint32_t len)
{
    if (!is_connected || client_pcb == NULL) {
        return TCP_DISCONNECTED;
    }
    
    err_t err = tcp_write(client_pcb, data, len, TCP_WRITE_FLAG_COPY);
    if (err != ERR_OK) {
        return TCP_ERROR;
    }
    
    tcp_output(client_pcb);
    
    return TCP_OK;
}

void TCP_Server_Disconnect(void)
{
    if (client_pcb != NULL) {
        tcp_close(client_pcb);
        client_pcb = NULL;
    }
    is_connected = 0;
}

/* 方案2: W5500硬件TCP/IP芯片 */
#elif defined(USE_W5500)

#include "w5500.h"
#include "socket.h"

#define SOCKET_NUM  0

TCP_Result_t TCP_Server_Init(uint16_t port)
{
    uint8_t status;
    
    /* 配置W5500为TCP服务器模式 */
    socket(SOCKET_NUM, Sn_MR_TCP, port, SF_TCP_NODELAY);
    
    return TCP_OK;
}

TCP_Result_t TCP_Server_WaitForClient(uint32_t timeout_ms)
{
    uint32_t start = HAL_GetTick();
    uint8_t status;
    
    listen(SOCKET_NUM);
    
    while (HAL_GetTick() - start < timeout_ms) {
        getsockopt(SOCKET_NUM, SO_STATUS, &status);
        
        if (status == SOCK_ESTABLISHED) {
            return TCP_OK;
        }
        
        HAL_Delay(1);
    }
    
    return TCP_TIMEOUT;
}

int TCP_Server_IsConnected(void)
{
    uint8_t status;
    getsockopt(SOCKET_NUM, SO_STATUS, &status);
    return (status == SOCK_ESTABLISHED) ? 1 : 0;
}

int TCP_Server_Receive(uint8_t* buffer, uint32_t max_len, uint32_t timeout_ms)
{
    if (!TCP_Server_IsConnected()) {
        return TCP_DISCONNECTED;
    }
    
    int len = recv(SOCKET_NUM, buffer, max_len);
    return len;
}

TCP_Result_t TCP_Server_Send(const uint8_t* data, uint32_t len)
{
    if (!TCP_Server_IsConnected()) {
        return TCP_DISCONNECTED;
    }
    
    int sent = send(SOCKET_NUM, (uint8_t*)data, len);
    
    return (sent == len) ? TCP_OK : TCP_ERROR;
}

void TCP_Server_Disconnect(void)
{
    disconnect(SOCKET_NUM);
    close(SOCKET_NUM);
}

/* 方案3: ENC28J60 + UIP (需要更多RAM) */
#elif defined(USE_ENC28J60)

#warning "ENC28J60 implementation not yet complete"

TCP_Result_t TCP_Server_Init(uint16_t port)
{
    return TCP_ERROR;  // TODO
}

TCP_Result_t TCP_Server_WaitForClient(uint32_t timeout_ms)
{
    return TCP_ERROR;  // TODO
}

int TCP_Server_IsConnected(void)
{
    return 0;  // TODO
}

int TCP_Server_Receive(uint8_t* buffer, uint32_t max_len, uint32_t timeout_ms)
{
    return 0;  // TODO
}

TCP_Result_t TCP_Server_Send(const uint8_t* data, uint32_t len)
{
    return TCP_ERROR;  // TODO
}

void TCP_Server_Disconnect(void)
{
    // TODO
}

#else
#error "Please define USE_LWIP, USE_W5500, or USE_ENC28J60"
#endif
