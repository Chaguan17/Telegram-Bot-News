import unittest

from bot.command_service import (
    ban_response,
    ban_target,
    command_from_text,
    extract_broadcast_text,
    help_text,
    news_messages,
    start_response,
    subscription_response,
    timezone_callback_response,
    timezone_keyboard_payload,
)


class CommandServiceTests(unittest.TestCase):
    def test_command_from_text_strips_bot_username(self):
        self.assertEqual(command_from_text("/start@MyBot hello"), "/start")

    def test_start_response_preserves_existing_states(self):
        self.assertIn("Suscrito", start_response({"status": "new"}))
        self.assertIn("desactivadas", start_response({"status": "existing", "news_enabled": False}))
        self.assertIn("Error", start_response({"status": "error"}))

    def test_subscription_response(self):
        self.assertIn("activadas", subscription_response("ok", enabled=True))
        self.assertIn("desactivadas", subscription_response("ok", enabled=False))
        self.assertIn("Primero", subscription_response("error", enabled=True))

    def test_help_text_includes_admin_commands_only_for_admin(self):
        self.assertNotIn("/broadcast", help_text(is_admin=False))
        self.assertIn("/broadcast", help_text(is_admin=True))

    def test_news_messages(self):
        self.assertIn("No he encontrado", news_messages([])[0])
        self.assertEqual(news_messages([{"message": "n1"}]), ["📰 **Top 3 Noticias de Impacto Actuales:**", "n1"])

    def test_timezone_keyboard_payload(self):
        payload = timezone_keyboard_payload()
        self.assertEqual(payload["inline_keyboard"][0][0]["callback_data"], "tz|Europe/Madrid")

    def test_broadcast_text_strips_github_action_hint(self):
        text = extract_broadcast_text(
            "/broadcast",
            reply_text="Release body\n---\n⚠️ *Para enviar a todos, respondé*",
        )
        self.assertEqual(text, "Release body")

    def test_ban_target_and_response(self):
        self.assertEqual(ban_target("/ban 123"), (123, None))
        self.assertIn("Usá", ban_target("/ban")[1])
        self.assertIn("número", ban_target("/ban abc")[1])
        self.assertIn("eliminado", ban_response("deleted", 123))
        self.assertIn("no encontrado", ban_response("not_found", 123))

    def test_timezone_callback_response(self):
        ok = timezone_callback_response("America/Caracas", True)
        self.assertFalse(ok["show_alert"])
        self.assertIn("America/Caracas", ok["message_text"])
        failed = timezone_callback_response("America/Caracas", False)
        self.assertTrue(failed["show_alert"])


if __name__ == "__main__":
    unittest.main()
