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
        any_sent = False
        for uid in usuarios:
            if is_news_sent(news_hash, uid):
                continue

            try:
                send_message(uid, noticia["message"])
                mark_news_sent(news_hash, uid)
                any_sent = True
            except Exception as e:
                print(f"Error enviando a {uid}: {e}")
                failed_count += 1

        if any_sent:
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
    cleanup_old_data=None,
    ignore_sent=False,
) -> dict:
    """Async cron orchestration for Cloudflare-friendly runtimes."""
    noticias_candidatas = await _maybe_await(buscar_noticias())
    usuarios = await _maybe_await(get_news_subscribers())

    print(f"[CRON] Inicio. Suscriptores: {len(usuarios)}, Candidatas en feed: {len(noticias_candidatas)}")

    enviadas_count = 0
    failed_count = 0
    MAX_NOTICIAS_POR_CRON = 3

    for noticia in noticias_candidatas:
        if enviadas_count >= MAX_NOTICIAS_POR_CRON and not ignore_sent:
            print(f"[CRON] Límite de {MAX_NOTICIAS_POR_CRON} noticias alcanzado. Deteniendo búsqueda.")
            break

        news_hash = noticia["hash"]
        
        if not usuarios:
            print("[CRON] WARN: No hay suscriptores habilitados. No se enviará nada.")
            continue

        any_user_sent_in_this_run = False
        for uid in usuarios:
            # Chequeo individual por usuario
            already_sent = await _maybe_await(is_news_sent(news_hash, uid))
            
            if already_sent and not ignore_sent:
                # Omitimos el log por usuario para no inundar la consola si hay muchos
                continue

            if ignore_sent and already_sent:
                print(f"[CRON] MODO FORCE: Re-enviando noticia ya conocida a {uid}: {news_hash}")

            try:
                print(f"[CRON] PROCESANDO para {uid}: {news_hash} (Score: {noticia.get('score', '?')})")
                await _maybe_await(send_message(uid, noticia["message"]))
                print(f"[CRON] -> Éxito enviando a {uid}")
                
                # Registramos el envío para ESTE usuario inmediatamente
                await _maybe_await(mark_news_sent(news_hash, uid))
                any_user_sent_in_this_run = True
            except Exception as e:
                print(f"[CRON] -> Error enviando a {uid}: {e}")
                failed_count += 1

        if any_user_sent_in_this_run:
            enviadas_count += 1

    if cleanup_old_data:
        await _maybe_await(cleanup_old_data())

    await _maybe_await(update_bot_health("ok"))
    return {"status": "ok", "news_processed": len(noticias_candidatas), "news_sent": enviadas_count, "send_errors": failed_count}
