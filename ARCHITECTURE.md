# Arquitectura de BNB Sentinel Bot

El objetivo arquitectónico central es simple: **la lógica del bot no debe saber dónde corre ni qué base de datos usa.** El runtime (Cloudflare Worker) solo adapta HTTP, cron, Telegram y persistencia. Los servicios del dominio no conocen nada de la infraestructura.

## Stack actual

| Componente | Tecnología |
| --- | --- |
| Compute | Cloudflare Workers (Python via Pyodide) |
| Base de datos | Cloudflare D1 (SQLite) |
| Cron | Cloudflare Scheduled Triggers |
| Telegram | Webhook sobre `/api/webhook` |
| Dashboard | `/` sirve el HTML estático del Worker |

## Vista rápida

```text
Telegram
   |
   | webhook POST
   v
+---------------------------+
| worker.py (Default class) |   ← routing HTTP + scheduled cron
+------------+--------------+
             |
             v
    bot/webhook_service.py        ← orquesta updates de Telegram
    bot/command_service.py        ← lógica de cada comando
    bot/cron_service.py           ← pipeline de noticias
             |
             v
    bot services (puros, sin runtime):
    ├── bot/news_service.py       ← feeds RSS + scoring
    ├── bot/price_service.py      ← precios Binance
    └── bot/market_service.py     ← horarios de mercados globales
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
| Runtime | `worker.py` | Routing HTTP, scheduled handler, construcción de adapters. |
| Aplicación | `bot/webhook_service.py`, `bot/cron_service.py` | Orquestar comandos y cron sin depender del runtime. |
| Dominio | `bot/command_service.py`, `bot/news_service.py`, `bot/price_service.py`, `bot/market_service.py` | Reglas de negocio, RSS, precios y mercados. Lógica pura. |
| Persistencia | `bot/repositories/d1_binding_repository.py`, `bot/db.py` | Contrato estable sobre D1. `bot/db.py` actúa como fachada. |
| Infra | `wrangler.jsonc`, `cloudflare/d1/schema.sql` | Configuración del Worker, cron schedule y schema SQLite. |
| Tests | `tests/` | Protegen los seams sin tocar producción. |

## Decisiones de diseño

### 1. La lógica del bot no conoce el runtime

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
Application service → Repository → Backend real
```

La implementación activa es `D1BindingRepository`, que accede a Cloudflare D1 vía el binding `env.DB`. `bot/db.py` expone las mismas funciones de siempre (`add_user`, `get_news_subscribers`, `mark_news_sent`, etc.) y delega internamente al repository. Los callers existentes no necesitaron cambios.

### 3. D1 usa SQLite, no PostgreSQL

El schema vive en `cloudflare/d1/schema.sql`. No es intercambiable con el SQL de Supabase/PostgreSQL que existía antes. Si necesitás referenciar el schema histórico, está en el historial de git.

### 4. Cron nativo de Cloudflare

El cron ya no depende de GitHub Actions ni de servicios externos. Cloudflare ejecuta el handler `scheduled()` directamente según el schedule definido en `wrangler.jsonc`. El flujo es:

```text
Cloudflare Cron Trigger
 → worker.scheduled()
 → run_news_cron_async()
 → buscar_noticias_with_async_loader()
 → D1: deduplicación con sent_news
 → TelegramHttpClient: envío a suscriptores
 → D1: actualiza bot_health
```

### 5. `worker.py` como adapter — deuda técnica conocida

El objetivo es que `worker.py` sea un adapter fino: solo routing y construcción de dependencias. Actualmente contiene tres cosas que deberían vivir en su propio módulo:

- `CloudflareTelegramClient` — cliente HTTP async para Telegram
- `fetch_feed_entries` — loader async de RSS
- `fetch_binance_prices` — loader async de precios Binance

Estas tres piezas son adaptadores de infraestructura Cloudflare, no lógica de routing. La solución natural es moverlas a `cloudflare/adapters.py` o equivalente. Hasta que eso suceda, `worker.py` tiene más responsabilidades de las que debería.

## Flujos principales

### Comando de usuario

```text
Telegram update POST /api/webhook
 → worker.py fetch()
 → handle_telegram_update()
 → command_service genera respuesta
 → D1BindingRepository lee/escribe estado
 → CloudflareTelegramClient responde al usuario
```

### Cron de noticias

```text
Cloudflare Scheduled Trigger
 → worker.scheduled()
 → run_news_cron_async()
 → buscar_noticias_with_async_loader() con fetch_feed_entries
 → D1: deduplicación por hash
 → CloudflareTelegramClient envía a suscriptores
 → D1: actualiza bot_health
```

### Dashboard de estadísticas

```text
GET /api/stats
 → worker.fetch()
 → D1BindingRepository.get_dashboard_stats()
 → JSON público consumido por el dashboard en /
```

### Debug del cron

```text
GET /api/debug-cron[?force=1]
 → worker.fetch()
 → worker.scheduled() con force=True si se pasa el parámetro
 → mismo flujo que el cron real
```

> `?force=1` ignora la deduplicación de `sent_news`. Útil para verificar que el pipeline completo funciona.

## Reglas para futuros cambios

- No meter lógica de negocio nueva en `worker.py`. Solo routing y construcción de adapters.
- No hacer que los servicios dependan de D1 o Cloudflare directamente. Todo a través del Repository.
- Si aparece un nuevo backend de persistencia, agregar un Repository nuevo; no modificar los servicios.
- Si aparece un nuevo runtime, agregar un adapter; no duplicar lógica.
- Todo cambio de comportamiento debe tener test en `tests/`.
- Los adapters Cloudflare (`CloudflareTelegramClient`, loaders async) deben eventualmente moverse fuera de `worker.py`.
