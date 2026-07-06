# STM32F103C8 Five-Value Command Protocol

The Python backend now sends only the AI move command produced from the board:

```text
startX,startY,endX,endY,signal
```

Example:

```text
272,272,0,0,1
```

- `startX,startY`: source square position in the board/arm coordinate system.
- `endX,endY`: destination square position.
- `signal = 0`: normal move.
- `signal = 1`: capture move.

The coordinate origin is the top-right black line intersection when red is at
the bottom and black is at the top. The measured board dimensions are:

```text
horizontal interval = 34 mm
normal vertical interval = 30 mm
river interval = 32 mm
total width = 34 * 8 = 272 mm
total height = 30 * 8 + 32 = 272 mm
```

UCI square `i9` is `(0,0)` and `a0` is `(272,272)`. For ranks on the red side
of the river (`rank <= 4`), the Y coordinate includes the river's additional
`2 mm`.

NetAssist listens on port `8086`. The backend sends the ASCII payload directly;
a trailing newline is not required.

## STM32 Side

All SCARA inverse-kinematics, motor angle conversion, capture routing, pump
timing, lift motor timing, and homing should be handled in the STM32 firmware.

The receive parser can start from the original five-value branch:

```c
int sx, sy, ex, ey, capture;
if (sscanf(data, "%d,%d,%d,%d,%d", &sx, &sy, &ex, &ey, &capture) == 5) {
    /* Convert sx/sy/ex/ey to M1/M2 angles here.
       capture == 1 means run the capture sequence before moving the AI piece. */
}
```

The older `PLAN;...` angle-plan files in this folder are legacy references only
and are no longer sent by the Python backend.
