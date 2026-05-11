import unittest

from cloudflare.d1.migration import generate_d1_import_sql, sql_literal


class D1MigrationTests(unittest.TestCase):
    def test_sql_literal_escapes_strings_and_converts_booleans(self):
        self.assertEqual(sql_literal("Bob's bot"), "'Bob''s bot'")
        self.assertEqual(sql_literal(True), "1")
        self.assertEqual(sql_literal(False), "0")
        self.assertEqual(sql_literal(None), "NULL")

    def test_generate_d1_import_sql_is_ordered_and_idempotent(self):
        sql = generate_d1_import_sql({
            "users": [{
                "chat_id": 42,
                "news_enabled": True,
                "created_at": "2026-05-10 00:00:00",
                "timezone": "America/Caracas",
            }],
            "sent_news": [{"news_hash": "abc", "created_at": "2026-05-10 00:00:00"}],
            "command_log": [{
                "id": 1,
                "chat_id": 42,
                "command": "/start",
                "created_at": "2026-05-10 00:00:00",
            }],
            "bot_health": [{
                "id": 1,
                "last_cron_at": "2026-05-10 00:00:00",
                "last_cron_status": "ok",
                "updated_at": "2026-05-10 00:00:00",
            }],
        })

        self.assertTrue(sql.startswith("-- Generated Supabase -> Cloudflare D1 import.\nBEGIN TRANSACTION;"))
        self.assertIn("INSERT OR REPLACE INTO users", sql)
        self.assertIn("INSERT OR REPLACE INTO bot_health", sql)
        self.assertTrue(sql.endswith("COMMIT;\n"))


if __name__ == "__main__":
    unittest.main()
