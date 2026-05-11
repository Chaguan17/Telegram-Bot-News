-- Cloudflare D1 schema for BNB Sentinel Bot.
-- D1 uses SQLite syntax, not PostgreSQL/Supabase types.

CREATE TABLE IF NOT EXISTS users (
    chat_id INTEGER PRIMARY KEY,
    news_enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    timezone TEXT NOT NULL DEFAULT 'Europe/Madrid'
);

CREATE TABLE IF NOT EXISTS sent_news (
    news_hash TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS command_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    command TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_command_log_created_at ON command_log(created_at);

CREATE TABLE IF NOT EXISTS bot_health (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    last_cron_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_cron_status TEXT NOT NULL DEFAULT 'ok',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO bot_health (id, last_cron_at, last_cron_status, updated_at)
VALUES (1, CURRENT_TIMESTAMP, 'ok', CURRENT_TIMESTAMP)
ON CONFLICT(id) DO NOTHING;
