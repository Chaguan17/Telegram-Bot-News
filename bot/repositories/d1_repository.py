from datetime import datetime, timedelta, timezone


class D1Repository:
    """SQLite/D1-compatible implementation of the bot persistence contract.

    The repository uses plain SQL so behavior can be verified locally with
    sqlite3 before wiring a Cloudflare D1 binding into the runtime.
    """

    def __init__(self, connection):
        self.connection = connection

    def _execute(self, sql: str, params=()):
        return self.connection.execute(sql, params)

    @staticmethod
    def _row_value(row, key: str):
        try:
            return row[key]
        except (TypeError, KeyError, IndexError):
            return getattr(row, key)

    def get_all_users(self) -> list:
        try:
            rows = self._execute("SELECT chat_id FROM users").fetchall()
            return [self._row_value(row, "chat_id") for row in rows]
        except Exception as e:
            print(f"Error en get_all_users: {e}")
            return []

    def add_user(self, chat_id: int) -> dict:
        try:
            row = self._execute(
                "SELECT chat_id, news_enabled FROM users WHERE chat_id = ?",
                (chat_id,),
            ).fetchone()
            if row:
                return {
                    "status": "existing",
                    "news_enabled": bool(self._row_value(row, "news_enabled")),
                }
            self._execute(
                "INSERT INTO users (chat_id, news_enabled) VALUES (?, 1)",
                (chat_id,),
            )
            self.connection.commit()
            return {"status": "new", "news_enabled": True}
        except Exception as e:
            print(f"Error en add_user: {e}")
            return {"status": "error"}

    def set_news_enabled(self, chat_id: int, enabled: bool) -> str:
        try:
            self._execute(
                """
                INSERT INTO users (chat_id, news_enabled)
                VALUES (?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET news_enabled = excluded.news_enabled
                """,
                (chat_id, 1 if enabled else 0),
            )
            self.connection.commit()
            return "ok"
        except Exception as e:
            print(f"Error en set_news_enabled: {e}")
            return "error"

    def get_user_timezone(self, chat_id: int) -> str:
        try:
            row = self._execute(
                "SELECT timezone FROM users WHERE chat_id = ?",
                (chat_id,),
            ).fetchone()
            if row and self._row_value(row, "timezone"):
                return self._row_value(row, "timezone")
            return "Europe/Madrid"
        except Exception as e:
            print(f"Error en get_user_timezone: {e}")
            return "Europe/Madrid"

    def set_user_timezone(self, chat_id: int, tz_string: str) -> bool:
        try:
            self._execute(
                "UPDATE users SET timezone = ? WHERE chat_id = ?",
                (tz_string, chat_id),
            )
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error en set_user_timezone: {e}")
            return False

    def get_news_subscribers(self) -> list:
        try:
            rows = self._execute(
                "SELECT chat_id FROM users WHERE news_enabled = 1"
            ).fetchall()
            return [self._row_value(row, "chat_id") for row in rows]
        except Exception as e:
            print(f"Error en get_news_subscribers: {e}")
            return []

    def is_news_sent(self, news_hash: str) -> bool:
        try:
            row = self._execute(
                "SELECT news_hash FROM sent_news WHERE news_hash = ?",
                (news_hash,),
            ).fetchone()
            return row is not None
        except Exception as e:
            print(f"Error en is_news_sent: {e}")
            return False

    def mark_news_sent(self, news_hash: str) -> bool:
        try:
            self._execute(
                "INSERT OR IGNORE INTO sent_news (news_hash) VALUES (?)",
                (news_hash,),
            )
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error en mark_news_sent: {e}")
            return False

    def get_user_stats(self) -> dict:
        try:
            row = self._execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COALESCE(SUM(CASE WHEN news_enabled = 1 THEN 1 ELSE 0 END), 0) AS subscribed
                FROM users
                """
            ).fetchone()
            total = self._row_value(row, "total")
            subscribed = self._row_value(row, "subscribed")
            return {
                "total": total,
                "subscribed": subscribed,
                "unsubscribed": total - subscribed,
            }
        except Exception as e:
            print(f"Error en get_user_stats: {e}")
            return {"total": 0, "subscribed": 0, "unsubscribed": 0}

    def ban_user(self, chat_id: int) -> str:
        try:
            row = self._execute(
                "SELECT chat_id FROM users WHERE chat_id = ?",
                (chat_id,),
            ).fetchone()
            if not row:
                return "not_found"
            self._execute("DELETE FROM users WHERE chat_id = ?", (chat_id,))
            self.connection.commit()
            return "deleted"
        except Exception as e:
            print(f"Error en ban_user: {e}")
            return "error"

    def log_command(self, chat_id: int, command: str) -> None:
        try:
            self._execute(
                "INSERT INTO command_log (chat_id, command) VALUES (?, ?)",
                (chat_id, command),
            )
            self.connection.commit()
        except Exception as e:
            print(f"Error en log_command: {e}")

    def update_bot_health(self, status: str = "ok") -> None:
        try:
            now = datetime.now(timezone.utc).isoformat()
            self._execute(
                """
                UPDATE bot_health
                SET last_cron_at = ?, last_cron_status = ?, updated_at = ?
                WHERE id = 1
                """,
                (now, status, now),
            )
            self.connection.commit()
        except Exception as e:
            print(f"Error en update_bot_health: {e}")

    def get_dashboard_stats(self) -> dict:
        try:
            week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

            users = self._execute(
                "SELECT news_enabled, created_at FROM users"
            ).fetchall()
            total_users = len(users)
            subscribed = sum(1 for user in users if self._row_value(user, "news_enabled"))

            commands = self._execute(
                "SELECT command, created_at FROM command_log WHERE created_at >= ?",
                (week_ago,),
            ).fetchall()
            commands_by_type = {}
            commands_by_day = {}
            for entry in commands:
                command = self._row_value(entry, "command")
                day = self._row_value(entry, "created_at")[:10]
                commands_by_type[command] = commands_by_type.get(command, 0) + 1
                commands_by_day[day] = commands_by_day.get(day, 0) + 1

            sent_news = self._execute(
                "SELECT created_at FROM sent_news WHERE created_at >= ?",
                (week_ago,),
            ).fetchall()
            news_by_day = {}
            for entry in sent_news:
                day = self._row_value(entry, "created_at")[:10]
                news_by_day[day] = news_by_day.get(day, 0) + 1

            new_users_by_day = {}
            for user in users:
                created = self._row_value(user, "created_at")
                if created and created >= week_ago:
                    day = created[:10]
                    new_users_by_day[day] = new_users_by_day.get(day, 0) + 1

            health = self._execute(
                "SELECT last_cron_at, last_cron_status, updated_at FROM bot_health WHERE id = 1"
            ).fetchone()
            total_news = self._execute("SELECT COUNT(*) AS total FROM sent_news").fetchone()

            return {
                "total_users": total_users,
                "subscribed": subscribed,
                "unsubscribed": total_users - subscribed,
                "total_commands_week": len(commands),
                "commands_by_type": commands_by_type,
                "commands_by_day": commands_by_day,
                "news_by_day": news_by_day,
                "new_users_by_day": new_users_by_day,
                "total_news_sent": self._row_value(total_news, "total"),
                "last_cron_at": self._row_value(health, "last_cron_at") if health else None,
                "last_cron_status": self._row_value(health, "last_cron_status") if health else None,
                "updated_at": self._row_value(health, "updated_at") if health else None,
            }
        except Exception as e:
            print(f"Error en get_dashboard_stats: {e}")
            return {"error": str(e)}
