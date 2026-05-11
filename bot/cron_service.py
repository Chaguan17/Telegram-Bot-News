async def _maybe_await(value):
    if hasattr(value, "__await__"):
        return await value
    return value


def run_news_cron(
    *,
    buscar_noticias,
    get_news_subscribers,
    is_news_sent,
    mark_news_sent,
    send_message,
    update_bot_health,
) -> dict:
    """Run the news delivery job independent from a specific serverless runtime."""
    noticias_nuevas = buscar_noticias()
    usuarios = get_news_subscribers()

    enviadas_count = 0
    failed_count = 0

    for noticia in noticias_nuevas:
        news_hash = noticia["hash"]
        if is_news_sent(news_hash):
            continue

        for uid in usuarios:
            try:
                send_message(uid, noticia["message"])
            except Exception as e:
                print(f"Error enviando a {uid}: {e}")
                failed_count += 1

        mark_news_sent(news_hash)
        enviadas_count += 1

    update_bot_health("ok")
    return {"status": "ok", "news_sent": enviadas_count, "send_errors": failed_count}


async def run_news_cron_async(
    *,
    buscar_noticias,
    get_news_subscribers,
    is_news_sent,
    mark_news_sent,
    send_message,
    update_bot_health,
) -> dict:
    """Async cron orchestration for Cloudflare-friendly runtimes."""
    noticias_nuevas = await _maybe_await(buscar_noticias())
    usuarios = await _maybe_await(get_news_subscribers())

    enviadas_count = 0
    failed_count = 0

    for noticia in noticias_nuevas:
        news_hash = noticia["hash"]
        already_sent = await _maybe_await(is_news_sent(news_hash))
        if already_sent:
            continue

        for uid in usuarios:
            try:
                await _maybe_await(send_message(uid, noticia["message"]))
            except Exception as e:
                print(f"Error enviando a {uid}: {e}")
                failed_count += 1

        await _maybe_await(mark_news_sent(news_hash))
        enviadas_count += 1

    await _maybe_await(update_bot_health("ok"))
    return {"status": "ok", "news_sent": enviadas_count, "send_errors": failed_count}
