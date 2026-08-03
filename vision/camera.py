"""
Camera manager for low-latency USB capture.

Re-exports the source helpers (:mod:`vision.camera_source`) and the HTTP
snapshot capturer (:mod:`vision.http_capture`) so that existing imports such as
``from vision.camera import CameraManager, HttpSnapshotCapture,
normalize_camera_source, build_http_camera_candidate_urls`` keep working.
"""

import cv2
import logging
import os
import threading
import time
from typing import Optional, Tuple

import numpy as np
from urllib.parse import urlparse

from .camera_source import (
    CameraSource,
    NETWORK_CAMERA_SCHEMES,
    HTTP_CAMERA_SCHEMES,
    HTTP_STREAM_PATHS,
    normalize_camera_source,
    is_network_camera_source,
    build_http_camera_candidate_urls,
)
from .http_capture import HttpSnapshotCapture, JPEG_SOI, JPEG_EOI

__all__ = [
    "CameraSource",
    "NETWORK_CAMERA_SCHEMES",
    "HTTP_CAMERA_SCHEMES",
    "HTTP_STREAM_PATHS",
    "normalize_camera_source",
    "is_network_camera_source",
    "build_http_camera_candidate_urls",
    "HttpSnapshotCapture",
    "JPEG_SOI",
    "JPEG_EOI",
    "CameraManager",
]

logger = logging.getLogger(__name__)


class CameraManager:
    """Small OpenCV wrapper with background reading and auto-recovery."""

    def __init__(self, camera_index: int = 0, width: int = 640,
                 height: int = 480, fps: int = 30,
                 camera_source: CameraSource = None):
        self.camera_source = normalize_camera_source(
            camera_index if camera_source is None else camera_source
        )
        self.camera_index = self.camera_source if isinstance(self.camera_source, int) else int(camera_index)
        self.width = width
        self.height = height
        self.fps = fps
        self.camera: Optional[cv2.VideoCapture] = None
        self.last_frame: Optional[np.ndarray] = None
        self.last_frame_time = 0.0
        self.last_error = ""

        self._frame_lock = threading.Lock()
        self._camera_lock = threading.RLock()
        self._lifecycle_lock = threading.RLock()
        self._reader_thread: Optional[threading.Thread] = None
        self._reader_running = False
        self._recovering = False
        self._failed_reads = 0

        logger.info("CameraManager init source=%s, %sx%s@%sfps",
                    self.source_label, width, height, fps)

    @property
    def is_network_source(self) -> bool:
        return isinstance(self.camera_source, str)

    @property
    def source_label(self) -> str:
        return str(self.camera_source)

    @property
    def is_http_network_source(self) -> bool:
        return (
            self.is_network_source and
            urlparse(self.camera_source).scheme.lower() in HTTP_CAMERA_SCHEMES
        )

    def set_source(self, source: CameraSource):
        with self._lifecycle_lock:
            self.stop()
            self.camera_source = normalize_camera_source(source)
            if isinstance(self.camera_source, int):
                self.camera_index = self.camera_source
            self.last_frame = None
            self.last_frame_time = 0.0
            self.last_error = ""

    def start(self) -> bool:
        """Open the selected camera and start the background reader."""
        with self._lifecycle_lock:
            try:
                with self._frame_lock:
                    has_valid_frame = self._is_usable_frame(self.last_frame)
                if self.is_opened() and has_valid_frame:
                    return True

                self.stop()
                cap, first_frame = self._open_capture_with_frame()
                if cap is None or first_frame is None:
                    self.last_error = f"camera source {self.source_label} opened no frame"
                    logger.error(self.last_error)
                    return False

                with self._camera_lock:
                    self.camera = cap
                    self._failed_reads = 0

                self._store_frame(first_frame)
                self._start_reader()
                logger.info("Camera source %s started", self.source_label)
                return True
            except Exception as exc:
                self.last_error = str(exc)
                logger.error("Start camera failed: %s", exc, exc_info=True)
                self.stop()
                return False

    def stop(self):
        """Close the camera and stop the reader thread."""
        with self._lifecycle_lock:
            self._reader_running = False
            if (
                self._reader_thread
                and self._reader_thread.is_alive()
                and threading.current_thread() is not self._reader_thread
            ):
                self._reader_thread.join(timeout=1.0)
            self._reader_thread = None

            with self._camera_lock:
                if self.camera:
                    self.camera.release()
                    self.camera = None
                    logger.info("Camera closed")

    def capture_frame(self) -> Optional[np.ndarray]:
        """Return the newest frame immediately; recover the camera if needed."""
        with self._frame_lock:
            if self.last_frame is not None:
                if self._is_usable_frame(self.last_frame):
                    return self.last_frame.copy()
                self.last_frame = None
                self.last_frame_time = 0.0

        if not self.is_opened():
            self.start()

        with self._camera_lock:
            if not self.camera or not self.camera.isOpened():
                logger.warning("Camera is not open")
                return None
            ret, frame = self.camera.read()

        if ret and frame is not None and self._store_frame(frame):
            return frame.copy()

        self._request_recover()
        logger.warning("Capture frame failed")
        return None

    def is_opened(self) -> bool:
        with self._camera_lock:
            return self.camera is not None and self.camera.isOpened()

    def _start_reader(self):
        if self._reader_thread and self._reader_thread.is_alive():
            return
        self._reader_running = True
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()

    def _reader_loop(self):
        frame_interval = 1.0 / max(1, self._effective_reader_fps())
        stale_timeout = max(1.2, frame_interval * 20)

        while self._reader_running:
            with self._camera_lock:
                cap = self.camera
                if cap is None or not cap.isOpened():
                    ret, frame = False, None
                else:
                    ret, frame = cap.read()

            if ret and frame is not None and self._store_frame(frame):
                self._failed_reads = 0
                time.sleep(min(0.004, frame_interval))
                continue

            self._failed_reads += 1
            stale_for = time.monotonic() - self.last_frame_time if self.last_frame_time else 999.0
            if self._failed_reads >= 12 or stale_for > stale_timeout:
                self._recover_in_reader()
            time.sleep(0.03)

    def _request_recover(self):
        if self._recovering:
            return
        if self._reader_thread and self._reader_thread.is_alive():
            return
        self._recover_in_reader()

    def _recover_in_reader(self):
        if self._recovering:
            return

        with self._lifecycle_lock:
            if self._recovering:
                return

            self._recovering = True
            try:
                logger.warning("Recovering camera %s after %s failed reads",
                               self.source_label, self._failed_reads)
                cap, first_frame = self._open_capture_with_frame()
                if cap is None or first_frame is None:
                    return

                with self._camera_lock:
                    old = self.camera
                    self.camera = cap
                    self._failed_reads = 0
                    if old is not None and old is not cap:
                        old.release()
                self._store_frame(first_frame)
                logger.info("Camera source %s recovered", self.source_label)
            finally:
                self._recovering = False

    def _store_frame(self, frame: np.ndarray) -> bool:
        if not self._is_usable_frame(frame):
            self.last_error = f"camera source {self.source_label} returned a blank frame"
            return False

        with self._frame_lock:
            self.last_frame = frame.copy()
            self.last_frame_time = time.monotonic()
        self.last_error = ""
        return True

    def _is_usable_frame(self, frame: Optional[np.ndarray]) -> bool:
        if frame is None or frame.size == 0:
            return False
        if self.is_network_source:
            return True

        sample = frame[::16, ::16]
        return not (float(sample.mean()) < 1.0 and float(sample.std()) < 2.0)

    def _open_capture_with_frame(self) -> Tuple[Optional[cv2.VideoCapture], Optional[np.ndarray]]:
        if self.is_http_network_source:
            cap = self._open_capture_for_backend(None)
            frame = self._warmup_read(cap, timeout=3.0)
            if frame is not None:
                logger.info(
                    "Camera source %s opened with HTTP snapshot mode size=%sx%s",
                    self.source_label,
                    frame.shape[1],
                    frame.shape[0],
                )
                return cap, frame
            cap.release()
            return None, None

        for backend in self._candidate_backends():
            for width, height in self._candidate_resolutions():
                cap = self._open_capture_for_backend(backend)
                if not cap.isOpened():
                    cap.release()
                    continue

                self._configure_capture(cap, width, height)
                frame = self._warmup_read(cap)
                if frame is not None:
                    logger.info("Camera source %s opened with backend=%s size=%sx%s",
                                self.source_label, backend, frame.shape[1], frame.shape[0])
                    return cap, frame

                cap.release()

        return None, None

    def _open_capture_for_backend(self, backend: int):
        if self.is_http_network_source:
            return HttpSnapshotCapture(self.camera_source)
        return cv2.VideoCapture(self.camera_source, backend)

    def _configure_capture(self, cap: cv2.VideoCapture, width: int, height: int):
        settings = [(cv2.CAP_PROP_BUFFERSIZE, 1)]
        if self.is_network_source:
            for prop_name in ("CAP_PROP_OPEN_TIMEOUT_MSEC", "CAP_PROP_READ_TIMEOUT_MSEC"):
                prop = getattr(cv2, prop_name, None)
                if prop is not None:
                    settings.append((prop, 2500))
        else:
            settings.extend([
                (cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG")),
                (cv2.CAP_PROP_FRAME_WIDTH, width),
                (cv2.CAP_PROP_FRAME_HEIGHT, height),
                (cv2.CAP_PROP_FPS, self.fps),
            ])
        for prop, value in settings:
            try:
                cap.set(prop, value)
            except Exception:
                pass

    def _warmup_read(self, cap: cv2.VideoCapture, timeout: float = 2.0) -> Optional[np.ndarray]:
        deadline = time.monotonic() + timeout
        best_frame = None
        while time.monotonic() < deadline:
            ret, frame = cap.read()
            if ret and self._is_usable_frame(frame):
                best_frame = frame
                # A second good frame avoids returning a stale startup frame.
                ret2, frame2 = cap.read()
                if ret2 and self._is_usable_frame(frame2):
                    return frame2
                return best_frame
            time.sleep(0.03)
        return best_frame

    def _candidate_backends(self):
        if self.is_network_source:
            if self.is_http_network_source:
                return [None]
            backends = []
            ffmpeg = getattr(cv2, "CAP_FFMPEG", None)
            if ffmpeg is not None:
                backends.append(ffmpeg)
            backends.append(cv2.CAP_ANY)
            return _dedupe(backends)

        if os.name != "nt":
            return [cv2.CAP_ANY]

        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        return _dedupe(backends)

    def _candidate_resolutions(self):
        if self.is_network_source:
            return [(self.width, self.height)]

        candidates = [
            (self.width, self.height),
            (1280, 720),
            (640, 480),
        ]
        seen = set()
        result = []
        for width, height in candidates:
            key = (int(width), int(height))
            if key not in seen:
                result.append(key)
                seen.add(key)
        return result

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def _effective_reader_fps(self) -> int:
        if self.is_http_network_source:
            return min(self.fps, 8)
        return self.fps


def _dedupe(values):
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
