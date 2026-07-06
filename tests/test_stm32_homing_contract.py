from pathlib import Path
import unittest


STM32_ROOT = Path(__file__).resolve().parents[1] / "firmware" / "stm32-f103-keil-robot"


class Stm32HomingContractTests(unittest.TestCase):
    def setUp(self):
        self.header = (STM32_ROOT / "esp8266" / "esp8266.h").read_text(
            encoding="utf-8", errors="replace"
        )
        self.transport = (STM32_ROOT / "esp8266" / "esp8266.c").read_text(
            encoding="utf-8", errors="replace"
        )
        self.main = (STM32_ROOT / "robot_main.c").read_text(
            encoding="utf-8", errors="replace"
        )

    def test_system_state_enum_is_shared_by_transport_and_main(self):
        self.assertIn("SYS_HOMING", self.header)
        self.assertIn("extern volatile SystemState_TypeDef g_SystemState;", self.header)
        self.assertNotIn("typedef enum {", self.transport)
        self.assertNotIn("typedef enum {", self.main)

    def test_homing_completion_reply_contains_command_id(self):
        self.assertIn(
            'sprintf(buf, "STATE:%d,RESULT:%d,CMD:%d\\r\\n"',
            self.transport,
        )
        self.assertIn("ESP8266_Send_CommandResult(99, 1);", self.main)

    def test_homing_reports_finish_before_sending_success(self):
        finish_index = self.main.index("g_SystemState = SYS_FINISH;", self.main.index("signal == 99"))
        reply_index = self.main.index("ESP8266_Send_CommandResult(99, 1);")

        self.assertLess(finish_index, reply_index)

    def test_client_disconnect_keeps_server_ready_for_other_clients(self):
        closed_branch = self.transport[
            self.transport.index('strstr((char*)USART2_RX_BUF,"CLOSED")') :
        ]
        self.assertNotIn("AT_STEP = 6;", closed_branch.split("break;", 1)[0])


if __name__ == "__main__":
    unittest.main()
