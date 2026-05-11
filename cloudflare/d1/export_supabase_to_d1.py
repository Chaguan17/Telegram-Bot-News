"""Export Supabase rows into an idempotent Cloudflare D1 SQL import file.

Usage:
    python -m cloudflare.d1.export_supabase_to_d1 > cloudflare/d1/import.sql
"""

from bot.repositories.supabase_repository import create_supabase_client
from cloudflare.d1.migration import generate_d1_import_sql


TABLES = {
    "users": "chat_id, news_enabled, created_at, timezone",
    "sent_news": "news_hash, created_at",
    "command_log": "id, chat_id, command, created_at",
    "bot_health": "id, last_cron_at, last_cron_status, updated_at",
}


def fetch_snapshot(supabase) -> dict[str, list[dict]]:
    snapshot = {}
    for table, columns in TABLES.items():
        response = supabase.table(table).select(columns).execute()
        snapshot[table] = response.data or []
    return snapshot


def main() -> None:
    supabase = create_supabase_client()
    if not supabase:
        raise SystemExit("Supabase no está configurado.")
    print(generate_d1_import_sql(fetch_snapshot(supabase)), end="")


if __name__ == "__main__":
    main()
