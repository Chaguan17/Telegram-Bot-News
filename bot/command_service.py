from bot.market_service import timezone_or_default


TIMEZONE_OPTIONS = [
    ("🇪🇸 España", "Europe/Madrid"),
    ("🇺🇸 EE.UU. (NY)", "America/New_York"),
    ("🇦🇷 Argentina", "America/Argentina/Buenos_Aires"),
    ("🇲🇽 México", "America/Mexico_City"),
    ("🇨🇴 Colombia", "America/Bogota"),
    ("🇨🇱 Chile", "America/Santiago"),
    ("🇻🇪 Venezuela", "America/Caracas"),
]


def command_from_text(text: str) -> str:
    return (text or "").split()[0].split("@", 1)[0].lower()


def help_text(*, is_admin: bool = False) -> str:
    text = ("📋 **Comandos disponibles:**\n\n"
            "• /start — Suscribirse al bot\n"
            "• /subscribe — Activar noticias automáticas\n"
            "• /unsubscribe — Desactivar noticias automáticas\n"
            "• /prices — Precios de BTC, ETH y BNB\n"
            "• /mercados — Estado de bolsas mundiales\n"
            "• /timezone — Configurar tu zona horaria local\n"
            "• /noticias — Top 3 noticias de impacto")
    if is_admin:
        text += ("\n\n👑 **Comandos de admin:**\n"
                 "• /stats — Estadísticas de usuarios\n"
                 "• /broadcast <mensaje> — Enviar mensaje a todos los suscritos\n"
                 "• /ban <chat_id> — Eliminar un usuario")
    return text


def timezone_keyboard_payload() -> dict:
    rows = []
    options = list(TIMEZONE_OPTIONS)
    for index in range(0, len(options), 2):
        rows.append([
            {"text": label, "callback_data": f"tz|{tz}"}
            for label, tz in options[index:index + 2]
        ])
    return {"inline_keyboard": rows}


def start_response(add_user_result: dict) -> str:
    status = add_user_result.get("status")
    news_on = add_user_result.get("news_enabled", True)
    if status == "new":
        return "🚀 **Bot Serverless Activo**\n• Suscrito a noticias automáticas.\n• /help : Ver comandos disponibles"
    if status == "existing":
        state = "**activadas**" if news_on else "**desactivadas**"
        toggle = "/unsubscribe para desactivar" if news_on else "/subscribe para reactivar"
        return f"🤖 **Ya estás registrado.** Las noticias automáticas están {state}. Usá {toggle} o /help para ver comandos."
    return "❌ Error de conexión con la base de datos. Intentá más tarde."


def subscription_response(result: str, *, enabled: bool) -> str:
    if result != "ok":
        return "❌ Primero debés usar /start para registrarte, o hay un error de conexión."
    if enabled:
        return "✅ Noticias automáticas **activadas**. Recibirás noticias cada 15 min. Usá /unsubscribe para desactivar."
    return "🔇 Noticias automáticas **desactivadas**. Seguís pudiendo usar /noticias para consultar a demanda. Usá /subscribe para reactivar."


def markets_response(timezone_name: str, obtener_estado_mercados) -> str:
    return obtener_estado_mercados(timezone_or_default(timezone_name))


def news_messages(noticias: list) -> list:
    if not noticias:
        return ["No he encontrado noticias de alto impacto en los feeds en este momento."]
    return ["📰 **Top 3 Noticias de Impacto Actuales:**"] + [n["message"] for n in noticias]


def stats_response(stats: dict) -> str:
    return (f"📊 **Estadísticas de usuarios:**\n\n"
            f"• Total registrados: {stats['total']}\n"
            f"• Suscritos a noticias: {stats['subscribed']}\n"
            f"• Desuscritos: {stats['unsubscribed']}")


def extract_broadcast_text(message_text: str, reply_text: str | None = None, reply_caption: str | None = None) -> str:
    text = (message_text or "").replace('/broadcast', '', 1).strip()
    if not text:
        text = reply_text or reply_caption or ""
        if "\n---\n⚠️ *Para enviar a todos" in text:
            text = text.split("\n---\n⚠️ *Para enviar a todos")[0].strip()
    return text


def ban_target(message_text: str):
    parts = (message_text or "").split()
    if len(parts) != 2:
        return None, "❌ Usá: /ban <chat_id>"
    try:
        return int(parts[1]), None
    except ValueError:
        return None, "❌ El chat_id debe ser un número."


def ban_response(result: str, target_id: int) -> str:
    if result == "deleted":
        return f"✅ Usuario {target_id} eliminado."
    if result == "not_found":
        return f"⚠️ Usuario {target_id} no encontrado."
    return "❌ Error de conexión con la base de datos."


def timezone_callback_response(tz_string: str, success: bool) -> dict:
    if success:
        return {
            "answer_text": f"Zona horaria actualizada a {tz_string}",
            "message_text": f"✅ **Zona horaria configurada:** `{tz_string}`\nLos horarios en /mercados ahora se mostrarán en tu hora local.",
            "show_alert": False,
        }
    return {
        "answer_text": "Error actualizando zona horaria",
        "message_text": None,
        "show_alert": True,
    }
