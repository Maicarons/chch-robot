import os
import time
from typing import List, Tuple, Union

import cv2
import numpy as np
from pandas import DataFrame

from .runonnx.rtmpose import RTMPOSE_ONNX
from .runonnx.full_classifier import FULL_CLASSIFIER_ONNX
from .keypoint_helper import extract_chessboard


class ChessboardDetector:
    """ONNX chessboard corner detector plus full-board classifier."""

    def __init__(self, pose_model_path: str, full_classifier_model_path: str = None):
        self.pose = RTMPOSE_ONNX(model_path=pose_model_path)
        self.full_classifier = FULL_CLASSIFIER_ONNX(model_path=full_classifier_model_path)

        self.board_positions = []
        self.current_image = None
        self.current_filename = None

        self.cached_keypoints = None
        self.cached_scores = None
        self.cached_image_shape = None
        self.cache_time = 0.0
        self.cache_hits = 0
        self.pose_refresh_interval = float(os.getenv("CHRO_POSE_REFRESH_INTERVAL", "8.0"))
        self.pose_cache_hits = int(os.getenv("CHRO_POSE_CACHE_HITS", "120"))

    def reset_board_cache(self):
        self.cached_keypoints = None
        self.cached_scores = None
        self.cached_image_shape = None
        self.cache_time = 0.0
        self.cache_hits = 0

    def _keypoints_valid(self, keypoints, scores, image_shape) -> bool:
        if keypoints is None:
            return False
        keypoints = np.asarray(keypoints)
        if keypoints.shape != (4, 2) or not np.isfinite(keypoints).all():
            return False

        height, width = image_shape[:2]
        margin = 80
        if np.any(keypoints[:, 0] < -margin) or np.any(keypoints[:, 0] > width + margin):
            return False
        if np.any(keypoints[:, 1] < -margin) or np.any(keypoints[:, 1] > height + margin):
            return False

        if scores is not None and len(scores) >= 4:
            try:
                if float(np.min(scores[:4])) < 0.20:
                    return False
            except Exception:
                return False
        return True

    def _can_use_cached_keypoints(self, image_shape, draw_debug=False, force_pose=False) -> bool:
        if force_pose or draw_debug or self.cached_keypoints is None:
            return False
        if self.cached_image_shape != tuple(image_shape[:2]):
            return False
        if time.monotonic() - self.cache_time > self.pose_refresh_interval:
            return False
        if self.cache_hits >= self.pose_cache_hits:
            return False
        return True

    def pred_keypoints(self, image_bgr: Union[np.ndarray, None] = None) -> Tuple[List[List[int]], List[float]]:
        height, width = image_bgr.shape[:2]
        bbox = [0, 0, width, height]
        keypoints, scores = self.pose.pred(image=image_bgr, bbox=bbox)
        return keypoints, scores

    def draw_pred_with_keypoints(self, image_rgb: Union[np.ndarray, None] = None):
        if image_rgb is None:
            return None, None, None

        draw_image = image_rgb.copy()
        original_image = image_rgb.copy()
        image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
        keypoints, scores = self.pred_keypoints(image_bgr)
        draw_image = self.pose.draw_pred(img=draw_image, keypoints=keypoints, scores=scores)

        keypoint_list = [
            {"name": bone_name, "x": keypoint[0], "y": keypoint[1]}
            for bone_name, keypoint in zip(self.pose.bone_names, keypoints)
        ]
        return draw_image, original_image, DataFrame(keypoint_list)

    def extract_chessboard_and_classifier_layout(
        self,
        image_rgb: Union[np.ndarray, None] = None,
        keypoints: Union[np.ndarray, None] = None,
    ) -> Tuple[np.ndarray, str, List[List[float]]]:
        transformed_image, _transformed_keypoints, _corner_points = extract_chessboard(
            img=image_rgb,
            keypoints=keypoints,
        )
        _, _, scores, pred_result = self.full_classifier.pred(transformed_image, is_rgb=True)
        return transformed_image, pred_result, scores

    def pred_detect_board_and_classifier(
        self,
        image_rgb: Union[np.ndarray, None] = None,
        draw_debug: bool = False,
        force_pose: bool = False,
    ) -> Tuple[np.ndarray, np.ndarray, str, List[List[float]], str]:
        if image_rgb is None:
            return None, None, None, None, ""

        start_time = time.time()
        pose_time = 0.0
        classifier_time = 0.0
        used_cached_pose = False
        original_image_with_keypoints = None

        try:
            if self._can_use_cached_keypoints(image_rgb.shape, draw_debug=draw_debug, force_pose=force_pose):
                keypoints = self.cached_keypoints.copy()
                pose_scores = self.cached_scores
                used_cached_pose = True
                self.cache_hits += 1
            else:
                pose_start = time.time()
                image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
                keypoints, pose_scores = self.pred_keypoints(image_bgr)
                pose_time = time.time() - pose_start
                if self._keypoints_valid(keypoints, pose_scores, image_rgb.shape):
                    self.cached_keypoints = np.asarray(keypoints, dtype=np.float32).copy()
                    self.cached_scores = np.asarray(pose_scores).copy() if pose_scores is not None else None
                    self.cached_image_shape = tuple(image_rgb.shape[:2])
                    self.cache_time = time.monotonic()
                    self.cache_hits = 0

            if draw_debug:
                original_image_with_keypoints = self.pose.draw_pred(
                    img=image_rgb.copy(),
                    keypoints=keypoints,
                    scores=pose_scores,
                )

            classifier_start = time.time()
            transformed_image, cells_labels, scores = self.extract_chessboard_and_classifier_layout(
                image_rgb=image_rgb,
                keypoints=keypoints,
            )
            classifier_time = time.time() - classifier_start
        except Exception:
            if used_cached_pose:
                self.reset_board_cache()
                return self.pred_detect_board_and_classifier(
                    image_rgb,
                    draw_debug=draw_debug,
                    force_pose=True,
                )
            return None, None, None, None, ""

        total_time = time.time() - start_time
        pose_label = "cached" if used_cached_pose else f"{pose_time:.3f}s"
        time_info = (
            f"inference: total={total_time:.3f}s "
            f"pose={pose_label} classifier={classifier_time:.3f}s"
        )

        return original_image_with_keypoints, transformed_image, cells_labels, scores, time_info
