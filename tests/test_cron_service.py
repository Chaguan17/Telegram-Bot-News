import unittest

from bot.cron_service import run_news_cron, run_news_cron_async


class CronServiceTests(unittest.TestCase):
    def test_sends_only_unsent_news_to_subscribers_and_marks_once(self):
        sent_messages = []
        marked = []
        health = []

        result = run_news_cron(
            buscar_noticias=lambda: [
                {"hash": "old", "message": "old message"},
                {"hash": "new", "message": "new message"},
            ],
            get_news_subscribers=lambda: [1, 2],
            is_news_sent=lambda news_hash: news_hash == "old",
            mark_news_sent=marked.append,
            send_message=lambda chat_id, message: sent_messages.append((chat_id, message)),
            update_bot_health=health.append,
        )

        self.assertEqual(sent_messages, [(1, "new message"), (2, "new message")])
        self.assertEqual(marked, ["new"])
        self.assertEqual(health, ["ok"])
        self.assertEqual(result, {"status": "ok", "news_sent": 1, "send_errors": 0})

    def test_send_failures_do_not_block_other_users_or_marking(self):
        marked = []

        def send_message(chat_id, message):
            if chat_id == 1:
                raise RuntimeError("telegram unavailable")

        result = run_news_cron(
            buscar_noticias=lambda: [{"hash": "new", "message": "new message"}],
            get_news_subscribers=lambda: [1, 2],
            is_news_sent=lambda news_hash: False,
            mark_news_sent=marked.append,
            send_message=send_message,
            update_bot_health=lambda status: None,
        )

        self.assertEqual(marked, ["new"])
        self.assertEqual(result, {"status": "ok", "news_sent": 1, "send_errors": 1})


class AsyncCronServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_async_sends_only_unsent_news_to_subscribers_and_marks_once(self):
        sent_messages = []
        marked = []
        health = []

        async def buscar_noticias():
            return [
                {"hash": "old", "message": "old message"},
                {"hash": "new", "message": "new message"},
            ]

        async def get_news_subscribers():
            return [1, 2]

        async def is_news_sent(news_hash):
            return news_hash == "old"

        async def mark_news_sent(news_hash):
            marked.append(news_hash)

        async def send_message(chat_id, message):
            sent_messages.append((chat_id, message))

        async def update_bot_health(status):
            health.append(status)

        result = await run_news_cron_async(
            buscar_noticias=buscar_noticias,
            get_news_subscribers=get_news_subscribers,
            is_news_sent=is_news_sent,
            mark_news_sent=mark_news_sent,
            send_message=send_message,
            update_bot_health=update_bot_health,
        )

        self.assertEqual(sent_messages, [(1, "new message"), (2, "new message")])
        self.assertEqual(marked, ["new"])
        self.assertEqual(health, ["ok"])
        self.assertEqual(result, {"status": "ok", "news_sent": 1, "send_errors": 0})

    async def test_async_send_failures_do_not_block_other_users_or_marking(self):
        marked = []

        async def send_message(chat_id, message):
            if chat_id == 1:
                raise RuntimeError("telegram unavailable")

        result = await run_news_cron_async(
            buscar_noticias=lambda: [{"hash": "new", "message": "new message"}],
            get_news_subscribers=lambda: [1, 2],
            is_news_sent=lambda news_hash: False,
            mark_news_sent=marked.append,
            send_message=send_message,
            update_bot_health=lambda status: None,
        )

        self.assertEqual(marked, ["new"])
        self.assertEqual(result, {"status": "ok", "news_sent": 1, "send_errors": 1})


if __name__ == "__main__":
    unittest.main()
