# Start Game Homing Handshake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gate game startup and visual recognition on a confirmed STM32 homing operation.

**Architecture:** Add a homing-specific command and TCP acknowledgement contract to the robot protocol, expose connection status and guarded startup through Flask, then make the browser log the robot connection first. Update the actual Keil ESP8266 source and main loop to return a command-specific completion result.

**Tech Stack:** Python 3, Flask, browser JavaScript, STM32F103 C, ESP8266 AT TCP server.

---

### Task 1: Robot Protocol

**Files:**
- Modify: `robot/protocol.py`
- Modify: `robot/__init__.py`
- Test: `tests/test_robot_protocol.py`

- [ ] Add failing tests for exact homing wire format, homing acknowledgement, timeout failure, and TCP endpoint probing.
- [ ] Run the focused protocol tests and confirm they fail because the homing APIs do not exist.
- [ ] Implement `RobotHomingCommand`, `send_homing_command`, and `probe_robot_connection`.
- [ ] Run the focused protocol tests and confirm they pass.

### Task 2: Guarded Flask Startup

**Files:**
- Modify: `config.py`
- Modify: `web_simulation/app.py`
- Test: `tests/test_robot_backend_loop.py`

- [ ] Add failing tests proving that startup sends homing first, starts only after `CMD:99`, and remains stopped after failure.
- [ ] Add a failing test for `/api/robot/status`.
- [ ] Run the focused backend tests and confirm expected failures.
- [ ] Configure `192.168.0.101:8086`, homing angles, and timeout.
- [ ] Implement the status endpoint and homing startup gate.
- [ ] Run focused backend tests and confirm they pass.

### Task 3: Browser Ordering

**Files:**
- Modify: `web_simulation/static/js/app.js`

- [ ] Make initialization await robot status before other startup work.
- [ ] Log STM32 connectivity as the first system-log entry.
- [ ] Show homing send, wait, success, and failure details during Start Game.
- [ ] Disable Start Game while the request is active.

### Task 4: STM32 Command Lifecycle

**Files:**
- Modify: `firmware/stm32-f103-keil-robot/esp8266/esp8266.h`
- Modify: `firmware/stm32-f103-keil-robot/esp8266/esp8266.c`
- Modify: `firmware/stm32-f103-keil-robot/robot_main.c`

- [ ] Move the shared system-state enum to the ESP8266 header.
- [ ] Harden five-value parsing and idle-state command acceptance.
- [ ] Send `STATE:5,RESULT:1,CMD:99` only after both homing rotations finish.
- [ ] Preserve existing normal move and safe-stop behavior.

### Task 5: Verification

**Files:**
- Modify: `C:/CodexWork/CODEX_MEMORY.md`

- [ ] Run the complete Python test suite.
- [ ] Run Python compile checks.
- [ ] Run a fake STM32 TCP integration test for exact payload and acknowledgement.
- [ ] Verify the Keil project references the edited ESP8266 source.
- [ ] Update durable workspace memory with the final protocol and endpoint.
