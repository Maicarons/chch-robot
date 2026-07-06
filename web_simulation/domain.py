"""Pure web-domain helpers for board state, turns, and request parameters."""

ROBOT_MODE_HARDWARE = "hardware"
ROBOT_MODE_SIMULATION = "simulation"
ROBOT_MODES = {ROBOT_MODE_HARDWARE, ROBOT_MODE_SIMULATION}
UCI_FILES = "abcdefghi"

STANDARD_INITIAL_BOARD = {
    "0,0": "r", "1,0": "n", "2,0": "b", "3,0": "a", "4,0": "k", "5,0": "a", "6,0": "b", "7,0": "n", "8,0": "r",
    "1,2": "c", "7,2": "c",
    "0,3": "p", "2,3": "p", "4,3": "p", "6,3": "p", "8,3": "p",
    "0,6": "P", "2,6": "P", "4,6": "P", "6,6": "P", "8,6": "P",
    "1,7": "C", "7,7": "C",
    "0,9": "R", "1,9": "N", "2,9": "B", "3,9": "A", "4,9": "K", "5,9": "A", "6,9": "B", "7,9": "N", "8,9": "R",
}
STANDARD_INITIAL_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"


def normalize_robot_mode(value=None):
    mode = (value or ROBOT_MODE_HARDWARE).strip().lower()
    if mode not in ROBOT_MODES:
        raise ValueError(f"invalid robot mode: {value!r}")
    return mode


def color_to_turn_char(color):
    return "w" if color == "red" else "b"


def turn_char_to_color(turn_char):
    return "red" if turn_char == "w" else "black"


def opposite_color(color):
    return "black" if color == "red" else "red"


def apply_turn_to_fen(fen, turn_color):
    fen_parts = fen.split()
    if len(fen_parts) >= 2:
        fen_parts[1] = color_to_turn_char(turn_color)
        return " ".join(fen_parts)
    return f"{fen} {color_to_turn_char(turn_color)} - - 0 1"


def board_pos_to_uci(pos):
    """Convert board array coordinates (col,row; row 0 at top) to Xiangqi UCI."""
    col, row = pos
    return f"{UCI_FILES[col]}{9 - row}"


def points_to_uci(from_pos, to_pos):
    return f"{board_pos_to_uci(from_pos)}{board_pos_to_uci(to_pos)}"


def parse_positive_int_parameter(raw_value, current_value, label):
    value = str(raw_value).strip()
    if not value:
        return int(current_value)
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be a positive integer") from exc
    if parsed <= 0:
        raise ValueError(f"{label} must be greater than 0")
    return parsed


def parse_robot_ip_parameter(raw_value, current_host):
    value = str(raw_value).strip()
    if not value:
        return str(current_host)

    if value.isdigit():
        octet = int(value)
        if 0 <= octet <= 255:
            return f"192.168.0.{octet}"
        raise ValueError("Robot IP last octet must be between 0 and 255")

    parts = value.split(".")
    if len(parts) != 4:
        raise ValueError("Robot IP must look like 192.168.0.102, or use only the last octet")

    octets = []
    for part in parts:
        if not part.isdigit():
            raise ValueError("Robot IP can only contain digits and dots")
        octet = int(part)
        if not 0 <= octet <= 255:
            raise ValueError("Each robot IP octet must be between 0 and 255")
        octets.append(str(octet))
    return ".".join(octets)


def apply_uci_to_board_state(board_state, uci_move):
    """Apply a UCI move to a string-key board state and return whether it captures."""
    if not uci_move or len(uci_move) < 4:
        return False

    from_col = UCI_FILES.index(uci_move[0])
    from_row = 9 - int(uci_move[1])
    to_col = UCI_FILES.index(uci_move[2])
    to_row = 9 - int(uci_move[3])
    from_key = f"{from_col},{from_row}"
    to_key = f"{to_col},{to_row}"

    piece = board_state.get(from_key)
    captured = to_key in board_state
    if piece:
        board_state.pop(from_key, None)
        board_state[to_key] = piece
    return captured


def board_state_to_fen(board_state, turn_color="red"):
    """Convert a string-key board state such as {"col,row": "piece"} to FEN."""
    board = [["." for _ in range(9)] for _ in range(10)]

    for pos_key, piece in board_state.items():
        col, row = map(int, pos_key.split(","))
        if 0 <= col < 9 and 0 <= row < 10:
            board[row][col] = piece

    fen_rows = []
    for row in range(10):
        fen_row = ""
        empty_count = 0
        for col in range(9):
            if board[row][col] == ".":
                empty_count += 1
            else:
                if empty_count > 0:
                    fen_row += str(empty_count)
                    empty_count = 0
                fen_row += board[row][col]
        if empty_count > 0:
            fen_row += str(empty_count)
        fen_rows.append(fen_row)

    return f"{'/'.join(fen_rows)} {color_to_turn_char(turn_color)} - - 0 1"


def serialize_board_state(board_state):
    """Convert tuple-key board states to JSON-safe string-key states."""
    return {f"{k[0]},{k[1]}": v for k, v in (board_state or {}).items()}


def deserialize_board_state(board_state):
    """Convert JSON string-key board states to tuple-key states."""
    converted = {}
    for pos_key, piece in (board_state or {}).items():
        col, row = map(int, pos_key.split(","))
        converted[(col, row)] = piece
    return converted


def is_red_piece(piece):
    """Chinese-chess piece chars use uppercase for red and lowercase for black."""
    return isinstance(piece, str) and piece.isupper()
