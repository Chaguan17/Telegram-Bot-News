import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client


class SupabaseRepository:
    """Supabase-backed implementation of the bot persistence contract."""

    def __init__(self, supabase: Client | None):
        self.supabase = supabase

    def get_all_users(self) -> list:
        if not self.supabase: return []
        try:
            response = self.supabase.table("users").select("chat_id").execute()
            return [user["chat_id"] for user in response.data]
        except Exception as e:
            print(f"Error en get_all_users: {e}")
            return []

    def add_user(self, chat_id: int) -> dict:
        if not self.supabase: return {"status": "error"}
        try:
            response = self.supabase.table("users").select("chat_id, news_enabled").eq("chat_id", chat_id).execute()
            if response.data:
                return {"status": "existing", "news_enabled": response.data[0]["news_enabled"]}
            self.supabase.table("users").insert({"chat_id": chat_id, "news_enabled": True}).execute()
            return {"status": "new", "news_enabled": True}
        except Exception as e:
            print(f"Error en add_user: {e}")
            return {"status": "error"}

    def set_news_enabled(self, chat_id: int, enabled: bool) -> str:
        if not self.supabase: return "error"
        try:
            self.supabase.table("users").upsert({"chat_id": chat_id, "news_enabled": enabled}).execute()
            return "ok"
        except Exception as e:
            print(f"Error en set_news_enabled: {e}")
            return "error"

    def get_user_timezone(self, chat_id: int) -> str:
        if not self.supabase: return "Europe/Madrid"
        try:
            response = self.supabase.table("users").select("timezone").eq("chat_id", chat_id).execute()
            if response.data and response.data[0].get("timezone"):
                return response.data[0]["timezone"]
            return "Europe/Madrid"
        except Exception as e:
            print(f"Error en get_user_timezone: {e}")
            return "Europe/Madrid"

    def set_user_timezone(self, chat_id: int, tz_string: str) -> bool:
        if not self.supabase: return False
        try:
            self.supabase.table("users").update({"timezone": tz_string}).eq("chat_id", chat_id).execute()
            return True
        except Exception as e:
            print(f"Error en set_user_timezone: {e}")
            return False

    def get_news_subscribers(self) -> list:
        if not self.supabase: return []
        try:
            response = self.supabase.table("users").select("chat_id").eq("news_enabled", True).execute()
            return [user["chat_id"] for user in response.data]
        except Exception as e:
            print(f"Error en get_news_subscribers: {e}")
            return []

    def is_news_sent(self, news_hash: str) -> bool:
        if not self.supabase: return False
        try:
            response = self.supabase.table("sent_news").select("news_hash").eq("news_hash", news_hash).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"Error en is_news_sent: {e}")
            return False

    def mark_news_sent(self, news_hash: str) -> bool:
        if not self.supabase: return False
        try:
            self.supabase.table("sent_news").upsert({"news_hash": news_hash}).execute()
            return True
        except Exception as e:
            print(f"Error en mark_news_sent: {e}")
            return False

    def get_user_stats(self) -> dict:
        if not self.supabase: return {"total": 0, "subscribed": 0, "unsubscribed": 0}
        try:
            response = self.supabase.table("users").select("news_enabled").execute()
            total = len(response.data)
            subscribed = sum(1 for u in response.data if u["news_enabled"])
            return {"total": total, "subscribed": subscribed, "unsubscribed": total - subscribed}
        except Exception as e:
            print(f"Error en get_user_stats: {e}")
            return {"total": 0, "subscribed": 0, "unsubscribed": 0}

    def ban_user(self, chat_id: int) -> str:
        if not self.supabase: return "error"
        try:
            response = self.supabase.table("users").select("chat_id").eq("chat_id", chat_id).execute()
            if not response.data:
                return "not_found"
            self.supabase.table("users").delete().eq("chat_id", chat_id).execute()
            return "deleted"
        except Exception as e:
            print(f"Error en ban_user: {e}")
            return "error"

    def log_command(self, chat_id: int, command: str) -> None:
        if not self.supabase: return
        try:
            self.supabase.table("command_log").insert({
                "chat_id": chat_id,
                "command": command
            }).execute()
        except Exception as e:
            print(f"Error en log_command: {e}")

    def update_bot_health(self, status: str = "ok") -> None:
        if not self.supabase: return
        try:
            now = datetime.now(timezone.utc).isoformat()
            self.supabase.table("bot_health").update({
                "last_cron_at": now,
                "last_cron_status": status,
                "updated_at": now
            }).eq("id", 1).execute()
        except Exception as e:
            print(f"Error en update_bot_health: {e}")

    def get_dashboard_stats(self) -> dict:
        if not self.supabase:
            return {"error": "Sin conexión a Supabase"}

        try:
            users_data = self.supabase.table("users").select("news_enabled, created_at").execute()
            total_users = len(users_data.data)
            subscribed = sum(1 for u in users_data.data if u["news_enabled"])

            from datetime import datetime, timedelta
            week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()

            recent_commands = self.supabase.table("command_log").select("command, created_at").gte("created_at", week_ago).execute()
            total_commands_week = len(recent_commands.data)

            commands_by_type = {}
            for entry in recent_commands.data:
                cmd = entry["command"]
                commands_by_type[cmd] = commands_by_type.get(cmd, 0) + 1

            commands_by_day = {}
            for entry in recent_commands.data:
                day = entry["created_at"][:10]
                commands_by_day[day] = commands_by_day.get(day, 0) + 1

            recent_news = self.supabase.table("sent_news").select("created_at").gte("created_at", week_ago).execute()
            news_by_day = {}
            for entry in recent_news.data:
                day = entry["created_at"][:10]
                news_by_day[day] = news_by_day.get(day, 0) + 1

            new_users_by_day = {}
            for u in users_data.data:
                created = u.get("created_at", "")
                if created and created >= week_ago:
                    day = created[:10]
                    new_users_by_day[day] = new_users_by_day.get(day, 0) + 1

            health = self.supabase.table("bot_health").select("*").eq("id", 1).execute()
            health_data = health.data[0] if health.data else None

            total_news = self.supabase.table("sent_news").select("news_hash", count="exact").execute()
            total_news_count = total_news.count if hasattr(total_news, 'count') else len(total_news.data)

            return {
                "total_users": total_users,
                "subscribed": subscribed,
                "unsubscribed": total_users - subscribed,
                "total_commands_week": total_commands_week,
                "commands_by_type": commands_by_type,
                "commands_by_day": commands_by_day,
                "news_by_day": news_by_day,
                "new_users_by_day": new_users_by_day,
                "total_news_sent": total_news_count,
                "last_cron_at": health_data["last_cron_at"] if health_data else None,
                "last_cron_status": health_data["last_cron_status"] if health_data else None,
                "updated_at": health_data["updated_at"] if health_data else None,
            }
        except Exception as e:
            print(f"Error en get_dashboard_stats: {e}")
            return {"error": str(e)}


def create_supabase_client() -> Client | None:
    load_dotenv()

    url: str = os.getenv("SUPABASE_URL", "").strip()
    key: str = os.getenv("SUPABASE_KEY", "").strip()

    if url.endswith("/rest/v1/"):
        url = url[:-9]
    elif url.endswith("/rest/v1"):
        url = url[:-8]

    if not url or not key:
        print("ADVERTENCIA: SUPABASE_URL o SUPABASE_KEY no estan configurados.")

    try:
        return create_client(url, key)
    except Exception as e:
        print(f"Error inicializando Supabase: {e}")
        return None
