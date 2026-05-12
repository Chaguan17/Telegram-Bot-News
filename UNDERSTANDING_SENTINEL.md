# Understanding Sentinel

Este documento es para humanos. La meta no es "saber qué archivo tocar", sino entender **qué problema resuelve este proyecto, cómo piensa, y cómo no romperlo por operar en piloto automático**.

## El proyecto en una frase

BNB Sentinel Bot es un bot de Telegram que:

1. registra usuarios,
2. permite activar/desactivar noticias automáticas,
3. consulta precios cripto,
4. muestra estado de mercados globales por zona horaria,
5. filtra noticias RSS de impacto,
6. expone estadísticas de uso y salud del bot.

## El concepto más importante

El bot tiene dos mundos:

```text
Lo que el bot sabe hacer        Dónde corre el bot
------------------------        ------------------
responder comandos              Cloudflare Workers
buscar noticias                 Cloudflare D1
calcular mercados               Cloudflare Scheduled Trigger
formatear mensajes              Telegram HTTP API
```

Una buena arquitectura mantiene esos mundos separados.

Si mezclás "qué hace" con "dónde corre", cada cambio de infraestructura se vuelve una cirugía mayor. Si los separás, cambiar de plataforma es cambiar adaptadores.

## Mapa mental del repo

```text
worker.py               Entrypoint: routing HTTP + cron scheduled
bot/                    Lógica del bot (sin dependencias de runtime)
bot/repositories/       Persistencia intercambiable
cloudflare/d1/          Schema SQLite y herramientas de migración
tests/                  Red de seguridad
public/                 Dashboard estático
```

## Cómo leer el proyecto

### 1. Empezá por los comandos

Archivo:

```text
bot/command_service.py
```

Ahí vas a ver respuestas puras:

- `/start`
- `/help`
- `/subscribe`
- `/unsubscribe`
- `/timezone`
- `/stats`
- `/ban`
- `/broadcast`

Este archivo te enseña el lenguaje del bot.

### 2. Después mirá el orquestador webhook

Archivo:

```text
bot/webhook_service.py
```

Este archivo responde la pregunta:
> "Cuando llega un update de Telegram, ¿qué hacemos?"

No sabe nada de Cloudflare. Solo recibe:

- `repository`
- `telegram`
- `admin_chat_id`
- providers de precios/noticias como callables

Eso es inyección de dependencias. No es moda: es lo que permite testear y migrar sin tocar la lógica.

### 3. Después entendé la base de datos

Archivos:

```text
bot/db.py
bot/repositories/d1_binding_repository.py
```

La idea:

```text
bot/db.py
 → D1BindingRepository
 → Cloudflare D1 (SQLite)
```

`bot/db.py` expone las funciones de siempre (`add_user`, `get_news_subscribers`, `mark_news_sent`, etc.) como fachada estable. El repository es la pieza que realmente habla con D1.

### 4. Recién después mirá el Worker

Archivo:

```text
worker.py
```

Este archivo es infraestructura. Si empezás por acá, vas a creer que el proyecto "es Cloudflare". No. Cloudflare es solo el lugar donde corre.

El Worker debería ser aburrido:

- parsea request,
- construye adapters (`D1BindingRepository`, `CloudflareTelegramClient`),
- inyecta los loaders async de RSS y Binance,
- llama servicios,
- devuelve response.

Si el Worker empieza a tener demasiada lógica, la arquitectura se está pudriendo. Hoy tiene más de lo ideal — `CloudflareTelegramClient`, `fetch_feed_entries` y `fetch_binance_prices` viven ahí cuando deberían estar en su propio módulo. Es deuda técnica conocida.

## Flujo de `/prices`

```text
Telegram manda /prices
 → worker.py recibe webhook POST
 → webhook_service detecta comando
 → price_service formatea precios
 → CloudflareTelegramClient envía respuesta
```

Lo importante: el formato de precios no vive en el Worker. El Worker solo provee el loader async que busca los datos en Binance.

## Flujo de noticias automáticas

```text
Cloudflare Scheduled Trigger (cada 15 min)
 → worker.scheduled()
 → cron_service busca noticias
 → news_service puntúa feeds RSS por keywords
 → D1: pregunta si el hash ya fue enviado
 → CloudflareTelegramClient envía solo noticias nuevas
 → D1: marca hash como enviado
 → D1: actualiza bot_health
```

La tabla `sent_news` es el mecanismo anti-duplicados. El cron no depende de GitHub Actions ni servicios externos — es un Scheduled Trigger nativo de Cloudflare configurado en `wrangler.jsonc`.

## Flujo de mercados

El comando `/mercados` no consulta ninguna API externa. Calcula el estado de cada bolsa usando sus horarios oficiales y zonas horarias locales:

- Tokio: `Asia/Tokyo`
- Europa: `Europe/Madrid`
- EE.UU.: `America/New_York`

El resultado se muestra en la zona horaria del usuario (configurable con `/timezone`).

## Qué significa "serverless" acá

Serverless no significa "sin arquitectura".

Significa:

- no administrás servidores,
- cada request debe ser independiente,
- no podés confiar en estado global mutable,
- los secretos viven en Wrangler secrets,
- las tareas periódicas son Scheduled Triggers, no procesos vivos.

Por eso el diseño evita guardar estado en memoria y empuja todo lo importante a D1.

## Qué NO hacer

- No meter queries directas a D1 dentro de `webhook_service.py`.
- No llamar al Worker desde `command_service.py`.
- No agregar lógica de negocio en `worker.py` — solo routing y construcción de adapters.
- No mover los adapters Cloudflare (`CloudflareTelegramClient`, loaders async) a los servicios del dominio.
- No hardcodear URLs o tokens en ningún archivo — todo por Wrangler secrets.

## Cómo cambiar algo sin romperlo

Usá este orden:

1. Encontrá el seam correcto.
2. Cambiá la pieza más chica posible.
3. Agregá o ajustá test.
4. Corré:

```bash
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

1. Recién después seguí.

Ese orden importa. Si codeás primero y entendés después, vas a estar construyendo una casa moviendo paredes al azar.

## Qué mirar cuando algo falla

| Síntoma | Dónde mirar primero |
| --- | --- |
| Comando responde mal | `bot/command_service.py`, `bot/webhook_service.py` |
| No envía noticias | `bot/cron_service.py`, `bot/news_service.py`, tabla `sent_news` |
| Duplicados de noticias | `is_news_sent`, `mark_news_sent`, tabla `sent_news` |
| Admin bloqueado | secret `ADMIN_CHAT_ID` en Wrangler |
| Stats rotas | `get_dashboard_stats`, tabla `bot_health`, tabla `command_log` |
| Worker falla | `worker.py`, bindings y secrets en `wrangler.jsonc` |
| Cron no dispara | Scheduled Triggers en Cloudflare dashboard, `worker.scheduled()` |

## Cómo saber si entendiste el proyecto

Podés explicar estas tres frases sin mirar código:

1. "El runtime adapta; no decide negocio."
2. "El repository persiste; no decide comandos."
3. "Los servicios orquestan reglas; no saben que están corriendo en Cloudflare."

Si esas tres frases te hacen sentido, ya estás leyendo el proyecto como arquitecto, no como turista mirando archivos.

## Orden de lectura recomendado

1. `bot/command_service.py`
2. `bot/webhook_service.py`
3. `bot/cron_service.py`
4. `bot/repositories/d1_binding_repository.py`
5. `worker.py`
6. `tests/test_webhook_service.py`
7. `tests/test_cron_service.py`

No es el orden de ejecución. Es el orden para entender.
