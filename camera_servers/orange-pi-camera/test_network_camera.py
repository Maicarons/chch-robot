"""
网络摄像头测试脚本 - Windows主机端
测试从香橙派接收图像并显示
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision import BoardRecognizer
import cv2
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TestNetworkCamera")


def test_network_camera():
    """测试网络摄像头连接和图像捕获"""
    
    print("=" * 60)
    print("网络摄像头测试")
    print("=" * 60)
    print("\n请确保:")
    print("1. 香橙派已启动摄像头服务器")
    print("2. config.py中USE_NETWORK_CAMERA=True")
    print("3. NETWORK_CAMERA_URL设置正确")
    print("\n按任意键开始测试，ESC退出\n")
    
    input("按Enter开始...")
    
    try:
        # 创建识别器（使用网络摄像头）
        recognizer = BoardRecognizer(use_network=True)
        
        if not recognizer.start():
            print("❌ 网络摄像头启动失败")
            return False
        
        print("✅ 网络摄像头已连接")
        print("\n正在捕获图像...")
        print("按ESC键退出\n")
        
        while True:
            # 捕获帧
            frame = recognizer.camera_manager.capture_frame()
            
            if frame is not None:
                # 显示图像
                cv2.imshow('Network Camera Test', frame)
                
                # 检查按键
                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC
                    break
            else:
                print("⚠️  无法获取图像，等待重连...")
                import time
                time.sleep(1)
        
        recognizer.stop()
        cv2.destroyAllWindows()
        
        print("\n✅ 测试完成")
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        print(f"\n❌ 测试失败: {e}")
        return False


def test_board_recognition():
    """测试棋盘识别功能"""
    
    print("\n" + "=" * 60)
    print("棋盘识别测试")
    print("=" * 60)
    
    try:
        recognizer = BoardRecognizer(use_network=True)
        
        if not recognizer.start():
            print("❌ 网络摄像头启动失败")
            return False
        
        print("✅ 网络摄像头已连接")
        print("\n按任意键进行识别，ESC退出\n")
        
        while True:
            print("正在识别棋盘...")
            board_state = recognizer.recognize_board()
            
            if board_state:
                print(f"✅ 识别成功: {len(board_state)} 个棋子")
                for (col, row), piece in sorted(board_state.items()):
                    print(f"  ({col},{row}): {piece}")
            else:
                print("❌ 识别失败")
            
            # 显示图像
            frame = recognizer.camera_manager.last_frame
            if frame is not None:
                cv2.imshow('Board Recognition', frame)
            
            key = cv2.waitKey(1000) & 0xFF
            if key == 27:  # ESC
                break
        
        recognizer.stop()
        cv2.destroyAllWindows()
        
        print("\n✅ 测试完成")
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        print(f"\n❌ 测试失败: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="网络摄像头测试")
    parser.add_argument('--mode', type=str, default='camera', 
                       choices=['camera', 'recognition'],
                       help='测试模式: camera(仅摄像头), recognition(棋盘识别)')
    
    args = parser.parse_args()
    
    if args.mode == 'camera':
        success = test_network_camera()
    else:
        success = test_board_recognition()
    
    sys.exit(0 if success else 1)
