# CH-RO Robot Documentation

CH-RO is a Xiangqi human-machine robot system. It combines ONNX-based board recognition, the Pikafish UCI engine, STM32 robot-arm control over TCP, and a Flask web control panel.

Use this documentation to install dependencies, configure cameras and robot targets, run the web UI, and understand the project layout.

## Main Capabilities

- USB or network camera capture.
- RTMPose and classifier ONNX inference.
- Board stabilization and dynamic move detection.
- Pikafish engine integration for Xiangqi AI moves.
- Simulation and hardware robot modes.
- STM32 five-value command protocol and homing handshake.

## Recommended Entry Points

- Start locally: [Getting Started](./guide/getting-started.md)
- Understand modules: [Architecture](./guide/architecture.md)
- Tune runtime values: [Configuration](./guide/configuration.md)
- Work on code: [Development](./guide/development.md)
