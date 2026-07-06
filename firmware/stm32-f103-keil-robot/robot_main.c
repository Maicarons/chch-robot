#include "stm32f10x.h"  
#include "esp8266.h"
#include "pump_valve.h"
#include "motor.h"
#include "ik.h"

// 弧度转角度宏
#define RAD_TO_DEG(rad)  ((rad) * 180.0f / 3.1415926535f)

volatile SystemState_TypeDef g_SystemState = SYS_IDLE;

// ===================== 安全停机=====================
void System_SafeStop(void)
{
    Motor_StopAll();
    Pump_Off();
    Valve_Off();

    g_SystemState = SYS_SAFE_STOP;
    USART1_SendStr("\r\n!!! 系统安全停机：所有电机/气泵已关闭\r\n");

    ESP8266_Send_StateAndResult(0);

    Delay_ms(1000);
    g_SystemState = SYS_IDLE;
    USART1_SendStr("\r\n系统已复位，等待新指令...\r\n");
}

// ===================== 动作函数 =====================
//sport1:移动机械臂并吸棋子
void sport1(SCARA_Motion_t result)
{
    if (g_SystemState == SYS_SAFE_STOP) return;
    USART1_SendStr("\r\n===== 执行 sport1 =====\r\n");
    
		USART1_SendStr("\r\n电机1\r\n");
    Motor_M1_Rotate(result.dq1_rel_deg);
    
		USART1_SendStr("\r\n电机2\r\n");
    Motor_M2_Rotate(result.dq2_rel_deg);
    
		Delay_ms(800);
    
		USART1_SendStr("\r\n电机3\r\n");
    Motor_M3_RunPulse(5000, 1);
    
		USART1_SendStr("\r\n开阀门并吸\r\n");
		Valve_On();
	  Pump_On();
    Delay_ms(300);//进气量
    
		USART1_SendStr("\r\n松气泵\r\n");
    Pump_Off();
    Valve_Off();
    
		USART1_SendStr("\r\n开始转电机3\r\n");
    Motor_M3_RunPulse(5000, 0);
}
//移动机械臂放棋子
void sport2(SCARA_Motion_t result)
{
    if (g_SystemState == SYS_SAFE_STOP) return;
    USART1_SendStr("\r\n===== 执行 sport2 =====\r\n");
    
		USART1_SendStr("\r\n电机1\r\n");
    Motor_M1_Rotate(result.dq1_rel_deg);
    
		USART1_SendStr("\r\n电机2\r\n");
    Motor_M2_Rotate(result.dq2_rel_deg);
    
		Delay_ms(800);
    
		USART1_SendStr("\r\n开始转电机3\r\n");
    Motor_M3_RunPulse(5000, 1);
    Delay_ms(600);
		USART1_SendStr("\r\n开阀门\r\n");
    Valve_On();
 	 //  Delay_ms(6000);//放气时间
	   //Valve_Off();

    Motor_M3_RunPulse(5000, 0);
	 //  Delay_ms(6000);
}
//机械臂移动
void sport3(SCARA_Motion_t result)
{
    if (g_SystemState == SYS_SAFE_STOP) return;
    USART1_SendStr("\r\n===== 执行 sport3=====\r\n");
    
		USART1_SendStr("\r\n电机1\r\n");
    Motor_M1_Rotate(result.dq1_rel_deg);
    
		USART1_SendStr("\r\n电机2\r\n");
    Motor_M2_Rotate(result.dq2_rel_deg);
    
		Delay_ms(500);
}

// ===================== 执行单步棋子移动 =====================
void Execute_Chess_Move(float start_x, float start_y, float end_x, float end_y, int step_idx, int signal)
{
    if (g_SystemState == SYS_SAFE_STOP) return;

    SCARA_Params_t my_robot = {220.0f, 220.0f, 136.0f, -100.0f};
    SCARA_Point_t  p_start  = {start_x, start_y};
    SCARA_Point_t  p_end    = {end_x,   end_y};
    SCARA_Motion_t result;

    uint8_t err = SCARA_Calc_Movement(p_start, p_end, my_robot, &result);

    if (err == 0)
    {
        USART1_SendStr("q1: ");
        USART1_SendFloat(result.dq1_rel_deg);
        USART1_SendStr(" | q2: ");
        USART1_SendFloat(result.dq2_rel_deg);
        USART1_SendStr("\r\n");
        Delay_ms(300);

        if (signal == 0)
        {
            if      (step_idx == 0) sport1(result);
            else if (step_idx == 1) sport2(result);
            else                    sport3(result);
        }
        else
        {
            if      (step_idx == 0 || step_idx == 2) sport1(result);
            else if (step_idx == 1 || step_idx == 3) sport2(result);
            else                                      sport3(result);
        }
    }
    else
    {
        USART1_SendStr("\r\nIK 计算错误\r\n");
        g_SystemState = SYS_IK_ERROR;
        System_SafeStop();
    }
}

// ===================== 主函数 =====================
int main(void)
{
    SystemInit();

    ESP8266_Init();
	
    Pump_Valve_PWM_Init();
	
    Motor_InitAll();

    g_SystemState = SYS_IDLE;
    USART1_SendStr("\r\n系统初始化完成，状态：空闲，等待指令...\r\n");

    while (1)
    {
        ESP8266_Task();

        if (g_SystemState == SYS_SAFE_STOP)
        {
            Delay_ms(100);
            continue;
        }

        if (g_RobotCmd.is_new_cmd == 1)
        {
            g_RobotCmd.is_new_cmd = 0;

            // ===================== Homing 分支（sig=99）=====================
	if (g_RobotCmd.signal == 99)
	{
			g_SystemState = SYS_HOMING;

			float m1_angle = (float)g_RobotCmd.startX;  // 上位机直接发的M1转动角度
			float m2_angle = (float)g_RobotCmd.startY;  // 上位机直接发的M2转动角度

			USART1_SendStr("\r\n===== HOMING =====\r\n");
			USART1_SendStr("M1 角度: ");
			USART1_SendFloat(m1_angle);
			USART1_SendStr("\r\nM2 角度: ");
			USART1_SendFloat(m2_angle);
			USART1_SendStr("\r\n");

			Motor_M1_Rotate(m1_angle);
			Motor_M2_Rotate(m2_angle);

			USART1_SendStr("HOMING 完成\r\n");
			g_SystemState = SYS_FINISH;
			ESP8266_Send_CommandResult(99, 1);
			g_SystemState = SYS_IDLE;
			continue;
		}

            // ===================== 正常运动指令 =====================
            g_SystemState = SYS_RUNNING;
            USART1_SendStr("\r\n收到新指令，开始执行...状态：运行中\r\n");
            Delay_ms(500);

            float pos0[2][4] = {
                {356.0f, g_RobotCmd.startX, g_RobotCmd.endX, 356.0f},
                {120.0f, g_RobotCmd.startY, g_RobotCmd.endY, 120.0f}
            };
            float pos1[2][6] = {
                {356.0f, g_RobotCmd.endX, 356.0f, g_RobotCmd.startX, g_RobotCmd.endX, 356.0f},
                {120.0f, g_RobotCmd.endY, 200.0f, g_RobotCmd.startY, g_RobotCmd.endY, 120.0f}
            };

            if (g_RobotCmd.signal == 0)
            {
                for (int i = 0; i < 3; i++)
                {
                    Execute_Chess_Move(pos0[0][i], pos0[1][i],
                                       pos0[0][i+1], pos0[1][i+1], i, 0);
                    if (g_SystemState == SYS_IDLE) break;
                }
            }
            else if (g_RobotCmd.signal == 1)
            {
                for (int i = 0; i < 5; i++)
                {
                    Execute_Chess_Move(pos1[0][i], pos1[1][i],
                                       pos1[0][i+1], pos1[1][i+1], i, 1);
                    if (g_SystemState == SYS_IDLE) break;
                }
            }
            else
            {
                USART1_SendStr("\r\n指令信号错误\r\n");
                g_SystemState = SYS_CMD_ERROR;
                System_SafeStop();
                continue;
            }

            if (g_SystemState == SYS_RUNNING)
            {
                g_SystemState = SYS_FINISH;
                USART1_SendStr("\r\n动作执行完成！状态：完成\r\n");
                ESP8266_Send_StateAndResult(1);
                g_SystemState = SYS_IDLE;
                USART1_SendStr("\r\n状态复位，等待新指令...\r\n");
            }
        }
    }
}



