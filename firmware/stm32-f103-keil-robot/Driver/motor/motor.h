#ifndef __MOTOR_H
#define __MOTOR_H

#ifdef __cplusplus
extern "C" {
#endif

#include "stm32f10x.h"
#include <stdint.h>

void Motor_GPIO_Init(void);
void Motor_TIM_PWM_Init(void);
void Motor_InitAll(void);

void Motor_StopAll(void);
void Motor_ClearPulseRemain(void);

void Motor_M1_Rotate(float angle);
void Motor_M2_Rotate(float angle);

void Motor_M3_RunPulse(uint32_t pulse, uint8_t dir);
uint32_t Motor_M3_Angle2Pulse(float angle);

float Motor_Get_M1_PulsePerDeg(void);
float Motor_Get_M2_PulsePerDeg(void);
float Motor_Get_M3_PulsePerDeg(void);

#ifdef __cplusplus
}
#endif

#endif
