# 🤖 BNB Sentinel Bot (Serverless Edition)

Un bot financiero para Telegram que corre **100% gratis en la nube**. Monitorea precios de criptomonedas, aperturas de mercados globales con lógica de husos horarios (Market-Aware) y filtra noticias RSS de alto impacto.

## 🏗 Arquitectura

El bot opera sobre infraestructura serverless de **Cloudflare**:

- **Cloudflare Workers (Compute):** Maneja los webhooks de Telegram y ejecuta el cron de noticias mediante un Scheduled Handler nativo.
- **Cloudflare D1 (SQLite):** Base de datos en el edge para persistir usuarios suscritos y mantener un caché de noticias ya enviadas, evitando duplicados.

> Para un entendimiento profundo de las capas y decisiones de diseño, consultá [ARCHITECTURE.md](./ARCHITECTURE.md).

## 🚀 Guía de Configuración Rápida

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

Copiá el `database_id` que devuelve el comando y actualizalo en `wrangler.jsonc`.

Luego aplicá el schema:

```bash
wrangler d1 execute bnb-sentinel-db --file=cloudflare/d1/schema.sql
```

### 3. Configurar Secrets

Configurá las variables de entorno del Worker usando Wrangler:

```bash
wrangler secret put TELEGRAM_TOKEN
wrangler secret put ADMIN_CHAT_ID
```

### 4. Desplegar el Worker

```bash
wrangler deploy
```

Wrangler te dará una URL pública (ej. `https://telegram-bot-news.<tu-subdominio>.workers.dev`).

### 5. Conectar Telegram (Webhook)

Registrá la URL del Worker como webhook de Telegram:

```text
https://api.telegram.org/bot<TU_TELEGRAM_TOKEN>/setWebhook?url=https://<TU_WORKER_URL>/api/webhook
```

Si todo está bien, verás `"Webhook was set"` en la respuesta.

## ⏰ Cron Automático (Cada 15 min)

El Cron está configurado directamente en `wrangler.jsonc` como un **Scheduled Trigger nativo** de Cloudflare Workers — no requiere GitHub Actions ni servicios externos. Cloudflare ejecuta el handler `scheduled()` automáticamente según el schedule definido.

Para verificar o ajustar la frecuencia, editá la sección `triggers` en `wrangler.jsonc`.

## 📂 Estructura del Proyecto

```text
worker.py                   # Entrypoint: routing HTTP + scheduled cron
bot/
├── webhook_service.py      # Orquesta los comandos de Telegram
├── command_service.py      # Lógica de cada comando (/prices, /mercados, etc.)
├── cron_service.py         # Pipeline de búsqueda y envío de noticias
├── news_service.py         # Parsing y scoring de feeds RSS
├── price_service.py        # Consulta de precios a Binance
├── market_service.py       # Lógica de horarios de mercados globales
├── dashboard_html.py       # HTML del dashboard público
├── repositories/
│   └── d1_binding_repository.py  # Persistencia sobre Cloudflare D1
├── utils/
│   └── rss_parser.py       # Parser RSS custom (sin dependencias)
└── db.py                   # Fachada backward-compatible
cloudflare/
└── d1/
    └── schema.sql          # Schema SQLite para D1
public/
└── index.html              # Dashboard público de estadísticas
```

## 🚀 Notificaciones de Release

Hay un GitHub Action configurado para notificarte por Telegram cada vez que publiques un Release. Requiere dos Secrets en tu repositorio:

1. Ve a `Settings > Secrets and variables > Actions > New repository secret`.
2. Agrega `TELEGRAM_TOKEN` (tu token de BotFather).
3. Agrega `ADMIN_CHAT_ID` (tu ID de Telegram).

Si no los configurás, el Action simplemente fallará sin afectar el funcionamiento del bot.

## 🛠 Comandos Disponibles

| Comando | Descripción |
| --- | --- |
| `/start` | Suscribe al usuario a alertas automáticas (o muestra su estado actual). |
| `/subscribe` | Activa las noticias automáticas. |
| `/unsubscribe` | Desactiva las noticias automáticas. |
| `/prices` | Precio actual de BTC, ETH y BNB. |
| `/mercados` | Bolsas mundiales abiertas en este momento (localizado a tu zona horaria). |
| `/timezone` | Configura tu zona horaria. |
| `/noticias` | Top 3 noticias de alto impacto bajo demanda. |

### 👑 Comandos de Administrador

> Requieren que tu Chat ID coincida con el secret `ADMIN_CHAT_ID` configurado en Wrangler.

| Comando | Descripción |
| --- | --- |
| `/stats` | Estadísticas de usuarios (totales, suscritos, desuscritos). |
| `/broadcast <mensaje>` | Mensaje masivo a todos los usuarios. También funciona respondiendo un mensaje con `/broadcast`. |
| `/ban <chat_id>` | Elimina un usuario de la base de datos. |

> **Nota:** Si `ADMIN_CHAT_ID` no está configurado como secret, el bot asumirá el valor `0` y denegará el acceso a estos comandos.

## 🔧 Debug Local

Para disparar el cron manualmente sin esperar el schedule:

```text
GET https://<TU_WORKER_URL>/api/debug-cron
GET https://<TU_WORKER_URL>/api/debug-cron?force=1   # ignora deduplicación
```

El endpoint `/api/stats` devuelve el estado actual del bot en JSON y alimenta el dashboard público.
