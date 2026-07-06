#ifndef __PUMP_VALVE_H
#define __PUMP_VALVE_H

#include "stm32f10x.h"

// GPIO Configuration
#define PUMP_PIN        0
#define PUMP_GPIO       GPIOA
#define PUMP_TIM        TIM2
#define PUMP_TIM_CH     1

#define VALVE_PIN       1
#define VALVE_GPIO      GPIOA
#define VALVE_TIM       TIM2
#define VALVE_TIM_CH    2

// PWM Pulse Value (50Hz servo: 500~2500us)
#define PUMP_OFF_US     500
#define PUMP_ON_US      2500
#define VALVE_OFF_US    500
#define VALVE_ON_US     2500

// Functions
void Pump_Valve_PWM_Init(void);
void Pump_On(void);
void Pump_Off(void);
void Valve_On(void);
void Valve_Off(void);

#endif