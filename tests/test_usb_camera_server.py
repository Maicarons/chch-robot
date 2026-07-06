import importlib.util
import pathlib
import unittest


MODULE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "camera_servers"
    / "raspberry-pi-zero2w-usb-camera"
    / "usb_mjpeg_server.py"
)
SPEC = importlib.util.spec_from_file_location("usb_mjpeg_server", MODULE_PATH)
USB_CAMERA_SERVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(USB_CAMERA_SERVER)


class UsbCameraServerTests(unittest.TestCase):
    def test_preview_html_links_stream_snapshot_and_health(self):
        html = USB_CAMERA_SERVER.build_preview_html()

        self.assertIn("/stream.mjpg", html)
        self.assertIn("/snapshot.jpg", html)
        self.assertIn("/health", html)
        self.assertIn("<img", html)


if __name__ == "__main__":
    unittest.main()
