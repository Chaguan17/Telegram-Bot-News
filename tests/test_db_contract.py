import importlib
import os
import sys
import types
import unittest
from unittest.mock import patch


class FakeResponse:
    def __init__(self, data=None, count=None):
        self.data = data or []
        if count is not None:
            self.count = count


class FakeTable:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def select(self, *args, **kwargs):
        self.calls.append(("select", args, kwargs))
        return self

    def eq(self, *args, **kwargs):
        self.calls.append(("eq", args, kwargs))
        return self

    def gte(self, *args, **kwargs):
        self.calls.append(("gte", args, kwargs))
        return self

    def insert(self, *args, **kwargs):
        self.calls.append(("insert", args, kwargs))
        return self

    def upsert(self, *args, **kwargs):
        self.calls.append(("upsert", args, kwargs))
        return self

    def update(self, *args, **kwargs):
        self.calls.append(("update", args, kwargs))
        return self

    def delete(self, *args, **kwargs):
        self.calls.append(("delete", args, kwargs))
        return self

    def execute(self):
        self.calls.append(("execute", (), {}))
        return self.response


class FakeClient:
    def __init__(self, table_responses):
        self.table_responses = {name: list(responses) for name, responses in table_responses.items()}
        self.tables = []

    def table(self, name):
        responses = self.table_responses[name]
        response = responses.pop(0) if responses else FakeResponse()
        table = FakeTable(response)
        self.tables.append((name, table))
        return table


def import_db_without_real_dependencies():
    sys.modules.pop("bot.db", None)
    sys.modules.pop("bot.repositories.factory", None)
    sys.modules.pop("bot.repositories.supabase_repository", None)
    sys.modules["dotenv"] = types.SimpleNamespace(load_dotenv=lambda: None)
    sys.modules["supabase"] = types.SimpleNamespace(
        Client=object,
        create_client=lambda url, key: None,
    )
    return importlib.import_module("bot.db")


class DbContractTests(unittest.TestCase):
    def test_add_user_returns_existing_user_without_insert(self):
        db = import_db_without_real_dependencies()
        client = FakeClient({"users": [FakeResponse([{"chat_id": 42, "news_enabled": False}])]})
        db.supabase = client
        db.reset_repository()

        result = db.add_user(42)

        self.assertEqual(result, {"status": "existing", "news_enabled": False})
        self.assertEqual(len(client.tables), 1)
        self.assertEqual(client.tables[0][0], "users")

    def test_add_user_inserts_new_enabled_user(self):
        db = import_db_without_real_dependencies()
        client = FakeClient({"users": [FakeResponse([]), FakeResponse([])]})
        db.supabase = client
        db.reset_repository()

        result = db.add_user(42)

        self.assertEqual(result, {"status": "new", "news_enabled": True})
        self.assertEqual(client.tables[1][1].calls[0], ("insert", ({"chat_id": 42, "news_enabled": True},), {}))

    def test_get_news_subscribers_returns_enabled_chat_ids(self):
        db = import_db_without_real_dependencies()
        client = FakeClient({"users": [FakeResponse([{"chat_id": 1}, {"chat_id": 2}])]})
        db.supabase = client
        db.reset_repository()

        self.assertEqual(db.get_news_subscribers(), [1, 2])

    def test_missing_supabase_keeps_safe_fallbacks(self):
        db = import_db_without_real_dependencies()
        db.supabase = None
        db.reset_repository()

        self.assertEqual(db.get_all_users(), [])
        self.assertEqual(db.add_user(1), {"status": "error"})
        self.assertEqual(db.set_news_enabled(1, True), "error")
        self.assertEqual(db.get_user_timezone(1), "Europe/Madrid")
        self.assertFalse(db.is_news_sent("abc"))
        self.assertEqual(db.get_user_stats(), {"total": 0, "subscribed": 0, "unsubscribed": 0})

    def test_d1_backend_can_be_selected_without_api_callers_changing(self):
        db = import_db_without_real_dependencies()

        with patch.dict(os.environ, {"BOT_DB_BACKEND": "d1"}, clear=False):
            db.reset_repository()
            self.assertEqual(db.add_user(42), {"status": "new", "news_enabled": True})
            self.assertEqual(db.get_all_users(), [42])
            self.assertEqual(db.get_user_stats(), {"total": 1, "subscribed": 1, "unsubscribed": 0})


if __name__ == "__main__":
    unittest.main()
