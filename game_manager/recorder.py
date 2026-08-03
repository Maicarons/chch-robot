"""
棋谱（对局记录）持久化。

将对局过程写入本地文本文件，便于赛后复盘。与 :class:`game_manager.manager.GameManager`
解耦，便于替换为数据库或云端存储。
"""

import datetime
import logging

import config

logger = logging.getLogger(__name__)


def save_game_record(manager) -> str:
    """
    保存游戏记录（棋谱）。

    Args:
        manager: :class:`game_manager.manager.GameManager` 实例，提供
            ``move_history``、``player_color``、``current_fen`` 等属性。

    Returns:
        写入的文件名；失败时返回空字符串。
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"game_record_{timestamp}.txt"

    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("中国象棋人机对弈记录\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"时间：{datetime.datetime.now()}\n")
            f.write(f"玩家颜色：{manager.player_color}\n")
            f.write(f"初始 FEN: {config.FEN_START_POSITION}\n\n")
            f.write("走法记录:\n")

            for i, move in enumerate(manager.move_history):
                if i % 2 == 0:
                    f.write(f"{i // 2 + 1}. ")
                f.write(f"{move} ")

                if i % 2 == 1:
                    f.write("\n")

            f.write(f"\n最终 FEN: {manager.current_fen}\n")

        logger.info(f"游戏记录已保存到：{filename}")
        print(f"\n游戏记录已保存到：{filename}")
        return filename

    except Exception as e:
        logger.error(f"保存游戏记录失败：{e}")
        return ""
