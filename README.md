# ðŸ¤– BNB Sentinel Bot (Serverless Edition)

Un bot financiero para Telegram que corre **100% gratis en la nube**. Monitorea precios de criptomonedas, aperturas de mercados globales con lÃ³gica de husos horarios (Market-Aware) y filtra noticias RSS de alto impacto.

## ðŸ— Arquitectura

El bot opera sobre infraestructura serverless de **Cloudflare**:

- **Cloudflare Workers (Compute):** Maneja los webhooks de Telegram y ejecuta el cron de noticias mediante un Scheduled Handler nativo.
- **Cloudflare D1 (SQLite):** Base de datos en el edge para persistir usuarios suscritos y mantener un cachÃ© de noticias ya enviadas, evitando duplicados.

> Para un entendimiento profundo de las capas y decisiones de diseÃ±o, consultÃ¡ [ARCHITECTURE.md](./ARCHITECTURE.md).

## ðŸš€ GuÃ­a de ConfiguraciÃ³n RÃ¡pida

### 1. Prerrequisitos

- [Node.js](https://nodejs.org/) (requerido por Wrangler)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/): `npm install -g wrangler`
- Cuenta gratuita en [Cloudflare](https://cloudflare.com/)

Autenticate con tu cuenta:

```bash
wrangler login
```

### 2. Crear la Base de Datos D1

```bash
wrangler d1 create bnb-sentinel-db
```

CopiÃ¡ el `database_id` que devuelve el comando y actualizalo en `wrangler.jsonc`.

Luego aplicÃ¡ el schema:

```bash
wrangler d1 execute bnb-sentinel-db --file=cloudflare/d1/schema.sql
```

### 3. Configurar Secrets

ConfigurÃ¡ las variables de entorno del Worker usando Wrangler:

```bash
wrangler secret put TELEGRAM_TOKEN
wrangler secret put ADMIN_CHAT_ID
```

### 4. Desplegar el Worker

```bash
wrangler deploy
```

Wrangler te darÃ¡ una URL pÃºblica (ej. `https://telegram-bot-news.<tu-subdominio>.workers.dev`).

### 5. Conectar Telegram (Webhook)

RegistrÃ¡ la URL del Worker como webhook de Telegram:

```text
https://api.telegram.org/bot<TU_TELEGRAM_TOKEN>/setWebhook?url=https://<TU_WORKER_URL>/api/webhook
```

Si todo estÃ¡ bien, verÃ¡s `"Webhook was set"` en la respuesta.

## â° Cron AutomÃ¡tico (Cada 15 min)

El Cron estÃ¡ configurado directamente en `wrangler.jsonc` como un **Scheduled Trigger nativo** de Cloudflare Workers â€” no requiere GitHub Actions ni servicios externos. Cloudflare ejecuta el handler `scheduled()` automÃ¡ticamente segÃºn el schedule definido.

Para verificar o ajustar la frecuencia, editÃ¡ la secciÃ³n `triggers` en `wrangler.jsonc`.

## ðŸ“‚ Estructura del Proyecto

```text
worker.py                   # Entrypoint: routing HTTP + scheduled cron
bot/
â”œâ”€â”€ webhook_service.py      # Orquesta los comandos de Telegram
â”œâ”€â”€ command_service.py      # LÃ³gica de cada comando (/prices, /mercados, etc.)
â”œâ”€â”€ cron_service.py         # Pipeline de bÃºsqueda y envÃ­o de noticias
â”œâ”€â”€ news_service.py         # Parsing y scoring de feeds RSS
â”œâ”€â”€ price_service.py        # Consulta de precios a Binance
â”œâ”€â”€ market_service.py       # LÃ³gica de horarios de mercados globales
â”œâ”€â”€ dashboard_html.py       # HTML del dashboard pÃºblico
â”œâ”€â”€ repositories/
â”‚   â””â”€â”€ d1_binding_repository.py  # Persistencia sobre Cloudflare D1
â”œâ”€â”€ utils/
â”‚   â””â”€â”€ rss_parser.py       # Parser RSS custom (sin dependencias)
â””â”€â”€ db.py                   # Fachada backward-compatible
cloudflare/
â””â”€â”€ d1/
    â””â”€â”€ schema.sql          # Schema SQLite para D1
public/
â””â”€â”€ index.html              # Dashboard pÃºblico de estadÃ­sticas
```

## ðŸš€ Notificaciones de Release

Hay un GitHub Action configurado para notificarte por Telegram cada vez que publiques un Release. Requiere dos Secrets en tu repositorio:

1. Ve a `Settings > Secrets and variables > Actions > New repository secret`.
2. Agrega `TELEGRAM_TOKEN` (tu token de BotFather).
3. Agrega `ADMIN_CHAT_ID` (tu ID de Telegram).

Si no los configurÃ¡s, el Action simplemente fallarÃ¡ sin afectar el funcionamiento del bot.

## ðŸ›  Comandos Disponibles

| Comando | DescripciÃ³n |
| --- | --- |
| `/start` | Suscribe al usuario a alertas automÃ¡ticas (o muestra su estado actual). |
| `/subscribe` | Activa las noticias automÃ¡ticas. |
| `/unsubscribe` | Desactiva las noticias automÃ¡ticas. |
| `/prices` | Precio actual de BTC, ETH y BNB. |
| `/mercados` | Bolsas mundiales abiertas en este momento (localizado a tu zona horaria). |
| `/timezone` | Configura tu zona horaria. |
| `/noticias` | Top 3 noticias de alto impacto bajo demanda. |

### ðŸ‘‘ Comandos de Administrador

> Requieren que tu Chat ID coincida con el secret `ADMIN_CHAT_ID` configurado en Wrangler.

| Comando | DescripciÃ³n |
| --- | --- |
| `/stats` | EstadÃ­sticas de usuarios (totales, suscritos, desuscritos). |
| `/broadcast <mensaje>` | Mensaje masivo a todos los usuarios. TambiÃ©n funciona respondiendo un mensaje con `/broadcast`. |
| `/ban <chat_id>` | Elimina un usuario de la base de datos. |

> **Nota:** Si `ADMIN_CHAT_ID` no estÃ¡ configurado como secret, el bot asumirÃ¡ el valor `0` y denegarÃ¡ el acceso a estos comandos.

## ðŸ”§ Debug Local

Para disparar el cron manualmente sin esperar el schedule:

```text
GET https://<TU_WORKER_URL>/api/debug-cron
GET https://<TU_WORKER_URL>/api/debug-cron?force=1   # ignora deduplicaciÃ³n
```

El endpoint `/api/stats` devuelve el estado actual del bot en JSON y alimenta el dashboard pÃºblico.
