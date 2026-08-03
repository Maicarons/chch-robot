"""
日志系统初始化。
"""

import logging

import config


def setup_logging():
    """配置日志系统"""
    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)

    # 创建日志格式
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # 文件处理器（可选）
    handlers = [console_handler]

    if config.SAVE_LOG_TO_FILE:
        try:
            file_handler = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
        except Exception as e:
            print(f"警告：无法创建日志文件 {e}")

    # 配置根日志记录器
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
    )

    logger = logging.getLogger("main")
    logger.info("日志系统已初始化")
