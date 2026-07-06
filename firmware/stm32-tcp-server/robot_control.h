/**
 * robot_control.h - 机械臂控制头文件
 */

#ifndef __ROBOT_CONTROL_H
#define __ROBOT_CONTROL_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>

/* 返回码定义 */
typedef enum {
    ROBOT_OK = 0,
    ROBOT_ERROR_PARAM = 1,
    ROBOT_ERROR_EXECUTE = 2,
    ROBOT_ERROR_TIMEOUT = 3,
    ROBOT_BUSY = 4
} RobotResult_t;

/* 移动参数结构体 */
typedef struct {
    float from_x;      // 起始X坐标（毫米）
    float from_y;      // 起始Y坐标（毫米）
    float to_x;        // 目标X坐标（毫米）
    float to_y;        // 目标Y坐标（毫米）
    float z_height;    // Z轴高度（毫米）
    uint8_t is_capture; // 是否吃子 (0=否, 1=是)
    char piece_char;   // 棋子字符
} RobotMoveParams_t;

/**
 * @brief  初始化机械臂
 * @retval RobotResult_t
 */
RobotResult_t Robot_Init(void);

/**
 * @brief  移动棋子
 * @param  piece_char: 棋子字符 ('R'/'r', 'N'/'n'等)
 * @param  from_x: 起始X坐标（毫米）
 * @param  from_y: 起始Y坐标（毫米）
 * @param  to_x: 目标X坐标（毫米）
 * @param  to_y: 目标Y坐标（毫米）
 * @param  is_capture: 是否吃子
 * @param  z_height: Z轴高度，0表示使用默认值
 * @retval RobotResult_t
 */
RobotResult_t Robot_MovePiece(char piece_char, 
                              float from_x, float from_y,
                              float to_x, float to_y,
                              uint8_t is_capture,
                              float z_height);

/**
 * @brief  回到home点
 * @retval RobotResult_t
 */
RobotResult_t Robot_GoHome(void);

/**
 * @brief  执行测试序列
 * @retval RobotResult_t
 */
RobotResult_t Robot_TestSequence(void);

/**
 * @brief  急停
 * @retval None
 */
void Robot_EmergencyStop(void);

/**
 * @brief  获取机械臂状态
 * @retval 1=空闲, 0=忙碌, -1=错误
 */
int Robot_GetStatus(void);

#ifdef __cplusplus
}
#endif

#endif /* __ROBOT_CONTROL_H */
