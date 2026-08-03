"""
通过 HTTP 端点抓取 JPEG 帧，无需 OpenCV 的网络 IO。

适用于仅提供快照/ MJPEG 接口的网络摄像头（如香橙派、树莓派上的 MJPEG 服务）。
"""

import logging
import threading
import time
from typing import Optional, Tuple

import cv2
import numpy as np
import urllib.error
import urllib.request

from .camera_source import normalize_camera_source, build_http_camera_candidate_urls

logger = logging.getLogger(__name__)

JPEG_SOI = b"\xff\xd8"
JPEG_EOI = b"\xff\xd9"


class HttpSnapshotCapture:
    """Fetch JPEG frames from HTTP camera endpoints without OpenCV network IO."""

    def __init__(self, source: str, timeout: float = 2.5):
        self.source = str(normalize_camera_source(source))
        self.timeout = float(timeout)
        self._opened = True
        self._candidate_urls = build_http_camera_candidate_urls(self.source)
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def isOpened(self) -> bool:
        return self._opened

    def set(self, _prop: int, _value: float) -> bool:
        return False

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self._opened:
            return False, None

        last_error = None
        for url in self._candidate_urls:
            try:
                frame = self._read_frame_from_url(url)
                if frame is not None:
                    return True, frame
            except Exception as exc:
                last_error = exc

        if last_error is not None:
            logger.debug("HTTP camera read failed for %s: %s", self.source, last_error)
        return False, None

    def release(self):
        self._opened = False

    def _read_frame_from_url(self, url: str) -> np.ndarray:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "CHROCamera/1.0",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Connection": "close",
            },
        )
        with self._opener.open(request, timeout=self.timeout) as response:
            content_type = str(response.headers.get("Content-Type", "")).lower()
            if "multipart/x-mixed-replace" in content_type:
                data = self._read_first_mjpeg_frame(response)
            else:
                data = response.read()
            frame = self._decode_frame_bytes(data)
            if frame is None:
                raise RuntimeError(f"{url} returned no decodable JPEG frame")
            return frame

    def _read_first_mjpeg_frame(self, response) -> bytes:
        deadline = time.monotonic() + self.timeout
        buffer = bytearray()

        while time.monotonic() < deadline and len(buffer) < 2 * 1024 * 1024:
            chunk = response.read(4096)
            if not chunk:
                break
            buffer.extend(chunk)

            start = buffer.find(JPEG_SOI)
            if start < 0:
                continue

            end = buffer.find(JPEG_EOI, start + len(JPEG_SOI))
            if end < 0:
                if start > 0:
                    del buffer[:start]
                continue

            return bytes(buffer[start : end + len(JPEG_EOI)])

        raise RuntimeError("timed out waiting for first MJPEG frame")

    def _decode_frame_bytes(self, data: bytes) -> Optional[np.ndarray]:
        if not data:
            return None

        start = data.find(b"\xff\xd8")
        end = data.rfind(b"\xff\xd9")
        if start >= 0 and end > start:
            data = data[start : end + 2]

        encoded = np.frombuffer(data, dtype=np.uint8)
        if encoded.size == 0:
            return None
        return cv2.imdecode(encoded, cv2.IMREAD_COLOR)
