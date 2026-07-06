"""Verify the Orange Pi camera server files and local Python environment."""

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]


def check_imports():
    print("=" * 60)
    print("1. Checking Python imports")
    print("=" * 60)

    modules = [
        ("cv2", "OpenCV"),
        ("numpy", "NumPy"),
        ("asyncio", "AsyncIO"),
        ("json", "JSON"),
        ("base64", "Base64"),
    ]

    all_ok = True
    for module, name in modules:
        try:
            __import__(module)
            print(f"[OK]   {name:20s} ({module})")
        except ImportError as exc:
            print(f"[MISS] {name:20s} ({module}) - {exc}")
            all_ok = False

    try:
        __import__("websockets")
        print("[OK]   WebSockets           (websockets)")
    except ImportError:
        print("[WARN] WebSockets           (websockets) - install with: pip install websockets")

    print()
    return all_ok


def check_files():
    print("=" * 60)
    print("2. Checking repository files")
    print("=" * 60)

    files = [
        "camera_servers/orange-pi-camera/camera_server.py",
        "camera_servers/orange-pi-camera/requirements.txt",
        "camera_servers/orange-pi-camera/start_server.sh",
        "camera_servers/orange-pi-camera/test_network_camera.py",
        "vision/network_camera.py",
        "vision/camera.py",
        "vision/recognizer.py",
        "config.py",
    ]

    all_exist = True
    for rel_path in files:
        path = REPO_ROOT / rel_path
        if path.exists():
            print(f"[OK]   {rel_path:55s} ({path.stat().st_size:>6} bytes)")
        else:
            print(f"[MISS] {rel_path}")
            all_exist = False

    print()
    return all_exist


def check_config():
    print("=" * 60)
    print("3. Checking config.py")
    print("=" * 60)

    config_path = REPO_ROOT / "config.py"
    try:
        content = config_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"[MISS] Could not read config.py: {exc}")
        print()
        return False

    keys = [
        ("USE_IP_CAMERA", "network camera switch"),
        ("IP_CAMERA_URL", "network camera URL"),
    ]

    all_ok = True
    for key, desc in keys:
        matching = [line.strip() for line in content.splitlines() if line.strip().startswith(key)]
        if matching:
            print(f"[OK]   {desc:24s} - {matching[0]}")
        else:
            print(f"[MISS] {desc:24s} - {key}")
            all_ok = False

    print()
    return all_ok


def check_code_syntax():
    print("=" * 60)
    print("4. Checking Python syntax")
    print("=" * 60)

    files = [
        "vision/camera.py",
        "vision/network_camera.py",
        "vision/recognizer.py",
        "camera_servers/orange-pi-camera/camera_server.py",
        "camera_servers/orange-pi-camera/test_network_camera.py",
    ]

    all_ok = True
    for rel_path in files:
        path = REPO_ROOT / rel_path
        try:
            code = path.read_text(encoding="utf-8", errors="replace")
            compile(code, str(path), "exec")
            print(f"[OK]   {rel_path}")
        except SyntaxError as exc:
            print(f"[FAIL] {rel_path} - syntax error: {exc}")
            all_ok = False
        except OSError as exc:
            print(f"[FAIL] {rel_path} - read failed: {exc}")
            all_ok = False

    print()
    return all_ok


def main():
    print()
    print("=" * 60)
    print("Orange Pi camera server verification")
    print("=" * 60)
    print()

    results = [
        ("Imports", check_imports()),
        ("Files", check_files()),
        ("Config", check_config()),
        ("Syntax", check_code_syntax()),
    ]

    print("=" * 60)
    print("Summary")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        print(f"{name:16s} {'PASS' if passed else 'FAIL'}")
        all_passed = all_passed and passed

    print()
    if all_passed:
        print("All checks passed.")
        print("Next steps:")
        print("1. Install dependencies: pip install -r camera_servers/orange-pi-camera/requirements.txt")
        print("2. Start server: bash camera_servers/orange-pi-camera/start_server.sh")
        print("3. Test connection: python camera_servers/orange-pi-camera/test_network_camera.py")
    else:
        print("Some checks failed. Review the messages above.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
