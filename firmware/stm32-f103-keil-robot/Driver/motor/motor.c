#include "motor.h"
#include <math.h>
#include <stdint.h>

/************************ 电机独立参数配置 ************************/

#define STEP_ANGLE              1.8f
#define MOTOR_FULL_STEPS_REV    (360.0f / STEP_ANGLE)

/************************ M1 大臂电机 ************************/

#define M1_SUBDIVIDE            16.0f
#define M1_REDUCTION_RATIO      1.9365f
//1.9365f

/************************ M2 小臂电机 ************************/

#define M2_SUBDIVIDE            16.0f
#define M2_REDUCTION_RATIO      1.6161f
//1.6161f  1.71
/************************ M3 Z轴电机 ************************/

#define M3_SUBDIVIDE            8.0f
#define M3_REDUCTION_RATIO      1.0f

/************************ 每度对应脉冲数 ************************/

#define PULSE_PER_DEG_M1        (MOTOR_FULL_STEPS_REV * M1_SUBDIVIDE * M1_REDUCTION_RATIO / 360.0f)
#define PULSE_PER_DEG_M2        (MOTOR_FULL_STEPS_REV * M2_SUBDIVIDE * M2_REDUCTION_RATIO / 360.0f)
#define PULSE_PER_DEG_M3        (MOTOR_FULL_STEPS_REV * M3_SUBDIVIDE * M3_REDUCTION_RATIO / 360.0f)

/************************ M1/M2 梯形速度参数（TIM3） ************************/

#define MOTOR_SPEED_PSC         71

#define MOTOR_ARR_START         4999   //4999
#define MOTOR_ARR_RUN           1999    //1999
#define MOTOR_ACCEL_PULSES      80

/************************ M3 独立梯形速度参数（TIM1） ************************/
/* ARR 越小速度越快，建议从 999 开始，确认不丢步后再继续降低             */
/* 72MHz / (PSC+1=72) / (ARR_RUN+1) = 脉冲频率                          */
/*   ARR_RUN = 1999 → ~500  Hz  (原速度)                                 */
/*   ARR_RUN =  999 → ~1000 Hz  (2x)                                     */
/*   ARR_RUN =  499 → ~2000 Hz  (4x)                                     */
/*   ARR_RUN =  249 → ~4000 Hz  (8x)                                     */

#define M3_ARR_START            1999        /* 启动/停止时的 ARR（慢速） */
#define M3_ARR_RUN              499         /* 匀速运行时的 ARR（快速）,改小就快*/
#define M3_ACCEL_PULSES         40          /* 加减速段脉冲数 */

/************************ 方向引脚定义 ************************/

#define M1_DIR_PIN              (1U << 10)
#define M2_DIR_PIN              (1U << 11)
#define M3_DIR_PIN              (1U << 12)

/************************ 脉冲小数补偿 ************************/

static float m1_pulse_remain = 0.0f;
static float m2_pulse_remain = 0.0f;
static float m3_pulse_remain = 0.0f;

/************************ 内部工具函数 ************************/

static int32_t Motor_Round_To_Int(float x)
{
    if (x >= 0.0f) {
        return (int32_t)(x + 0.5f);
    } else {
        return (int32_t)(x - 0.5f);
    }
}

static uint32_t Motor_Abs_Int32(int32_t x)
{
    return (x >= 0) ? (uint32_t)x : (uint32_t)(-x);
}

static int32_t Motor_Angle_To_Pulse_With_Remain(float angle,
                                                float pulse_per_deg,
                                                float *remain)
{
    float pulse_float;
    int32_t pulse_int;

    pulse_float = angle * pulse_per_deg + (*remain);
    pulse_int = Motor_Round_To_Int(pulse_float);

    *remain = pulse_float - (float)pulse_int;

    return pulse_int;
}

/************************ M1/M2 梯形速度 ARR 计算（TIM3） ************************/

static uint16_t Motor_Calc_Trapezoid_ARR(uint32_t step_idx, uint32_t total_steps)
{
    uint32_t accel_steps;
    uint32_t decel_start;
    uint32_t denom;
    int32_t arr_range;
    uint32_t arr;

    if (total_steps <= 1) {
        return MOTOR_ARR_START;
    }

    accel_steps = MOTOR_ACCEL_PULSES;

    if (accel_steps * 2 > total_steps) {
        accel_steps = total_steps / 2;
    }

    if (accel_steps == 0) {
        return MOTOR_ARR_START;
    }

    if (accel_steps <= 1) {
        denom = 1;
    } else {
        denom = accel_steps - 1;
    }

    decel_start = total_steps - accel_steps;
    arr_range = (int32_t)MOTOR_ARR_START - (int32_t)MOTOR_ARR_RUN;

    if (step_idx < accel_steps) {
        arr = MOTOR_ARR_START -
              (uint32_t)((arr_range * step_idx) / denom);
    }
    else if (step_idx >= decel_start) {
        uint32_t decel_idx;

        decel_idx = step_idx - decel_start;

        arr = MOTOR_ARR_RUN +
              (uint32_t)((arr_range * decel_idx) / denom);
    }
    else {
        arr = MOTOR_ARR_RUN;
    }

    if (arr < MOTOR_ARR_RUN) {
        arr = MOTOR_ARR_RUN;
    }

    if (arr > MOTOR_ARR_START) {
        arr = MOTOR_ARR_START;
    }

    return (uint16_t)arr;
}

/************************ M3 独立梯形速度 ARR 计算（TIM1） ************************/

static uint16_t Motor_Calc_Trapezoid_ARR_M3(uint32_t step_idx, uint32_t total_steps)
{
    uint32_t accel_steps;
    uint32_t decel_start;
    uint32_t denom;
    int32_t arr_range;
    uint32_t arr;

    if (total_steps <= 1) {
        return M3_ARR_START;
    }

    accel_steps = M3_ACCEL_PULSES;

    if (accel_steps * 2 > total_steps) {
        accel_steps = total_steps / 2;
    }

    if (accel_steps == 0) {
        return M3_ARR_START;
    }

    if (accel_steps <= 1) {
        denom = 1;
    } else {
        denom = accel_steps - 1;
    }

    decel_start = total_steps - accel_steps;
    arr_range = (int32_t)M3_ARR_START - (int32_t)M3_ARR_RUN;

    if (step_idx < accel_steps) {
        arr = M3_ARR_START -
              (uint32_t)((arr_range * step_idx) / denom);
    }
    else if (step_idx >= decel_start) {
        uint32_t decel_idx;

        decel_idx = step_idx - decel_start;

        arr = M3_ARR_RUN +
              (uint32_t)((arr_range * decel_idx) / denom);
    }
    else {
        arr = M3_ARR_RUN;
    }

    if (arr < M3_ARR_RUN) {
        arr = M3_ARR_RUN;
    }

    if (arr > M3_ARR_START) {
        arr = M3_ARR_START;
    }

    return (uint16_t)arr;
}

/************************ GPIO 初始化 ************************/

void Motor_GPIO_Init(void)
{
    RCC->APB2ENR |= (1U << 2) | (1U << 3);

    GPIOA->CRL &= ~(0xFFU << 24);
    GPIOA->CRL |=  (0xBBU << 24);

    GPIOA->CRH &= ~(0x0FU << 0);
    GPIOA->CRH |=  (0x0BU << 0);

    GPIOB->CRH &= ~(0xFFFFU << 8);
    GPIOB->CRH |=  (0x3333U << 8);

    GPIOB->BRR = M1_DIR_PIN | M2_DIR_PIN | M3_DIR_PIN;
}

/************************ 定时器 PWM 初始化 ************************/

void Motor_TIM_PWM_Init(void)
{
    RCC->APB1ENR |= RCC_APB1ENR_TIM3EN;
    RCC->APB2ENR |= RCC_APB2ENR_TIM1EN;

    /* TIM3：M1 / M2 */
    TIM3->PSC = MOTOR_SPEED_PSC;
    TIM3->ARR = MOTOR_ARR_START;

    TIM3->CCMR1 = 0x6060;

    TIM3->CCR1 = 0;
    TIM3->CCR2 = 0;

    TIM3->CCER &= ~(TIM_CCER_CC1E | TIM_CCER_CC2E);

    TIM3->SR &= ~TIM_SR_UIF;
    TIM3->CNT = 0;

    TIM3->CR1 |= TIM_CR1_CEN;

    /* TIM1：M3，使用 M3 独立起始 ARR */
    TIM1->PSC = MOTOR_SPEED_PSC;
    TIM1->ARR = M3_ARR_START;           /* ← 改为 M3 独立参数 */

    TIM1->CCMR1 = 0x0060;

    TIM1->CCR1 = 0;

    TIM1->CCER &= ~TIM_CCER_CC1E;

    TIM1->BDTR |= TIM_BDTR_MOE;

    TIM1->SR &= ~TIM_SR_UIF;
    TIM1->CNT = 0;

    TIM1->CR1 |= TIM_CR1_CEN;
}

/************************ 电机整体初始化 ************************/

void Motor_InitAll(void)
{
    Motor_GPIO_Init();
    Motor_TIM_PWM_Init();

    m1_pulse_remain = 0.0f;
    m2_pulse_remain = 0.0f;
    m3_pulse_remain = 0.0f;
	
	
	
	
	
}

/************************ 清除累计小数补偿 ************************/

void Motor_ClearPulseRemain(void)
{
    m1_pulse_remain = 0.0f;
    m2_pulse_remain = 0.0f;
    m3_pulse_remain = 0.0f;
}

/************************ 紧急停止所有电机 ************************/

void Motor_StopAll(void)
{
    TIM3->CCER &= ~(TIM_CCER_CC1E | TIM_CCER_CC2E);
    TIM1->CCER &= ~TIM_CCER_CC1E;

    TIM3->CCR1 = 0;
    TIM3->CCR2 = 0;
    TIM1->CCR1 = 0;

    GPIOB->BRR = M1_DIR_PIN | M2_DIR_PIN | M3_DIR_PIN;

    TIM3->SR = 0;
    TIM1->SR = 0;
}

/************************ 底层通用梯形发脉冲函数 ************************/

static void Motor_SendPulse(TIM_TypeDef *TIMx, uint8_t ch, uint32_t cnt)
{
    uint16_t arr_now;

    if (cnt == 0) return;

    if (TIMx == TIM3)
    {
        TIM3->ARR = MOTOR_ARR_START;
        TIM3->CNT = 0;
        TIM3->SR &= ~TIM_SR_UIF;

        if (ch == 1)
        {
            TIM3->CCR1 = TIM3->ARR / 2;
            TIM3->CCER |= TIM_CCER_CC1E;
        }
        else if (ch == 2)
        {
            TIM3->CCR2 = TIM3->ARR / 2;
            TIM3->CCER |= TIM_CCER_CC2E;
        }
        else
        {
            return;
        }

        for (uint32_t i = 0; i < cnt; i++)
        {
            arr_now = Motor_Calc_Trapezoid_ARR(i, cnt);   /* M1/M2 用原参数 */

            TIM3->ARR = arr_now;

            if (ch == 1) {
                TIM3->CCR1 = arr_now / 2;
            } else {
                TIM3->CCR2 = arr_now / 2;
            }

            TIM3->CNT = 0;
            TIM3->SR &= ~TIM_SR_UIF;

            while (!(TIM3->SR & TIM_SR_UIF));

            TIM3->SR &= ~TIM_SR_UIF;

            if (!(TIM3->CR1 & TIM_CR1_CEN)) {
                break;
            }
        }

        if (ch == 1) {
            TIM3->CCER &= ~TIM_CCER_CC1E;
            TIM3->CCR1 = 0;
        }

        if (ch == 2) {
            TIM3->CCER &= ~TIM_CCER_CC2E;
            TIM3->CCR2 = 0;
        }

        TIM3->ARR = MOTOR_ARR_START;
        TIM3->CNT = 0;
        TIM3->SR &= ~TIM_SR_UIF;
    }
    else if (TIMx == TIM1)
    {
        TIM1->ARR = M3_ARR_START;               /* ← 改为 M3 独立参数 */
        TIM1->CCR1 = TIM1->ARR / 2;
        TIM1->CNT = 0;
        TIM1->SR &= ~TIM_SR_UIF;

        TIM1->CCER |= TIM_CCER_CC1E;

        for (uint32_t i = 0; i < cnt; i++)
        {
            arr_now = Motor_Calc_Trapezoid_ARR_M3(i, cnt); /* ← 改为 M3 专属函数 */

            TIM1->ARR = arr_now;
            TIM1->CCR1 = arr_now / 2;

            TIM1->CNT = 0;
            TIM1->SR &= ~TIM_SR_UIF;

            while (!(TIM1->SR & TIM_SR_UIF));

            TIM1->SR &= ~TIM_SR_UIF;

            if (!(TIM1->CR1 & TIM_CR1_CEN)) {
                break;
            }
        }

        TIM1->CCER &= ~TIM_CCER_CC1E;
        TIM1->CCR1 = 0;

        TIM1->ARR = M3_ARR_START;               /* ← 改为 M3 独立参数 */
        TIM1->CNT = 0;
        TIM1->SR &= ~TIM_SR_UIF;
    }
}

/************************ M1 角度控制 ************************/

void Motor_M1_Rotate(float angle)
{
    int32_t pulse;
    uint32_t cnt;

    if (angle == 0.0f) return;

    pulse = Motor_Angle_To_Pulse_With_Remain(angle,
                                             PULSE_PER_DEG_M1,
                                             &m1_pulse_remain);

    cnt = Motor_Abs_Int32(pulse);

    if (cnt == 0) return;

    if (pulse > 0) {
        GPIOB->BSRR = M1_DIR_PIN;
    } else {
        GPIOB->BRR = M1_DIR_PIN;
    }

    Motor_SendPulse(TIM3, 1, cnt);
}

/************************ M2 角度控制 ************************/

void Motor_M2_Rotate(float angle)
{
    int32_t pulse;
    uint32_t cnt;

    if (angle == 0.0f) return;

    pulse = Motor_Angle_To_Pulse_With_Remain(angle,
                                             PULSE_PER_DEG_M2,
                                             &m2_pulse_remain);

    cnt = Motor_Abs_Int32(pulse);

    if (cnt == 0) return;

    if (pulse > 0) {
        GPIOB->BRR = M2_DIR_PIN;
    } else {
        GPIOB->BSRR = M2_DIR_PIN;
    }

    Motor_SendPulse(TIM3, 2, cnt);
}

/************************ M3 脉冲 + 方向控制 ************************/

void Motor_M3_RunPulse(uint32_t pulse, uint8_t dir)
{
    if (pulse == 0) return;

    if (dir) {
        GPIOB->BRR = M3_DIR_PIN;
    } else {
        GPIOB->BSRR = M3_DIR_PIN;
    }

    Motor_SendPulse(TIM1, 1, pulse);
}

/************************ M3 角度转脉冲 ************************/

uint32_t Motor_M3_Angle2Pulse(float angle)
{
    float pulse_float;
    int32_t pulse_int;

    pulse_float = fabsf(angle) * PULSE_PER_DEG_M3 + m3_pulse_remain;

    pulse_int = Motor_Round_To_Int(pulse_float);

    m3_pulse_remain = pulse_float - (float)pulse_int;

    if (pulse_int < 0) {
        pulse_int = -pulse_int;
    }

    return (uint32_t)pulse_int;
}

/************************ 调试接口 ************************/

float Motor_Get_M1_PulsePerDeg(void)
{
    return PULSE_PER_DEG_M1;
}

float Motor_Get_M2_PulsePerDeg(void)
{
    return PULSE_PER_DEG_M2;
}

float Motor_Get_M3_PulsePerDeg(void)
{
    return PULSE_PER_DEG_M3;
}



