"""
摄像头信号源归一化与 HTTP 候选地址构造。

将不同形式的摄像头来源（本地索引、RTSP/HTTP 网络流、MJPEG 快照端点）
统一为 OpenCV 可识别的形式，并为 HTTP 端点生成一组可尝试的取帧 URL。
"""

from typing import Union
from urllib.parse import urlparse, urlunparse

CameraSource = Union[int, str]
NETWORK_CAMERA_SCHEMES = {"http", "https", "rtsp", "rtmp"}
HTTP_CAMERA_SCHEMES = {"http", "https"}
HTTP_STREAM_PATHS = {
    "/stream",
    "/stream.mjpg",
    "/stream.mjpeg",
    "/mjpeg",
    "/video.mjpg",
    "/video.mjpeg",
}


def normalize_camera_source(source: CameraSource) -> CameraSource:
    """Return an OpenCV-ready local index or network camera URL."""
    if isinstance(source, int):
        return source

    if source is None:
        return 0

    text = str(source).strip()
    if not text:
        raise ValueError("camera source cannot be empty")

    if text.startswith("camera:"):
        text = text.split(":", 1)[1].strip()

    if text.isdigit():
        return int(text)

    parsed = urlparse(text)
    if parsed.scheme.lower() in NETWORK_CAMERA_SCHEMES and parsed.netloc:
        return text

    raise ValueError(f"unsupported camera source: {source!r}")


def is_network_camera_source(source: CameraSource) -> bool:
    return isinstance(normalize_camera_source(source), str)


def build_http_camera_candidate_urls(source: str) -> list[str]:
    """Return HTTP URLs to try for fetching one frame."""
    normalized = str(normalize_camera_source(source))
    parsed = urlparse(normalized)
    if parsed.scheme.lower() not in HTTP_CAMERA_SCHEMES:
        return [normalized]

    candidates = []

    def add_candidate(path: str = None, *, keep_query: bool = False):
        next_path = parsed.path if path is None else path
        next_query = parsed.query if keep_query else ""
        url = urlunparse(
            parsed._replace(path=next_path, query=next_query, params="", fragment="")
        )
        if url not in candidates:
            candidates.append(url)

    path = parsed.path or "/"
    path_lower = path.lower()

    if path_lower in ("", "/"):
        add_candidate("/snapshot.jpg")
        add_candidate("/frame.jpg")
        add_candidate("/stream.mjpg")
        add_candidate(path, keep_query=True)
        return candidates

    directory = path.rsplit("/", 1)[0]
    directory = f"{directory}/" if directory else "/"
    filename = path.rsplit("/", 1)[-1].lower()

    if path_lower in HTTP_STREAM_PATHS or filename in {"stream", "stream.mjpg", "stream.mjpeg", "mjpeg"}:
        add_candidate(path, keep_query=True)
        add_candidate(f"{directory}snapshot.jpg")
        add_candidate(f"{directory}frame.jpg")
        return candidates

    if filename in {"snapshot.jpg", "frame.jpg"}:
        add_candidate(path, keep_query=True)
        return candidates

    add_candidate(f"{directory}snapshot.jpg")
    add_candidate(f"{directory}frame.jpg")
    add_candidate(path, keep_query=True)
    return candidates
