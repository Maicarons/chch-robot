#include "ik.h"
#include <math.h>

#define PI 3.1415926535f
#define RAD_TO_DEG(x) ((x) * 180.0f / PI)
#define LIMIT_CLAMP(val, min, max)  ((val) < (min) ? (min) : ((val) > (max) ? (max) : (val)))

// 内部函数：计算局部坐标下的单点逆解
static uint8_t SCARA_IK_Solve_Single(float x_local, float y_local, SCARA_Params_t params, float *q1_out, float *q2_out)
{
    float L1 = params.L1;
    float L2 = params.L2;
    
    float r_sq = (x_local * x_local) + (y_local * y_local);
    float cos_q2 = (r_sq - (L1 * L1) - (L2 * L2)) / (2.0f * L1 * L2);
    
    uint8_t err = 0;
    if (cos_q2 > 1.0f || cos_q2 < -1.0f) {
        err = 1; 
        cos_q2 = LIMIT_CLAMP(cos_q2, -1.0f, 1.0f);
    }
    
    *q2_out = acosf(cos_q2); 
    float term1 = atan2f(y_local, x_local);
    float term2 = atan2f(L2 * sinf(*q2_out), L1 + L2 * cosf(*q2_out));
    *q1_out = term1 - term2;
    
    return err;
}

uint8_t SCARA_Calc_Movement(SCARA_Point_t p_current_world, SCARA_Point_t p_target_world, 
                            SCARA_Params_t params, SCARA_Motion_t *motion)
{
    float q1_cur, q2_cur, q1_tar, q2_tar;
    uint8_t status = 0;

    // 1. 将世界坐标转换为底座局部坐标
    float cur_x_l = p_current_world.x - params.base_x;
    float cur_y_l = p_current_world.y - params.base_y;
    float tar_x_l = p_target_world.x - params.base_x;
    float tar_y_l = p_target_world.y - params.base_y;

    // 2. 解算当前位置角度
    if (SCARA_IK_Solve_Single(cur_x_l, cur_y_l, params, &q1_cur, &q2_cur) != 0) status |= 0x02;

    // 3. 解算目标位置角度
    if (SCARA_IK_Solve_Single(tar_x_l, tar_y_l, params, &q1_tar, &q2_tar) != 0) status |= 0x01;

    // 4. 填充增量 (弧度差转角度)
    motion->q1_abs = q1_tar;
    motion->q2_abs = q2_tar;
    motion->dq1_rel_deg = RAD_TO_DEG(q1_tar - q1_cur);
    motion->dq2_rel_deg = RAD_TO_DEG(q2_tar - q2_cur);

    return status;
}

