"""
网络摄像头系统 - 快速验证脚本
检查所有组件是否正确配置
"""

import sys
import os

def check_imports():
    """检查必要的导入"""
    print("=" * 60)
    print("1. 检查Python导入")
    print("=" * 60)
    
    modules = [
        ('cv2', 'OpenCV'),
        ('numpy', 'NumPy'),
        ('asyncio', 'AsyncIO'),
        ('json', 'JSON'),
        ('base64', 'Base64'),
    ]
    
    all_ok = True
    for module, name in modules:
        try:
            __import__(module)
            print(f"✓ {name:20s} ({module})")
        except ImportError as e:
            print(f"✗ {name:20s} ({module}) - {e}")
            all_ok = False
    
    # websockets是可选的（可能未安装）
    try:
        import websockets
        print(f"✓ WebSockets           (websockets)")
    except ImportError:
        print(f"⚠ WebSockets           (websockets) - 未安装，运行: pip install websockets")
    
    print()
    return all_ok


def check_files():
    """检查文件是否存在"""
    print("=" * 60)
    print("2. 检查文件结构")
    print("=" * 60)
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    files = [
        'orange-pi-camera/camera_server.py',
        'orange-pi-camera/requirements.txt',
        'orange-pi-camera/start_server.sh',
        'orange-pi-camera/test_network_camera.py',
        'vision/network_camera.py',
        'vision/camera.py',
        'vision/recognizer.py',
        'config.py',
    ]
    
    all_exist = True
    for file_path in files:
        full_path = os.path.join(project_root, file_path)
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            print(f"✓ {file_path:40s} ({size:>6} bytes)")
        else:
            print(f"✗ {file_path:40s} - 不存在")
            all_exist = False
    
    print()
    return all_exist


def check_config():
    """检查配置文件"""
    print("=" * 60)
    print("3. 检查配置")
    print("=" * 60)
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(project_root, 'config.py')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = [
            ('USE_NETWORK_CAMERA', '网络摄像头开关'),
            ('NETWORK_CAMERA_URL', '网络摄像头URL'),
        ]
        
        all_ok = True
        for key, desc in checks:
            if key in content:
                # 提取值
                for line in content.split('\n'):
                    if line.strip().startswith(key):
                        print(f"✓ {desc:20s} - {line.strip()}")
                        break
            else:
                print(f"✗ {desc:20s} - 未找到配置项")
                all_ok = False
        
        print()
        return all_ok
        
    except Exception as e:
        print(f"✗ 读取配置文件失败: {e}")
        print()
        return False


def check_code_syntax():
    """检查代码语法"""
    print("=" * 60)
    print("4. 检查代码语法")
    print("=" * 60)
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    files = [
        'vision/camera.py',
        'vision/network_camera.py',
        'vision/recognizer.py',
        'orange-pi-camera/camera_server.py',
    ]
    
    all_ok = True
    for file_path in files:
        full_path = os.path.join(project_root, file_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                code = f.read()
            compile(code, full_path, 'exec')
            print(f"✓ {os.path.basename(file_path):30s} - 语法正确")
        except SyntaxError as e:
            print(f"✗ {os.path.basename(file_path):30s} - 语法错误: {e}")
            all_ok = False
        except Exception as e:
            print(f"⚠ {os.path.basename(file_path):30s} - 检查失败: {e}")
    
    print()
    return all_ok


def main():
    """主函数"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "网络摄像头系统验证" + " " * 23 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    results = []
    
    # 执行检查
    results.append(("导入检查", check_imports()))
    results.append(("文件检查", check_files()))
    results.append(("配置检查", check_config()))
    results.append(("语法检查", check_code_syntax()))
    
    # 汇总结果
    print("=" * 60)
    print("验证结果汇总")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name:20s} {status}")
        if not passed:
            all_passed = False
    
    print()
    
    if all_passed:
        print("🎉 所有检查通过！系统已就绪。")
        print()
        print("下一步:")
        print("1. 在香橙派上安装依赖: pip install -r orange-pi-camera/requirements.txt")
        print("2. 启动香橙派服务器: bash orange-pi-camera/start_server.sh")
        print("3. 在Windows上配置: orange-pi-camera\\configure_windows.bat")
        print("4. 测试连接: python orange-pi-camera\\test_network_camera.py")
    else:
        print("⚠️  部分检查未通过，请查看上面的详细信息。")
    
    print()
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
