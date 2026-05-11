# Arquitectura de BNB Sentinel Bot

El objetivo arquitectónico es mover el bot desde **Vercel + Supabase + GitHub Actions** hacia **Cloudflare Workers + D1 + Cron Triggers** sin romper producción durante la transición.

La idea central es simple: **la lógica del bot no debe saber dónde corre ni qué base de datos usa**. Los runtimes (`api/` y `cloudflare/`) solo adaptan HTTP, cron, Telegram y persistencia.

## Vista rápida

```text
Telegram
   |
   | webhook
   v
+----------------------+        +----------------------+
| Runtime adapter      |        | Runtime adapter      |
| Vercel: api/webhook  |        | Cloudflare: worker   |
+----------+-----------+        +----------+-----------+
           |                               |
           v                               v
      bot/webhook_service.py / bot/command_service.py
           |
           v
      bot services: news, prices, markets, cron
           |
           v
      Repository contract
           |
    +------+-------------------+
    |                          |
SupabaseRepository        D1BindingRepository
    |                          |
Supabase/Postgres        Cloudflare D1/SQLite
```

## Capas

| Capa | Archivos | Responsabilidad |
|---|---|---|
| Runtime Vercel | `api/webhook.py`, `api/cron.py`, `api/stats.py` | Adaptar requests Vercel al core actual. |
| Runtime Cloudflare | `cloudflare/worker.py` | Adaptar fetch, scheduled cron, D1 binding y Telegram HTTP async. |
| Aplicación | `bot/webhook_service.py`, `bot/cron_service.py` | Orquestar comandos y cron sin depender del runtime. |
| Dominio/servicios | `bot/command_service.py`, `bot/news_service.py`, `bot/price_service.py`, `bot/services.py` | Reglas de mensajes, RSS, precios y mercados. |
| Persistencia | `bot/db.py`, `bot/repositories/*` | Mantener contrato estable y permitir backends Supabase/D1. |
| Infra Cloudflare | `wrangler.jsonc`, `cloudflare/d1/schema.sql` | Configuración Worker, cron y schema SQLite/D1. |
| Migración datos | `cloudflare/d1/export_supabase_to_d1.py`, `cloudflare/d1/migration.py` | Exportar Supabase a SQL importable en D1. |
| Verificación | `tests/` | Probar seams sin tocar producción. |

## Decisiones de diseño

### 1. Migración incremental, no rewrite

No se reemplazó todo de golpe. Primero se extrajeron seams:

- DB facade.
- Repositories.
- Cron service.
- Webhook service.
- Telegram HTTP adapter.
- News/price services.

Esto permite que Vercel/Supabase sigan vivos mientras Cloudflare se valida.

### 2. `bot/db.py` queda como fachada backward-compatible

Los callers existentes siguen importando funciones como:

- `add_user`
- `get_news_subscribers`
- `mark_news_sent`
- `get_dashboard_stats`

Internamente, `bot/db.py` delega a un repository seleccionado por configuración.

### 3. Repositories como puerto de persistencia

El contrato conceptual es:

```text
Application service -> Repository -> Backend real
```

Implementaciones actuales:

- `SupabaseRepository`: backend actual de producción Vercel.
- `D1Repository`: SQLite/D1-compatible para tests locales.
- `D1BindingRepository`: Cloudflare D1 real vía binding `env.DB`.

### 4. Cloudflare Worker como adapter fino

`cloudflare/worker.py` no debería contener reglas de negocio pesadas.

Debe hacer solo esto:

- routear `/api/stats`
- routear `/api/webhook`
- ejecutar `scheduled`
- construir adapters (`D1BindingRepository`, `TelegramHttpClient`)
- pasar loaders async para RSS/Binance

### 5. D1 usa SQLite, no SQL de Supabase

Por eso existe:

- `supabase_migration.sql`: historia/SQL PostgreSQL para Supabase.
- `cloudflare/d1/schema.sql`: schema SQLite/D1 real.

No son intercambiables.

### 6. Los tests protegen el corte

Los tests no prueban “Cloudflare completo”, prueban las piezas que hacen seguro el cambio:

- contrato DB
- repositories
- cron sync/async
- webhook runtime-neutral
- Telegram HTTP
- migración SQL
- servicios puros

## Flujos principales

### Comando Telegram en Cloudflare

```text
Telegram update
 -> cloudflare/worker.py fetch()
 -> handle_telegram_update()
 -> command_service genera respuesta
 -> repository lee/escribe estado
 -> TelegramHttpClient responde
```

### Cron Cloudflare

```text
Cloudflare Cron Trigger
 -> worker.scheduled()
 -> run_news_cron_async()
 -> buscar_noticias_with_async_loader()
 -> D1 dedupe con sent_news
 -> TelegramHttpClient envía mensajes
 -> D1 actualiza bot_health
```

### Dashboard stats

```text
GET /api/stats
 -> worker.fetch()
 -> D1BindingRepository.get_dashboard_stats()
 -> JSON público para dashboard
```

## Estado de transición

| Sistema | Estado |
|---|---|
| Vercel webhook | Se mantiene compatible. |
| Vercel cron | Se mantiene compatible. |
| Supabase | Se mantiene compatible. |
| Cloudflare Worker | Scaffold listo para validar. |
| Cloudflare D1 | Schema y adapter listos. |
| Telegram webhook | Todavía no debe moverse hasta validar Worker + D1. |

## Próxima arquitectura objetivo

```text
Telegram -> Cloudflare Worker /api/webhook
Cron     -> Cloudflare Scheduled Handler
Data     -> Cloudflare D1
Stats    -> Cloudflare Worker /api/stats
Secrets  -> Wrangler secrets
```

Después del corte exitoso, Vercel, Supabase y GitHub Actions cron deberían quedar fuera del camino crítico.

## Reglas para futuros cambios

- No meter lógica de negocio nueva en `cloudflare/worker.py`.
- No hacer que servicios dependan de Supabase o D1 directamente.
- Si aparece un backend nuevo, agregar repository; no modificar comandos.
- Si aparece un runtime nuevo, agregar adapter; no duplicar lógica.
- Todo cambio de comportamiento debe tener test en `tests/`.
- No mover Telegram webhook hasta que el path nuevo esté validado manualmente.
