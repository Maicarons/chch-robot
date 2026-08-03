import numpy as np
import cv2
from typing import Tuple, List


BONE_NAMES = [
    "A0", "A8",
    "J0", "J8",
]

def check_keypoints(keypoints: np.ndarray):
    """
    检查关键点坐标是否正确
    @param keypoints: 关键点坐标, shape 为 (N, 2)
    """
    if keypoints.shape != (len(BONE_NAMES), 2):
        raise Exception(f"keypoints shape error: {keypoints.shape}")
def perspective_transform(
        image: cv2.UMat, 
        src_points: np.ndarray, 
        keypoints: np.ndarray,
        dst_size=(450, 500)) -> Tuple[cv2.UMat, np.ndarray, np.ndarray]:
    """
    透视变换
    @param image: 图片
    @param src_points: 源点坐标
    @param keypoints: 关键点坐标
    @param dst_size: 目标尺寸 (width, height) 10 行 9 列

    @return:
        result: 透视变换后的图片
        transformed_keypoints: 透视变换后的关键点坐标
        corner_points: 棋盘的 corner 点坐标, shape 为 (4, 2) A0, A8, J0, J8
    """

    check_keypoints(keypoints)


    # 源点和目标点
    src = np.float32(src_points)
    padding = 50
    corner_points = np.float32([
        # 左上角
        [padding, padding], 
        # 右上角
        [dst_size[0]-padding, padding], 
        # 左下角
        [padding, dst_size[1]-padding], 
        # 右下角
        [dst_size[0]-padding, dst_size[1]-padding]])

    # 计算透视变换矩阵
    matrix = cv2.getPerspectiveTransform(src, corner_points)

    # 执行透视变换
    result = cv2.warpPerspective(image, matrix, dst_size)

    # 重塑数组为要求的格式 (N,1,2)
    keypoints_reshaped = keypoints.reshape(-1, 1, 2).astype(np.float32)
    transformed_keypoints = cv2.perspectiveTransform(keypoints_reshaped, matrix)
    # 转回原来的形状
    transformed_keypoints = transformed_keypoints.reshape(-1, 2)

    return result, transformed_keypoints, corner_points



def get_board_corner_points(keypoints: np.ndarray) -> np.ndarray:
    """
    计算棋局四个边角的 points
    @param keypoints: 关键点坐标, shape 为 (N, 2)
    @return: 边角的坐标, shape 为 (4, 2)
    """
    check_keypoints(keypoints)

    # 找到 A0 A8 J0 J8 的坐标 以及 A4 和 J4 的坐标
    a0_index = BONE_NAMES.index("A0")
    a8_index = BONE_NAMES.index("A8")
    j0_index = BONE_NAMES.index("J0")
    j8_index = BONE_NAMES.index("J8")

    a0_xy = keypoints[a0_index]
    a8_xy = keypoints[a8_index]
    j0_xy = keypoints[j0_index]
    j8_xy = keypoints[j8_index]

    # 计算新的四个角点坐标
    dst_points = np.array([
        a0_xy,
        a8_xy,
        j0_xy,
        j8_xy
    ], dtype=np.float32)

    return dst_points

def extract_chessboard(img: cv2.UMat, keypoints: np.ndarray) -> Tuple[cv2.UMat, np.ndarray, np.ndarray]:
    """
    提取棋盘信息
    @param img: 图片
    @param keypoints: 关键点坐标, shape 为 (N, 2)
    @return:
        transformed_image: 透视变换后的图片
        transformed_keypoints: 透视变换后的关键点坐标
        transformed_corner_points: 棋盘的 corner 点坐标, shape 为 (4, 2) A0, A8, J0, J8
    """

    check_keypoints(keypoints)

    source_corner_points = get_board_corner_points(keypoints)

    transformed_image, transformed_keypoints, transformed_corner_points = perspective_transform(img, source_corner_points, keypoints)

    return transformed_image, transformed_keypoints, transformed_corner_points
