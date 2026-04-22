/**
 * json_parser.c - 轻量级JSON解析器实现
 * 
 * 支持简单的键值对解析，适用于嵌入式系统
 */

#include "json_parser.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <ctype.h>

/* 跳过空白字符 */
static const char* skip_whitespace(const char* str)
{
    while (*str && isspace((unsigned char)*str)) {
        str++;
    }
    return str;
}

/**
 * @brief  提取字符串字段值
 */
int JSON_ExtractString(const char* json, const char* key, char* value, int max_len)
{
    char search_key[64];
    const char* pos;
    const char* start;
    const char* end;
    int len;
    
    /* 构建搜索键: "key": */
    snprintf(search_key, sizeof(search_key), "\"%s\"", key);
    
    /* 查找键 */
    pos = strstr(json, search_key);
    if (!pos) {
        return 0;
    }
    
    /* 移动到值的位置 */
    pos += strlen(search_key);
    pos = skip_whitespace(pos);
    
    /* 跳过冒号 */
    if (*pos != ':') {
        return 0;
    }
    pos++;
    pos = skip_whitespace(pos);
    
    /* 检查是否为字符串 */
    if (*pos != '"') {
        return 0;
    }
    pos++;  // 跳过开始引号
    
    /* 找到结束引号 */
    start = pos;
    end = strchr(pos, '"');
    if (!end) {
        return 0;
    }
    
    /* 复制字符串 */
    len = end - start;
    if (len >= max_len) {
        len = max_len - 1;
    }
    
    strncpy(value, start, len);
    value[len] = '\0';
    
    return 1;
}

/**
 * @brief  提取整数字段值
 */
int JSON_ExtractInt(const char* json, const char* key, int* value)
{
    char search_key[64];
    const char* pos;
    
    snprintf(search_key, sizeof(search_key), "\"%s\"", key);
    
    pos = strstr(json, search_key);
    if (!pos) {
        return 0;
    }
    
    pos += strlen(search_key);
    pos = skip_whitespace(pos);
    
    if (*pos != ':') {
        return 0;
    }
    pos++;
    pos = skip_whitespace(pos);
    
    /* 解析整数 */
    *value = atoi(pos);
    
    return 1;
}

/**
 * @brief  提取浮点数字段值
 */
int JSON_ExtractFloat(const char* json, const char* key, float* value)
{
    char search_key[64];
    const char* pos;
    char num_str[32];
    const char* start;
    int i;
    
    snprintf(search_key, sizeof(search_key), "\"%s\"", key);
    
    pos = strstr(json, search_key);
    if (!pos) {
        return 0;
    }
    
    pos += strlen(search_key);
    pos = skip_whitespace(pos);
    
    if (*pos != ':') {
        return 0;
    }
    pos++;
    pos = skip_whitespace(pos);
    
    /* 提取数字字符串 */
    start = pos;
    for (i = 0; i < 31 && (isdigit((unsigned char)*pos) || *pos == '.' || *pos == '-'); i++, pos++) {
        num_str[i] = *pos;
    }
    num_str[i] = '\0';
    
    /* 解析浮点数 */
    *value = atof(num_str);
    
    return 1;
}

/**
 * @brief  解析JSON指令
 */
JsonResult_t JSON_ParseCommand(const char* json_str, RobotCommand_t* cmd)
{
    char cmd_str[32];
    char piece_str[8];
    int is_capture_int;
    
    if (!json_str || !cmd) {
        return JSON_ERROR_FORMAT;
    }
    
    memset(cmd, 0, sizeof(RobotCommand_t));
    
    /* 提取命令类型 */
    if (!JSON_ExtractString(json_str, "cmd", cmd_str, sizeof(cmd_str))) {
        return JSON_ERROR_FIELD;
    }
    
    /* 判断命令类型 */
    if (strcmp(cmd_str, "MOVE") == 0) {
        cmd->type = CMD_MOVE_PIECE;
        
        /* 提取移动参数 */
        if (!JSON_ExtractString(json_str, "piece", piece_str, sizeof(piece_str))) {
            return JSON_ERROR_FIELD;
        }
        cmd->params.move.piece_char = piece_str[0];
        
        if (!JSON_ExtractFloat(json_str, "from_x", &cmd->params.move.from_x)) {
            return JSON_ERROR_FIELD;
        }
        if (!JSON_ExtractFloat(json_str, "from_y", &cmd->params.move.from_y)) {
            return JSON_ERROR_FIELD;
        }
        if (!JSON_ExtractFloat(json_str, "to_x", &cmd->params.move.to_x)) {
            return JSON_ERROR_FIELD;
        }
        if (!JSON_ExtractFloat(json_str, "to_y", &cmd->params.move.to_y)) {
            return JSON_ERROR_FIELD;
        }
        
        /* is_capture是可选的，默认为0 */
        if (JSON_ExtractInt(json_str, "is_capture", &is_capture_int)) {
            cmd->params.move.is_capture = (uint8_t)is_capture_int;
        } else {
            cmd->params.move.is_capture = 0;
        }
        
        /* z_height是可选的，默认为0 */
        if (!JSON_ExtractFloat(json_str, "z_height", &cmd->params.move.z_height)) {
            cmd->params.move.z_height = 0.0f;
        }
        
    } else if (strcmp(cmd_str, "TEST") == 0) {
        cmd->type = CMD_TEST;
        
    } else if (strcmp(cmd_str, "HOME") == 0) {
        cmd->type = CMD_HOME;
        
    } else if (strcmp(cmd_str, "STOP") == 0) {
        cmd->type = CMD_STOP;
        
    } else if (strcmp(cmd_str, "PING") == 0) {
        cmd->type = CMD_PING;
        
    } else {
        cmd->type = CMD_UNKNOWN;
        return JSON_ERROR_VALUE;
    }
    
    return JSON_OK;
}
