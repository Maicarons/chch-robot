#ifndef __ESP8266_H
#define __ESP8266_H

#include "stm32f10x.h"
#include <stdio.h>
#include <string.h>

// 类型定义
typedef unsigned char  u8;
typedef unsigned short u16;
typedef unsigned int   u32;
typedef volatile unsigned int vu32;

typedef enum {
    SYS_IDLE        = 0,
    SYS_RUNNING     = 1,
    SYS_IK_ERROR    = 2,
    SYS_CMD_ERROR   = 3,
    SYS_SAFE_STOP   = 4,
    SYS_FINISH      = 5,
    SYS_HOMING      = 6
} SystemState_TypeDef;

// 机器人指令结构体
typedef struct {
    float startX;
    float startY;
    float endX;
    float endY;
    int   signal;
    u8    is_new_cmd;
} RobotCommand_t;

// 全局变量外部声明
extern RobotCommand_t g_RobotCmd;
extern u8 USART2_RX_BUF[512];
extern u8 USART2_RX_CNT;
extern u8 AT_STEP;
extern u8 ESP_OK_FLAG;
extern u32 step_timeout;
extern volatile SystemState_TypeDef g_SystemState;

// 底层基础函数声明
void Delay_ms(u16 ms);
void MY_NVIC_PriorityGroupConfig(u8 NVIC_Group);
void MY_NVIC_Init(u8 pre,u8 sub,u8 ch,u8 group);
void USART1_Init(u32 pclk2,u32 baud);
void USART2_Init(u32 pclk1,u32 baud);
void SysTick_Init(void);
void USART1_SendStr(char *str);
void USART1_SendFloat(float num);
void USART2_SendStr(char *str);
void Clear_Buf(void);
void Check_OK(void);

// ESP8266业务对外函数
void ESP8266_Init(void);
void ESP8266_Task(void);
void ESP8266_Send_StateAndResult(u8 result);
void ESP8266_Send_CommandResult(int command_id, u8 result);

#endif

