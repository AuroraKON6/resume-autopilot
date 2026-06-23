import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "mimo_ocr_agent.py"


def load_agent():
    spec = importlib.util.spec_from_file_location("mimo_ocr_agent_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


agent = load_agent()


def args(**overrides):
    base = {
        "platform": "boss",
        "dry_run": True,
        "auto_submit": True,
        "action_delay": 0,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def elements(*texts):
    return [{"text": text, "x": 100 + i * 50, "y": 200} for i, text in enumerate(texts)]


class BossSuccessDialogTests(unittest.TestCase):
    def test_boss_success_dialog_is_detected(self):
        self.assertTrue(
            agent.boss_success_dialog_detected(
                elements("\u5df2\u5411BOSS\u53d1\u9001\u6d88\u606f", "\u7559\u5728\u6b64\u9875", "\u7ee7\u7eed\u6c9f\u901a")
            )
        )

    def test_boss_success_dialog_requires_action_buttons(self):
        self.assertFalse(agent.boss_success_dialog_detected(elements("\u5df2\u5411BOSS\u53d1\u9001\u6d88\u606f")))

    def test_dismiss_boss_success_dialog_dry_run_is_safe(self):
        outcome = agent.dismiss_boss_success_dialog(
            elements("\u5df2\u5411BOSS\u53d1\u9001\u6d88\u606f", "\u7559\u5728\u6b64\u9875", "\u7ee7\u7eed\u6c9f\u901a"),
            args(dry_run=True),
        )
        self.assertEqual(outcome, "dry_run")

    def test_dismiss_boss_success_dialog_prefers_stay_button(self):
        clicks = []
        with patch.object(agent.pyautogui, "click", side_effect=lambda x, y: clicks.append((x, y))), \
             patch.object(agent.time, "sleep", return_value=None):
            outcome = agent.dismiss_boss_success_dialog(
                elements("\u5df2\u5411BOSS\u53d1\u9001\u6d88\u606f", "\u7559\u5728\u6b64\u9875", "\u7ee7\u7eed\u6c9f\u901a"),
                args(dry_run=False),
            )
        self.assertTrue(outcome.startswith("clicked_"))
        self.assertEqual(clicks[0], (150, 200))

    def test_dismiss_boss_success_dialog_clicks_left_of_continue_as_fallback(self):
        clicks = []
        with patch.object(agent.pyautogui, "click", side_effect=lambda x, y: clicks.append((x, y))), \
             patch.object(agent.pyautogui, "size", return_value=(2000, 1000)), \
             patch.object(agent.time, "sleep", return_value=None):
            outcome = agent.dismiss_boss_success_dialog(
                elements("\u5df2\u5411BOSS\u53d1\u9001\u6d88\u606f", "\u7ee7\u7eed\u6c9f\u901a"),
                args(dry_run=False),
            )
        self.assertEqual(outcome, "clicked_left_of_\u7ee7\u7eed\u6c9f\u901a")
        self.assertEqual(clicks[0], (40, 200))

    def test_continue_chat_click_is_blocked_on_boss(self):
        decision = {"action": "click", "text": "\u7ee7\u7eed\u6c9f\u901a"}
        self.assertTrue(agent.boss_continue_chat_decision(decision, args(platform="boss")))
        self.assertEqual(agent.execute_decision(decision, args(platform="boss")), "blocked_boss_continue_chat")

    def test_continue_chat_is_not_blocked_on_other_platforms(self):
        decision = {"action": "click", "text": "\u7ee7\u7eed\u6c9f\u901a", "x": -1, "y": -1}
        self.assertFalse(agent.boss_continue_chat_decision(decision, args(platform="liepin")))


class DecisionParsingTests(unittest.TestCase):
    def test_mimo_null_and_none_actions_become_wait(self):
        for raw in ['{"action": null}', '{"action": "None"}', '{"action": "noop"}', '{"action": ""}']:
            parsed = agent.parse_decision(raw)
            self.assertEqual(parsed["action"], "wait")
            self.assertIn("omitted action", parsed.get("reason", ""))

    def test_common_action_aliases_are_normalized(self):
        self.assertEqual(agent.parse_decision('{"action": "tap", "x": 1, "y": 2}')["action"], "click")
        back = agent.parse_decision('{"action": "back"}')
        self.assertEqual(back["action"], "hotkey")
        self.assertEqual(back["value"], ["alt", "left"])

    def test_unknown_action_fails_closed(self):
        parsed = agent.parse_decision('{"action": "unsupported_action"}')
        self.assertEqual(parsed["action"], "need_user")
        self.assertIn("unsupported", parsed["reason"])

    def test_extract_json_ignores_surrounding_text(self):
        parsed = agent.parse_decision("prefix ```json\n{\"action\":\"wait\"}\n``` suffix")
        self.assertEqual(parsed["action"], "wait")


class DetectionTests(unittest.TestCase):
    def test_success_detected_includes_boss_message_sent(self):
        self.assertTrue(agent.success_detected(elements("\u5df2\u5411BOSS\u53d1\u9001\u6d88\u606f")))

    def test_blocking_detection_still_catches_security_pages(self):
        self.assertTrue(agent.is_blocked(elements("\u9a8c\u8bc1\u7801", "\u5b89\u5168\u9a8c\u8bc1")))
        self.assertTrue(agent.is_blocked(elements("\u626b\u7801\u767b\u5f55", "\u4e8c\u7ef4\u7801\u767b\u5f55")))

    def test_prompt_forbids_boss_continue_chat(self):
        prompt = agent.build_prompt(
            SimpleNamespace(platform="boss", objective="test", keyword="test", count=1),
            elements("\u5df2\u5411BOSS\u53d1\u9001\u6d88\u606f", "\u7559\u5728\u6b64\u9875", "\u7ee7\u7eed\u6c9f\u901a"),
            1,
            0,
        )
        self.assertIn("\u7ee7\u7eed\u6c9f\u901a", prompt)
        self.assertIn("\u7559\u5728\u6b64\u9875", prompt)
        self.assertIn("Never", prompt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
