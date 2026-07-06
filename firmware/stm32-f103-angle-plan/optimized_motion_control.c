#include "optimized_motion_control.h"
#include "motor.h"
#include "pump_valve.h"
#include "esp8266.h"

#define M3_TRAVEL_PULSES 1000U
#define PICK_SETTLE_MS 500U
#define DROP_SETTLE_MS 200U
#define BETWEEN_STEP_MS 120U

static float centideg_to_deg(int32_t centideg)
{
    return ((float)centideg) / 100.0f;
}

static void rotate_m1_m2(const ArmPlanStep_t *step)
{
    Motor_M1_Rotate(centideg_to_deg(step->m1_centideg));
    Motor_M2_Rotate(centideg_to_deg(step->m2_centideg));
    Delay_ms(BETWEEN_STEP_MS);
}

static void m3_down(void)
{
    Motor_M3_RunPulse(M3_TRAVEL_PULSES, 1);
}

static void m3_up(void)
{
    Motor_M3_RunPulse(M3_TRAVEL_PULSES, 0);
}

static void pickup_piece(void)
{
    m3_down();
    Pump_On();
    Valve_On();
    Delay_ms(PICK_SETTLE_MS);
    m3_up();
}

static void drop_piece(void)
{
    m3_down();
    Pump_Off();
    Valve_Off();
    Delay_ms(DROP_SETTLE_MS);
    m3_up();
}

void MotionControl_SafeStop(void)
{
    Motor_StopAll();
    Pump_Off();
    Valve_Off();
}

uint8_t MotionControl_RunPlan(const ArmPlan_t *plan)
{
    uint8_t i;

    if (plan == 0 || plan->step_count == 0 || plan->step_count > ARM_PLAN_MAX_STEPS) {
        MotionControl_SafeStop();
        return MOTION_FAIL;
    }

    for (i = 0; i < plan->step_count; i++) {
        const ArmPlanStep_t *step = &plan->steps[i];

        rotate_m1_m2(step);

        switch (step->action) {
        case ARM_ACTION_PICK:
            pickup_piece();
            break;

        case ARM_ACTION_DROP:
        case ARM_ACTION_DROP_CAPTURE:
            drop_piece();
            break;

        case ARM_ACTION_HOME:
            Pump_Off();
            Valve_Off();
            break;

        default:
            MotionControl_SafeStop();
            return MOTION_FAIL;
        }
    }

    Pump_Off();
    Valve_Off();
    return MOTION_OK;
}
