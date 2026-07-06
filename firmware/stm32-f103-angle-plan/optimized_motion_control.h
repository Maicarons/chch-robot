#ifndef __OPTIMIZED_MOTION_CONTROL_H
#define __OPTIMIZED_MOTION_CONTROL_H

#include "arm_plan_protocol.h"

#define MOTION_OK 1
#define MOTION_FAIL 0

uint8_t MotionControl_RunPlan(const ArmPlan_t *plan);
void MotionControl_SafeStop(void);

#endif
