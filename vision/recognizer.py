"""
Board recognizer: camera capture, ONNX detection, stabilization, and FEN output.
"""

import datetime
import logging
import os
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

from .camera import CameraManager
from .detector import ChessboardDetector
from .stabilizer import DynamicBoardTracker, StableBoardBuffer
from xq_utils import FENUtils
from config import (
    BOARD_TOP_LEFT_X,
    BOARD_TOP_LEFT_Y,
    BOARD_TOP_LEFT_Z,
    CAMERA_FPS,
    CAMERA_HEIGHT,
    CAMERA_WIDTH,
    STABLE_RATIO,
    STABLE_WINDOW,
)

logger = logging.getLogger(__name__)


class BoardRecognizer:
    """High-level API used by the Flask simulation."""

    def __init__(
        self,
        camera_index: int = 0,
        camera_source=None,
        detect_interval: float = 3.0,
        pose_model_path: str = None,
        classifier_model_path: str = None,
        width: int = None,
        height: int = None,
        fps: int = None,
    ):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if pose_model_path is None:
            pose_model_path = os.path.join(project_root, "model", "pose", "4_v6-0301.onnx")
        if classifier_model_path is None:
            classifier_model_path = os.path.join(project_root, "model", "layout_recognition", "nano_v3-0319.onnx")

        self.camera_manager = CameraManager(
            camera_index=camera_index,
            camera_source=camera_source,
            width=width or CAMERA_WIDTH,
            height=height or CAMERA_HEIGHT,
            fps=fps or CAMERA_FPS,
        )
        self.detector = ChessboardDetector(
            pose_model_path=pose_model_path,
            classifier_model_path=classifier_model_path,
        )
        self.stabilizer = StableBoardBuffer(maxlen=STABLE_WINDOW, ratio=STABLE_RATIO)
        self.dynamic_tracker = DynamicBoardTracker(
            buffer_window=1,
            buffer_ratio=1.0,
            stable_seconds=0.0,
            min_piece_count=10,
        )
        self.detect_interval = detect_interval
        self.last_board_state = None
        self.current_fen = None
        # 棋盘原点在机械臂坐标系中的位置（毫米），供机械臂执行走法时使用。
        # 由 config.BOARD_TOP_LEFT_* 提供，作为未校准时的默认基准。
        self.board_origin = (
            BOARD_TOP_LEFT_X,
            BOARD_TOP_LEFT_Y,
            BOARD_TOP_LEFT_Z,
        )

        logger.info("BoardRecognizer ready (camera=%s, interval=%ss)", self.camera_manager.source_label, detect_interval)

    def start(self) -> bool:
        return self.camera_manager.start()

    def start_camera(self) -> bool:
        return self.start()

    def stop(self):
        self.camera_manager.stop()

    def stop_camera(self):
        self.stop()

    def reset_dynamic_tracking(self):
        self.dynamic_tracker.reset()
        if hasattr(self.detector, "reset_board_cache"):
            self.detector.reset_board_cache()

    def sync_dynamic_baseline(self, board_state):
        self.dynamic_tracker.sync_baseline(board_state)

    def capture_frame(self) -> np.ndarray:
        return self.camera_manager.capture_frame()

    def calibrate_board(self) -> bool:
        logger.info("Board calibration placeholder completed")
        return True

    def _detect_board_state(self, image: np.ndarray = None, save_debug: bool = False):
        if image is None:
            image = self.camera_manager.capture_frame()
        if image is None:
            logger.warning("No camera frame available for recognition")
            return None, None

        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        height, width = image_rgb.shape[:2]
        max_width = int(os.getenv("CHRO_RECOGNITION_MAX_WIDTH", "960"))
        if width > max_width:
            scale = max_width / width
            new_size = (int(width * scale), int(height * scale))
            image_rgb = cv2.resize(image_rgb, new_size, interpolation=cv2.INTER_AREA)
            logger.debug("Recognition frame downscaled %sx%s -> %sx%s", width, height, *new_size)

        original_with_kpts, transformed, layout_str, scores, time_info = self.detector.detect_and_classify(
            image_rgb,
            draw_debug=save_debug,
        )
        if layout_str is None:
            logger.warning("Board detection failed")
            return None, None

        if save_debug and transformed is not None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                f"debug_board_{timestamp}.jpg",
            )
            cv2.imwrite(debug_path, cv2.cvtColor(transformed, cv2.COLOR_RGB2BGR))
            logger.info("Saved transformed board debug image: %s", debug_path)

        if scores:
            confidences = [conf for row in scores for conf in row if conf > 0]
            if confidences:
                logger.info(
                    "Recognition confidence avg=%.3f min=%.3f",
                    float(np.mean(confidences)),
                    float(np.min(confidences)),
                )
        logger.info(time_info)
        return self.detector.parse_layout_string(layout_str), layout_str

    def recognize_dynamic_frame(self, image: np.ndarray = None):
        raw_state, _ = self._detect_board_state(image=image, save_debug=False)
        if raw_state is None:
            return {
                "event": "detection_failed",
                "stable": False,
                "board_state": {},
                "message": "board detection failed",
                "move": None,
            }
        return self.dynamic_tracker.update(raw_state)

    def recognize_board(self, image: np.ndarray = None) -> Optional[Dict[Tuple[int, int], str]]:
        if image is None:
            image = self.camera_manager.capture_frame()
        if image is None:
            logger.warning("No image available")
            return None

        try:
            board_state, _ = self._detect_board_state(image=image, save_debug=False)
            if board_state is None:
                return None
            self.stabilizer.add(board_state)
            stable_state = self.stabilizer.get_stable()
            logger.info("Detected %s stable pieces", len(stable_state))
            return stable_state
        except Exception as exc:
            logger.error("Recognition failed: %s", exc, exc_info=True)
            return None

    def get_fen_from_recognition(self, image: np.ndarray = None) -> Optional[str]:
        """识别当前棋盘并返回 FEN 串。"""
        try:
            stable_state = self.recognize_board(image)
            if stable_state is None:
                return None

            board_2d = [[None for _ in range(9)] for _ in range(10)]
            for (col, row), piece in stable_state.items():
                if 0 <= col < 9 and 0 <= row < 10:
                    board_2d[row][col] = piece

            fen = FENUtils.to_fen(board_2d, side_to_move="w")
            self.current_fen = fen
            logger.info("Generated FEN: %s", fen)
            return fen
        except Exception as exc:
            logger.error("FEN generation failed: %s", exc, exc_info=True)
            return None

    def show_detection_result(self, image: np.ndarray = None):
        return self.show_result(image)

    def show_result(self, image: np.ndarray = None):
        if image is None:
            image = self.camera_manager.last_frame
        if image is None:
            return

        try:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            original_with_kpts, transformed, _, _, _ = self.detector.detect_and_classify(
                image_rgb,
                draw_debug=True,
            )
            if original_with_kpts is not None:
                cv2.imshow("Board Detection - Keypoints", cv2.cvtColor(original_with_kpts, cv2.COLOR_RGB2BGR))
            if transformed is not None:
                cv2.imshow("Transformed Board", cv2.cvtColor(transformed, cv2.COLOR_RGB2BGR))
            cv2.waitKey(1)
        except Exception as exc:
            logger.error("Show detection result failed: %s", exc)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
