# Development

## Project Hygiene

Keep generated logs, virtual environments, camera captures, downloaded engines, and firmware build outputs out of commits. Use `tests/` for behavior coverage and keep hardware-dependent code behind simulation or loopback tests where possible.

## Common Commands

```bash
python -m pytest tests/ -v
python -m py_compile web_simulation/app.py
npm run docs:dev
npm run docs:build
```

Install docs dependencies first:

```bash
npm install
```

## Style

- Python uses 4-space indentation and module-level loggers.
- Tests follow `tests/test_<area>.py`.
- Keep robot protocol changes covered by loopback tests.
- For web UI changes, include a screenshot or describe tested browser flows in the PR.

## Commit Style

Recent history uses short Conventional Commit-style subjects such as `feat(vision): ...`, `feat(ai): ...`, `refactor(core): ...`, and `docs: ...`.
