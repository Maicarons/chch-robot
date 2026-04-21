
import time
import numpy as np
import cv2
from typing import List, Tuple, Union
from pandas import DataFrame
from .runonnx.rtmpose import RTMPOSE_ONNX
from .runonnx.full_classifier import FULL_CLASSIFIER_ONNX

from core.helper_4_kpt import extract_chessboard

class ChessboardDetector:
    def __init__(self,
                 pose_model_path: str,
                 full_classifier_model_path: str = None
                 ):

        self.pose = RTMPOSE_ONNX(
            model_path=pose_model_path,
        )

        self.full_classifier = FULL_CLASSIFIER_ONNX(
            model_path=full_classifier_model_path,
        )

        self.board_positions = []  # 存储棋盘位置坐标
        self.current_image = None
        self.current_filename = None
    

    # 检测中国象棋棋盘
    def pred_keypoints(self, image_bgr: Union[np.ndarray, None] = None) -> Tuple[List[List[int]], List[float]]:

        # 预测关键点, 绘制关键点

        width, height = image_bgr.shape[:2]
        bbox = [0, 0, width, height]

        keypoints, scores = self.pose.pred(image=image_bgr, bbox=bbox)

        return keypoints, scores
    

    def draw_pred_with_keypoints(self, image_rgb: Union[np.ndarray, None] = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        if image_rgb is None:
            return None, None, None
        
        image_rgb = image_rgb.copy()

        original_image = image_rgb.copy()

        image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)

        keypoints, scores = self.pred_keypoints(image_bgr)

        # 绘制棋盘框架
        draw_image = self.pose.draw_pred(img=image_rgb, keypoints=keypoints, scores=scores)

        # 融合 self.pose.bone_names 与 keypoints, 再转换成 DataFrame
        keypoint_list = []
        for bone_name, keypoint in zip(self.pose.bone_names, keypoints):
            keypoint_list.append({"name": bone_name, "x": keypoint[0], "y": keypoint[1]})

        keypoint_df = DataFrame(keypoint_list)

        return draw_image, original_image, keypoint_df

    # 拉伸棋盘 detect board, 然后预测
    def extract_chessboard_and_classifier_layout(self, 
                                                image_rgb: Union[np.ndarray, None] = None, 
                                                keypoints: Union[np.ndarray, None] = None
                                                ) -> Tuple[np.ndarray, List[List[str]], List[List[float]]]:
        
        # 提取棋盘, 绘制 每个位置的 范围信息
        transformed_image, _transformed_keypoints, _corner_points = extract_chessboard(img=image_rgb, keypoints=keypoints)

        transformed_image_copy = transformed_image.copy()
   
        # 预测每个位置的 棋子类别
        _, _, scores, pred_result = self.full_classifier.pred(transformed_image_copy, is_rgb=True)


        return transformed_image, pred_result, scores


    # 检测棋盘 detect board
    def pred_detect_board_and_classifier(self, 
                                         image_rgb: Union[np.ndarray, None] = None, 
                                        ) -> Tuple[np.ndarray, np.ndarray, str, List[List[float]], str]:

        """
        @param image_rgb: 输入的 RGB 图像
        @return: 
            - transformed_image_layout  # 拉伸棋盘
            - original_image_with_keypoints  # 原图关键点
            - layout_pred_info  # 每个位置的 棋子类别
            - scores  # 每个位置的 置信度
            - time_info  # 推理用时
        """

        if image_rgb is None:
            return None, None, [], [], ""
        
        image_rgb_for_extract = image_rgb.copy()
        image_rgb_for_draw = image_rgb.copy()
        
        start_time = time.time()

        try:
            image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)

            keypoints, scores = self.pred_keypoints(image_bgr)

            """
            绘制 原图关键点
            """
            original_image_with_keypoints = self.pose.draw_pred(img=image_rgb_for_draw, keypoints=keypoints, scores=scores)

            transformed_image, cells_labels, scores = self.extract_chessboard_and_classifier_layout(image_rgb=image_rgb_for_extract, keypoints=keypoints)
        except Exception as e:
            print("检测棋盘失败", e)
            return None, None, None, None, ""


        use_time = time.time() - start_time

        time_info = f"推理用时: {use_time:.2f}s"

        return original_image_with_keypoints, transformed_image, cells_labels, scores, time_info
    