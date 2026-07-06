# Robot Angle Plan Design

## Goal

Move the robot control boundary from a raw five-value coordinate command to an upper-computer generated angle action plan. The web backend should still compute and display the five-value command, then convert it into SCARA M1/M2 relative angle steps plus pickup/drop actions, send that plan to TCP port 8086, and resume vision after the STM32F103C8 reports completion or after the existing local simulation pause.

## Protocol

The backend sends ASCII:

```text
PLAN;<signal>;<step_count>;<m1_centideg>,<m2_centideg>,<action>;...
```

Example:

```text
PLAN;0;3;-1713,3569,PICK;2276,-1962,DROP;-563,-1607,HOME
```

Angles are relative motor movements in centidegrees. `-1713` means `-17.13` degrees. This avoids expensive float parsing on STM32F103C8 while keeping the command readable in NetAssist.

Actions:

- `PICK`: rotate to source/captured piece, lower M3, pump on, wait 0.5s, raise M3.
- `DROP`: rotate to destination, lower M3, pump off, raise M3.
- `DROP_CAPTURE`: rotate to discard area, lower M3, pump off, raise M3.
- `HOME`: rotate back to the neutral/home point. No M3 or pump action.

## Motion Routes

Normal move (`signal=0`):

```text
HOME_POINT -> START(PICK) -> END(DROP) -> HOME_POINT(HOME)
```

Capture move (`signal=1`):

```text
HOME_POINT -> END(PICK) -> CAPTURE_DROP(DROP_CAPTURE) -> START(PICK) -> END(DROP) -> HOME_POINT(HOME)
```

Defaults match the existing lower-controller project:

- `L1 = 220mm`
- `L2 = 220mm`
- `base = (160, -40)`
- `HOME_POINT = (380, 180)`
- `CAPTURE_DROP = (-60, 180)`

## Web Logging

The backend includes `robot_log_messages` in `/api/ai_status`. The frontend writes these into the existing system log when the AI bestmove is handled:

- NetAssist target host/port
- five-value command
- angle plan summary
- TCP send result and STM32 response/error

## STM32F103C8 Runtime

The STM32 side should parse the new `PLAN` command into a bounded action array, execute each step through optimized motor functions, and return:

```text
STATE:5,RESULT:1
```

on success. The reference firmware files live under `firmware/stm32-f103-angle-plan/` so they can be merged into the Keil project without rewriting the original zip.
