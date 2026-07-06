# Robot Angle Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert AI moves into five-value coordinates, SCARA angle action plans, and TCP commands for the STM32F103C8 robot controller, with NetAssist status shown in the web system log.

**Architecture:** Keep coordinate conversion and network transport in `robot/protocol.py`, add SCARA kinematics and action-plan serialization there, and keep Flask as the workflow orchestrator. Add reference STM32F103C8 firmware files under `firmware/stm32-f103-angle-plan/` for parsing/executing the new command without modifying the original vendor zip.

**Tech Stack:** Python standard library, Flask backend, vanilla JavaScript frontend, STM32F103C8 C reference firmware.

---

### Task 1: Angle Plan Protocol Tests

**Files:**
- Modify: `tests/test_robot_protocol.py`

- [ ] Add failing tests for `build_motion_plan`, `ArmMotionPlan.to_wire()`, and `RobotSendResult.acknowledged`.
- [ ] Run `python -m unittest discover -s tests -p "test_robot_protocol.py" -v`; expected failure: imports for new functions/classes do not exist.

### Task 2: Python Angle Plan Implementation

**Files:**
- Modify: `robot/protocol.py`
- Modify: `robot/__init__.py`

- [ ] Add SCARA config dataclasses, IK solver, route generation for normal/capture moves, centidegree serialization, and STM32 response acknowledgement parsing.
- [ ] Run `python -m unittest discover -s tests -p "test_robot_protocol.py" -v`; expected success.

### Task 3: Flask AI Loop Integration

**Files:**
- Modify: `web_simulation/app.py`

- [ ] Build an angle plan immediately after the five-value command.
- [ ] Send the angle plan over TCP instead of the raw five-value command.
- [ ] Store five-value command text, angle plan text, host/port, send response/error, and human-readable robot log messages in `game_state['ai_analysis']`.
- [ ] Keep the 15 second simulated robot pause and vision resume behavior.

### Task 4: Frontend System Log Integration

**Files:**
- Modify: `web_simulation/static/js/app.js`

- [ ] In AI polling, when a bestmove is handled, write backend `robot_log_messages` into the existing system log.
- [ ] Keep current UI layout and avoid opening NetAssist automatically.

### Task 5: STM32F103C8 Reference Firmware

**Files:**
- Create: `firmware/stm32-f103-angle-plan/README.md`
- Create: `firmware/stm32-f103-angle-plan/arm_plan_protocol.h`
- Create: `firmware/stm32-f103-angle-plan/arm_plan_protocol.c`
- Create: `firmware/stm32-f103-angle-plan/optimized_motion_control.h`
- Create: `firmware/stm32-f103-angle-plan/optimized_motion_control.c`

- [ ] Provide bounded parser for `PLAN;<signal>;<step_count>;...`.
- [ ] Provide action execution helpers for `PICK`, `DROP`, `DROP_CAPTURE`, and `HOME`.
- [ ] Optimize motor control around integer centidegrees, trapezoid pulse generation, M3 down/up, pump dwell, and safe stop.
- [ ] Document how to merge the files into the Keil STM32F103C8 project.

### Task 6: Verification

**Files:**
- Read-only verification across changed files.

- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Run `python -m compileall robot web_simulation tests`.
- [ ] Run a backend smoke test that imports `web_simulation.app`, converts a sample move, and confirms the AI status payload can contain robot log messages.
- [ ] Restart the Flask server on port 5000 if it is already running from the old code.
