"""
Command conversion and TCP transport for the robot arm.

The backend sends only the five-value command to NetAssist/STM32:
    startX,startY,endX,endY,signal

signal = 0 means a normal move, and signal = 1 means a capture sequence.
All motor angle conversion and pump sequencing now belong on the STM32 side.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
import socket
import threading
from typing import Callable, Mapping, Optional, Sequence


UCI_FILES = "abcdefghi"


@dataclass(frozen=True)
class BoardToArmConfig:
    """Map Xiangqi UCI squares to the arm coordinate system.

    The origin is the board's top-right intersection (black side, right rook).
    Horizontal intersections are 34 mm apart. Vertical intersections are
    normally 30 mm apart, except the river interval, which is 32 mm.
    """

    origin_x: int = 0
    origin_y: int = 0
    file_spacing_mm: int = 34
    rank_spacing_mm: int = 30
    river_spacing_mm: int = 32

    def __post_init__(self) -> None:
        if self.file_spacing_mm <= 0:
            raise ValueError("file spacing must be positive")
        if self.rank_spacing_mm <= 0:
            raise ValueError("rank spacing must be positive")
        if self.river_spacing_mm <= 0:
            raise ValueError("river spacing must be positive")

    def point_for_square(self, file_index: int, rank: int) -> tuple[int, int]:
        if not 0 <= file_index <= 8:
            raise ValueError(f"file index out of range: {file_index}")
        if not 0 <= rank <= 9:
            raise ValueError(f"rank out of range: {rank}")

        vertical_intervals = 9 - rank
        river_extra = (
            self.river_spacing_mm - self.rank_spacing_mm
            if rank <= 4
            else 0
        )
        return (
            self.origin_x + (8 - file_index) * self.file_spacing_mm,
            self.origin_y + vertical_intervals * self.rank_spacing_mm + river_extra,
        )


@dataclass(frozen=True)
class RobotArmCommand:
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    signal: int

    def __post_init__(self) -> None:
        if self.signal not in (0, 1):
            raise ValueError("signal must be 0 for normal moves or 1 for captures")

    @classmethod
    def from_sequence(cls, values: Sequence[int]) -> "RobotArmCommand":
        if len(values) != 5:
            raise ValueError("robot command must contain five integer values")
        return cls(*(int(value) for value in values))

    def to_tuple(self) -> list[int]:
        return [self.start_x, self.start_y, self.end_x, self.end_y, self.signal]

    def to_wire(self) -> str:
        return ",".join(str(value) for value in self.to_tuple())


@dataclass(frozen=True)
class RobotHomingCommand:
    """Direct relative motor angles used only for the startup homing cycle."""

    m1_angle_deg: float = -17.1848
    m2_angle_deg: float = -55.6304

    def __post_init__(self) -> None:
        if not math.isfinite(self.m1_angle_deg) or not math.isfinite(self.m2_angle_deg):
            raise ValueError("homing motor angles must be finite")

    def to_wire(self) -> str:
        return f"{self.m1_angle_deg:.4f},{self.m2_angle_deg:.4f},0,0,99"


@dataclass(frozen=True)
class RobotSendResult:
    success: bool
    command_text: str
    response: str = ""
    error: str = ""

    @property
    def acknowledged(self) -> bool:
        response = self.response.strip()
        return self.result_acknowledged and self.finish_state_acknowledged

    @property
    def result_acknowledged(self) -> bool:
        response = self.response.strip()
        return response == "1" or re.search(r"(?:^|[,\s])RESULT:1(?:[,\s]|$)", response) is not None

    @property
    def finish_state_acknowledged(self) -> bool:
        response = self.response.strip()
        return re.search(r"(?:^|[,\s])STATE:5(?:[,\s]|$)", response) is not None

    @property
    def motion_acknowledged(self) -> bool:
        """A normal move is complete only after STM32 reports STATE:5,RESULT:1."""

        if not self.acknowledged:
            return False

        command_ids = [
            int(match.group(1))
            for match in re.finditer(r"(?:^|,)\s*CMD:(-?\d+)\s*(?:,|$)", self.response.strip())
        ]
        return not any(command_id == 99 for command_id in command_ids)

    def acknowledged_for(self, command_id: int) -> bool:
        if not self.acknowledged:
            return False
        return re.search(
            rf"(?:^|,)\s*CMD:{int(command_id)}\s*(?:,|$)",
            self.response.strip(),
        ) is not None

    @property
    def homing_acknowledged(self) -> bool:
        """Accept the deployed idle reply and the newer command-tagged reply."""

        if not self.acknowledged:
            return False

        response = self.response.strip()
        if re.search(r"(?:^|,)\s*CMD:", response):
            return self.acknowledged_for(99)

        return re.search(r"(?:^|,)\s*STATE:5\s*(?:,|$)", response) is not None


def uci_to_arm_command(
    uci_move: str,
    board_state: Optional[Mapping[str, str]] = None,
    config: Optional[BoardToArmConfig] = None,
) -> RobotArmCommand:
    """Convert a Xiangqi UCI move into the STM32 five-value arm command."""

    if not uci_move or len(uci_move) < 4:
        raise ValueError(f"invalid UCI move: {uci_move!r}")

    start_file = _file_index(uci_move[0])
    start_rank = _rank_value(uci_move[1])
    end_file = _file_index(uci_move[2])
    end_rank = _rank_value(uci_move[3])
    arm_config = config or BoardToArmConfig()

    start_x, start_y = arm_config.point_for_square(start_file, start_rank)
    end_x, end_y = arm_config.point_for_square(end_file, end_rank)
    signal = 1 if _target_has_piece(board_state, end_file, end_rank) else 0

    return RobotArmCommand(start_x, start_y, end_x, end_y, signal)


def send_robot_command(
    command: RobotArmCommand,
    host: str = "127.0.0.1",
    port: int = 8086,
    timeout: float = 1.0,
) -> RobotSendResult:
    """Send a five-value robot command to NetAssist/lower controller.

    Hardware mode requires the lower controller to report completion. Simulation
    mode is handled by the web backend and must not reuse this transport.
    """

    if not isinstance(command, RobotArmCommand):
        raise TypeError("send_robot_command expects RobotArmCommand five-value payload")

    client = RobotPersistentClient(host, port, timeout)
    try:
        return client.send_robot_command(command, timeout=timeout)
    finally:
        client.close()


class RobotPersistentClient:
    """Reusable TCP client for STM32/ESP8266 command sessions."""

    COMMAND_TERMINATOR = "\r\n"

    def __init__(self, host: str = "127.0.0.1", port: int = 8086, timeout: float = 1.0):
        self.host = host
        self.port = int(port)
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._lock = threading.RLock()

    @property
    def is_connected(self) -> bool:
        return self._sock is not None

    def connect(self, timeout: float | None = None) -> socket.socket:
        if self._sock is None:
            sock = socket.create_connection((self.host, self.port), timeout=timeout or self.timeout)
            sock.settimeout(timeout or self.timeout)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            except OSError:
                pass
            try:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except OSError:
                pass
            self._sock = sock
        else:
            self._sock.settimeout(timeout or self.timeout)
        return self._sock

    def close(self) -> None:
        sock = self._sock
        self._sock = None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    def send_robot_command(
        self,
        command: RobotArmCommand,
        timeout: float | None = None,
    ) -> RobotSendResult:
        if not isinstance(command, RobotArmCommand):
            raise TypeError("send_robot_command expects RobotArmCommand five-value payload")

        return self._send_and_wait(
            command.to_wire(),
            ack_predicate=lambda result: result.motion_acknowledged,
            timeout=timeout,
            error_message="STM32 did not acknowledge command completion with STATE:5,RESULT:1",
        )

    def send_homing_command(
        self,
        command: RobotHomingCommand,
        timeout: float | None = None,
    ) -> RobotSendResult:
        if not isinstance(command, RobotHomingCommand):
            raise TypeError("send_homing_command expects RobotHomingCommand")

        return self._send_and_wait(
            command.to_wire(),
            ack_predicate=lambda result: result.homing_acknowledged,
            timeout=timeout,
            error_message=(
                "STM32 did not return the homing acknowledgement "
                "STATE:5,RESULT:1 or a CMD:99 success reply before timeout"
            ),
        )

    def _send_and_wait(
        self,
        command_text: str,
        ack_predicate: Callable[[RobotSendResult], bool],
        timeout: float | None,
        error_message: str,
    ) -> RobotSendResult:
        wire_payload = self._frame_command(command_text)
        with self._lock:
            response_parts: list[str] = []
            last_error = ""
            try:
                sock = self.connect(timeout=timeout)
                # Robot motions are non-idempotent; after bytes leave the PC,
                # missing ACK must be reported rather than retried automatically.
                sock.sendall(wire_payload.encode("ascii"))

                while True:
                    try:
                        chunk = sock.recv(1024)
                    except socket.timeout:
                        if not response_parts:
                            last_error = "STM32 TCP connection timed out without any reply"
                        break
                    if not chunk:
                        last_error = "STM32 TCP connection closed before acknowledgement"
                        break

                    response_parts.append(chunk.decode("ascii", errors="replace"))
                    result = RobotSendResult(
                        success=True,
                        command_text=command_text,
                        response="".join(response_parts).strip(),
                    )
                    if ack_predicate(result):
                        self._close_if_peer_already_closed(sock, timeout=timeout)
                        return result
            except OSError as exc:
                last_error = str(exc)
            self.close()

            response = "".join(response_parts).strip()
            return RobotSendResult(
                success=False,
                command_text=command_text,
                response=response,
                error=error_message if response else (last_error or error_message),
            )

    def _frame_command(self, command_text: str) -> str:
        return command_text.rstrip("\r\n") + self.COMMAND_TERMINATOR

    def _close_if_peer_already_closed(
        self,
        sock: socket.socket,
        timeout: float | None = None,
    ) -> None:
        peek_flag = getattr(socket, "MSG_PEEK", None)
        if peek_flag is None:
            return

        try:
            sock.settimeout(min(timeout or self.timeout, 0.05))
            chunk = sock.recv(1, peek_flag)
        except socket.timeout:
            return
        except OSError:
            self.close()
            return
        finally:
            if self._sock is sock:
                try:
                    sock.settimeout(timeout or self.timeout)
                except OSError:
                    self.close()

        if not chunk:
            self.close()


def send_homing_command(
    command: RobotHomingCommand,
    host: str = "127.0.0.1",
    port: int = 8086,
    timeout: float = 30.0,
) -> RobotSendResult:
    """Send startup homing angles and wait for the command-specific result."""

    if not isinstance(command, RobotHomingCommand):
        raise TypeError("send_homing_command expects RobotHomingCommand")

    client = RobotPersistentClient(host, port, timeout)
    try:
        return client.send_homing_command(command, timeout=timeout)
    finally:
        client.close()


def probe_robot_connection(
    host: str = "127.0.0.1",
    port: int = 8086,
    timeout: float = 1.0,
) -> RobotSendResult:
    """Check whether the STM32/ESP8266 TCP endpoint accepts connections."""

    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return RobotSendResult(success=True, command_text="")
    except OSError as exc:
        return RobotSendResult(success=False, command_text="", error=str(exc))


def _file_index(file_char: str) -> int:
    if file_char not in UCI_FILES:
        raise ValueError(f"invalid UCI file: {file_char!r}")
    return UCI_FILES.index(file_char)


def _rank_value(rank_char: str) -> int:
    if not rank_char.isdigit():
        raise ValueError(f"invalid UCI rank: {rank_char!r}")
    rank = int(rank_char)
    if not 0 <= rank <= 9:
        raise ValueError(f"invalid UCI rank: {rank}")
    return rank


def _target_has_piece(
    board_state: Optional[Mapping[str, str]],
    end_file: int,
    end_rank: int,
) -> bool:
    if not board_state:
        return False

    # app.py stores board keys as "col,row", with row 0 at black's home rank.
    target_key = f"{end_file},{9 - end_rank}"
    return target_key in board_state
