/**
 * json_parser.h - 轻量级JSON解析器头文件
 * 
 * 专为STM32设计，避免使用动态内存分配
 */

#ifndef __JSON_PARSER_H
#define __JSON_PARSER_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>

/* 指令类型枚举 */
typedef enum {
    CMD_MOVE_PIECE = 0,
    CMD_TEST = 1,
    CMD_HOME = 2,
    CMD_STOP = 3,
    CMD_PING = 4,
    CMD_UNKNOWN = 255
} CommandType_t;

/* 移动参数结构体 */
typedef struct {
    char piece_char;
    float from_x;
    float from_y;
    float to_x;
    float to_y;
    uint8_t is_capture;
    float z_height;
} MoveParams_t;

/* 完整指令结构体 */
typedef struct {
    CommandType_t type;
    union {
        MoveParams_t move;
    } params;
} RobotCommand_t;

/* 返回码 */
typedef enum {
    JSON_OK = 0,
    JSON_ERROR_FORMAT = 1,
    JSON_ERROR_FIELD = 2,
    JSON_ERROR_VALUE = 3
} JsonResult_t;

/**
 * @brief  解析JSON指令
 * @param  json_str: JSON字符串
 * @param  cmd: 输出指令结构体
 * @retval JsonResult_t
 */
JsonResult_t JSON_ParseCommand(const char* json_str, RobotCommand_t* cmd);

/**
 * @brief  提取字符串字段值
 * @param  json: JSON字符串
 * @param  key: 键名
 * @param  value: 输出缓冲区
 * @param  max_len: 缓冲区最大长度
 * @retval 1=成功, 0=失败
 */
int JSON_ExtractString(const char* json, const char* key, char* value, int max_len);

/**
 * @brief  提取整数字段值
 * @param  json: JSON字符串
 * @param  key: 键名
 * @param  value: 输出值
 * @retval 1=成功, 0=失败
 */
int JSON_ExtractInt(const char* json, const char* key, int* value);

/**
 * @brief  提取浮点数字段值
 * @param  json: JSON字符串
 * @param  key: 键名
 * @param  value: 输出值
 * @retval 1=成功, 0=失败
 */
int JSON_ExtractFloat(const char* json, const char* key, float* value);

#ifdef __cplusplus
}
#endif

#endif /* __JSON_PARSER_H */
