"""
Interactive startup parameter overrides for the web simulation.

These are only used when the backend is launched from the command line and a
TTY is attached. They mutate the project ``config`` module directly so the
rest of the runtime picks up the operator's choices. The parsing primitives
themselves live in :mod:`web_simulation.domain` (single source of truth).
"""

import logging
import os
import sys

import config
from web_simulation import domain as web_domain

logger = logging.getLogger(__name__)

# Re-export the canonical parsers so the app module and callers can import them
# from a single place.
parse_positive_int_parameter = web_domain.parse_positive_int_parameter
parse_robot_ip_parameter = web_domain.parse_robot_ip_parameter


def prompt_positive_int_parameter(label, current_value):
    while True:
        raw_value = input(f"{label} [{current_value}]: ")
        try:
            return web_domain.parse_positive_int_parameter(raw_value, current_value, label)
        except ValueError as exc:
            print(f"  输入无效: {exc}")


def prompt_robot_ip_parameter(current_host):
    while True:
        raw_value = input(f"下位机 IP，输入完整地址或最后一段 [{current_host}]: ")
        try:
            return web_domain.parse_robot_ip_parameter(raw_value, current_host)
        except ValueError as exc:
            print(f"  输入无效: {exc}")


def prompt_startup_parameter_overrides():
    if os.environ.get("CHRO_SKIP_STARTUP_PROMPT", "").lower() in {"1", "true", "yes", "y"}:
        return
    if not getattr(sys, "stdin", None) or not sys.stdin.isatty():
        return

    print()
    print("=" * 60)
    print("启动参数")
    print("=" * 60)
    print(f"棋盘横向格距: {getattr(config, 'ROBOT_COMMAND_FILE_SPACING_MM', 34)} mm")
    print(f"棋盘纵向格距: {getattr(config, 'ROBOT_COMMAND_RANK_SPACING_MM', 30)} mm")
    print(f"楚河汉界纵向长: {getattr(config, 'ROBOT_COMMAND_RIVER_SPACING_MM', 32)} mm")
    print(f"下位机 IP: {getattr(config, 'ROBOT_NETWORK_HOST', '192.168.0.102')}")
    print("=" * 60)

    try:
        choice = input("启动前是否更改这些参数？[y/N]: ").strip().lower()
    except EOFError:
        return
    if choice not in {"y", "yes", "是"}:
        print("沿用当前启动参数。")
        return

    try:
        config.ROBOT_COMMAND_FILE_SPACING_MM = prompt_positive_int_parameter(
            "棋盘横向格距 mm",
            getattr(config, "ROBOT_COMMAND_FILE_SPACING_MM", 34),
        )
        config.ROBOT_COMMAND_RANK_SPACING_MM = prompt_positive_int_parameter(
            "棋盘纵向格距 mm",
            getattr(config, "ROBOT_COMMAND_RANK_SPACING_MM", 30),
        )
        config.ROBOT_COMMAND_RIVER_SPACING_MM = prompt_positive_int_parameter(
            "楚河汉界纵向长 mm",
            getattr(config, "ROBOT_COMMAND_RIVER_SPACING_MM", 32),
        )
        config.ROBOT_NETWORK_HOST = prompt_robot_ip_parameter(
            getattr(config, "ROBOT_NETWORK_HOST", "192.168.0.102")
        )
    except KeyboardInterrupt:
        print()
        print("已取消参数修改，沿用当前值。")
        return

    from web_simulation.services import close_robot_tcp_client

    close_robot_tcp_client()
    print("=" * 60)
    print("本次运行参数:")
    print(
        f"棋盘尺寸: 横向={config.ROBOT_COMMAND_FILE_SPACING_MM} mm, "
        f"纵向={config.ROBOT_COMMAND_RANK_SPACING_MM} mm, "
        f"楚河汉界={config.ROBOT_COMMAND_RIVER_SPACING_MM} mm"
    )
    print(f"下位机目标: {config.ROBOT_NETWORK_HOST}:{getattr(config, 'ROBOT_NETWORK_PORT', 8086)}")
    print("=" * 60)
