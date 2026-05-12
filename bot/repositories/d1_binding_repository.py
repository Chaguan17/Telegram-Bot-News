from datetime import datetime, timedelta, timezone


class D1BindingRepository:
    """Async D1 binding adapter for Cloudflare Workers runtime."""

    def __init__(self, db):
        self.db = db

    @staticmethod
    def _results(result):
        if isinstance(result, dict):
            return result.get("results", [])
        return getattr(result, "results", [])

    @staticmethod
    def _value(row, key: str, default=None):
        if row is None:
            return default
        if isinstance(row, dict):
            return row.get(key, default)
        return getattr(row, key, default)

    async def _run(self, sql: str, *params):
        print(f"[D1] RUN: {sql} | PARAMS: {params}")
        statement = self.db.prepare(sql)
        if params:
            statement = statement.bind(*params)
        res = await statement.run()
        if not res.success:
            print(f"[D1] ERROR: {res.error}")
        return res

    async def _first(self, sql: str, *params):
        print(f"[D1] FIRST: {sql} | PARAMS: {params}")
        statement = self.db.prepare(sql)
        if params:
            statement = statement.bind(*params)
        res = await statement.first()
        
        # En Cloudflare Workers (Pyodide), res puede ser un PyProxy que represente null
        if res is None:
            return None
            
        try:
            py_res = res.to_py()
            # Si to_py devuelve None o un diccionario vacío, tratamos como No Result
            return py_res if py_res is not None else None
        except (AttributeError, Exception):
            # Fallback por si res no tiene to_py pero es un valor directo
            return res

    async def _all(self, sql: str, *params):
        print(f"[D1] ALL: {sql} | PARAMS: {params}")
        statement = self.db.prepare(sql)
        if params:
            statement = statement.bind(*params)
        res = await statement.all()
        try:
            # Convert JS Proxy to Python dict
            return res.to_py() if res is not None else {"results": [], "success": True}
        except (AttributeError, Exception):
            return res

    async def get_all_users(self) -> list:
        try:
            result = await self._all("SELECT chat_id FROM users")
            return [self._value(row, "chat_id") for row in self._results(result)]
        except Exception as e:
            print(f"Error en get_all_users: {e}")
            return []

    async def add_user(self, chat_id: int) -> dict:
        try:
            print(f"[D1] Intentando añadir/verificar usuario: {chat_id}")
            row = await self._first(
                "SELECT chat_id, news_enabled FROM users WHERE chat_id = ?",
                chat_id,
            )
            if row:
                print(f"[D1] Usuario {chat_id} ya existe.")
                return {"status": "existing", "news_enabled": bool(self._value(row, "news_enabled"))}
            
            print(f"[D1] Insertando nuevo usuario: {chat_id}")
            await self._run(
                "INSERT INTO users (chat_id, news_enabled) VALUES (?, 1)",
                chat_id,
            )
            return {"status": "new", "news_enabled": True}
        except Exception as e:
            print(f"[D1] ERROR en add_user: {e}")
            return {"status": "error"}

    async def set_news_enabled(self, chat_id: int, enabled: bool) -> str:
        try:
            await self._run(
                """
                INSERT INTO users (chat_id, news_enabled)
                VALUES (?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET news_enabled = excluded.news_enabled
                """,
                chat_id,
                1 if enabled else 0,
            )
            return "ok"
        except Exception as e:
            print(f"Error en set_news_enabled: {e}")
            return "error"

    async def get_user_timezone(self, chat_id: int) -> str:
        try:
            row = await self._first(
                "SELECT timezone FROM users WHERE chat_id = ?",
                chat_id,
            )
            timezone_name = self._value(row, "timezone")
            if timezone_name:
                return timezone_name
            return "Europe/Madrid"
        except Exception as e:
            print(f"Error en get_user_timezone: {e}")
            return "Europe/Madrid"

    async def set_user_timezone(self, chat_id: int, tz_string: str) -> bool:
        try:
            await self._run(
                "UPDATE users SET timezone = ? WHERE chat_id = ?",
                tz_string,
                chat_id,
            )
            return True
        except Exception as e:
            print(f"Error en set_user_timezone: {e}")
            return False

    async def get_news_subscribers(self) -> list:
        try:
            result = await self._all("SELECT chat_id FROM users WHERE news_enabled = 1")
            return [self._value(row, "chat_id") for row in self._results(result)]
        except Exception as e:
            print(f"Error en get_news_subscribers: {e}")
            return []

    async def is_news_sent(self, news_hash: str, chat_id: int) -> bool:
        try:
            row = await self._first(
                "SELECT news_hash FROM sent_news WHERE news_hash = ? AND chat_id = ? LIMIT 1",
                news_hash,
                int(chat_id),
            )
            # Chequeo ultra-estricto para evitar falsos positivos de PyProxy
            return bool(row and self._value(row, "news_hash"))
        except Exception as e:
            print(f"Error en is_news_sent: {e}")
            return False

    async def mark_news_sent(self, news_hash: str, chat_id: int) -> bool:
        try:
            await self._run(
                "INSERT OR IGNORE INTO sent_news (news_hash, chat_id) VALUES (?, ?)",
                news_hash,
                chat_id,
            )
            return True
        except Exception as e:
            print(f"Error en mark_news_sent: {e}")
            return False

    async def get_user_stats(self) -> dict:
        try:
            row = await self._first(
                """
                SELECT
                    COUNT(*) AS total,
                    COALESCE(SUM(CASE WHEN news_enabled = 1 THEN 1 ELSE 0 END), 0) AS subscribed
                FROM users
                """
            )
            total = self._value(row, "total", 0)
            subscribed = self._value(row, "subscribed", 0)
            return {"total": total, "subscribed": subscribed, "unsubscribed": total - subscribed}
        except Exception as e:
            print(f"Error en get_user_stats: {e}")
            return {"total": 0, "subscribed": 0, "unsubscribed": 0}

    async def ban_user(self, chat_id: int) -> str:
        try:
            row = await self._first("SELECT chat_id FROM users WHERE chat_id = ?", chat_id)
            if not row:
                return "not_found"
            await self._run("DELETE FROM users WHERE chat_id = ?", chat_id)
            return "deleted"
        except Exception as e:
            print(f"Error en ban_user: {e}")
            return "error"

    async def log_command(self, chat_id: int, command: str) -> None:
        try:
            await self._run(
                "INSERT INTO command_log (chat_id, command) VALUES (?, ?)",
                chat_id,
                command,
            )
        except Exception as e:
            print(f"Error en log_command: {e}")

    async def update_bot_health(self, status: str = "ok") -> None:
        try:
            now = datetime.now(timezone.utc).isoformat()
            await self._run(
                """
                INSERT OR REPLACE INTO bot_health (id, last_cron_at, last_cron_status, updated_at)
                VALUES (1, ?, ?, ?)
                """,
                now,
                status,
                now,
            )
        except Exception as e:
            print(f"Error en update_bot_health: {e}")

    async def get_dashboard_stats(self) -> dict:
        try:
            week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

            users = self._results(await self._all("SELECT news_enabled, created_at FROM users"))
            total_users = len(users)
            subscribed = sum(1 for user in users if self._value(user, "news_enabled"))

            commands = self._results(await self._all(
                "SELECT command, created_at FROM command_log WHERE created_at >= ?",
                week_ago,
            ))
            commands_by_type = {}
            commands_by_day = {}
            for entry in commands:
                command = self._value(entry, "command")
                day = self._value(entry, "created_at", "")[:10]
                commands_by_type[command] = commands_by_type.get(command, 0) + 1
                commands_by_day[day] = commands_by_day.get(day, 0) + 1

            sent_news = self._results(await self._all(
                "SELECT created_at FROM sent_news WHERE created_at >= ?",
                week_ago,
            ))
            news_by_day = {}
            for entry in sent_news:
                day = self._value(entry, "created_at", "")[:10]
                news_by_day[day] = news_by_day.get(day, 0) + 1

            new_users_by_day = {}
            for user in users:
                created = self._value(user, "created_at", "")
                if created and created >= week_ago:
                    day = created[:10]
                    new_users_by_day[day] = new_users_by_day.get(day, 0) + 1

            health = await self._first(
                "SELECT last_cron_at, last_cron_status, updated_at FROM bot_health WHERE id = 1"
            )
            total_news = await self._first("SELECT COUNT(DISTINCT news_hash) AS total FROM sent_news")

            return {
                "total_users": total_users,
                "subscribed": subscribed,
                "unsubscribed": total_users - subscribed,
                "total_commands_week": len(commands),
                "commands_by_type": commands_by_type,
                "commands_by_day": commands_by_day,
                "news_by_day": news_by_day,
                "new_users_by_day": new_users_by_day,
                "total_news_sent": self._value(total_news, "total", 0),
                "last_cron_at": self._value(health, "last_cron_at"),
                "last_cron_status": self._value(health, "last_cron_status"),
                "updated_at": self._value(health, "updated_at"),
            }
        except Exception as e:
            print(f"Error en get_dashboard_stats: {e}")
            return {"error": str(e)}
