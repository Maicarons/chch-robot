# 开发

## 项目卫生

不要提交生成日志、虚拟环境、摄像头抓拍、下载的引擎和固件构建产物。行为覆盖放在 `tests/`，硬件相关逻辑优先通过 `simulation` 或 loopback 测试覆盖。

## 常用命令

```bash
python -m pytest tests/ -v
python -m py_compile web_simulation/app.py
npm run docs:dev
npm run docs:build
```

首次构建文档前安装依赖：

```bash
npm install
```

## 风格

- Python 使用 4 空格缩进和模块级 logger。
- 测试文件命名为 `tests/test_<area>.py`。
- 机器人协议变更需要覆盖 loopback 测试。
- Web UI 变更在 PR 中附截图或说明已验证的浏览器流程。

## 提交风格

近期历史使用简短的 Conventional Commit 风格标题，例如 `feat(vision): ...`、`feat(ai): ...`、`refactor(core): ...` 和 `docs: ...`。
