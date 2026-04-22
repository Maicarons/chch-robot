"""
配置文件 - 线下棋盘人机博弈中国象棋项目
"""

# ============= 摄像头配置 =============
CAMERA_INDEX = 0              # 摄像头索引（0 为默认摄像头）
CAMERA_WIDTH = 1280           # 摄像头宽度
CAMERA_HEIGHT = 720           # 摄像头高度
CAMERA_FPS = 30               # 帧率

# 网络摄像头配置（香橙派）
USE_NETWORK_CAMERA = False    # 是否使用网络摄像头
NETWORK_CAMERA_URL = "ws://192.168.1.100:8765"  # 香橙派WebSocket地址

# ============= 棋盘识别配置 =============
BOARD_ROWS = 10               # 棋盘行数
BOARD_COLS = 9                # 棋盘列数
SQUARE_SIZE_MM = 50           # 每个格子的实际尺寸（毫米）
BOARD_MARGIN_MM = 20          # 棋盘边缘留白（毫米）

# YOLO 模型配置
YOLO_MODEL_PATH = "./best.pt"       # YOLOv8 棋子检测模型路径
YOLO_CONF_THRES = 0.10        # YOLO 置信度阈值
MIN_PIECE_SIZE = 70           # 最小棋子像素尺寸（过滤误识）
SNAP_DIST_THRES = 0.45        # 检测框中心吸附到交点的最大容许距离

# 稳定化参数
STABLE_WINDOW = 5             # 最近若干帧做稳定化
STABLE_RATIO = 0.60           # 稳定化比例阈值
AUTO_STABLE_FRAMES = 25       # 持续稳定帧数触发自动识别

# 图像处理参数
CANNY_THRESHOLD1 = 50         # Canny 边缘检测阈值 1
CANNY_THRESHOLD2 = 150        # Canny 边缘检测阈值 2
MIN_CONTOUR_AREA = 500        # 最小轮廓面积（像素）
MAX_CONTOUR_AREA = 5000       # 最大轮廓面积（像素）

# 棋子颜色识别阈值（HSV 空间）
RED_LOWER1 = (0, 100, 100)    # 红色下限 1
RED_UPPER1 = (10, 255, 255)   # 红色上限 1
RED_LOWER2 = (160, 100, 100)  # 红色下限 2（跨越 180 度）
RED_UPPER2 = (180, 255, 255)  # 红色上限 2
BLACK_LOWER = (0, 0, 0)       # 黑色下限
BLACK_UPPER = (180, 255, 60)  # 黑色上限

# ============= AI 引擎配置 =============
ENGINE_PATH = "./Pikafish/pikafish-avx2.exe"  # Pikafish 引擎路径
ENGINE_DEPTH = 15                    # 搜索深度
THINK_TIME = 5000                    # 思考时间（毫秒）
USE_HASH_TABLE = True                # 使用哈希表
HASH_SIZE_MB = 128                   # 哈希表大小（MB）

# ============= 机械臂配置 =============
ROBOT_TYPE = "simulation"   # 机械臂类型："simulation", "dobot", "elephant_robotics"

# 机械臂 home 点坐标（毫米）
HOME_POSITION_X = 100
HOME_POSITION_Y = 100
HOME_POSITION_Z = 150

# 抓取高度（毫米）
GRIPPER_PICK_HEIGHT = 80    # 夹爪初始高度
GRIPPER_GRASP_HEIGHT = 10   # 抓取时下降高度
GRIPPER_MOVE_HEIGHT = 50    # 移动时安全高度

# 运动速度（毫米/秒）
ROBOT_SPEED_FAST = 100      # 快速移动速度
ROBOT_SPEED_SLOW = 30       # 精细操作速度

# ============= 游戏配置 =============
PLAYER_COLOR = "red"        # 玩家颜色："red" 或 "black"
AI_AUTO_PLAY = False        # AI 是否自动连续走棋（测试用）
WAIT_PLAYER_MOVE_TIMEOUT = 120  # 等待玩家走棋超时时间（秒）

# ============= 显示配置 =============
SHOW_CAMERA_PREVIEW = True  # 显示摄像头预览
SHOW_DETECTION_RESULT = True  # 显示检测结果
DEBUG_MODE = False          # 调试模式

# ============= 日志配置 =============
LOG_LEVEL = "INFO"          # 日志级别："DEBUG", "INFO", "WARNING", "ERROR"
LOG_FILE = "./chchess.log"  # 日志文件路径
SAVE_LOG_TO_FILE = True     # 是否保存日志到文件

# ============= 坐标校准 =============
# 棋盘左上角在机械臂坐标系中的位置（毫米）
BOARD_TOP_LEFT_X = 0
BOARD_TOP_LEFT_Y = 0
BOARD_TOP_LEFT_Z = 0

# 棋盘旋转角度（度）
BOARD_ROTATION_ANGLE = 0

# ============= 备用配置 =============
FEN_START_POSITION = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"

# ============= 已废弃配置 =============
# USE_IP_CAMERA = False  # 已废弃，改用 USE_NETWORK_CAMERA
# IP_CAMERA_URL = "http://192.168.1.100:8080/video"  # 已废弃
