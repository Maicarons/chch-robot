import unittest

from web_simulation import domain


class WebDomainTests(unittest.TestCase):
    def test_robot_ip_parameter_accepts_last_octet_and_full_ip(self):
        self.assertEqual(
            domain.parse_robot_ip_parameter("103", "192.168.0.102"),
            "192.168.0.103",
        )
        self.assertEqual(
            domain.parse_robot_ip_parameter("192.168.0.104", "192.168.0.102"),
            "192.168.0.104",
        )
        self.assertEqual(
            domain.parse_robot_ip_parameter("", "192.168.0.102"),
            "192.168.0.102",
        )

    def test_board_state_to_fen_uses_red_and_black_turns(self):
        board = {"0,0": "r", "4,9": "K"}

        self.assertEqual(domain.board_state_to_fen(board, "red"), "r8/9/9/9/9/9/9/9/9/4K4 w - - 0 1")
        self.assertEqual(domain.board_state_to_fen(board, "black"), "r8/9/9/9/9/9/9/9/9/4K4 b - - 0 1")

    def test_apply_uci_to_board_state_moves_and_detects_capture(self):
        board = {"0,9": "R", "0,8": "p"}

        captured = domain.apply_uci_to_board_state(board, "a0a1")

        self.assertTrue(captured)
        self.assertEqual(board, {"0,8": "R"})


if __name__ == "__main__":
    unittest.main()
