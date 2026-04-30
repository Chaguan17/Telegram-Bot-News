import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client

"""
=== SQL SNIPPETS PARA SUPABASE ===
Ejecuta esto en el SQL Editor de Supabase para crear las tablas:

CREATE TABLE users (
    chat_id BIGINT PRIMARY KEY,
    news_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE sent_news (
    news_hash TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Si ya tenés la tabla users, agregá la columna nueva:
-- ALTER TABLE users ADD COLUMN news_enabled BOOLEAN DEFAULT TRUE;

-- Ver supabase_migration.sql para tablas adicionales (command_log, bot_health)
===================================
"""

load_dotenv()

# Inicialización del cliente Supabase
url: str = os.getenv("SUPABASE_URL", "").strip()
key: str = os.getenv("SUPABASE_KEY", "").strip()

# Limpieza de URL para evitar el error "double rest/v1"
if url.endswith("/rest/v1/"):
    url = url[:-9]
elif url.endswith("/rest/v1"):
    url = url[:-8]

if not url or not key:
    print("⚠️ ADVERTENCIA: SUPABASE_URL o SUPABASE_KEY no están configurados.")

try:
    supabase: Client = create_client(url, key)
except Exception as e:
    supabase = None
    print(f"Error inicializando Supabase: {e}")


def get_all_users() -> list:
    """Devuelve una lista con todos los chat_id de los usuarios."""
    if not supabase: return []
    try:
        response = supabase.table("users").select("chat_id").execute()
        return [user["chat_id"] for user in response.data]
    except Exception as e:
        print(f"Error en get_all_users: {e}")
        return []

def add_user(chat_id: int) -> dict:
    """Añade un usuario. Devuelve dict con status y news_enabled."""
    if not supabase: return {"status": "error"}
    try:
        response = supabase.table("users").select("chat_id, news_enabled").eq("chat_id", chat_id).execute()
        if response.data:
            return {"status": "existing", "news_enabled": response.data[0]["news_enabled"]}
        supabase.table("users").insert({"chat_id": chat_id, "news_enabled": True}).execute()
        return {"status": "new", "news_enabled": True}
    except Exception as e:
        print(f"Error en add_user: {e}")
        return {"status": "error"}


def set_news_enabled(chat_id: int, enabled: bool) -> str:
    """Activa o desactiva las noticias automáticas para un usuario. Crea el usuario si no existe. Devuelve 'ok' o 'error'."""
    if not supabase: return "error"
    try:
        supabase.table("users").upsert({"chat_id": chat_id, "news_enabled": enabled}).execute()
        return "ok"
    except Exception as e:
        print(f"Error en set_news_enabled: {e}")
        return "error"


def get_news_subscribers() -> list:
    """Devuelve los chat_id de usuarios con news_enabled=True."""
    if not supabase: return []
    try:
        response = supabase.table("users").select("chat_id").eq("news_enabled", True).execute()
        return [user["chat_id"] for user in response.data]
    except Exception as e:
        print(f"Error en get_news_subscribers: {e}")
        return []

def is_news_sent(news_hash: str) -> bool:
    """Comprueba si una noticia ya fue enviada buscando su hash."""
    if not supabase: return False
    try:
        response = supabase.table("sent_news").select("news_hash").eq("news_hash", news_hash).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error en is_news_sent: {e}")
        return False

def mark_news_sent(news_hash: str) -> bool:
    """Guarda el hash de la noticia en la base de datos para marcarla como enviada."""
    if not supabase: return False
    try:
        supabase.table("sent_news").upsert({"news_hash": news_hash}).execute()
        return True
    except Exception as e:
        print(f"Error en mark_news_sent: {e}")
        return False

def get_user_stats() -> dict:
    """Devuelve estadísticas de usuarios: total, suscritos y desuscritos."""
    if not supabase: return {"total": 0, "subscribed": 0, "unsubscribed": 0}
    try:
        response = supabase.table("users").select("news_enabled").execute()
        total = len(response.data)
        subscribed = sum(1 for u in response.data if u["news_enabled"])
        return {"total": total, "subscribed": subscribed, "unsubscribed": total - subscribed}
    except Exception as e:
        print(f"Error en get_user_stats: {e}")
        return {"total": 0, "subscribed": 0, "unsubscribed": 0}

def ban_user(chat_id: int) -> str:
    """Elimina un usuario de la tabla. Devuelve 'deleted', 'not_found' o 'error'."""
    if not supabase: return "error"
    try:
        response = supabase.table("users").select("chat_id").eq("chat_id", chat_id).execute()
        if not response.data:
            return "not_found"
        supabase.table("users").delete().eq("chat_id", chat_id).execute()
        return "deleted"
    except Exception as e:
        print(f"Error en ban_user: {e}")
        return "error"


def log_command(chat_id: int, command: str) -> None:
    """Registra un comando ejecutado en command_log."""
    if not supabase: return
    try:
        supabase.table("command_log").insert({
            "chat_id": chat_id,
            "command": command
        }).execute()
    except Exception as e:
        print(f"Error en log_command: {e}")


def update_bot_health(status: str = "ok") -> None:
    """Actualiza el registro de health del bot (último cron exitoso)."""
    if not supabase: return
    try:
        now = datetime.now(timezone.utc).isoformat()
        supabase.table("bot_health").update({
            "last_cron_at": now,
            "last_cron_status": status,
            "updated_at": now
        }).eq("id", 1).execute()
    except Exception as e:
        print(f"Error en update_bot_health: {e}")


def get_dashboard_stats() -> dict:
    """Devuelve todas las métricas para el dashboard público."""
    if not supabase:
        return {"error": "Sin conexión a Supabase"}

    try:
        # 1. Estadísticas generales de usuarios
        users_data = supabase.table("users").select("news_enabled, created_at").execute()
        total_users = len(users_data.data)
        subscribed = sum(1 for u in users_data.data if u["news_enabled"])

        # 2. Últimas 24h de command_log
        from datetime import datetime, timedelta
        yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
        week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()

        recent_commands = supabase.table("command_log").select("command, created_at").gte("created_at", week_ago).execute()
        total_commands_week = len(recent_commands.data)

        # Comandos por tipo (última semana)
        commands_by_type = {}
        for entry in recent_commands.data:
            cmd = entry["command"]
            commands_by_type[cmd] = commands_by_type.get(cmd, 0) + 1

        # Comandos por día (últimos 7 días)
        commands_by_day = {}
        for entry in recent_commands.data:
            day = entry["created_at"][:10]
            commands_by_day[day] = commands_by_day.get(day, 0) + 1

        # 3. Noticias enviadas (última semana)
        recent_news = supabase.table("sent_news").select("created_at").gte("created_at", week_ago).execute()
        news_by_day = {}
        for entry in recent_news.data:
            day = entry["created_at"][:10]
            news_by_day[day] = news_by_day.get(day, 0) + 1

        # 4. Usuarios nuevos por día (última semana)
        new_users_by_day = {}
        for u in users_data.data:
            created = u.get("created_at", "")
            if created and created >= week_ago:
                day = created[:10]
                new_users_by_day[day] = new_users_by_day.get(day, 0) + 1

        # 5. Bot health
        health = supabase.table("bot_health").select("*").eq("id", 1).execute()
        health_data = health.data[0] if health.data else None

        # 6. Total de noticias enviadas (histórico)
        total_news = supabase.table("sent_news").select("news_hash", count="exact").execute()
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
