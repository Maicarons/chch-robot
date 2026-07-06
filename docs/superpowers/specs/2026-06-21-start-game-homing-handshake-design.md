# Start Game Homing Handshake Design

## Goal

Before a game starts, the web backend must connect to the STM32/ESP8266 TCP
server, send the exact homing command
`-17.1848,-55.6304,0,0,99`, wait for the arm to finish, and only then enable
the game and visual move recognition.

## Network Topology

- The STM32's ESP8266 is the TCP server at `192.168.0.101:8086`.
- The Python backend is the automated TCP client.
- NetAssist may connect to the same ESP8266 server as a manual diagnostic
  client, but it is not a relay and its socket cannot be controlled by the
  Python process.
- Both clients use ASCII payloads over TCP.

## Startup Flow

1. The page calls `/api/robot/status` before writing any other system log.
2. The backend probes `192.168.0.101:8086`.
3. The first system log reports whether the STM32 TCP service is reachable.
4. Clicking Start Game sends `-17.1848,-55.6304,0,0,99`.
5. The STM32 parses the floating-point motor angles and enters homing state.
6. It rotates M1 and M2, returns to idle, then replies `STATE:0,RESULT:1`.
7. The backend also accepts a newer command-tagged `CMD:99` success reply,
   while `STATE:5` remains reserved for normal move completion.
8. Only after acknowledgement does it initialize the standard board and mark
   the game as running.
9. The successful HTTP response causes the browser to start dynamic visual
   recognition.

## Failure Rules

- Connection failure, send failure, timeout, malformed reply, or
  `RESULT:0` keeps the game stopped.
- Start Game remains retryable after a failure.
- Normal move commands continue to use integer board coordinates with
  `signal=0` or `signal=1`.
- Normal moves must not satisfy the homing acknowledgement check.

## STM32 Reliability Changes

- Define the system-state enum once in `esp8266.h`.
- Validate the complete five-value payload, including trailing characters.
- Reject a second command while the controller is not idle.
- Send a command-specific completion response after homing.
- Keep safe-stop responses as failures.

## Verification

- Unit-test exact homing serialization and command-specific acknowledgement.
- Unit-test that the start endpoint remains stopped on failure and starts only
  after the homing acknowledgement.
- Test the status probe response.
- Run a local TCP fake STM32 to verify send/receive sequencing.
- Compile-check all Python files and inspect the Keil source paths selected by
  `stm32-f103-robot.uvprojx`.
