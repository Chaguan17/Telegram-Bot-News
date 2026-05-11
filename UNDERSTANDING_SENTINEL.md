# Understanding Sentinel

Este documento es para humanos. La meta no es “saber qué archivo tocar”, sino entender **qué problema resuelve este proyecto, cómo piensa, y cómo no romperlo por operar en piloto automático**.

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
responder comandos              Vercel o Cloudflare
buscar noticias                 Supabase o D1
calcular mercados               GitHub Actions o Cron Trigger
formatear mensajes              Telegram HTTP API
```

Una buena arquitectura mantiene esos mundos separados.

Si mezclás “qué hace” con “dónde corre”, cada migración se vuelve una cirugía mayor. Si los separás, cambiar de plataforma es cambiar adaptadores.

## Mapa mental del repo

```text
api/                    Entrada actual Vercel
cloudflare/             Entrada nueva Cloudflare
bot/                    Lógica del bot
bot/repositories/       Persistencia intercambiable
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

> “Cuando llega un update de Telegram, qué hacemos?”

No debería saber demasiado sobre Cloudflare ni Vercel. Solo recibe:

- `repository`
- `telegram`
- `admin_chat_id`
- providers de precios/noticias

Eso es inyección de dependencias. No es moda: es lo que permite testear y migrar.

### 3. Después entendé la base de datos

Archivos:

```text
bot/db.py
bot/repositories/
```

La idea:

```text
bot/db.py
 -> repository
 -> Supabase o D1
```

`bot/db.py` existe para no romper código viejo. Los repositories existen para no atar la app a una base concreta.

### 4. Recién después mirá Cloudflare

Archivo:

```text
cloudflare/worker.py
```

Este archivo es infraestructura. Si empezás por acá, vas a creer que el proyecto “es Cloudflare”. No. Cloudflare es solo el nuevo lugar donde corre.

El Worker debería ser aburrido:

- parsea request,
- crea adapters,
- llama servicios,
- devuelve response.

Si el Worker empieza a tener demasiada lógica, la arquitectura se está pudriendo.

## Flujo de `/prices`

```text
Telegram manda /prices
 -> runtime recibe webhook
 -> webhook_service detecta comando
 -> price_service formatea precios
 -> TelegramHttpClient envía respuesta
```

Lo importante: el formato de precios no vive en Cloudflare. Cloudflare solo provee un loader async.

## Flujo de noticias automáticas

```text
Cron cada 15 minutos
 -> cron_service busca noticias
 -> news_service puntúa RSS por keywords
 -> repository pregunta si ya fue enviada
 -> Telegram envía solo noticias nuevas
 -> repository marca hash como enviado
 -> repository actualiza bot_health
```

La tabla `sent_news` es el mecanismo anti-duplicados.

## Flujo de mercados

El comando `/mercados` no pregunta a una API externa. Calcula estado usando horarios de mercado y timezone.

La clave es que cada mercado se evalúa en su propia zona horaria:

- Tokio: `Asia/Tokyo`
- Europa: `Europe/Madrid`
- EE.UU.: `America/New_York`

Después se muestra en la zona horaria del usuario.

## Qué significa “serverless” acá

Serverless no significa “sin arquitectura”.

Significa:

- no administrás servidores,
- cada request debe ser independiente,
- no podés confiar en estado global mutable,
- los secretos viven en variables/secrets del proveedor,
- las tareas periódicas son triggers, no procesos vivos.

Por eso el diseño evita guardar estado en memoria y empuja todo lo importante a DB.

## Qué NO hacer

- No meter queries directas a D1 dentro de `webhook_service.py`.
- No llamar Supabase desde `command_service.py`.
- No duplicar comandos entre Vercel y Cloudflare.
- No mover Telegram webhook antes de validar Worker + D1.
- No convertir `cloudflare/worker.py` en “el nuevo monolito”.
- No borrar Supabase/Vercel hasta que el corte esté probado.

## Cómo cambiar algo sin romperlo

Usá este orden:

1. Encontrá el seam correcto.
2. Cambiá la pieza más chica posible.
3. Agregá o ajustá test.
4. Corré:

```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

5. Recién después seguí.

Ese orden importa. Si codeás primero y entendés después, vas a estar construyendo una casa moviendo paredes al azar.

## Qué mirar cuando algo falla

| Síntoma | Dónde mirar primero |
|---|---|
| Comando responde mal | `bot/command_service.py`, `bot/webhook_service.py` |
| No envía noticias | `bot/cron_service.py`, `bot/news_service.py`, `sent_news` |
| Duplicados de noticias | `is_news_sent`, `mark_news_sent`, tabla `sent_news` |
| Admin bloqueado | `ADMIN_CHAT_ID` |
| Stats rotas | `get_dashboard_stats`, `bot_health`, `command_log` |
| Cloudflare falla | `cloudflare/worker.py`, bindings/secrets en Wrangler |
| Vercel falla | `api/webhook.py`, `api/cron.py`, env vars Vercel |

## Cómo saber si entendiste el proyecto

Podés explicar estas tres frases sin mirar código:

1. “El runtime adapta; no decide negocio.”
2. “El repository persiste; no decide comandos.”
3. “Los servicios orquestan reglas; no saben si están en Vercel o Cloudflare.”

Si esas tres frases te hacen sentido, ya estás leyendo el proyecto como arquitecto, no como turista mirando archivos.

## Siguiente aprendizaje recomendado

Leé en este orden:

1. `bot/command_service.py`
2. `bot/webhook_service.py`
3. `bot/cron_service.py`
4. `bot/repositories/d1_binding_repository.py`
5. `cloudflare/worker.py`
6. `tests/test_webhook_service.py`
7. `tests/test_cron_service.py`

No es el orden de ejecución. Es el orden para entender.
