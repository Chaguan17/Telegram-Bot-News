import unittest
from types import SimpleNamespace

from bot.repositories.d1_binding_repository import D1BindingRepository


class FakeStatement:
    def __init__(self, db, sql):
        self.db = db
        self.sql = sql
        self.params = ()

    def bind(self, *params):
        self.params = params
        return self

    async def run(self):
        self.db.calls.append(("run", self.sql, self.params))
        if "SELECT chat_id FROM users" in self.sql:
            return SimpleNamespace(results=[{"chat_id": 1}, {"chat_id": 2}], success=True)
        if "SELECT news_enabled, created_at FROM users" in self.sql:
            return SimpleNamespace(results=[
                {"news_enabled": 1, "created_at": "2099-01-01 00:00:00"},
                {"news_enabled": 0, "created_at": "2099-01-01 00:00:00"},
            ], success=True)
        if "SELECT command, created_at FROM command_log" in self.sql:
            return SimpleNamespace(results=[
                {"command": "/start", "created_at": "2099-01-01 00:00:00"},
                {"command": "/prices", "created_at": "2099-01-01 00:00:00"},
            ], success=True)
        if "SELECT created_at FROM sent_news" in self.sql:
            return SimpleNamespace(results=[{"created_at": "2099-01-01 00:00:00"}], success=True)
        return SimpleNamespace(results=[], success=True)

    async def all(self):
        # En este mock, all() devuelve lo mismo que run()
        return await self.run()

    async def first(self):
        self.db.calls.append(("first", self.sql, self.params))
        if self.params == ("sent", 1):
            return {"news_hash": "sent"}
        if "SELECT last_cron_at" in self.sql:
            return {
                "last_cron_at": "2099-01-01 00:00:00",
                "last_cron_status": "ok",
                "updated_at": "2099-01-01 00:00:00",
            }
        if "SELECT COUNT(DISTINCT news_hash) AS total FROM sent_news" in self.sql:
            return {"total": 7}
        return None


class FakeD1:
    def __init__(self):
        self.calls = []

    def prepare(self, sql):
        self.calls.append(("prepare", sql, ()))
        return FakeStatement(self, sql)


class D1BindingRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_news_subscribers_reads_results(self):
        db = FakeD1()
        repo = D1BindingRepository(db)

        self.assertEqual(await repo.get_news_subscribers(), [1, 2])

    async def test_row_access_supports_js_proxy_like_attributes(self):
        class ProxyStatement(FakeStatement):
            async def first(self):
                if "SELECT timezone FROM users" in self.sql:
                    return SimpleNamespace(timezone="America/Caracas")
                if "SELECT COUNT(DISTINCT news_hash) AS total FROM sent_news" in self.sql:
                    return SimpleNamespace(total=7)
                return await super().first()

            async def run(self):
                if "SELECT chat_id FROM users" in self.sql:
                    return SimpleNamespace(results=[
                        SimpleNamespace(chat_id=1),
                        SimpleNamespace(chat_id=2),
                    ])
                return await super().run()

        class ProxyD1(FakeD1):
            def prepare(self, sql):
                self.calls.append(("prepare", sql, ()))
                return ProxyStatement(self, sql)

        repo = D1BindingRepository(ProxyD1())

        self.assertEqual(await repo.get_user_timezone(42), "America/Caracas")
        self.assertEqual(await repo.get_all_users(), [1, 2])

    async def test_news_dedupe_uses_first_and_insert_or_ignore(self):
        db = FakeD1()
        repo = D1BindingRepository(db)

        self.assertTrue(await repo.is_news_sent("sent", 1))
        self.assertFalse(await repo.is_news_sent("new", 1))
        self.assertTrue(await repo.mark_news_sent("new", 1))

        self.assertTrue(any(call[0] == "run" and call[2] == ("new", 1) for call in db.calls))

    async def test_update_bot_health_writes_status(self):
        db = FakeD1()
        repo = D1BindingRepository(db)

        await repo.update_bot_health("ok")

        run_calls = [call for call in db.calls if call[0] == "run"]
        self.assertEqual(len(run_calls), 1)
        self.assertEqual(run_calls[0][2][1], "ok")

    async def test_get_dashboard_stats_matches_public_dashboard_shape(self):
        db = FakeD1()
        repo = D1BindingRepository(db)

        stats = await repo.get_dashboard_stats()

        self.assertEqual(stats["total_users"], 2)
        self.assertEqual(stats["subscribed"], 1)
        self.assertEqual(stats["unsubscribed"], 1)
        self.assertEqual(stats["total_commands_week"], 2)
        self.assertEqual(stats["commands_by_type"], {"/start": 1, "/prices": 1})
        self.assertEqual(stats["news_by_day"], {"2099-01-01": 1})
        self.assertEqual(stats["new_users_by_day"], {"2099-01-01": 2})
        self.assertEqual(stats["total_news_sent"], 7)
        self.assertEqual(stats["last_cron_status"], "ok")

    async def test_cleanup_old_data_executes_deletes(self):
        db = FakeD1()
        repo = D1BindingRepository(db)

        await repo.cleanup_old_data()

        run_calls = [call for call in db.calls if call[0] == "run"]
        # Debería haber 2 llamadas a DELETE
        self.assertEqual(len(run_calls), 2)
        self.assertTrue(any("DELETE FROM command_log" in call[1] for call in run_calls))
        self.assertTrue(any("DELETE FROM sent_news" in call[1] for call in run_calls))


if __name__ == "__main__":
    unittest.main()
