#ifndef __ARM_PLAN_PROTOCOL_H
#define __ARM_PLAN_PROTOCOL_H

#include "stm32f10x.h"
#include <stdint.h>

#define ARM_PLAN_MAX_STEPS 6
#define ARM_PLAN_RX_MAX_LEN 256

typedef enum {
    ARM_ACTION_PICK = 0,
    ARM_ACTION_DROP = 1,
    ARM_ACTION_DROP_CAPTURE = 2,
    ARM_ACTION_HOME = 3
} ArmPlanAction_t;

typedef struct {
    int32_t m1_centideg;
    int32_t m2_centideg;
    ArmPlanAction_t action;
} ArmPlanStep_t;

typedef struct {
    uint8_t signal;
    uint8_t step_count;
    ArmPlanStep_t steps[ARM_PLAN_MAX_STEPS];
} ArmPlan_t;

uint8_t ArmPlan_Parse(const char *input, ArmPlan_t *out_plan);
const char *ArmPlan_ActionName(ArmPlanAction_t action);

#endif
