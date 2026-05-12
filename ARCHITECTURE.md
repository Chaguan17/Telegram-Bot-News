# Arquitectura de BNB Sentinel Bot

El objetivo arquitectÃ³nico central es simple: **la lÃ³gica del bot no debe saber dÃ³nde corre ni quÃ© base de datos usa.** El runtime (Cloudflare Worker) solo adapta HTTP, cron, Telegram y persistencia. Los servicios del dominio no conocen nada de la infraestructura.

## Stack actual

| Componente | TecnologÃ­a |
| --- | --- |
| Compute | Cloudflare Workers (Python via Pyodide) |
| Base de datos | Cloudflare D1 (SQLite) |
| Cron | Cloudflare Scheduled Triggers |
| Telegram | Webhook sobre `/api/webhook` |
| Dashboard | `/` sirve el HTML estÃ¡tico del Worker |

## Vista rÃ¡pida

```text
Telegram
   |
   | webhook POST
   v
+---------------------------+
| worker.py (Default class) |   â† routing HTTP + scheduled cron
+------------+--------------+
             |
             v
    bot/webhook_service.py        â† orquesta updates de Telegram
    bot/command_service.py        â† lÃ³gica de cada comando
    bot/cron_service.py           â† pipeline de noticias
             |
             v
    bot services (puros, sin runtime):
    â”œâ”€â”€ bot/news_service.py       â† feeds RSS + scoring
    â”œâ”€â”€ bot/price_service.py      â† precios Binance
    â””â”€â”€ bot/market_service.py     â† horarios de mercados globales
             |
             v
    Repository contract
             |
    bot/repositories/d1_binding_repository.py
             |
    Cloudflare D1 (SQLite)
```

## Capas

| Capa | Archivos | Responsabilidad |
| --- | --- | --- |
| Runtime | `worker.py` | Routing HTTP, scheduled handler, construcciÃ³n de adapters. |
| AplicaciÃ³n | `bot/webhook_service.py`, `bot/cron_service.py` | Orquestar comandos y cron sin depender del runtime. |
| Dominio | `bot/command_service.py`, `bot/news_service.py`, `bot/price_service.py`, `bot/market_service.py` | Reglas de negocio, RSS, precios y mercados. LÃ³gica pura. |
| Persistencia | `bot/repositories/d1_binding_repository.py`, `bot/db.py` | Contrato estable sobre D1. `bot/db.py` actÃºa como fachada. |
| Infra | `wrangler.jsonc`, `cloudflare/d1/schema.sql` | ConfiguraciÃ³n del Worker, cron schedule y schema SQLite. |
| Tests | `tests/` | Protegen los seams sin tocar producciÃ³n. |

## Decisiones de diseÃ±o

### 1. La lÃ³gica del bot no conoce el runtime

Los servicios (`news_service`, `price_service`, `market_service`) son funciones puras. No importan nada de Cloudflare. El Worker construye los adapters async (HTTP loaders para RSS y Binance, cliente Telegram) y los inyecta como callables:

```python
result = await handle_telegram_update(
    update,
    repository=repository,
    telegram=telegram,
    get_prices=lambda: obtener_precios_with_async_loader(fetch_binance_prices),
    get_news=lambda: buscar_noticias_with_async_loader(fetch_feed_entries, feeds=RSS_FEEDS),
    ...
)
```

Esto permite testear los servicios sin levantar un Worker real.

### 2. Repository como puerto de persistencia

El contrato conceptual es:

```text
Application service â†’ Repository â†’ Backend real
```

La implementaciÃ³n activa es `D1BindingRepository`, que accede a Cloudflare D1 vÃ­a el binding `env.DB`. `bot/db.py` expone las mismas funciones de siempre (`add_user`, `get_news_subscribers`, `mark_news_sent`, etc.) y delega internamente al repository. Los callers existentes no necesitaron cambios.

### 3. D1 usa SQLite, no PostgreSQL

El schema vive en `cloudflare/d1/schema.sql`. No es intercambiable con el SQL de Supabase/PostgreSQL que existÃ­a antes. Si necesitÃ¡s referenciar el schema histÃ³rico, estÃ¡ en el historial de git.

### 4. Cron nativo de Cloudflare

El cron ya no depende de GitHub Actions ni de servicios externos. Cloudflare ejecuta el handler `scheduled()` directamente segÃºn el schedule definido en `wrangler.jsonc`. El flujo es:

```text
Cloudflare Cron Trigger
 â†’ worker.scheduled()
 â†’ run_news_cron_async()
 â†’ buscar_noticias_with_async_loader()
 â†’ D1: deduplicaciÃ³n con sent_news
 â†’ TelegramHttpClient: envÃ­o a suscriptores
 â†’ D1: actualiza bot_health
```

### 5. `worker.py` como adapter â€” deuda tÃ©cnica conocida

El objetivo es que `worker.py` sea un adapter fino: solo routing y construcciÃ³n de dependencias. Actualmente contiene tres cosas que deberÃ­an vivir en su propio mÃ³dulo:

- `CloudflareTelegramClient` â€” cliente HTTP async para Telegram
- `fetch_feed_entries` â€” loader async de RSS
- `fetch_binance_prices` â€” loader async de precios Binance

Estas tres piezas son adaptadores de infraestructura Cloudflare, no lÃ³gica de routing. La soluciÃ³n natural es moverlas a `cloudflare/adapters.py` o equivalente. Hasta que eso suceda, `worker.py` tiene mÃ¡s responsabilidades de las que deberÃ­a.

## Flujos principales

### Comando de usuario

```text
Telegram update POST /api/webhook
 â†’ worker.py fetch()
 â†’ handle_telegram_update()
 â†’ command_service genera respuesta
 â†’ D1BindingRepository lee/escribe estado
 â†’ CloudflareTelegramClient responde al usuario
```

### Cron de noticias

```text
Cloudflare Scheduled Trigger
 â†’ worker.scheduled()
 â†’ run_news_cron_async()
 â†’ buscar_noticias_with_async_loader() con fetch_feed_entries
 â†’ D1: deduplicaciÃ³n por hash
 â†’ CloudflareTelegramClient envÃ­a a suscriptores
 â†’ D1: actualiza bot_health
```

### Dashboard de estadÃ­sticas

```text
GET /api/stats
 â†’ worker.fetch()
 â†’ D1BindingRepository.get_dashboard_stats()
 â†’ JSON pÃºblico consumido por el dashboard en /
```

### Debug del cron

```text
GET /api/debug-cron[?force=1]
 â†’ worker.fetch()
 â†’ worker.scheduled() con force=True si se pasa el parÃ¡metro
 â†’ mismo flujo que el cron real
```

> `?force=1` ignora la deduplicaciÃ³n de `sent_news`. Ãštil para verificar que el pipeline completo funciona.

## Reglas para futuros cambios

- No meter lÃ³gica de negocio nueva en `worker.py`. Solo routing y construcciÃ³n de adapters.
- No hacer que los servicios dependan de D1 o Cloudflare directamente. Todo a travÃ©s del Repository.
- Si aparece un nuevo backend de persistencia, agregar un Repository nuevo; no modificar los servicios.
- Si aparece un nuevo runtime, agregar un adapter; no duplicar lÃ³gica.
- Todo cambio de comportamiento debe tener test en `tests/`.
- Los adapters Cloudflare (`CloudflareTelegramClient`, loaders async) deben eventualmente moverse fuera de `worker.py`.
