import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import amazon_account_patrol as patrol


class PatrolSafetyTests(unittest.TestCase):
    def setUp(self):
        patrol.RUN_LOG_PATH = None

    def test_side_effecting_cli_timeout_is_not_retried(self):
        timeout = subprocess.TimeoutExpired(cmd=["ziniao-cli"], timeout=1)
        with (
            patch.object(patrol, "cli_path", return_value="ziniao-cli"),
            patch.object(patrol.subprocess, "run", side_effect=timeout) as run,
        ):
            with self.assertRaisesRegex(patrol.PatrolError, "not retried"):
                patrol.run_cli("page", "exec", retry_safe=False)
        self.assertEqual(run.call_count, 1)

    def test_read_only_cli_timeout_keeps_one_bounded_retry(self):
        timeout = subprocess.TimeoutExpired(cmd=["ziniao-cli"], timeout=1)
        success = subprocess.CompletedProcess(args=["ziniao-cli"], returncode=0, stdout="{}", stderr="")
        with (
            patch.object(patrol, "cli_path", return_value="ziniao-cli"),
            patch.object(patrol.subprocess, "run", side_effect=[timeout, success]) as run,
            patch.object(patrol.time, "sleep"),
        ):
            self.assertEqual(patrol.run_cli("page", "content"), {})
        self.assertEqual(run.call_count, 2)

    def test_screenshot_requires_a_real_file(self):
        with patch.object(patrol, "run_cli", return_value={"data": {"data": {"filePath": ""}}}):
            with self.assertRaisesRegex(patrol.PatrolError, "empty screenshot path"):
                patrol.page_screenshot("store")
        with patch.object(patrol, "run_cli", return_value={"data": {"data": {"filePath": "missing.png"}}}):
            with self.assertRaisesRegex(patrol.PatrolError, "does not exist"):
                patrol.page_screenshot("store")
        with tempfile.NamedTemporaryFile(suffix=".png") as image:
            with patch.object(patrol, "run_cli", return_value={"data": {"data": {"filePath": image.name}}}):
                self.assertTrue(Path(patrol.page_screenshot("store")).is_file())

    def test_marketplace_id_wins_when_parameter_is_present(self):
        wrong_id = "https://sellercentral.amazon.com/home?mons_sel_mkid=A2EUQ1WTGCTBG2"
        with patch.object(patrol, "page_state", return_value={"url": wrong_id, "text": "United States"}):
            with self.assertRaisesRegex(patrol.PatrolError, "marketplace verification failed"):
                patrol.verify_marketplace("store", "us")

        wrapped_id = "https://sellercentral.amazon.ca/home?mons_sel_mkid=amzn1.mp.o.ATVPDKIKX0DER"
        with patch.object(patrol, "page_state", return_value={"url": wrapped_id, "text": "United States"}):
            patrol.verify_marketplace("store", "us")

        with patch.object(
            patrol,
            "page_state",
            return_value={"url": "https://sellercentral.amazon.com/home", "text": "United States"},
        ):
            patrol.verify_marketplace("store", "us")

    def test_store_id_cannot_escape_output_filename(self):
        safe = patrol.safe_store_filename("../../x\\y")
        self.assertNotIn("/", safe)
        self.assertNotIn("\\", safe)
        self.assertNotEqual(safe, "../../x\\y")
        self.assertEqual(patrol.safe_store_filename("123456"), "123456")

    def test_markdown_persists_actual_urls_and_both_raw_pages(self):
        health_url = "https://sellercentral.amazon.com/performance/dashboard?ref=health"
        notice_url = "https://sellercentral.amazon.com/performance/notifications?ref=notice"
        with tempfile.TemporaryDirectory() as temp:
            image_paths = []
            for name in ("health.png", "notices.png"):
                path = Path(temp, name)
                path.write_bytes(b"png")
                image_paths.append(str(path))
            with (
                patch.object(patrol, "patrol_time_basis", return_value="local"),
                patch.object(patrol, "visit"),
                patch.object(patrol, "ensure_store_login"),
                patch.object(patrol, "select_marketplace"),
                patch.object(patrol, "verify_marketplace"),
                patch.object(
                    patrol,
                    "page_state",
                    side_effect=[
                        {"url": health_url, "text": "RAW HEALTH Healthy"},
                        {"url": notice_url, "text": "RAW NOTIFICATIONS"},
                    ],
                ),
                patch.object(patrol, "page_screenshot", side_effect=image_paths),
            ):
                result = patrol.patrol_market("123456", "us", None, None, Path(temp))
            record = Path(result["record"]).read_text(encoding="utf-8")
            self.assertIn(health_url, record)
            self.assertIn(notice_url, record)
            self.assertIn("RAW HEALTH Healthy", record)
            self.assertIn("RAW NOTIFICATIONS", record)
            self.assertNotIn("账号：未识别账号\\n", record)

    def test_feishu_requires_code_zero_and_message_id(self):
        with patch.object(patrol, "json_request", return_value={"code": 0, "data": {}}):
            with self.assertRaisesRegex(patrol.PatrolError, "message rejected"):
                patrol.feishu_send_message("token", "chat", "text", {"text": "x"})
        with patch.object(
            patrol,
            "json_request",
            return_value={"code": 0, "data": {"message_id": "om_123"}},
        ) as request:
            self.assertEqual(patrol.feishu_send_message("token", "chat", "text", {"text": "x"}), "om_123")
            self.assertFalse(request.call_args.kwargs["retry_safe"])


if __name__ == "__main__":
    unittest.main()
