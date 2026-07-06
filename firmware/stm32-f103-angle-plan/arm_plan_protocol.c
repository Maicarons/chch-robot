#include "arm_plan_protocol.h"
#include <stdlib.h>
#include <string.h>

static uint8_t parse_action(const char *text, ArmPlanAction_t *action)
{
    if (strcmp(text, "PICK") == 0) {
        *action = ARM_ACTION_PICK;
        return 0;
    }
    if (strcmp(text, "DROP") == 0) {
        *action = ARM_ACTION_DROP;
        return 0;
    }
    if (strcmp(text, "DROP_CAPTURE") == 0) {
        *action = ARM_ACTION_DROP_CAPTURE;
        return 0;
    }
    if (strcmp(text, "HOME") == 0) {
        *action = ARM_ACTION_HOME;
        return 0;
    }
    return 1;
}

static uint8_t parse_step(char *token, ArmPlanStep_t *step)
{
    char *m1_text = token;
    char *m2_text = strchr(m1_text, ',');
    char *action_text;
    char *endptr;

    if (m2_text == 0) return 1;
    *m2_text++ = '\0';

    action_text = strchr(m2_text, ',');
    if (action_text == 0) return 1;
    *action_text++ = '\0';

    step->m1_centideg = strtol(m1_text, &endptr, 10);
    if (*endptr != '\0') return 1;

    step->m2_centideg = strtol(m2_text, &endptr, 10);
    if (*endptr != '\0') return 1;

    return parse_action(action_text, &step->action);
}

uint8_t ArmPlan_Parse(const char *input, ArmPlan_t *out_plan)
{
    char buffer[ARM_PLAN_RX_MAX_LEN];
    char *token;
    char *endptr;
    uint8_t i;
    long value;

    if (input == 0 || out_plan == 0) return 1;
    if (strlen(input) >= ARM_PLAN_RX_MAX_LEN) return 1;

    memset(out_plan, 0, sizeof(*out_plan));
    strcpy(buffer, input);

    token = strtok(buffer, ";\r\n");
    if (token == 0 || strcmp(token, "PLAN") != 0) return 1;

    token = strtok(0, ";\r\n");
    if (token == 0) return 1;
    value = strtol(token, &endptr, 10);
    if (*endptr != '\0' || value < 0 || value > 1) return 1;
    out_plan->signal = (uint8_t)value;

    token = strtok(0, ";\r\n");
    if (token == 0) return 1;
    value = strtol(token, &endptr, 10);
    if (*endptr != '\0' || value <= 0 || value > ARM_PLAN_MAX_STEPS) return 1;
    out_plan->step_count = (uint8_t)value;

    for (i = 0; i < out_plan->step_count; i++) {
        token = strtok(0, ";\r\n");
        if (token == 0) return 1;
        if (parse_step(token, &out_plan->steps[i]) != 0) return 1;
    }

    return 0;
}

const char *ArmPlan_ActionName(ArmPlanAction_t action)
{
    switch (action) {
    case ARM_ACTION_PICK:
        return "PICK";
    case ARM_ACTION_DROP:
        return "DROP";
    case ARM_ACTION_DROP_CAPTURE:
        return "DROP_CAPTURE";
    case ARM_ACTION_HOME:
        return "HOME";
    default:
        return "UNKNOWN";
    }
}
