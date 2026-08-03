"""
命令行入口相关模块。

将原先集中在 ``main.py`` 中的职责拆分为：

- :mod:`cli.logging_setup` —— 日志系统初始化
- :mod:`cli.interactive_shell` —— 交互式命令行外壳与欢迎横幅

``main.py`` 仅保留参数解析、自定义配置加载与命令分发，作为薄入口。
"""
