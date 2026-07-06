#ifndef __IK_H
#define __IK_H

#include <stdint.h>

// 笛卡尔坐标点结构体 (单位：毫米)
typedef struct {
    float x;
    float y;
} SCARA_Point_t;

// 机械臂物理参数结构体 (单位：毫米)
typedef struct {
    float L1;  // 大臂长度
    float L2;  // 小臂长度
    float base_x; // 基点在世界坐标系的X (160)
    float base_y; // 基点在世界坐标系的Y (-40)
} SCARA_Params_t;

// 关节运动数据结构体
typedef struct {
    float q1_abs;      // 目标点大臂绝对弧度
    float q2_abs;      // 目标点小臂绝对弧度
    float dq1_rel_deg; // 大臂需要转动的相对角度 (正:逆时针, 负:顺时针)
    float dq2_rel_deg; // 小臂需要转动的相对角度 (正:逆时针, 负:顺时针)
} SCARA_Motion_t;

/**
 * @brief 计算从世界坐标A到世界坐标B的机械臂关节运动增量
 * @retval 0: 成功, 1: 目标点超出工作空间, 2: 当前点超出工作空间
 */
uint8_t SCARA_Calc_Movement(SCARA_Point_t p_current_world, SCARA_Point_t p_target_world, 
                            SCARA_Params_t params, SCARA_Motion_t *motion);

#endif
