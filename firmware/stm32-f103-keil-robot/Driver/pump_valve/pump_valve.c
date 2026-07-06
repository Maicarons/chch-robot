#include "pump_valve.h"

/************************ TIM2 PWM Initialize ************************/
void Pump_Valve_PWM_Init(void)
{
    // Enable GPIOA and TIM2 clock
    RCC->APB2ENR |= RCC_APB2ENR_IOPAEN;
    RCC->APB1ENR |= RCC_APB1ENR_TIM2EN;

    // PA0 -> TIM2_CH1, Alternate function push-pull
    PUMP_GPIO->CRL &= ~(0x0FU << (PUMP_PIN * 4));
    PUMP_GPIO->CRL |= 0x0B << (PUMP_PIN * 4);

    // PA1 -> TIM2_CH2, Alternate function push-pull
    VALVE_GPIO->CRL &= ~(0x0FU << (VALVE_PIN * 4));
    VALVE_GPIO->CRL |= 0x0B << (VALVE_PIN * 4);

    // TIM2: 72MHz / 72 = 1MHz (1us per count)
    PUMP_TIM->PSC = 71;
    PUMP_TIM->ARR = 19999;    // 20ms period (50Hz)

    // CH1 PWM Mode 1
    PUMP_TIM->CCMR1 &= ~TIM_CCMR1_OC1M;
    PUMP_TIM->CCMR1 |= 0x6 << 4;
    PUMP_TIM->CCMR1 |= TIM_CCMR1_OC1PE;
    PUMP_TIM->CCER |= TIM_CCER_CC1E;
    PUMP_TIM->CCR1 = PUMP_OFF_US;

    // CH2 PWM Mode 1
    PUMP_TIM->CCMR1 &= ~TIM_CCMR1_OC2M;
    PUMP_TIM->CCMR1 |= 0x6 << 12;
    PUMP_TIM->CCMR1 |= TIM_CCMR1_OC2PE;
    PUMP_TIM->CCER |= TIM_CCER_CC2E;
    PUMP_TIM->CCR2 = VALVE_OFF_US;

    // Enable TIM2
    PUMP_TIM->CR1 |= TIM_CR1_CEN;
}

/************************ PUMP Control ************************/
void Pump_On(void)
{
    PUMP_TIM->CCR1 = PUMP_ON_US;
}

void Pump_Off(void)
{
    PUMP_TIM->CCR1 = PUMP_OFF_US;
}

/************************ VALVE Control ************************/
void Valve_On(void)
{
    VALVE_TIM->CCR2 = VALVE_ON_US;
}

void Valve_Off(void)
{
    VALVE_TIM->CCR2 = VALVE_OFF_US;
}

