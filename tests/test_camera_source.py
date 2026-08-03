import unittest
import urllib.error
import threading
import time
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

from vision.camera import (
    CameraManager,
    HttpSnapshotCapture,
    build_http_camera_candidate_urls,
    normalize_camera_source,
)


class FakeHttpResponse:
    def __init__(self, data, content_type="image/jpeg"):
        self._data = data
        self._content_type = content_type
        self._offset = 0
        self.headers = {"Content-Type": content_type}

    def read(self, size=-1):
        if size is None or size < 0:
            chunk = self._data[self._offset :]
            self._offset = len(self._data)
            return chunk
        chunk = self._data[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class CameraSourceTests(unittest.TestCase):
    def make_test_jpeg(self):
        image = np.zeros((8, 8, 3), dtype=np.uint8)
        image[:, :] = (32, 128, 224)
        ok, encoded = cv2.imencode(".jpg", image)
        self.assertTrue(ok)
        return encoded.tobytes()

    def test_normalize_camera_source_keeps_local_index_as_int(self):
        self.assertEqual(normalize_camera_source(1), 1)
        self.assertEqual(normalize_camera_source("2"), 2)

    def test_normalize_camera_source_accepts_rtsp_and_http_urls(self):
        self.assertEqual(
            normalize_camera_source(" rtsp://192.168.1.23:8554/cam "),
            "rtsp://192.168.1.23:8554/cam",
        )
        self.assertEqual(
            normalize_camera_source("http://192.168.1.23:8080/stream.mjpg"),
            "http://192.168.1.23:8080/stream.mjpg",
        )

    def test_normalize_camera_source_rejects_unsupported_url_scheme(self):
        with self.assertRaises(ValueError):
            normalize_camera_source("ftp://192.168.1.23/cam")

    def test_http_stream_url_uses_entered_stream_first(self):
        candidates = build_http_camera_candidate_urls(
            "http://192.168.1.23:8080/stream.mjpg"
        )

        self.assertEqual(
            candidates[0],
            "http://192.168.1.23:8080/stream.mjpg",
        )
        self.assertIn("http://192.168.1.23:8080/snapshot.jpg", candidates)

    def test_http_snapshot_capture_reads_snapshot_jpeg(self):
        jpeg_bytes = self.make_test_jpeg()
        requested_urls = []

        def fake_urlopen(request, timeout=0):
            requested_urls.append(request.full_url)
            return FakeHttpResponse(jpeg_bytes)

        fake_opener = MagicMock()
        fake_opener.open.side_effect = fake_urlopen

        with patch("vision.http_capture.urllib.request.build_opener", return_value=fake_opener):
            capture = HttpSnapshotCapture("http://192.168.1.23:8080/stream.mjpg")
            ok, frame = capture.read()

        self.assertTrue(ok)
        self.assertEqual(frame.shape[:2], (8, 8))
        self.assertEqual(
            requested_urls[0],
            "http://192.168.1.23:8080/stream.mjpg",
        )

    def test_http_snapshot_capture_uses_no_proxy_opener(self):
        jpeg_bytes = self.make_test_jpeg()
        fake_opener = MagicMock()
        fake_opener.open.return_value = FakeHttpResponse(jpeg_bytes)

        with patch("vision.http_capture.urllib.request.urlopen") as urlopen, \
             patch("vision.http_capture.urllib.request.build_opener", return_value=fake_opener) as build_opener:
            urlopen.side_effect = AssertionError("global urlopen would use proxy settings")
            capture = HttpSnapshotCapture("http://192.168.1.23:8080/stream.mjpg")
            ok, frame = capture.read()

        self.assertTrue(ok)
        self.assertEqual(frame.shape[:2], (8, 8))
        self.assertEqual(build_opener.call_count, 1)
        urlopen.assert_not_called()
        fake_opener.open.assert_called()

    def test_http_snapshot_capture_falls_back_from_stream_to_snapshot(self):
        jpeg_bytes = self.make_test_jpeg()
        requested_urls = []

        def fake_urlopen(request, timeout=0):
            requested_urls.append(request.full_url)
            if request.full_url.endswith("/stream.mjpg"):
                raise urllib.error.HTTPError(
                    request.full_url, 404, "not found", hdrs=None, fp=None
                )
            return FakeHttpResponse(jpeg_bytes)

        fake_opener = MagicMock()
        fake_opener.open.side_effect = fake_urlopen

        with patch("vision.http_capture.urllib.request.build_opener", return_value=fake_opener):
            capture = HttpSnapshotCapture("http://192.168.1.23:8080/stream.mjpg")
            ok, frame = capture.read()

        self.assertTrue(ok)
        self.assertEqual(frame.shape[:2], (8, 8))
        self.assertEqual(
            requested_urls,
            [
                "http://192.168.1.23:8080/stream.mjpg",
                "http://192.168.1.23:8080/snapshot.jpg",
            ],
        )

    def test_camera_manager_reports_url_source(self):
        manager = CameraManager(camera_source="rtsp://192.168.1.23:8554/cam")

        self.assertTrue(manager.is_network_source)
        self.assertEqual(manager.source_label, "rtsp://192.168.1.23:8554/cam")

    def test_network_source_uses_url_video_capture(self):
        manager = CameraManager(camera_source="rtsp://192.168.1.23:8554/cam")
        fake_capture = MagicMock()
        fake_capture.isOpened.return_value = True

        with patch("vision.camera.cv2.VideoCapture", return_value=fake_capture) as video_capture:
            cap = manager._open_capture_for_backend(1900)

        self.assertIs(cap, fake_capture)
        video_capture.assert_called_once_with("rtsp://192.168.1.23:8554/cam", 1900)

    def test_http_network_source_uses_snapshot_capture(self):
        manager = CameraManager(camera_source="http://192.168.1.23:8080/stream.mjpg")

        cap = manager._open_capture_for_backend(None)

        self.assertIsInstance(cap, HttpSnapshotCapture)

    def test_local_camera_warmup_skips_nearly_black_frames(self):
        manager = CameraManager(camera_index=1)
        black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        valid_frame = np.full((480, 640, 3), 120, dtype=np.uint8)
        fake_capture = MagicMock()
        fake_capture.read.side_effect = [
            (True, black_frame),
            (True, black_frame),
            (True, valid_frame),
            (True, valid_frame),
        ]

        frame = manager._warmup_read(fake_capture, timeout=0.2)

        self.assertIsNotNone(frame)
        self.assertGreater(float(frame.mean()), 100.0)

    def test_local_camera_does_not_cache_nearly_black_frame(self):
        manager = CameraManager(camera_index=1)
        black_frame = np.zeros((480, 640, 3), dtype=np.uint8)

        stored = manager._store_frame(black_frame)

        self.assertFalse(stored)
        self.assertIsNone(manager.last_frame)

    def test_concurrent_camera_start_opens_device_only_once(self):
        manager = CameraManager(camera_index=1)
        frame = np.full((480, 640, 3), 120, dtype=np.uint8)
        fake_capture = MagicMock()
        fake_capture.isOpened.return_value = True
        open_count = 0
        count_lock = threading.Lock()

        def open_capture():
            nonlocal open_count
            with count_lock:
                open_count += 1
            time.sleep(0.05)
            return fake_capture, frame

        with (
            patch.object(manager, "_open_capture_with_frame", side_effect=open_capture),
            patch.object(manager, "_start_reader"),
        ):
            threads = [threading.Thread(target=manager.start) for _ in range(4)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=1.0)

        self.assertEqual(open_count, 1)


if __name__ == "__main__":
    unittest.main()
