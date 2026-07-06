#include "delay.h"

// 静态变量，仅限本文件使用
static uint32_t fac_us = 0;

/**
 * @brief  初始化延时函数
 * @param  sysclk: 系统主频 (如 72)
 */


/**
 * @brief  微秒级延时
 */
void Delay_ms(u16 ms)
{
    u16 i,j;
    for(i=ms;i>0;i--)
        for(j=12000;j>0;j--);
}
