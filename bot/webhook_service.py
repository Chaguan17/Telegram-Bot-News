from bot.command_service import (
    ban_response,
    ban_target,
    command_from_text,
    extract_broadcast_text,
    help_text,
    markets_response,
    news_messages,
    start_response,
    stats_response,
    subscription_response,
    timezone_callback_response,
    timezone_keyboard_payload,
)


async def _maybe_await(value):
    if hasattr(value, "__await__"):
        return await value
    return value


def _reply_text(message: dict) -> tuple[str | None, str | None]:
    reply = message.get("reply_to_message") or {}
    return reply.get("text"), reply.get("caption")


async def handle_telegram_update(
    update: dict,
    *,
    repository,
    telegram,
    admin_chat_id: int,
    get_prices=None,
    get_market_state=None,
    get_news=None,
) -> dict:
    """Handle a Telegram webhook update without pyTelegramBotAPI."""
    if get_prices is None:
        from bot.services import obtener_precios
        get_prices = obtener_precios
    if get_market_state is None:
        from bot.services import obtener_estado_mercados
        get_market_state = obtener_estado_mercados
    if get_news is None:
        from bot.services import buscar_noticias
        get_news = buscar_noticias

    if "callback_query" in update:
        return await _handle_callback(update["callback_query"], repository=repository, telegram=telegram)

    message = update.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    text = message.get("text", "")
    command = command_from_text(text)

    if not chat_id or not command:
        return {"status": "ignored"}

    if command == "/start":
        await repository.log_command(chat_id, "/start")
        await telegram.send_message(chat_id, start_response(await repository.add_user(chat_id)))
        return {"status": "ok", "command": "/start"}

    if command == "/help":
        await repository.log_command(chat_id, "/help")
        await telegram.send_message(chat_id, help_text(is_admin=chat_id == admin_chat_id))
        return {"status": "ok", "command": "/help"}

    if command == "/subscribe":
        await repository.log_command(chat_id, "/subscribe")
        result = await repository.set_news_enabled(chat_id, True)
        await telegram.send_message(chat_id, subscription_response(result, enabled=True))
        return {"status": "ok", "command": "/subscribe"}

    if command == "/unsubscribe":
        await repository.log_command(chat_id, "/unsubscribe")
        result = await repository.set_news_enabled(chat_id, False)
        await telegram.send_message(chat_id, subscription_response(result, enabled=False))
        return {"status": "ok", "command": "/unsubscribe"}

    if command == "/prices":
        await repository.log_command(chat_id, "/prices")
        await telegram.send_message(chat_id, await _maybe_await(get_prices()))
        return {"status": "ok", "command": "/prices"}

    if command == "/mercados":
        await repository.log_command(chat_id, "/mercados")
        await telegram.send_message(
            chat_id,
            markets_response(await repository.get_user_timezone(chat_id), get_market_state),
        )
        return {"status": "ok", "command": "/mercados"}

    if command == "/timezone":
        await repository.log_command(chat_id, "/timezone")
        await telegram.send_message(
            chat_id,
            "🌍 **Configuración de Zona Horaria**\nSeleccioná tu región para que los horarios del mercado aparezcan en tu hora local:",
            reply_markup=timezone_keyboard_payload(),
        )
        return {"status": "ok", "command": "/timezone"}

    if command == "/stats":
        await repository.log_command(chat_id, "/stats")
        if chat_id != admin_chat_id:
            await telegram.send_message(chat_id, "⛔ Comando exclusivo del administrador.")
            return {"status": "forbidden", "command": "/stats"}
        await telegram.send_message(chat_id, stats_response(await repository.get_user_stats()))
        return {"status": "ok", "command": "/stats"}

    if command == "/noticias":
        await repository.log_command(chat_id, "/noticias")
        messages = news_messages(await _maybe_await(get_news()))
        for message in messages:
            await telegram.send_message(chat_id, message)
        return {"status": "ok", "command": "/noticias"}

    if command == "/ban":
        await repository.log_command(chat_id, "/ban")
        if chat_id != admin_chat_id:
            await telegram.send_message(chat_id, "⛔ Comando exclusivo del administrador.")
            return {"status": "forbidden", "command": "/ban"}
        target_id, error = ban_target(text)
        if error:
            await telegram.send_message(chat_id, error)
            return {"status": "validation_error", "command": "/ban"}
        await telegram.send_message(chat_id, ban_response(await repository.ban_user(target_id), target_id))
        return {"status": "ok", "command": "/ban"}

    if command == "/broadcast":
        await repository.log_command(chat_id, "/broadcast")
        if chat_id != admin_chat_id:
            await telegram.send_message(chat_id, "⛔ Comando exclusivo del administrador.")
            return {"status": "forbidden", "command": "/broadcast"}
        reply_text, reply_caption = _reply_text(message)
        broadcast_text = extract_broadcast_text(text, reply_text=reply_text, reply_caption=reply_caption)
        if not broadcast_text:
            await telegram.send_message(chat_id, "❌ Usá: /broadcast <mensaje> o respondé a un mensaje con /broadcast")
            return {"status": "validation_error", "command": "/broadcast"}

        users = await repository.get_all_users()
        if not users:
            await telegram.send_message(chat_id, "❌ No hay usuarios registrados.")
            return {"status": "ok", "command": "/broadcast", "sent": 0, "failed": 0}

        sent = 0
        failed = 0
        for uid in users:
            try:
                await telegram.send_message(uid, f"📢 **Mensaje del admin:**\n\n{broadcast_text}")
                sent += 1
            except Exception as e:
                print(f"Error broadcasting to {uid}: {e}")
                failed += 1
        await telegram.send_message(chat_id, f"✅ Broadcast enviado: {sent} exitosos, {failed} fallidos.")
        return {"status": "ok", "command": "/broadcast", "sent": sent, "failed": failed}

    return {"status": "ignored", "command": command}


async def _handle_callback(callback_query: dict, *, repository, telegram) -> dict:
    data = callback_query.get("data", "")
    if not data.startswith("tz|"):
        return {"status": "ignored"}

    tz_string = data.split("|", 1)[1]
    message = callback_query.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    message_id = message.get("message_id")
    response = timezone_callback_response(tz_string, await repository.set_user_timezone(chat_id, tz_string))

    await telegram.answer_callback_query(
        callback_query.get("id"),
        response["answer_text"],
        show_alert=response["show_alert"],
    )
    if response["message_text"]:
        await telegram.edit_message_text(chat_id, message_id, response["message_text"])

    return {"status": "ok", "callback": "timezone"}
