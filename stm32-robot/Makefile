# STM32机械臂TCP服务器 - Makefile示例
# 适用于ARM GCC工具链

# 项目名称
PROJECT = stm32_robot

# 工具链
CC = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE = arm-none-eabi-size

# 编译选项
CFLAGS = -mcpu=cortex-m4
CFLAGS += -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard
CFLAGS += -O2 -g
CFLAGS += -Wall -Wextra
CFLAGS += -ffunction-sections -fdata-sections

# 链接选项
LDFLAGS = -mcpu=cortex-m4
LDFLAGS += -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard
LDFLAGS += -specs=nano.specs -specs=nosys.specs
LDFLAGS += -Wl,--gc-sections

# 包含路径
INCLUDES = -I./Inc
INCLUDES += -I./Drivers/STM32F4xx_HAL_Driver/Inc
INCLUDES += -I./Drivers/CMSIS/Include
INCLUDES += -I./Middlewares/Third_Party/LwIP/src/include

# 源文件
SRCS = main.c
SRCS += robot_tcp_server.c
SRCS += robot_control.c
SRCS += json_parser.c
SRCS += system_stm32f4xx.c
SRCS += startup_stm32f407xx.s

# HAL驱动源文件（根据需要添加）
SRCS += Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal.c
SRCS += Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_gpio.c
SRCS += Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_eth.c
SRCS += Drivers/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_uart.c

# LwIP源文件（如果使用）
# SRCS += Middlewares/Third_Party/LwIP/src/core/tcp.c
# SRCS += Middlewares/Third_Party/LwIP/src/netif/ethernet.c

# 目标文件
OBJS = $(SRCS:.c=.o)
OBJS := $(OBJS:.s=.o)

# 输出文件
ELF = $(PROJECT).elf
HEX = $(PROJECT).hex
BIN = $(PROJECT).bin

# 默认目标
all: $(ELF) $(HEX) $(BIN)
	@echo "Build completed"
	@$(SIZE) $(ELF)

# 链接
$(ELF): $(OBJS)
	$(CC) $(LDFLAGS) -T STM32F407VGTx_FLASH.ld $(OBJS) -lm -o $@

# 编译C文件
%.o: %.c
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

# 编译汇编文件
%.o: %.s
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

# 生成HEX文件
$(HEX): $(ELF)
	$(OBJCOPY) -O ihex $< $@

# 生成BIN文件
$(BIN): $(ELF)
	$(OBJCOPY) -O binary -S $< $@

# 清理
clean:
	rm -f $(OBJS) $(ELF) $(HEX) $(BIN)

# 烧录（使用ST-Link）
flash: $(BIN)
	st-flash write $(BIN) 0x8000000

# 调试（使用OpenOCD）
debug: $(ELF)
	openocd -f interface/stlink-v2.cfg -f target/stm32f4x.cfg -c "program $(ELF) verify reset exit"

.PHONY: all clean flash debug
