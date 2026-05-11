import unittest

from bot.webhook_service import handle_telegram_update


class FakeRepository:
    def __init__(self):
        self.commands = []
        self.users = {}
        self.timezones = []
        self.all_users = [1, 2]
        self.banned = []

    async def log_command(self, chat_id, command):
        self.commands.append((chat_id, command))

    async def add_user(self, chat_id):
        return self.users.get(chat_id, {"status": "new", "news_enabled": True})

    async def set_news_enabled(self, chat_id, enabled):
        self.users[chat_id] = {"status": "existing", "news_enabled": enabled}
        return "ok"

    async def set_user_timezone(self, chat_id, tz_string):
        self.timezones.append((chat_id, tz_string))
        return True

    async def get_user_timezone(self, chat_id):
        return self.users.get(chat_id, {}).get("timezone", "America/Caracas")

    async def get_user_stats(self):
        return {"total": 2, "subscribed": 1, "unsubscribed": 1}

    async def get_all_users(self):
        return self.all_users

    async def ban_user(self, chat_id):
        self.banned.append(chat_id)
        return "deleted"


class FakeTelegram:
    def __init__(self):
        self.sent = []
        self.callback_answers = []
        self.edits = []
        self.fail_for = set()

    async def send_message(self, chat_id, message, **kwargs):
        if chat_id in self.fail_for:
            raise RuntimeError("telegram unavailable")
        self.sent.append((chat_id, message, kwargs))

    async def answer_callback_query(self, callback_query_id, text, **kwargs):
        self.callback_answers.append((callback_query_id, text, kwargs))

    async def edit_message_text(self, chat_id, message_id, text, **kwargs):
        self.edits.append((chat_id, message_id, text, kwargs))


class WebhookServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_command_registers_user_and_sends_response(self):
        repo = FakeRepository()
        telegram = FakeTelegram()

        result = await handle_telegram_update(
            {"message": {"chat": {"id": 42}, "text": "/start"}},
            repository=repo,
            telegram=telegram,
            admin_chat_id=1,
        )

        self.assertEqual(result, {"status": "ok", "command": "/start"})
        self.assertEqual(repo.commands, [(42, "/start")])
        self.assertIn("Bot Serverless", telegram.sent[0][1])

    async def test_timezone_command_sends_inline_keyboard_payload(self):
        repo = FakeRepository()
        telegram = FakeTelegram()

        await handle_telegram_update(
            {"message": {"chat": {"id": 42}, "text": "/timezone"}},
            repository=repo,
            telegram=telegram,
            admin_chat_id=1,
        )

        self.assertEqual(telegram.sent[0][2]["reply_markup"]["inline_keyboard"][0][0]["callback_data"], "tz|Europe/Madrid")

    async def test_prices_command_uses_injected_price_provider(self):
        repo = FakeRepository()
        telegram = FakeTelegram()

        result = await handle_telegram_update(
            {"message": {"chat": {"id": 42}, "text": "/prices"}},
            repository=repo,
            telegram=telegram,
            admin_chat_id=1,
            get_prices=lambda: "prices ok",
        )

        self.assertEqual(result, {"status": "ok", "command": "/prices"})
        self.assertEqual(repo.commands, [(42, "/prices")])
        self.assertEqual(telegram.sent[0][1], "prices ok")

    async def test_mercados_command_uses_user_timezone(self):
        repo = FakeRepository()
        repo.users[42] = {"timezone": "America/Caracas"}
        telegram = FakeTelegram()

        await handle_telegram_update(
            {"message": {"chat": {"id": 42}, "text": "/mercados"}},
            repository=repo,
            telegram=telegram,
            admin_chat_id=1,
            get_market_state=lambda tz_obj: f"markets {tz_obj.zone}",
        )

        self.assertEqual(telegram.sent[0][1], "markets America/Caracas")

    async def test_noticias_command_sends_news_messages(self):
        repo = FakeRepository()
        telegram = FakeTelegram()

        result = await handle_telegram_update(
            {"message": {"chat": {"id": 42}, "text": "/noticias"}},
            repository=repo,
            telegram=telegram,
            admin_chat_id=1,
            get_news=lambda: [{"message": "news one"}],
        )

        self.assertEqual(result, {"status": "ok", "command": "/noticias"})
        self.assertIn("Top 3", telegram.sent[0][1])
        self.assertEqual(telegram.sent[1][1], "news one")

    async def test_stats_requires_admin(self):
        repo = FakeRepository()
        telegram = FakeTelegram()

        result = await handle_telegram_update(
            {"message": {"chat": {"id": 42}, "text": "/stats"}},
            repository=repo,
            telegram=telegram,
            admin_chat_id=1,
        )

        self.assertEqual(result, {"status": "forbidden", "command": "/stats"})
        self.assertIn("exclusivo", telegram.sent[0][1])

    async def test_stats_admin_gets_stats(self):
        repo = FakeRepository()
        telegram = FakeTelegram()

        await handle_telegram_update(
            {"message": {"chat": {"id": 1}, "text": "/stats"}},
            repository=repo,
            telegram=telegram,
            admin_chat_id=1,
        )

        self.assertIn("Total registrados: 2", telegram.sent[0][1])

    async def test_ban_admin_deletes_user(self):
        repo = FakeRepository()
        telegram = FakeTelegram()

        result = await handle_telegram_update(
            {"message": {"chat": {"id": 1}, "text": "/ban 42"}},
            repository=repo,
            telegram=telegram,
            admin_chat_id=1,
        )

        self.assertEqual(result, {"status": "ok", "command": "/ban"})
        self.assertEqual(repo.banned, [42])
        self.assertIn("eliminado", telegram.sent[0][1])

    async def test_ban_requires_admin(self):
        repo = FakeRepository()
        telegram = FakeTelegram()

        result = await handle_telegram_update(
            {"message": {"chat": {"id": 42}, "text": "/ban 99"}},
            repository=repo,
            telegram=telegram,
            admin_chat_id=1,
        )

        self.assertEqual(result, {"status": "forbidden", "command": "/ban"})
        self.assertEqual(repo.banned, [])

    async def test_broadcast_admin_sends_to_all_users_and_reports(self):
        repo = FakeRepository()
        telegram = FakeTelegram()
        telegram.fail_for = {2}

        result = await handle_telegram_update(
            {"message": {"chat": {"id": 1}, "text": "/broadcast hola"}},
            repository=repo,
            telegram=telegram,
            admin_chat_id=1,
        )

        self.assertEqual(result, {"status": "ok", "command": "/broadcast", "sent": 1, "failed": 1})
        self.assertEqual(telegram.sent[0][0], 1)
        self.assertIn("Mensaje del admin", telegram.sent[0][1])
        self.assertIn("1 exitosos, 1 fallidos", telegram.sent[-1][1])

    async def test_broadcast_can_use_reply_text_and_strip_release_hint(self):
        repo = FakeRepository()
        telegram = FakeTelegram()

        await handle_telegram_update(
            {
                "message": {
                    "chat": {"id": 1},
                    "text": "/broadcast",
                    "reply_to_message": {"text": "Release body\n---\n⚠️ *Para enviar a todos"},
                }
            },
            repository=repo,
            telegram=telegram,
            admin_chat_id=1,
        )

        self.assertIn("Release body", telegram.sent[0][1])
        self.assertNotIn("Para enviar", telegram.sent[0][1])

    async def test_timezone_callback_updates_timezone_and_edits_message(self):
        repo = FakeRepository()
        telegram = FakeTelegram()

        result = await handle_telegram_update(
            {
                "callback_query": {
                    "id": "cb-1",
                    "data": "tz|America/Caracas",
                    "message": {"chat": {"id": 42}, "message_id": 7},
                }
            },
            repository=repo,
            telegram=telegram,
            admin_chat_id=1,
        )

        self.assertEqual(result, {"status": "ok", "callback": "timezone"})
        self.assertEqual(repo.timezones, [(42, "America/Caracas")])
        self.assertEqual(telegram.callback_answers[0][0], "cb-1")
        self.assertIn("America/Caracas", telegram.edits[0][2])


if __name__ == "__main__":
    unittest.main()
