import sqlite3
import unittest
from pathlib import Path

from bot.repositories.d1_repository import D1Repository


SCHEMA = Path(__file__).resolve().parents[1] / "cloudflare" / "d1" / "schema.sql"


def create_repository():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA.read_text(encoding="utf-8-sig"))
    return D1Repository(connection)


class D1RepositoryTests(unittest.TestCase):
    def test_add_user_preserves_contract_for_new_and_existing_user(self):
        repo = create_repository()

        self.assertEqual(repo.add_user(42), {"status": "new", "news_enabled": True})
        repo.set_news_enabled(42, False)

        self.assertEqual(repo.add_user(42), {"status": "existing", "news_enabled": False})

    def test_subscription_timezone_and_user_stats(self):
        repo = create_repository()

        repo.add_user(1)
        repo.add_user(2)
        repo.set_news_enabled(2, False)
        repo.set_user_timezone(1, "America/Caracas")

        self.assertEqual(repo.get_news_subscribers(), [1])
        self.assertEqual(repo.get_user_timezone(1), "America/Caracas")
        self.assertEqual(repo.get_user_timezone(999), "Europe/Madrid")
        self.assertEqual(repo.get_user_stats(), {"total": 2, "subscribed": 1, "unsubscribed": 1})

    def test_news_dedupe_and_ban_user(self):
        repo = create_repository()

        self.assertFalse(repo.is_news_sent("abc"))
        self.assertTrue(repo.mark_news_sent("abc"))
        self.assertTrue(repo.is_news_sent("abc"))

        repo.add_user(42)
        self.assertEqual(repo.ban_user(42), "deleted")
        self.assertEqual(repo.ban_user(42), "not_found")

    def test_dashboard_stats_shape(self):
        repo = create_repository()

        repo.add_user(1)
        repo.log_command(1, "/start")
        repo.log_command(1, "/prices")
        repo.mark_news_sent("abc")
        repo.update_bot_health("ok")

        stats = repo.get_dashboard_stats()

        self.assertEqual(stats["total_users"], 1)
        self.assertEqual(stats["subscribed"], 1)
        self.assertEqual(stats["unsubscribed"], 0)
        self.assertEqual(stats["total_commands_week"], 2)
        self.assertEqual(stats["commands_by_type"], {"/start": 1, "/prices": 1})
        self.assertEqual(stats["total_news_sent"], 1)
        self.assertEqual(stats["last_cron_status"], "ok")
        self.assertIn("commands_by_day", stats)
        self.assertIn("news_by_day", stats)
        self.assertIn("new_users_by_day", stats)


if __name__ == "__main__":
    unittest.main()
