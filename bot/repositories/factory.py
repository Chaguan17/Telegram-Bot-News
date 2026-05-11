import os
import sqlite3
from pathlib import Path

from bot.repositories.d1_repository import D1Repository
from bot.repositories.supabase_repository import SupabaseRepository, create_supabase_client


DEFAULT_BACKEND = "supabase"
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "cloudflare" / "d1" / "schema.sql"


def create_d1_sqlite_connection(database_path: str | None = None):
    """Create a local SQLite connection that follows the D1 schema.

    This is a local migration seam, not the final Cloudflare binding adapter.
    """
    path = database_path or os.getenv("D1_DATABASE_PATH", ":memory:")
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8-sig"))
    connection.commit()
    return connection


def create_repository(backend: str | None = None, *, supabase_client=None, d1_connection=None):
    selected = (backend or os.getenv("BOT_DB_BACKEND", DEFAULT_BACKEND)).strip().lower()

    if selected == "supabase":
        client = supabase_client if supabase_client is not None else create_supabase_client()
        return SupabaseRepository(client)

    if selected in {"d1", "sqlite", "d1-sqlite"}:
        connection = d1_connection if d1_connection is not None else create_d1_sqlite_connection()
        return D1Repository(connection)

    raise ValueError(f"Unsupported BOT_DB_BACKEND: {selected}")
