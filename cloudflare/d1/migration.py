from __future__ import annotations


TABLE_ORDER = ("users", "sent_news", "command_log", "bot_health")


def sql_literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int | float):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def insert_statement(table: str, row: dict, columns: tuple[str, ...]) -> str:
    values = ", ".join(sql_literal(row.get(column)) for column in columns)
    return f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES ({values});"


def generate_d1_import_sql(snapshot: dict[str, list[dict]]) -> str:
    """Generate idempotent D1 import SQL from a Supabase data snapshot."""
    lines = [
        "-- Generated Supabase -> Cloudflare D1 import.",
        "BEGIN TRANSACTION;",
    ]

    specs = {
        "users": ("chat_id", "news_enabled", "created_at", "timezone"),
        "sent_news": ("news_hash", "created_at"),
        "command_log": ("id", "chat_id", "command", "created_at"),
        "bot_health": ("id", "last_cron_at", "last_cron_status", "updated_at"),
    }

    for table in TABLE_ORDER:
        for row in snapshot.get(table, []):
            lines.append(insert_statement(table, row, specs[table]))

    lines.append("COMMIT;")
    return "\n".join(lines) + "\n"
