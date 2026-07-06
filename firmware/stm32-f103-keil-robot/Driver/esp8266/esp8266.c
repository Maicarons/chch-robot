#include "esp8266.h"
#include "stdio.h"
#include "string.h"


// ===================== 全局变量 =====================
RobotCommand_t g_RobotCmd = {0, 0, 0, 0, 0, 0};
static char Current_Link_ID = '0';

u8 USART2_RX_BUF[512];
u8 USART2_RX_CNT = 0;
u8 AT_STEP = 0;
u8 ESP_OK_FLAG = 0;
u32 step_timeout = 0;

// ===================== 位带操作 =====================
#define BITBAND(addr, bitnum) ((addr & 0xF0000000)+0x2000000+((addr &0xFFFFF)<<5)+(bitnum<<2))
#define MEM_ADDR(addr)  *((vu32  *)(addr))
#define BIT_ADDR(addr, bitnum)   MEM_ADDR(BITBAND(addr, bitnum))

#define GPIOA_ODR (u32)(GPIOA_BASE+0x0C)
#define GPIOA_IDR (u32)(GPIOA_BASE+0x08)
#define PAout(n)   BIT_ADDR(GPIOA_ODR,n)
#define PAin(n)    BIT_ADDR(GPIOA_IDR,n)

// ===================== 延时 =====================
void Delay_ms(u16 ms)
{
    u16 i,j;
    for(i=ms;i>0;i--)
        for(j=12000;j>0;j--);
}
// ===================== NVIC 配置 =====================
void MY_NVIC_PriorityGroupConfig(u8 NVIC_Group)
{
    u32 temp,temp1;
    temp1=(~NVIC_Group)&0x07;
    temp1<<=8;
    temp=SCB->AIRCR;
    temp&=0X0000F8FF;
    temp|=0X05FA0000;
    temp|=temp1;
    SCB->AIRCR=temp;
}

void MY_NVIC_Init(u8 NVIC_PreemptionPriority,u8 NVIC_SubPriority,u8 NVIC_Channel,u8 NVIC_Group)
{
    u32 temp;
    MY_NVIC_PriorityGroupConfig(NVIC_Group);
    temp=NVIC_PreemptionPriority<<(4-NVIC_Group);
    temp|=NVIC_SubPriority&(0x0f>>NVIC_Group);
    temp&=0xf;
    NVIC->ISER[NVIC_Channel/32]|=(1<<NVIC_Channel%32);
    NVIC->IP[NVIC_Channel]|=temp<<4;
}

// ===================== USART1 初始化（调试） =====================
void USART1_Init(u32 pclk2,u32 baud)
{
    float temp;
    u16 mantissa,frac;
    vu8 dummyread;

    RCC->APB2ENR |= 1<<2;
    RCC->APB2ENR |= 1<<14;

    GPIOA->CRH &= 0xFFFFF00F;
    GPIOA->CRH |= 0x000008B0;

    temp = (pclk2*1000000.0)/(baud*16);
    mantissa = temp;
    frac = (temp-mantissa)*16;
    USART1->BRR = (mantissa<<4)|frac;

    USART1->CR1 = 0x200C;
    USART1->CR1 |= 1<<5;

    MY_NVIC_Init(3,3,USART1_IRQn,2);
    dummyread = USART1->SR;
}

// ===================== USART2 初始化（ESP8266） =====================
void USART2_Init(u32 pclk1,u32 baud)
{
    float temp;
    u16 mantissa,frac;
    vu8 dummyread;

    RCC->APB2ENR |= 1<<2;
    RCC->APB1ENR |= 1<<17;

    GPIOA->CRL &= 0xFFFF00FF;
    GPIOA->CRL |= 0x00008B00;

    temp = (pclk1*1000000.0)/(baud*16);
    mantissa = temp;
    frac = (temp-mantissa)*16;
    USART2->BRR = (mantissa<<4)|frac;

    USART2->CR1 = 0x200C;
    USART2->CR1 |= 1<<5;

    MY_NVIC_Init(3,2,USART2_IRQn,2);
    dummyread = USART2->SR;
}

// ===================== 串口发送 =====================
void USART1_SendStr(char *str)
{
    while(*str)
    {
        USART1->DR = *str++;
        while(!(USART1->SR & (1<<6)));
    }
}

void USART2_SendStr(char *str)
{
    while(*str)
    {
        USART2->DR = *str++;
        while(!(USART2->SR & (1<<6)));
    }
}

// ===================== 缓存清空 & 检查OK =====================
void Clear_Buf(void)
{
    memset(USART2_RX_BUF,0,512);
    USART2_RX_CNT = 0;
    ESP_OK_FLAG = 0;
    step_timeout = 0;
}

void Check_OK(void)
{
    if(strstr((char*)USART2_RX_BUF,"OK") != NULL)
        ESP_OK_FLAG = 1;
}

// ===================== SysTick 超时 =====================
void SysTick_Init(void)
{
    SysTick->LOAD = 72000;
    SysTick->VAL = 0;
    SysTick->CTRL = 0x03;
}

void SysTick_Handler(void)
{
    if(step_timeout > 0)
        step_timeout--;
}

// ===================== 串口中断服务函数 =====================
void USART1_IRQHandler(void)
{
    u8 res;
    if(USART1->SR & (1<<5))
    {
        res = USART1->DR;
    }
}

void USART2_IRQHandler(void)
{
    u8 res;
    if(USART2->SR & (1<<5))
    {
        res = USART2->DR;
        if(USART2_RX_CNT < 511)
            USART2_RX_BUF[USART2_RX_CNT++] = res;
        Check_OK();
    }
}

// ===================== 硬件初始化 =====================
void ESP8266_Init(void)
{
    USART1_Init(72, 115200);
    USART2_Init(36, 115200);
    SysTick_Init();
    Delay_ms(1000);
    USART1_SendStr("\r\n=== ESP8266 TCP Server 启动成功 ===\r\n");
}

// ===================== AT指令启动服务器 =====================
//void ESP8266_Server_Start(void)
    // 主流程在 ESP8266_Task 中自动执行


// ===================== 指令解析 & 通信任务 =====================
void ESP8266_Task(void)
{
    switch(AT_STEP)
    {
        case 0:
            USART1_SendStr("\r\n[Step0] 发送AT测试...\r\n");
            Clear_Buf();
            USART2_SendStr("AT\r\n");
            step_timeout = 2000;
            AT_STEP = 100;
            break;

        case 100:
            if(ESP_OK_FLAG)
            {
                USART1_SendStr("[Step0] ESP8266响应OK\r\n");
                AT_STEP = 1;
            }
            else if(step_timeout == 0) AT_STEP = 0;
            break;

        case 1:
            USART1_SendStr("[Step1] 设置STA模式\r\n");
            Clear_Buf();
            USART2_SendStr("AT+CWMODE=1\r\n");
            step_timeout = 2000;
            AT_STEP = 101;
            break;

        case 101:
            if(ESP_OK_FLAG) { AT_STEP = 2; }
            else if(step_timeout == 0) AT_STEP = 1;
            break;

        case 2:
            USART1_SendStr("[Step2] 连接WiFi\r\n");
            Clear_Buf();
            // 请修改为你的WiFi名称和密码
            USART2_SendStr("AT+CWJAP=\"ACE\",\"12345678\"\r\n");
            step_timeout = 6000;
            AT_STEP = 102;
            break;

        case 102:
            if(ESP_OK_FLAG)
            {
                USART1_SendStr("[Step2] WiFi连接成功\r\n");
                AT_STEP = 3;
            }
            else if(step_timeout == 0) AT_STEP = 2;
            break;

        case 3:
            Clear_Buf();
            USART2_SendStr("AT+CIFSR\r\n");
            step_timeout = 2000;
            AT_STEP = 103;
            break;

        case 103:
            if(step_timeout == 0 || ESP_OK_FLAG)
			{
        USART1_SendStr("\r\n==================================\r\n");
        USART1_SendStr("[ESP8266 IP信息]: \r\n");
        USART1_SendStr((char*)USART2_RX_BUF);  // 打印完整IP
        USART1_SendStr("\r\n==================================\r\n");
        USART1_SendStr("请用上面的IP连接 TCP 8086\r\n");
        AT_STEP = 4;
			}
            break;

        case 4:
            USART1_SendStr("[Step4] 开启多连接\r\n");
            Clear_Buf();
            USART2_SendStr("AT+CIPMUX=1\r\n");
            step_timeout = 2000;
            AT_STEP = 104;
            break;

        case 104:
            if(ESP_OK_FLAG) { AT_STEP = 5; }
            else if(step_timeout == 0) AT_STEP = 4;
            break;

        case 5:
            USART1_SendStr("[Step5] 开启TCP Server(8086)\r\n");
            Clear_Buf();
            USART2_SendStr("AT+CIPSERVER=1,8086\r\n");
            step_timeout = 2000;
            AT_STEP = 105;
            break;

        case 105:
            if(ESP_OK_FLAG)
            {
                USART1_SendStr("=== 服务器就绪，等待客户端连接 ===\r\n");
                AT_STEP = 6;
            }
            else if(step_timeout == 0) AT_STEP = 5;
            break;

        case 6:
            if(strstr((char*)USART2_RX_BUF,"CONNECT") != NULL)
            {
                USART1_SendStr("\r\n=== 客户端已连接 ===\r\n");
                Clear_Buf();
                AT_STEP = 7;
            }
            break;

        case 7:
            if(USART2_RX_CNT > 0)
            {
                Delay_ms(20);
                char *ipd = strstr((char*)USART2_RX_BUF,"+IPD,");
                if(ipd)
                {
                    Current_Link_ID = *(ipd+5);
                    char *data = strchr(ipd,':');
                    if(data)
                    {
                        data++;
                        USART1_SendStr("\r\n[收到指令]:");
                        USART1_SendStr(data);

                        int x1,y1,x2,y2,sig;
                        if(sscanf(data,"%d,%d,%d,%d,%d",&x1,&y1,&x2,&y2,&sig)==5)
                        {
                            g_RobotCmd.startX = x1;
                            g_RobotCmd.startY = y1;
                            g_RobotCmd.endX = x2;
                            g_RobotCmd.endY = y2;
                            g_RobotCmd.signal = sig;
                            g_RobotCmd.is_new_cmd = 1;
                            USART1_SendStr("\r\n[解析成功]\r\n");
                        }
                        else
                        {
                            USART1_SendStr("\r\n[格式错误]\r\n");
                        }
                    }
                }
                else if(strstr((char*)USART2_RX_BUF,"CLOSED"))
                {
                    USART1_SendStr("\r\n=== 客户端断开 ===\r\n");
                    AT_STEP = 6;
                }
                Clear_Buf();
            }
            break;
    }
}

// ===================== 回传结果给客户端 =====================
void ESP8266_Send_Result(u8 success_flag)
{
    char res[4];
    sprintf(res,"%d",success_flag ? 1 : 0);

    char cmd[32];
    sprintf(cmd,"AT+CIPSEND=%c,%d\r\n",Current_Link_ID,strlen(res));

    USART2_SendStr(cmd);
    Delay_ms(50);
    USART2_SendStr(res);

    USART1_SendStr("\r\n[回传结果]:");
    USART1_SendStr(res);
    USART1_SendStr("\r\n");
}


