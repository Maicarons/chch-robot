# Architecture

## Runtime Flow

```text
Camera frame
  -> vision detector and classifier
  -> stabilized board state
  -> FEN and move history
  -> Pikafish UCI search
  -> robot coordinate conversion
  -> STM32 TCP command
```

## Main Modules

- `web_simulation/`: Flask backend, HTML template, CSS, and JavaScript UI.
- `vision/`: camera management, network camera support, detection, mapping, stabilization, and board recognition.
- `core/`: lower-level ONNX runtime wrappers.
- `ai/`: Pikafish process management and UCI protocol commands.
- `robot/`: board-to-arm coordinate conversion, TCP client, command protocol, and simulation controller.
- `model/`: ONNX model files used by the vision stack.
- `firmware/stm32-tcp-server/`: embedded C TCP server and robot-control firmware.
- `tests/`: protocol, backend loop, camera, recognizer, and stabilizer tests.

## Web Backend Notes

`web_simulation/app.py` currently owns routing and several runtime helpers. Pure board and mode helpers are being separated into `web_simulation/domain.py` to reduce coupling between Flask routes and game-state transformations.
