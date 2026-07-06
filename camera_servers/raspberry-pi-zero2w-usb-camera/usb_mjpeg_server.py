#!/usr/bin/env python3
"""
Small USB MJPEG camera server for Raspberry Pi Zero 2 W.

The default backend uses Linux V4L2 directly so it can run on a fresh Raspberry
Pi OS image without pip or apt packages, provided the USB camera supports MJPEG.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import json
import mmap
import os
import select
import signal
import subprocess
import sys
import tempfile
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional


JPEG_SOI = b"\xff\xd8"
JPEG_EOI = b"\xff\xd9"


def log(message: str) -> None:
    print(time.strftime("[%Y-%m-%d %H:%M:%S]"), message, flush=True)


def build_preview_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CH-RO USB Camera</title>
  <style>
    body {
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      background: #101522;
      color: #eef2ff;
    }
    main {
      max-width: 980px;
      margin: 0 auto;
      padding: 24px;
    }
    h1 {
      margin: 0 0 12px;
      font-size: 28px;
    }
    p {
      margin: 0 0 16px;
      color: #c5d0ea;
      line-height: 1.5;
    }
    .preview {
      background: #0b1020;
      border: 1px solid #24304b;
      border-radius: 14px;
      overflow: hidden;
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.28);
    }
    img {
      display: block;
      width: 100%;
      height: auto;
      background: #050814;
    }
    .links {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 16px;
    }
    a {
      color: #8ab4ff;
      text-decoration: none;
    }
    code {
      color: #d8e6ff;
    }
  </style>
</head>
<body>
  <main>
    <h1>CH-RO USB Camera</h1>
    <p>Open this page in a browser for preview. For CH-RO, enter <code>http://&lt;PI_IP&gt;:8080</code> or <code>/stream.mjpg</code>.</p>
    <div class="preview">
      <img src="/stream.mjpg" alt="USB camera stream">
    </div>
    <div class="links">
      <a href="/snapshot.jpg" target="_blank" rel="noreferrer">Snapshot</a>
      <a href="/stream.mjpg" target="_blank" rel="noreferrer">MJPEG stream</a>
      <a href="/health" target="_blank" rel="noreferrer">Health</a>
    </div>
  </main>
</body>
</html>
"""


def fourcc(text: str) -> int:
    if len(text) != 4:
        raise ValueError("fourcc needs exactly four characters")
    return (
        ord(text[0])
        | (ord(text[1]) << 8)
        | (ord(text[2]) << 16)
        | (ord(text[3]) << 24)
    )


class CameraBackend:
    name = "base"

    def read_jpeg(self) -> bytes:
        raise NotImplementedError

    def close(self) -> None:
        pass


class V4L2Capability(ctypes.Structure):
    _fields_ = [
        ("driver", ctypes.c_char * 16),
        ("card", ctypes.c_char * 32),
        ("bus_info", ctypes.c_char * 32),
        ("version", ctypes.c_uint32),
        ("capabilities", ctypes.c_uint32),
        ("device_caps", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32 * 3),
    ]


class V4L2PixFormat(ctypes.Structure):
    _fields_ = [
        ("width", ctypes.c_uint32),
        ("height", ctypes.c_uint32),
        ("pixelformat", ctypes.c_uint32),
        ("field", ctypes.c_uint32),
        ("bytesperline", ctypes.c_uint32),
        ("sizeimage", ctypes.c_uint32),
        ("colorspace", ctypes.c_uint32),
        ("priv", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("ycbcr_enc", ctypes.c_uint32),
        ("quantization", ctypes.c_uint32),
        ("xfer_func", ctypes.c_uint32),
    ]


class V4L2FormatUnion(ctypes.Union):
    _fields_ = [
        ("pix", V4L2PixFormat),
        ("raw_data", ctypes.c_uint8 * 200),
    ]


class V4L2Format(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("fmt", V4L2FormatUnion),
    ]


class V4L2RequestBuffers(ctypes.Structure):
    _fields_ = [
        ("count", ctypes.c_uint32),
        ("type", ctypes.c_uint32),
        ("memory", ctypes.c_uint32),
        ("capabilities", ctypes.c_uint32),
        ("flags", ctypes.c_uint8),
        ("reserved", ctypes.c_uint8 * 3),
    ]


class V4L2Timeval(ctypes.Structure):
    _fields_ = [
        ("tv_sec", ctypes.c_long),
        ("tv_usec", ctypes.c_long),
    ]


class V4L2Timecode(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("frames", ctypes.c_uint8),
        ("seconds", ctypes.c_uint8),
        ("minutes", ctypes.c_uint8),
        ("hours", ctypes.c_uint8),
        ("userbits", ctypes.c_uint8 * 4),
    ]


class V4L2BufferMemory(ctypes.Union):
    _fields_ = [
        ("offset", ctypes.c_uint32),
        ("userptr", ctypes.c_ulong),
        ("planes", ctypes.c_void_p),
        ("fd", ctypes.c_int32),
    ]


class V4L2Buffer(ctypes.Structure):
    _fields_ = [
        ("index", ctypes.c_uint32),
        ("type", ctypes.c_uint32),
        ("bytesused", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("field", ctypes.c_uint32),
        ("timestamp", V4L2Timeval),
        ("timecode", V4L2Timecode),
        ("sequence", ctypes.c_uint32),
        ("memory", ctypes.c_uint32),
        ("m", V4L2BufferMemory),
        ("length", ctypes.c_uint32),
        ("reserved2", ctypes.c_uint32),
        ("request_fd", ctypes.c_int32),
    ]


class V4L2MjpegCamera(CameraBackend):
    name = "v4l2-mjpeg"

    V4L2_BUF_TYPE_VIDEO_CAPTURE = 1
    V4L2_MEMORY_MMAP = 1
    V4L2_FIELD_ANY = 0
    V4L2_PIX_FMT_MJPEG = fourcc("MJPG")

    Capability = V4L2Capability
    Format = V4L2Format
    RequestBuffers = V4L2RequestBuffers
    Buffer = V4L2Buffer

    @staticmethod
    def _ioc(direction: int, request_type: int, nr: int, size: int) -> int:
        nr_bits = 8
        type_bits = 8
        size_bits = 14
        nr_shift = 0
        type_shift = nr_shift + nr_bits
        size_shift = type_shift + type_bits
        dir_shift = size_shift + size_bits
        return (
            (direction << dir_shift)
            | (request_type << type_shift)
            | (nr << nr_shift)
            | (size << size_shift)
        )

    @classmethod
    def _ior(cls, nr: int, struct_type: type[ctypes.Structure]) -> int:
        return cls._ioc(2, ord("V"), nr, ctypes.sizeof(struct_type))

    @classmethod
    def _iow(cls, nr: int, struct_type: object) -> int:
        size = ctypes.sizeof(struct_type)
        return cls._ioc(1, ord("V"), nr, size)

    @classmethod
    def _iowr(cls, nr: int, struct_type: type[ctypes.Structure]) -> int:
        return cls._ioc(3, ord("V"), nr, ctypes.sizeof(struct_type))

    def __init__(self, device: str, width: int, height: int, fps: int) -> None:
        import fcntl

        self._fcntl = fcntl
        self.fd = os.open(device, os.O_RDWR | os.O_NONBLOCK)
        self.device = device
        self.buffers: list[mmap.mmap] = []
        self.streaming = False
        try:
            self._init_device(width, height, fps)
        except Exception:
            self.close()
            raise

    def _xioctl(self, request: int, arg: object) -> None:
        while True:
            try:
                self._fcntl.ioctl(self.fd, request, arg, True)
                return
            except OSError as exc:
                if exc.errno == errno.EINTR:
                    continue
                raise

    def _init_device(self, width: int, height: int, fps: int) -> None:
        capability = self.Capability()
        self._xioctl(self._ior(0, self.Capability), capability)
        card = capability.card.split(b"\0", 1)[0].decode("ascii", "replace")
        log(f"V4L2 camera: {card or self.device}")

        fmt = self.Format()
        fmt.type = self.V4L2_BUF_TYPE_VIDEO_CAPTURE
        fmt.fmt.pix.width = width
        fmt.fmt.pix.height = height
        fmt.fmt.pix.pixelformat = self.V4L2_PIX_FMT_MJPEG
        fmt.fmt.pix.field = self.V4L2_FIELD_ANY
        self._xioctl(self._iowr(5, self.Format), fmt)

        actual_format = fmt.fmt.pix.pixelformat
        actual_width = fmt.fmt.pix.width
        actual_height = fmt.fmt.pix.height
        if actual_format != self.V4L2_PIX_FMT_MJPEG:
            raise RuntimeError(
                "USB camera did not accept MJPEG mode. "
                "Try installing python3-opencv or fswebcam as fallback."
            )
        log(f"V4L2 format: MJPEG {actual_width}x{actual_height}, target {fps} fps")

        req = self.RequestBuffers()
        req.count = 4
        req.type = self.V4L2_BUF_TYPE_VIDEO_CAPTURE
        req.memory = self.V4L2_MEMORY_MMAP
        self._xioctl(self._iowr(8, self.RequestBuffers), req)
        if req.count < 2:
            raise RuntimeError("V4L2 did not allocate enough buffers")

        for index in range(req.count):
            buf = self.Buffer()
            buf.type = self.V4L2_BUF_TYPE_VIDEO_CAPTURE
            buf.memory = self.V4L2_MEMORY_MMAP
            buf.index = index
            self._xioctl(self._iowr(9, self.Buffer), buf)
            mapped = mmap.mmap(
                self.fd,
                buf.length,
                mmap.MAP_SHARED,
                mmap.PROT_READ | mmap.PROT_WRITE,
                offset=buf.m.offset,
            )
            self.buffers.append(mapped)

        for index in range(len(self.buffers)):
            buf = self.Buffer()
            buf.type = self.V4L2_BUF_TYPE_VIDEO_CAPTURE
            buf.memory = self.V4L2_MEMORY_MMAP
            buf.index = index
            self._xioctl(self._iowr(15, self.Buffer), buf)

        buf_type = ctypes.c_int(self.V4L2_BUF_TYPE_VIDEO_CAPTURE)
        self._xioctl(self._iow(18, buf_type), buf_type)
        self.streaming = True

    def read_jpeg(self) -> bytes:
        ready, _, _ = select.select([self.fd], [], [], 2.0)
        if not ready:
            raise TimeoutError("timed out waiting for V4L2 frame")

        buf = self.Buffer()
        buf.type = self.V4L2_BUF_TYPE_VIDEO_CAPTURE
        buf.memory = self.V4L2_MEMORY_MMAP
        self._xioctl(self._iowr(17, self.Buffer), buf)
        try:
            frame = self.buffers[buf.index][: buf.bytesused]
            data = bytes(frame)
        finally:
            self._xioctl(self._iowr(15, self.Buffer), buf)

        start = data.find(JPEG_SOI)
        end = data.rfind(JPEG_EOI)
        if start >= 0 and end > start:
            return data[start : end + len(JPEG_EOI)]
        return data

    def close(self) -> None:
        if getattr(self, "fd", None) is None:
            return
        if self.streaming:
            try:
                buf_type = ctypes.c_int(self.V4L2_BUF_TYPE_VIDEO_CAPTURE)
                self._xioctl(self._iow(19, buf_type), buf_type)
            except Exception:
                pass
            self.streaming = False
        for mapped in self.buffers:
            try:
                mapped.close()
            except Exception:
                pass
        self.buffers.clear()
        try:
            os.close(self.fd)
        except Exception:
            pass
        self.fd = None


class OpenCVCamera(CameraBackend):
    name = "opencv"

    def __init__(self, device: str, width: int, height: int, fps: int, quality: int) -> None:
        try:
            import cv2
        except Exception as exc:
            raise RuntimeError("OpenCV is not installed") from exc

        self.cv2 = cv2
        source: object = device
        if device.startswith("/dev/video"):
            suffix = device.removeprefix("/dev/video")
            if suffix.isdigit():
                source = int(suffix)
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            raise RuntimeError(f"OpenCV cannot open {device}")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.quality = int(quality)

    def read_jpeg(self) -> bytes:
        ok, frame = self.cap.read()
        if not ok:
            raise RuntimeError("OpenCV failed to read a frame")
        ok, encoded = self.cv2.imencode(
            ".jpg",
            frame,
            [int(self.cv2.IMWRITE_JPEG_QUALITY), self.quality],
        )
        if not ok:
            raise RuntimeError("OpenCV failed to encode a JPEG")
        return encoded.tobytes()

    def close(self) -> None:
        self.cap.release()


class FswebcamCamera(CameraBackend):
    name = "fswebcam"

    def __init__(self, device: str, width: int, height: int, quality: int) -> None:
        self.device = device
        self.width = width
        self.height = height
        self.quality = quality

    def read_jpeg(self) -> bytes:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            path = tmp.name
        try:
            command = [
                "fswebcam",
                "-q",
                "--no-banner",
                "-d",
                self.device,
                "-r",
                f"{self.width}x{self.height}",
                "--jpeg",
                str(self.quality),
                path,
            ]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            with open(path, "rb") as fh:
                return fh.read()
        finally:
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass


def build_camera(args: argparse.Namespace) -> CameraBackend:
    errors: list[str] = []
    order = ["v4l2", "opencv", "fswebcam"] if args.backend == "auto" else [args.backend]

    for backend in order:
        try:
            if backend == "v4l2":
                camera = V4L2MjpegCamera(args.device, args.width, args.height, args.fps)
            elif backend == "opencv":
                camera = OpenCVCamera(
                    args.device, args.width, args.height, args.fps, args.jpeg_quality
                )
            elif backend == "fswebcam":
                camera = FswebcamCamera(
                    args.device, args.width, args.height, args.jpeg_quality
                )
            else:
                raise ValueError(f"unknown backend: {backend}")
            log(f"Using camera backend: {camera.name}")
            return camera
        except Exception as exc:
            errors.append(f"{backend}: {exc}")
            log(f"Backend {backend} unavailable: {exc}")

    details = "\n".join(errors)
    raise RuntimeError(f"No camera backend could start:\n{details}")


class CameraWorker:
    def __init__(self, camera: CameraBackend, fps: int) -> None:
        self.camera = camera
        self.delay = max(0.02, 1.0 / max(1, fps))
        self.latest: Optional[bytes] = None
        self.frame_count = 0
        self.error: Optional[str] = None
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._loop, name="camera-worker", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def _loop(self) -> None:
        while not self.stop_event.is_set():
            started = time.monotonic()
            try:
                frame = self.camera.read_jpeg()
                if not frame.startswith(JPEG_SOI):
                    raise RuntimeError("captured data is not a JPEG frame")
                with self.lock:
                    self.latest = frame
                    self.frame_count += 1
                    self.error = None
            except Exception as exc:
                with self.lock:
                    self.error = str(exc)
                time.sleep(0.5)

            elapsed = time.monotonic() - started
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)

    def get_frame(self) -> Optional[bytes]:
        with self.lock:
            return self.latest

    def status(self) -> dict[str, object]:
        with self.lock:
            return {
                "backend": self.camera.name,
                "frames": self.frame_count,
                "has_frame": self.latest is not None,
                "error": self.error,
            }

    def close(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=2)
        self.camera.close()


def make_handler(worker: CameraWorker, fps: int) -> type[BaseHTTPRequestHandler]:
    boundary = b"frame"
    delay = max(0.02, 1.0 / max(1, fps))

    class Handler(BaseHTTPRequestHandler):
        server_version = "CHROUsbCamera/1.0"

        def log_message(self, fmt: str, *args: object) -> None:
            log(f"{self.client_address[0]} - {fmt % args}")

        def do_GET(self) -> None:
            if self.path in ("/", "/index.html"):
                self._send_html(build_preview_html())
                return
            if self.path.startswith("/health"):
                payload = json.dumps(worker.status(), ensure_ascii=False).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            if self.path.startswith("/snapshot.jpg"):
                self._send_snapshot()
                return
            if self.path.startswith("/stream.mjpg"):
                self._send_stream()
                return
            self.send_error(HTTPStatus.NOT_FOUND, "not found")

        def _send_text(self, text: str) -> None:
            payload = text.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _send_html(self, text: str) -> None:
            payload = text.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _send_snapshot(self) -> None:
            frame = worker.get_frame()
            if frame is None:
                self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, "camera frame not ready")
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(frame)))
            self.end_headers()
            self.wfile.write(frame)

        def _send_stream(self) -> None:
            self.send_response(HTTPStatus.OK)
            self.send_header(
                "Content-Type",
                "multipart/x-mixed-replace; boundary=frame",
            )
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

            while not worker.stop_event.is_set():
                frame = worker.get_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue
                try:
                    self.wfile.write(b"--" + boundary + b"\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii"))
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    return
                time.sleep(delay)

    return Handler


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CH-RO USB MJPEG camera server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--device", default="/dev/video0")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=int, default=8)
    parser.add_argument("--jpeg-quality", type=int, default=80)
    parser.add_argument(
        "--backend",
        choices=("auto", "v4l2", "opencv", "fswebcam"),
        default="auto",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    camera = build_camera(args)
    worker = CameraWorker(camera, args.fps)
    worker.start()

    handler = make_handler(worker, args.fps)
    server = ThreadingHTTPServer((args.host, args.port), handler)

    def shutdown(_signum: int, _frame: object) -> None:
        log("Shutting down")
        worker.close()
        server.shutdown()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    log(f"Preview URL: http://{args.host}:{args.port}/")
    log(f"Stream URL: http://{args.host}:{args.port}/stream.mjpg")
    log(f"Snapshot URL: http://{args.host}:{args.port}/snapshot.jpg")
    log("Use hostname -I on the Pi, then replace 0.0.0.0 with that LAN IP.")
    try:
        server.serve_forever()
    finally:
        worker.close()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
